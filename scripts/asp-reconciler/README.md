# ASP Designated-Task Reconciler + Session Watchdog

Independent safety net for ASP #6262 against a confirmed daemon-side bug: the OKX A2A
daemon (`@okxweb3/a2a-node`) can receive a `job_asp_selected` event, store it at the XMTP
transport layer, and then silently drop it before ever dispatching a session — with zero
local log trace. See `docs/ASP-6262-OKX-Daemon-Bug-Report.md` for the full root-cause
writeup (exact file/line citations in the installed daemon package).

This does not patch the daemon (its source isn't ours to durably fix). Instead it trusts
on-chain state over the daemon's own bookkeeping and re-applies directly when they disagree.

## What it does, every 30 seconds (default)

1. `onchainos agent active-tasks --role asp` — ground truth: which designated tasks are
   currently assigned to this ASP and still in `created` status.
2. Determines which of those tasks have a **confirmed on-chain Apply** by scanning the
   daemon's `listener.log` for a `provider_applied` system event per job — see "Ground truth:
   confirmed Apply, not binding presence" below.
3. Any task present in (1) with no confirmed Apply in (2) is treated as missed and is
   re-applied directly via `onchainos agent apply <jobId> --agent-id 6262 --token-amount
   <amt> --token-symbol <sym>`, with exponential backoff (5s / 15s / 45s) on failure.
4. State is exposed on `GET http://localhost:4790/health` and logged to
   `scripts/asp-reconciler/logs/reconciler.log` (JSON lines: task detected, apply
   started/succeeded/failed, tx hash, retry attempts).

## Ground truth: confirmed Apply, not binding presence (fixed 2026-07-21)

Originally step (2) read the daemon's own `job_provider_bindings` table in
`~/.okx-agent-task/sqlite/session-store.sqlite` — "did the daemon dispatch a session for
this job" — and treated a binding row as proof the job was handled. That's wrong: the daemon
writes that row the moment it *starts* dispatching a session, before the session has done
anything. This is precisely what let job `0xd75ab029…94ab9a2` go un-applied: the daemon
created the binding at 13:23:34, the spawned session then hung producing zero output for
hours, and a binding-based reconciler would have permanently ignored that job from the
moment the binding appeared — never noticing no Apply was ever actually submitted.

Fixed by switching the "already handled" check to `getConfirmedAppliedJobIds()`
(`reconcile.mjs`): it scans `listener.log` for `event=provider_applied job=<fingerprint>`
lines — a system event the OKX backend only sends after confirming the Apply on-chain,
regardless of whether the Apply came from the daemon's own dispatch or from this reconciler
calling `apply` directly. `job_provider_bindings` is still read and logged (`boundCount` in
`/health`) for visibility, but no longer gates the retry decision.

Reproduced the exact bug and confirmed the fix closes it: seeded a fake binding row for a
job with no `provider_applied` event anywhere in a test `listener.log` — the old
binding-based filter treated it as handled (`missing: []`, bug reproduced); the new
confirmed-apply filter correctly flagged it as still needing an apply (`missing:
[thatJobId]`, bug fixed). Also verified against the real `listener.log`: all 5 currently
known jobs (including `0xd75ab029…94ab9a2` and the original `0xa6139e…c6aee7` incident) are
correctly recognized as confirmed-applied (`confirmedAppliedCount: 5` in a live tick), and a
synthetic never-applied job is correctly recognized as not confirmed.

**Residual caveat:** this depends on `provider_applied` staying in `listener.log` — if that
log is ever rotated/truncated far enough to drop an old confirmation line, a
long-since-applied job could look "missing" again and get a harmless-but-wasteful duplicate
apply attempt (this is a false positive on "needs retry," not a repeat of the original
failure mode — the original bug was silently *never* retrying, which is strictly worse).
`listener.log` has not shown any rotation behavior in practice (one continuously-growing
file since at least 2026-07-17). Not fixed further given that; worth revisiting if rotation
is ever observed.

Requires `onchainos` on `PATH` and to be logged in (same account the daemon uses). One
instance enforced via a lockfile + heartbeat (`logs/reconciler.lock.json`, implemented in
`lib/lock.mjs`, shared with the session watchdog below) — a second `node reconcile.mjs`
started while one is already running exits immediately rather than double-applying. The lock
is only honored while its holder's PID is alive *and* it heartbeated within the last
`RECONCILE_LOCK_STALE_MS` (default 5 min); a dead process or a stale heartbeat is reclaimed
automatically, so a stuck instance or a reboot that recycles the old PID to an unrelated
process can't wedge the lock permanently (this happened once with the old bare-PID-only lock
— see git history).

**Non-overlapping cycles.** A second, independent bug (found in production on 2026-07-21):
`setInterval` fired every `RECONCILE_INTERVAL_MS` regardless of whether the previous
`reconcileOnce()` — including its serial `applyWithRetry` calls, which can block for minutes
across backoff retries, or for *hours* if the machine sleeps mid-retry — had finished. A
sleep/resume mid-retry let two overlapping cycles both discover the same missing job and
each submit their own on-chain Apply (two tx hashes, ~14s apart, for job
`0xd75ab029…94ab9a2`). Fixed with an in-flight mutex (`runReconcileTick` in `reconcile.mjs`):
at most one `reconcileOnce()` runs at a time; a tick that fires while one is still in
progress is skipped and logged (`totalTicksSkippedOverlap` in `/health`) rather than starting
a second cycle. Verified with an isolated harness that drives the identical guard pattern
with a cycle deliberately slower than the tick interval — see conversation history for the
test; not checked into the repo since it tests the pattern, not this module directly.

## Session watchdog (`session-watchdog.mjs`)

Separate, independent problem from the above: the daemon dispatches each inbound message to
a spawned AI session fire-and-forget, with no completion confirmation and no timeout (see
the bug report). In production this let a spawned session (pid 4856, job
`0xd75ab029…94ab9a2`) sit alive for 3+ hours producing zero bytes of output, with no error,
no timeout, and no daemon-side log line — silently blocking that task's Apply.

Every `WATCHDOG_POLL_INTERVAL_MS` (default 60s):
1. Tails new `AI session start` / `AI session done` lines out of
   `~/.okx-agent-task/logs/listener.log` incrementally (persisted byte-offset cursor in
   `logs/watchdog-state.json`), tracking active sessions by their `message=` fingerprint (the
   one field the daemon logs consistently, untruncated, across both lines — `session=` is
   truncated inconsistently and isn't reliable for correlation).
2. For each active session, checks its own per-session log file for growth and total age.
3. Terminates (`process.kill(pid)` — Windows has no SIGTERM, this is a hard kill) and clearly
   logs why, any session that either exceeds `SESSION_MAX_LIFETIME_MS` (default 15 min)
   outright, or has produced zero new output for `SESSION_STALL_GRACE_MS` (default 3 min).
   Both are generous relative to every normal session duration observed in production
   (~150-165s) and far tighter than the multi-hour hang that motivated this.
4. Records every termination in `logs/watchdog-terminated-sessions.json` (keyed by the
   `message=` fingerprint) so a session is never acted on twice, even across a watchdog
   restart.

Uses the same lock+heartbeat single-instance guard and the same non-overlapping-tick mutex as
the reconciler, for the same reasons.

Killing the hung process does **not**, by itself, make the daemon retry that job — from the
daemon's perspective, dispatch already happened (it's fire-and-forget) — so recovery for that
specific job still depends on the reconciler above. What the watchdog buys you: the stuck
process stops consuming resources, and — because sessions run as independent child processes
per job — a hung session for one job does not block the daemon from dispatching a *different*
job's session; killing it doesn't change that, it just stops one already-broken thing from
running forever.

**Known gap, not yet fixed:** the reconciler currently treats "a `job_provider_bindings` row
exists" as "handled, don't touch again" — but a session that hangs (this watchdog's whole
reason for existing) still gets a binding row created *before* it hangs (the daemon writes
that row immediately on receipt, before dispatch). If the daemon's binding write happens to
land before the reconciler's on-chain poll notices the job (a timing race — it went the other
way, by luck, for job `0xd75ab029…94ab9a2`), the reconciler will permanently consider that job
handled even though the session watchdog later has to kill it with no Apply ever submitted.
Closing this needs the reconciler to verify actual on-chain application state, not just
binding-row presence — currently blocked on the same `onchainos agent status` JWT issue noted
above.

Verified (see conversation history for the live test transcript): a synthetic hung session
(real disposable process, zero-growth log file) was detected and killed within one stall-
grace window, with a clean log line stating why; a synthetic healthy session (real output,
followed by a matching `AI session done`) was left running untouched. Also currently deployed
against the real daemon and its real `listener.log`.

## Production setup (installed and verified on this machine)

Mirrors the OKX A2A daemon's own autostart pattern: a Windows Scheduled Task, named
**`ASP-6262-Reconciler`**, runs at user logon and launches `run-supervised.bat` via
`launch-hidden.vbs` (no visible console window, like `okx-a2a daemon autostart`'s own
`launch-okx-a2a-daemon.vbs`). The batch file is a restart-on-crash loop: if `node
reconcile.mjs` ever exits (crash, killed, `npm` update to Node, anything), it's relaunched
after a 5s pause — verified by force-killing the process mid-session and confirming the
supervisor brought it back and polling resumed within seconds.

Verified after install:
- `schtasks /Query /TN "ASP-6262-Reconciler"` shows the task, `Status: Ready`.
- `schtasks /Run /TN "ASP-6262-Reconciler"` launched it successfully.
- `http://localhost:4790/health` responded immediately after launch.
- Killing the node process directly: supervisor restarted it within 5s, health resumed,
  `boundCount`/`missingCount` unchanged (no false re-apply from the restart itself).
- A second manually-started `node reconcile.mjs` exits immediately: `another instance is
  already running (pid=...); exiting.`

### Start manually (foreground, for debugging)

```bash
node scripts/asp-reconciler/reconcile.mjs
```

Environment overrides: `ASP_AGENT_ID`, `RECONCILE_INTERVAL_MS`, `RECONCILE_HEALTH_PORT`,
`SESSION_STORE_PATH`.

### Start the installed scheduled task now (without waiting for next logon)

```powershell
schtasks /Run /TN "ASP-6262-Reconciler"
```

### Stop

```powershell
schtasks /End /TN "ASP-6262-Reconciler"
```
This kills the supervisor batch process. If the `node` child is still running under it,
also stop it directly (find the pid in `logs/reconciler.lock.json`) — the supervisor loop
only restarts `node`, it doesn't independently respawn itself once `/End`ed.

## Session watchdog production setup

Same pattern (`run-watchdog-supervised.bat` via `launch-watchdog-hidden.vbs`), **but its
Scheduled Task registration is not yet installed**: creating a logon-triggered (`ONLOGON`)
task requires an elevated shell, and the session this was built in was not elevated (a
one-time `ONCE`-triggered task creates fine from the same shell — it's specifically
`ONLOGON`/`ONSTART` triggers that Task Scheduler gates behind elevation here). The watchdog
is running right now (started directly via the same hidden-launcher `wscript.exe` the
Scheduled Task would use, restart-on-crash supervisor active), but that won't survive a
reboot until the task is registered. To finish installing it, run **once**, from an elevated
("Run as Administrator") PowerShell:

```powershell
schtasks /Create /TN "ASP-6262-SessionWatchdog" /TR "wscript.exe C:\Users\dell\Desktop\AGENTO~1\scripts\ASP-RE~1\launch-watchdog-hidden.vbs" /SC ONLOGON /F
```

Verified (non-persistent instance, this session): started via `Start-Process wscript.exe
launch-watchdog-hidden.vbs`, ticking against the real `listener.log`, health endpoint at
`http://localhost:4791/health`; killing the node process directly, supervisor restarted it
within 5s and it correctly reclaimed the now-dead lock rather than refusing to start.

### Start manually (foreground, for debugging)

```bash
node scripts/asp-reconciler/session-watchdog.mjs
```

Environment overrides: `WATCHDOG_POLL_INTERVAL_MS`, `SESSION_STALL_GRACE_MS`,
`SESSION_MAX_LIFETIME_MS`, `WATCHDOG_HEALTH_PORT`, `WATCHDOG_LOCK_STALE_MS`,
`OKX_AGENT_TASK_HOME` (points at a different `~/.okx-agent-task`-shaped directory; used for
isolated testing so a test run never touches the real daemon's logs).

### Stop

```powershell
schtasks /End /TN "ASP-6262-SessionWatchdog"
```
(or, until the task is installed: find and kill the `node session-watchdog.mjs` pid directly
— check `logs/watchdog.lock.json`.)

### View logs

- `logs/watchdog.log` — structured JSON lines: every tick, every session tracked/untracked,
  every termination and why.
- `logs/watchdog-supervisor.log` — batch-loop restarts.
- `logs/watchdog-health.json` — current snapshot, same content as `/health`.
- `logs/watchdog-terminated-sessions.json` — permanent record of every session this watchdog
  has ever killed, so a restart never re-acts on (or re-kills a recycled-PID process in place
  of) one it already handled.

### View logs

- `scripts/asp-reconciler/logs/reconciler.log` — structured JSON lines: every poll tick,
  every apply attempt/success/failure, every retry.
- `scripts/asp-reconciler/logs/supervisor.log` — batch-loop restarts (when/why the node
  process was relaunched).
- `scripts/asp-reconciler/logs/health.json` — current snapshot, same content as `/health`.
- `scripts/asp-reconciler/logs/recovered-jobs.json` — jobIds this reconciler has itself
  applied to, so it never re-applies to the same job twice.

### Uninstall

```powershell
schtasks /End /TN "ASP-6262-Reconciler"
schtasks /Delete /TN "ASP-6262-Reconciler" /F
```
