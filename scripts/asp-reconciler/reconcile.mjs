#!/usr/bin/env node
// ASP designated-task reconciliation service.
//
// Root cause this exists for: the OKX A2A daemon (@okxweb3/a2a-node) can silently drop an
// inbound `job_asp_selected` event before it ever creates a `job_provider_bindings` row —
// with zero local log trace (verified against dist/cli.js's createFileMessageHandler /
// processFileMessage — see docs/ASP-6262-OKX-Daemon-Bug-Report.md). The daemon's own
// "offline replay" reuses the same code path, so it can never recover a message dropped
// this way. This script is an independent safety net: it trusts on-chain state over the
// daemon's local bookkeeping, and re-applies directly via `onchainos` when the two disagree.
//
// Every POLL_INTERVAL_MS:
//   1. Ask onchainos for this ASP's on-chain active tasks (ground truth).
//   2. Determine which of those tasks have a *confirmed* on-chain Apply — see
//      getConfirmedAppliedJobIds() below for why this is NOT the same question as "does the
//      daemon have a job_provider_bindings row for it."
//   3. Any task with status "created" and no confirmed Apply is treated as missed and is
//      re-applied directly via `onchainos agent apply`, with exponential-backoff retry.
//   4. State is exposed on GET /health for external monitoring.

import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { createServer } from "node:http";
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { createSingleInstanceLock } from "./lib/lock.mjs";

const ASP_AGENT_ID = process.env.ASP_AGENT_ID || "6262";
const POLL_INTERVAL_MS = Number(process.env.RECONCILE_INTERVAL_MS || 30_000);
const HEALTH_PORT = Number(process.env.RECONCILE_HEALTH_PORT || 4790);
const OKX_HOME = process.env.OKX_AGENT_TASK_HOME || path.join(homedir(), ".okx-agent-task");
const SESSION_STORE_PATH =
  process.env.SESSION_STORE_PATH || path.join(OKX_HOME, "sqlite", "session-store.sqlite");
const LISTENER_LOG = path.join(OKX_HOME, "logs", "listener.log");
const RETRY_DELAYS_MS = [5_000, 15_000, 45_000]; // exponential backoff for a failed apply

const LOG_DIR = path.join(import.meta.dirname, "logs");
const LOG_FILE = path.join(LOG_DIR, "reconciler.log");
const HEALTH_FILE = path.join(LOG_DIR, "health.json");
const RECOVERED_JOBS_FILE = path.join(LOG_DIR, "recovered-jobs.json");
mkdirSync(LOG_DIR, { recursive: true });

const lock = createSingleInstanceLock({
  lockFile: path.join(LOG_DIR, "reconciler.lock.json"),
  legacyPidFile: path.join(LOG_DIR, "reconciler.pid"),
  staleMs: Number(process.env.RECONCILE_LOCK_STALE_MS || 5 * 60_000), // 5 min
  label: "reconciler",
});
lock.acquire();

// Own idempotency record, independent of the daemon's job_provider_bindings table.
// A reconciler-driven `apply` does NOT create a daemon-side binding row (only the daemon's
// own dispatcher does that), so without this a recovered job would look "missing" again on
// every subsequent poll and get re-applied on-chain every cycle, forever.
function loadRecoveredJobs() {
  if (!existsSync(RECOVERED_JOBS_FILE)) return new Map();
  try {
    const entries = JSON.parse(readFileSync(RECOVERED_JOBS_FILE, "utf8"));
    return new Map(Object.entries(entries));
  } catch {
    return new Map();
  }
}
function saveRecoveredJobs(map) {
  writeFileSync(RECOVERED_JOBS_FILE, JSON.stringify(Object.fromEntries(map), null, 2), "utf8");
}
const recoveredJobs = loadRecoveredJobs();

const health = {
  startedAt: new Date().toISOString(),
  aspAgentId: ASP_AGENT_ID,
  pollIntervalMs: POLL_INTERVAL_MS,
  pollingActive: true,
  lastPollAt: null,
  lastPollOk: null,
  lastPollError: null,
  lastActiveTaskCount: null,
  lastMissingApplyJobs: [],
  lastRecoveryAttemptAt: null,
  lastRecoverySuccessAt: null,
  lastApplyTxHash: null,
  lastApplyJobId: null,
  walletGateOk: null,
  totalRecoveriesAttempted: 0,
  totalRecoveriesSucceeded: 0,
  totalRecoveriesFailed: 0,
  reconcileInFlight: false,
  currentCycleStartedAt: null,
  totalTicksSkippedOverlap: 0,
};

function log(level, message, extra) {
  const line = {
    ts: new Date().toISOString(),
    level,
    message,
    ...extra,
  };
  const text = JSON.stringify(line);
  appendFileSync(LOG_FILE, text + "\n", "utf8");
  // Mirror to stdout too, so `node reconcile.mjs` run interactively is readable live.
  // eslint-disable-next-line no-console
  console.log(`[${line.ts}] [${level}] ${message}`, extra ? JSON.stringify(extra) : "");
}

function writeHealth() {
  writeFileSync(HEALTH_FILE, JSON.stringify(health, null, 2), "utf8");
}

function runOnchainos(args, { timeoutMs = 30_000 } = {}) {
  // spawnSync blocks the event loop for the full duration of the call (we've observed single
  // calls take 2+ minutes), so a timer-only heartbeat can go stale mid-call even though the
  // process is legitimately busy, not dead. Touch right before blocking so the lock file
  // always reflects "still actively working" at the moment we start a long operation.
  lock.touch();
  const result = spawnSync("onchainos", args, {
    encoding: "utf8",
    timeout: timeoutMs,
    windowsHide: true,
  });
  if (result.error) {
    throw new Error(`onchainos ${args.join(" ")} failed to spawn: ${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(
      `onchainos ${args.join(" ")} exited ${result.status}: ${(result.stderr || result.stdout || "").trim()}`
    );
  }
  return result.stdout;
}

function parseJsonOutput(stdout, context) {
  try {
    return JSON.parse(stdout);
  } catch (err) {
    throw new Error(`${context}: could not parse JSON output (${err.message}): ${stdout.slice(0, 500)}`);
  }
}

function getActiveCreatedTasks() {
  const stdout = runOnchainos(["agent", "active-tasks", "--role", "asp"]);
  const parsed = parseJsonOutput(stdout, "active-tasks");
  const tasks = parsed?.data?.tasks ?? [];
  return tasks.filter(
    (t) => t.myRole === "asp" && t.myAgentId === ASP_AGENT_ID && t.statusCode === 0
  );
}

// Purely informational now — kept for the `boundCount` visibility in the tick log/health, NOT
// used to decide whether a job still needs an Apply. See getConfirmedAppliedJobIds() for why:
// the daemon writes this row the moment it *starts* dispatching a session, before that session
// has done anything — including the case where the session then hangs forever and never
// applies. Treating "a binding row exists" as "handled, don't touch again" is exactly the bug
// that let job 0xd75ab029…94ab9a2 sit un-applied: the daemon created the binding at 13:23:34,
// the spawned session then hung producing zero output, and — had this reconciler's "missing"
// filter still keyed off binding presence instead of confirmed Apply — it would have
// permanently ignored that job from the moment the binding appeared, even though no Apply was
// ever submitted from that path.
function getLocalBoundJobIds() {
  const db = new DatabaseSync(SESSION_STORE_PATH, { readOnly: true });
  try {
    const rows = db.prepare("SELECT job_id FROM job_provider_bindings").all();
    return new Set(rows.map((r) => r.job_id));
  } finally {
    db.close();
  }
}

// Ground truth for "has this job actually been applied to" — a `provider_applied` system
// event, which the OKX backend only sends after confirming the Apply on-chain, regardless of
// whether the Apply was submitted by the daemon's own dispatch path or by this reconciler
// calling `onchainos agent apply` directly. Unlike job_provider_bindings, this can't be
// "created" without an actual successful apply ever happening.
//
// The daemon truncates jobId in this log field to `<first 8 chars>…<last 6 chars>` (e.g.
// `0xd75ab0…4ab9a2` for `0xd75ab029...94ab9a2`) rather than logging it in full, so we build the
// same truncated fingerprint for each job we're actually asking about this cycle and match
// against that — restricting the match space to the small set of currently-active tasks makes
// an accidental fingerprint collision against some unrelated historical job a non-concern.
const PROVIDER_APPLIED_RE = /event=provider_applied\s+job=(\S+)/g;

function getConfirmedAppliedJobIds(activeTasks) {
  const confirmed = new Set();
  if (!existsSync(LISTENER_LOG)) return confirmed;
  let content;
  try {
    content = readFileSync(LISTENER_LOG, "utf8");
  } catch (err) {
    log("error", "failed to read listener.log for provider_applied confirmation", {
      error: String(err.message || err),
    });
    return confirmed;
  }
  const fingerprintToJobId = new Map(
    activeTasks.map((t) => [`${t.jobId.slice(0, 8)}…${t.jobId.slice(-6)}`, t.jobId])
  );
  for (const match of content.matchAll(PROVIDER_APPLIED_RE)) {
    const fullJobId = fingerprintToJobId.get(match[1]);
    if (fullJobId) confirmed.add(fullJobId);
  }
  return confirmed;
}

function checkWalletGate() {
  try {
    const stdout = runOnchainos(["agent", "gate-check", "--role", "asp"], { timeoutMs: 60_000 });
    const parsed = parseJsonOutput(stdout, "gate-check");
    return Boolean(parsed?.data?.ready);
  } catch (err) {
    log("error", "gate-check failed", { error: String(err.message || err) });
    return false;
  }
}

function extractTxHash(applyStdout) {
  const match = applyStdout.match(/txHash:\s*([0-9a-fA-Fx]+)/);
  return match ? match[1] : null;
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function applyWithRetry(task) {
  const attempts = RETRY_DELAYS_MS.length + 1;
  for (let attempt = 0; attempt < attempts; attempt++) {
    health.totalRecoveriesAttempted += 1;
    health.lastRecoveryAttemptAt = new Date().toISOString();
    writeHealth();
    log("info", "apply attempt started", {
      jobId: task.jobId,
      title: task.title,
      attempt: attempt + 1,
      of: attempts,
    });
    try {
      const stdout = runOnchainos([
        "agent",
        "apply",
        task.jobId,
        "--agent-id",
        ASP_AGENT_ID,
        "--token-amount",
        String(task.tokenAmount ?? "0"),
        "--token-symbol",
        String(task.tokenSymbol ?? "USDT"),
      ]);
      const txHash = extractTxHash(stdout);
      health.lastRecoverySuccessAt = new Date().toISOString();
      health.lastApplyTxHash = txHash;
      health.lastApplyJobId = task.jobId;
      health.totalRecoveriesSucceeded += 1;
      recoveredJobs.set(task.jobId, { txHash, appliedAt: new Date().toISOString() });
      saveRecoveredJobs(recoveredJobs);
      writeHealth();
      log("info", "apply succeeded", { jobId: task.jobId, txHash, rawOutput: stdout.trim() });
      return { ok: true, txHash };
    } catch (err) {
      log("error", "apply attempt failed", {
        jobId: task.jobId,
        attempt: attempt + 1,
        of: attempts,
        error: String(err.message || err),
      });
      if (attempt < attempts - 1) {
        const delay = RETRY_DELAYS_MS[attempt];
        log("warn", "retrying after backoff", { jobId: task.jobId, delayMs: delay });
        await sleep(delay);
      }
    }
  }
  health.totalRecoveriesFailed += 1;
  writeHealth();
  log("error", "apply exhausted all retries; giving up for this cycle", { jobId: task.jobId });
  return { ok: false };
}

async function reconcileOnce() {
  health.lastPollAt = new Date().toISOString();
  try {
    health.walletGateOk = checkWalletGate();

    const activeTasks = getActiveCreatedTasks();
    const boundJobIds = getLocalBoundJobIds(); // informational only — see comment on getLocalBoundJobIds
    const confirmedAppliedJobIds = getConfirmedAppliedJobIds(activeTasks);
    health.lastActiveTaskCount = activeTasks.length;

    const missing = activeTasks.filter(
      (t) => !confirmedAppliedJobIds.has(t.jobId) && !recoveredJobs.has(t.jobId)
    );
    health.lastMissingApplyJobs = missing.map((t) => ({
      jobId: t.jobId,
      title: t.title,
      counterpartyAgentId: t.counterpartyAgentId,
    }));

    log("info", "reconciliation tick", {
      activeTaskCount: activeTasks.length,
      boundCount: boundJobIds.size,
      confirmedAppliedCount: confirmedAppliedJobIds.size,
      missingCount: missing.length,
    });

    for (const task of missing) {
      log(
        "warn",
        "designated task has no confirmed on-chain Apply — daemon may have missed " +
          "job_asp_selected, or dispatched a session that never completed the apply",
        { jobId: task.jobId, title: task.title, counterpartyAgentId: task.counterpartyAgentId }
      );
      await applyWithRetry(task);
    }

    health.lastPollOk = true;
    health.lastPollError = null;
  } catch (err) {
    health.lastPollOk = false;
    health.lastPollError = String(err.message || err);
    log("error", "reconciliation tick failed", { error: String(err.message || err) });
  }
  writeHealth();
}

// Non-overlapping tick guard. `setInterval` fires on a fixed cadence regardless of whether
// the previous `reconcileOnce()` (including its serial `applyWithRetry` calls, which can
// block for minutes across backoff retries — or, as happened in production, for hours if the
// machine sleeps mid-retry) has finished. Without this guard, a slow/stuck cycle plus a
// resumed-from-sleep timer pile-up let two independent reconciliation cycles discover the
// same "missing" job and each submit their own on-chain Apply — a real duplicate-Apply
// incident, not a hypothetical one. This flag makes cycles strictly serial: at most one
// `reconcileOnce()` runs at a time, and a tick that fires while one is still in flight is
// skipped (and logged) rather than starting a second, overlapping cycle.
let reconcileInFlight = false;

async function runReconcileTick() {
  if (reconcileInFlight) {
    health.totalTicksSkippedOverlap += 1;
    log("warn", "reconciliation tick skipped — previous cycle still in progress", {
      currentCycleStartedAt: health.currentCycleStartedAt,
    });
    writeHealth();
    return;
  }
  reconcileInFlight = true;
  health.reconcileInFlight = true;
  health.currentCycleStartedAt = new Date().toISOString();
  writeHealth();
  try {
    await reconcileOnce();
  } finally {
    reconcileInFlight = false;
    health.reconcileInFlight = false;
    health.currentCycleStartedAt = null;
    writeHealth();
  }
}

function startHealthServer() {
  const server = createServer((req, res) => {
    if (req.url === "/health") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify(health, null, 2));
      return;
    }
    res.writeHead(404, { "content-type": "text/plain" });
    res.end("not found");
  });
  server.listen(HEALTH_PORT, () => {
    log("info", "health endpoint listening", { port: HEALTH_PORT, url: `http://localhost:${HEALTH_PORT}/health` });
  });
  return server;
}

async function main() {
  log("info", "reconciler starting", {
    aspAgentId: ASP_AGENT_ID,
    pollIntervalMs: POLL_INTERVAL_MS,
    sessionStorePath: SESSION_STORE_PATH,
  });
  const server = startHealthServer();

  await runReconcileTick();
  const interval = setInterval(runReconcileTick, POLL_INTERVAL_MS);
  // Keeps the heartbeat fresh during idle gaps between ticks (e.g. a slow-poll interval or a
  // sleep() backoff between apply retries) — separate from the per-call touch in
  // runOnchainos(), which covers the blocking-call case the timer can't fire during.
  const heartbeatTimer = setInterval(() => lock.touch(), Math.min(POLL_INTERVAL_MS, 30_000));

  const shutdown = () => {
    log("info", "reconciler shutting down");
    health.pollingActive = false;
    writeHealth();
    clearInterval(interval);
    clearInterval(heartbeatTimer);
    lock.release();
    server.close(() => process.exit(0));
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((err) => {
  log("error", "fatal error, exiting", { error: String(err?.stack || err) });
  process.exit(1);
});
