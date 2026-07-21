// Shared single-instance lock: lockfile + heartbeat, not a bare PID check.
//
// A bare "does a process with this PID exist" check is not sufficient: PIDs get recycled by
// the OS, especially right after a reboot. In production this caused a real outage — the
// reconciler died, Windows recycled its PID to an unrelated svchost.exe, and every restart
// attempt refused to start because *a* process happened to hold that PID number. Requiring a
// fresh heartbeat closes that gap regardless of PID reuse or reboots: a dead or hung process
// simply stops heartbeating, full stop.
//
// Used by both reconcile.mjs and session-watchdog.mjs so the fix (and any future fix) lives
// in one place.

import {
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";

function isProcessAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

/**
 * @param {object} opts
 * @param {string} opts.lockFile - path to the JSON lock file
 * @param {string} [opts.legacyPidFile] - optional pre-upgrade bare-pid lock file to migrate away from
 * @param {number} [opts.staleMs] - how old a heartbeat may be before the lock is considered abandoned
 * @param {string} [opts.label] - name used in log/console messages (e.g. "reconciler", "session-watchdog")
 */
export function createSingleInstanceLock({ lockFile, legacyPidFile, staleMs = 5 * 60_000, label = "process" }) {
  mkdirSync(path.dirname(lockFile), { recursive: true });
  let owned = false;
  let startedAt = null;

  function readLock() {
    if (existsSync(lockFile)) {
      try {
        const data = JSON.parse(readFileSync(lockFile, "utf8"));
        if (data && typeof data.pid === "number" && typeof data.heartbeatAt === "string") {
          return data;
        }
      } catch {
        // Corrupt lock file — treat as absent/stale, safe to reclaim below.
      }
    }
    // One-time fallback for a pre-upgrade plain-pid lock file: treat it as maximally stale
    // (no heartbeat concept existed), so it never blocks a fresh start, and remove it so we
    // don't keep re-parsing it.
    if (legacyPidFile && existsSync(legacyPidFile)) {
      try {
        rmSync(legacyPidFile, { force: true });
      } catch {
        // best-effort cleanup
      }
    }
    return null;
  }

  function writeLock() {
    writeFileSync(
      lockFile,
      JSON.stringify({ pid: process.pid, startedAt, heartbeatAt: new Date().toISOString() }, null, 2),
      "utf8"
    );
  }

  /** Touch the heartbeat. Call this both on an idle timer AND immediately before any
   * event-loop-blocking work (e.g. spawnSync), since a timer can't fire while the loop is
   * blocked but a call made just before blocking still gets the timestamp fresh. */
  function touch() {
    if (!owned) return;
    writeLock();
  }

  /** Acquire the lock or exit(1) if another instance genuinely holds it. */
  function acquire() {
    const existing = readLock();
    if (existing) {
      const ageMs = Date.now() - new Date(existing.heartbeatAt).getTime();
      const stillAlive = isProcessAlive(existing.pid);
      if (stillAlive && ageMs < staleMs) {
        console.error(
          `[${label}] another instance is already running (pid=${existing.pid}, ` +
            `last heartbeat ${ageMs}ms ago); exiting.`
        );
        process.exit(1);
      }
      console.error(
        `[${label}] reclaiming stale lock (pid=${existing.pid}, alive=${stillAlive}, ` +
          `lastHeartbeat=${existing.heartbeatAt}, ageMs=${ageMs}) — ` +
          `${stillAlive ? "PID is alive but heartbeat is stale (likely a recycled PID or a hung process), " : "PID is dead, "}` +
          `taking over.`
      );
    }
    startedAt = new Date().toISOString();
    owned = true;
    writeLock();
    return { startedAt };
  }

  function release() {
    owned = false;
    try {
      rmSync(lockFile, { force: true });
    } catch {
      // best-effort; a stale-and-unheartbeated lock is safely reclaimed on next start anyway
    }
  }

  return { acquire, touch, release };
}
