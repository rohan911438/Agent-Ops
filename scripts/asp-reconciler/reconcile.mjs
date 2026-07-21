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
//   2. Read the daemon's local job_provider_bindings table (what it thinks it has handled).
//   3. Any task with status "created" and no local binding is treated as missed and is
//      re-applied directly via `onchainos agent apply`, with exponential-backoff retry.
//   4. State is exposed on GET /health for external monitoring.

import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { createServer } from "node:http";
import {
  appendFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

const ASP_AGENT_ID = process.env.ASP_AGENT_ID || "6262";
const POLL_INTERVAL_MS = Number(process.env.RECONCILE_INTERVAL_MS || 30_000);
const HEALTH_PORT = Number(process.env.RECONCILE_HEALTH_PORT || 4790);
const SESSION_STORE_PATH =
  process.env.SESSION_STORE_PATH ||
  path.join(homedir(), ".okx-agent-task", "sqlite", "session-store.sqlite");
const RETRY_DELAYS_MS = [5_000, 15_000, 45_000]; // exponential backoff for a failed apply

const LOG_DIR = path.join(import.meta.dirname, "logs");
const LOG_FILE = path.join(LOG_DIR, "reconciler.log");
const HEALTH_FILE = path.join(LOG_DIR, "health.json");
const RECOVERED_JOBS_FILE = path.join(LOG_DIR, "recovered-jobs.json");
const LOCK_FILE = path.join(LOG_DIR, "reconciler.lock.json");
// Legacy bare-pid lock file from before the heartbeat-based lock. Only read once, to avoid
// treating a leftover file from the old format as a live instance on first upgrade.
const LEGACY_PID_LOCK_FILE = path.join(LOG_DIR, "reconciler.pid");
mkdirSync(LOG_DIR, { recursive: true });

// A lock is only honored while its holder is both (a) a live PID and (b) has heartbeated
// recently. (b) is what actually matters: a bare PID check can't tell "the reconciler is
// still running" from "some unrelated process now happens to hold this recycled PID" — which
// is exactly what happened in production (reconciler died, Windows recycled its PID to
// svchost.exe after a reboot, and every restart attempt refused to start because *a* process
// with that PID existed). Requiring a fresh heartbeat closes that gap regardless of PID reuse
// or reboots: a dead or hung process simply stops heartbeating, full stop.
const LOCK_STALE_MS = Number(process.env.RECONCILE_LOCK_STALE_MS || 5 * 60_000); // 5 min

function isProcessAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function readLock() {
  if (existsSync(LOCK_FILE)) {
    try {
      const data = JSON.parse(readFileSync(LOCK_FILE, "utf8"));
      if (data && typeof data.pid === "number" && typeof data.heartbeatAt === "string") {
        return data;
      }
    } catch {
      // Corrupt lock file — treat as absent/stale, safe to reclaim below.
    }
  }
  // One-time fallback for the pre-upgrade plain-pid lock file: treat it as maximally stale
  // (no heartbeat concept existed), so it never blocks a fresh start, and remove it so we
  // don't keep re-parsing it.
  if (existsSync(LEGACY_PID_LOCK_FILE)) {
    try {
      rmSync(LEGACY_PID_LOCK_FILE, { force: true });
    } catch {
      // best-effort cleanup
    }
  }
  return null;
}

function writeLock() {
  writeFileSync(
    LOCK_FILE,
    JSON.stringify({ pid: process.pid, startedAt: lockStartedAt, heartbeatAt: new Date().toISOString() }, null, 2),
    "utf8"
  );
}

// Called at the start of every blocking `onchainos` call (the actual event-loop-blocking
// work `spawnSync` does) and on an idle timer between ticks, so the heartbeat stays fresh
// both while busy and while sleeping between polls.
function touchLockHeartbeat() {
  if (!lockOwned) return;
  writeLock();
}

let lockStartedAt = null;
let lockOwned = false;

// Single-instance guard. Needed once this runs unattended under a scheduled task/supervisor
// loop, where a restart-on-crash wrapper and a manual `node reconcile.mjs` could otherwise
// both be alive at once and double-apply against the same jobs.
function acquireSingleInstanceLock() {
  const existing = readLock();
  if (existing) {
    const ageMs = Date.now() - new Date(existing.heartbeatAt).getTime();
    const stillAlive = isProcessAlive(existing.pid);
    if (stillAlive && ageMs < LOCK_STALE_MS) {
      console.error(
        `[reconciler] another instance is already running (pid=${existing.pid}, ` +
          `last heartbeat ${ageMs}ms ago); exiting.`
      );
      process.exit(1);
    }
    console.error(
      `[reconciler] reclaiming stale lock (pid=${existing.pid}, ` +
        `alive=${stillAlive}, lastHeartbeat=${existing.heartbeatAt}, ageMs=${ageMs}) — ` +
        `${stillAlive ? "PID is alive but heartbeat is stale (likely a recycled PID or a hung process), " : "PID is dead, "}` +
        `taking over.`
    );
  }
  lockStartedAt = new Date().toISOString();
  lockOwned = true;
  writeLock();
}
acquireSingleInstanceLock();

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
  lastMissingBindingJobs: [],
  lastRecoveryAttemptAt: null,
  lastRecoverySuccessAt: null,
  lastApplyTxHash: null,
  lastApplyJobId: null,
  walletGateOk: null,
  totalRecoveriesAttempted: 0,
  totalRecoveriesSucceeded: 0,
  totalRecoveriesFailed: 0,
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
  touchLockHeartbeat();
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

function getLocalBoundJobIds() {
  const db = new DatabaseSync(SESSION_STORE_PATH, { readOnly: true });
  try {
    const rows = db.prepare("SELECT job_id FROM job_provider_bindings").all();
    return new Set(rows.map((r) => r.job_id));
  } finally {
    db.close();
  }
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
    const boundJobIds = getLocalBoundJobIds();
    health.lastActiveTaskCount = activeTasks.length;

    const missing = activeTasks.filter(
      (t) => !boundJobIds.has(t.jobId) && !recoveredJobs.has(t.jobId)
    );
    health.lastMissingBindingJobs = missing.map((t) => ({
      jobId: t.jobId,
      title: t.title,
      counterpartyAgentId: t.counterpartyAgentId,
    }));

    log("info", "reconciliation tick", {
      activeTaskCount: activeTasks.length,
      boundCount: boundJobIds.size,
      missingCount: missing.length,
    });

    for (const task of missing) {
      log(
        "warn",
        "designated task has no local dispatch record — daemon likely missed job_asp_selected",
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

  await reconcileOnce();
  const interval = setInterval(reconcileOnce, POLL_INTERVAL_MS);
  // Keeps the heartbeat fresh during idle gaps between ticks (e.g. a slow-poll interval or a
  // sleep() backoff between apply retries) — separate from the per-call touch in
  // runOnchainos(), which covers the blocking-call case the timer can't fire during.
  const heartbeatTimer = setInterval(touchLockHeartbeat, Math.min(POLL_INTERVAL_MS, 30_000));

  const shutdown = () => {
    log("info", "reconciler shutting down");
    health.pollingActive = false;
    writeHealth();
    clearInterval(interval);
    clearInterval(heartbeatTimer);
    lockOwned = false;
    try {
      rmSync(LOCK_FILE, { force: true });
    } catch {
      // best-effort; a stale-and-unheartbeated lock is safely reclaimed on next start anyway
    }
    server.close(() => process.exit(0));
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((err) => {
  log("error", "fatal error, exiting", { error: String(err?.stack || err) });
  process.exit(1);
});
