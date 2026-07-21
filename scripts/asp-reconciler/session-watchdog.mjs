#!/usr/bin/env node
// OKX A2A daemon AI-session watchdog.
//
// Root cause this exists for: the daemon dispatches each inbound message to a spawned AI
// session fire-and-forget (`void Promise.resolve(deps.onSessionMessage?.({...})).then(...)`,
// per dist/cli.js — see docs/ASP-6262-OKX-Daemon-Bug-Report.md) with no completion
// confirmation and no timeout. In production this let a spawned session (pid 4856, job
// 0xd75ab0…4ab9a2) sit alive for 3+ hours producing zero bytes of output and never
// completing, with no error, no timeout, and no log line from the daemon — silently
// blocking that designated task's on-chain Apply until an unrelated safety net (the
// reconciler) happened to catch it hours later.
//
// This script is an independent watchdog, not a patch to the vendored package (there's no
// upstream repo to patch — see the bug report). Every POLL_INTERVAL_MS:
//   1. Tail new "AI session start" / "AI session done" lines out of the daemon's listener.log
//      (incrementally, via a persisted byte-offset cursor) to track which sessions are
//      currently active: {messageKey, pid, logFile, firstSeenAt}.
//   2. For each active session, check its own per-session log file for growth (progress) and
//      its total age.
//   3. Terminate (and clearly log why) any session that either exceeds SESSION_MAX_LIFETIME_MS
//      outright, or has produced no new output for SESSION_STALL_GRACE_MS.
//   4. State is exposed on GET /health for external monitoring.

import { createServer } from "node:http";
import {
  appendFileSync,
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readSync,
  statSync,
  writeFileSync,
  readFileSync,
} from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { createSingleInstanceLock } from "./lib/lock.mjs";

const POLL_INTERVAL_MS = Number(process.env.WATCHDOG_POLL_INTERVAL_MS || 60_000);
const HEALTH_PORT = Number(process.env.WATCHDOG_HEALTH_PORT || 4791);
// Configurable timeouts (this is the "configurable timeout for spawned AI sessions" requirement).
// Defaults are generous relative to every normal session duration we've observed in
// listener.log (~150-165s) but far tighter than the multi-hour hang that motivated this.
const SESSION_STALL_GRACE_MS = Number(process.env.SESSION_STALL_GRACE_MS || 3 * 60_000); // 3 min with zero output growth
const SESSION_MAX_LIFETIME_MS = Number(process.env.SESSION_MAX_LIFETIME_MS || 15 * 60_000); // 15 min hard cap regardless of growth

const OKX_HOME = process.env.OKX_AGENT_TASK_HOME || path.join(homedir(), ".okx-agent-task");
const LISTENER_LOG = path.join(OKX_HOME, "logs", "listener.log");

const LOG_DIR = path.join(import.meta.dirname, "logs");
const LOG_FILE = path.join(LOG_DIR, "watchdog.log");
const HEALTH_FILE = path.join(LOG_DIR, "watchdog-health.json");
const STATE_FILE = path.join(LOG_DIR, "watchdog-state.json");
const TERMINATED_FILE = path.join(LOG_DIR, "watchdog-terminated-sessions.json");
mkdirSync(LOG_DIR, { recursive: true });

const lock = createSingleInstanceLock({
  lockFile: path.join(LOG_DIR, "watchdog.lock.json"),
  staleMs: Number(process.env.WATCHDOG_LOCK_STALE_MS || 5 * 60_000),
  label: "session-watchdog",
});
lock.acquire();

function log(level, message, extra) {
  const line = { ts: new Date().toISOString(), level, message, ...extra };
  appendFileSync(LOG_FILE, JSON.stringify(line) + "\n", "utf8");
  // eslint-disable-next-line no-console
  console.log(`[${line.ts}] [${level}] ${message}`, extra ? JSON.stringify(extra) : "");
}

// --- persisted state: byte cursor into listener.log + currently-tracked active sessions ---
function loadState() {
  if (!existsSync(STATE_FILE)) return null;
  try {
    return JSON.parse(readFileSync(STATE_FILE, "utf8"));
  } catch {
    return null;
  }
}
function saveState(state) {
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf8");
}
function loadTerminatedHistory() {
  if (!existsSync(TERMINATED_FILE)) return {};
  try {
    return JSON.parse(readFileSync(TERMINATED_FILE, "utf8"));
  } catch {
    return {};
  }
}
function saveTerminatedHistory(map) {
  writeFileSync(TERMINATED_FILE, JSON.stringify(map, null, 2), "utf8");
}

let state = loadState();
if (!state) {
  // First run: skip pre-existing history in listener.log (which can span days) and start
  // tracking from the current end of file, so we only ever act on sessions that start after
  // the watchdog comes online.
  const size = existsSync(LISTENER_LOG) ? statSync(LISTENER_LOG).size : 0;
  state = { cursorOffset: size, activeSessions: {} };
  log("info", "first run — starting cursor at current end of listener.log", { cursorOffset: size });
}
const terminatedHistory = loadTerminatedHistory();

const health = {
  startedAt: new Date().toISOString(),
  pollingActive: true,
  sessionStallGraceMs: SESSION_STALL_GRACE_MS,
  sessionMaxLifetimeMs: SESSION_MAX_LIFETIME_MS,
  lastPollAt: null,
  lastPollOk: null,
  lastPollError: null,
  activeSessionsCount: 0,
  totalSessionsSeen: 0,
  totalSessionsCompletedNormally: 0,
  totalSessionsTerminatedByWatchdog: 0,
  lastTerminatedSession: null,
  watchdogInFlight: false,
  totalTicksSkippedOverlap: 0,
};
function writeHealth() {
  writeFileSync(HEALTH_FILE, JSON.stringify(health, null, 2), "utf8");
}

function isProcessAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

// Reads only the bytes appended to listener.log since the last poll (cheap even on a
// multi-hundred-KB, continuously-growing log — we never re-read from the start).
function readNewLogLines() {
  if (!existsSync(LISTENER_LOG)) return [];
  const size = statSync(LISTENER_LOG).size;
  if (size < state.cursorOffset) {
    // Log was rotated/truncated out from under us — restart from the top.
    log("warn", "listener.log shrank since last poll (rotated?) — resetting cursor to 0", {
      previousCursor: state.cursorOffset,
      newSize: size,
    });
    state.cursorOffset = 0;
  }
  if (size === state.cursorOffset) return [];
  const length = size - state.cursorOffset;
  const buf = Buffer.alloc(length);
  const fd = openSync(LISTENER_LOG, "r");
  try {
    readSync(fd, buf, 0, length, state.cursorOffset);
  } finally {
    closeSync(fd);
  }
  state.cursorOffset = size;
  return buf.toString("utf8").split("\n").filter(Boolean);
}

// Lines look like:
//   [21/07/2026, 13:24:05.261] [okx-agent-task] AI session start ... message=5833dce3…0fddc9 provider=claude
//     mode=new pid=4856 ... log=C:\...\ai-session-....log
//   [21/07/2026, 16:52:19.400] [okx-agent-task] AI session done ... message=5833dce3…0fddc9 ... exitCode=0 ...
// The daemon truncates jobId/messageId in most human-readable fields but always writes the
// full, untruncated pair in the `message=` field consistently across both lines for the same
// session, so it's a reliable (if unusually-shaped) correlation key — no need to depend on the
// (inconsistently truncated) `session=` field.
const START_RE = /AI session start\b.*?\bmessage=(\S+)\b.*?\bpid=(\d+)\b.*?\blog=(\S+)\s*$/;
const DONE_RE = /AI session done\b.*?\bmessage=(\S+)\b.*?\bexitCode=(\S+)\b/;

function ingestNewLines(lines) {
  for (const line of lines) {
    const startMatch = line.match(START_RE);
    if (startMatch) {
      const [, messageKey, pidStr, logFile] = startMatch;
      if (terminatedHistory[messageKey]) continue; // already handled in a prior watchdog run
      state.activeSessions[messageKey] = {
        pid: Number(pidStr),
        logFile,
        firstSeenAt: new Date().toISOString(),
        lastLogSizeBytes: 0,
        lastGrowthAt: new Date().toISOString(),
      };
      health.totalSessionsSeen += 1;
      log("info", "tracking new AI session", { messageKey, pid: Number(pidStr), logFile });
      continue;
    }
    const doneMatch = line.match(DONE_RE);
    if (doneMatch) {
      const [, messageKey, exitCode] = doneMatch;
      if (state.activeSessions[messageKey]) {
        delete state.activeSessions[messageKey];
        health.totalSessionsCompletedNormally += 1;
        log("info", "AI session completed normally, stopped tracking", { messageKey, exitCode });
      }
    }
  }
}

function checkAndEnforceTimeouts() {
  const now = Date.now();
  for (const [messageKey, session] of Object.entries(state.activeSessions)) {
    const alive = isProcessAlive(session.pid);
    if (!alive) {
      // Process is gone but we never saw an "AI session done" line for it (e.g. it crashed,
      // or was killed outside the watchdog). Nothing to terminate — just stop tracking it.
      log("info", "session process no longer running (no 'AI session done' seen) — untracking", {
        messageKey,
        pid: session.pid,
      });
      delete state.activeSessions[messageKey];
      continue;
    }

    const ageMs = now - new Date(session.firstSeenAt).getTime();
    let currentLogSize = session.lastLogSizeBytes;
    try {
      currentLogSize = existsSync(session.logFile) ? statSync(session.logFile).size : 0;
    } catch {
      // best-effort — treat as no change
    }
    const grew = currentLogSize > session.lastLogSizeBytes;
    if (grew) {
      session.lastLogSizeBytes = currentLogSize;
      session.lastGrowthAt = new Date().toISOString();
    }
    const stalledMs = now - new Date(session.lastGrowthAt).getTime();

    let reason = null;
    if (ageMs > SESSION_MAX_LIFETIME_MS) {
      reason = `exceeded max lifetime (${ageMs}ms > ${SESSION_MAX_LIFETIME_MS}ms), regardless of output`;
    } else if (stalledMs > SESSION_STALL_GRACE_MS) {
      reason = `no output growth for ${stalledMs}ms (grace period ${SESSION_STALL_GRACE_MS}ms) — session log stuck at ${currentLogSize} bytes`;
    }

    if (reason) {
      terminateHungSession(messageKey, session, { ageMs, currentLogSize, reason });
    }
  }
}

function terminateHungSession(messageKey, session, { ageMs, currentLogSize, reason }) {
  log("warn", "terminating hung AI session", {
    messageKey,
    pid: session.pid,
    logFile: session.logFile,
    ageMs,
    currentLogSizeBytes: currentLogSize,
    reason,
  });
  let killOk = true;
  let killError = null;
  try {
    process.kill(session.pid); // no signal semantics on Windows — this is a hard terminate
  } catch (err) {
    killOk = false;
    killError = String(err.message || err);
  }
  const record = {
    messageKey,
    pid: session.pid,
    logFile: session.logFile,
    firstSeenAt: session.firstSeenAt,
    terminatedAt: new Date().toISOString(),
    ageMsAtTermination: ageMs,
    logSizeBytesAtTermination: currentLogSize,
    reason,
    killOk,
    killError,
  };
  terminatedHistory[messageKey] = record;
  saveTerminatedHistory(terminatedHistory);
  delete state.activeSessions[messageKey];
  health.totalSessionsTerminatedByWatchdog += 1;
  health.lastTerminatedSession = record;
  log(killOk ? "warn" : "error", killOk ? "hung session terminated" : "failed to terminate hung session", record);
}

// Same non-overlapping-tick guard as reconcile.mjs, and for the same reason: a slow poll (or
// a machine sleep mid-poll) must not let a second poll start concurrently and double-act on
// the same session.
let inFlight = false;

async function pollOnce() {
  health.lastPollAt = new Date().toISOString();
  try {
    const newLines = readNewLogLines();
    ingestNewLines(newLines);
    checkAndEnforceTimeouts();
    health.activeSessionsCount = Object.keys(state.activeSessions).length;
    saveState(state);
    log("info", "watchdog tick", {
      newLines: newLines.length,
      activeSessionsCount: health.activeSessionsCount,
    });
    health.lastPollOk = true;
    health.lastPollError = null;
  } catch (err) {
    health.lastPollOk = false;
    health.lastPollError = String(err.message || err);
    log("error", "watchdog tick failed", { error: String(err.message || err) });
  }
  writeHealth();
}

async function runTick() {
  if (inFlight) {
    health.totalTicksSkippedOverlap += 1;
    log("warn", "watchdog tick skipped — previous tick still in progress");
    writeHealth();
    return;
  }
  inFlight = true;
  health.watchdogInFlight = true;
  try {
    await pollOnce();
  } finally {
    inFlight = false;
    health.watchdogInFlight = false;
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
  log("info", "session watchdog starting", {
    pollIntervalMs: POLL_INTERVAL_MS,
    sessionStallGraceMs: SESSION_STALL_GRACE_MS,
    sessionMaxLifetimeMs: SESSION_MAX_LIFETIME_MS,
    listenerLog: LISTENER_LOG,
    resumedActiveSessions: Object.keys(state.activeSessions).length,
  });
  const server = startHealthServer();

  await runTick();
  const interval = setInterval(runTick, POLL_INTERVAL_MS);
  const heartbeatTimer = setInterval(() => lock.touch(), Math.min(POLL_INTERVAL_MS, 30_000));

  const shutdown = () => {
    log("info", "session watchdog shutting down");
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
