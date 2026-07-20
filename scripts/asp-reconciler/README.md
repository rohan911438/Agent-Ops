# ASP Designated-Task Reconciler

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
2. Reads the daemon's own `job_provider_bindings` table in
   `~/.okx-agent-task/sqlite/session-store.sqlite` — what the daemon believes it has
   already dispatched a session for.
3. Any task present in (1) but absent from (2) is treated as a missed dispatch and is
   re-applied directly via `onchainos agent apply <jobId> --agent-id 6262 --token-amount
   <amt> --token-symbol <sym>`, with exponential backoff (5s / 15s / 45s) on failure.
4. State is exposed on `GET http://localhost:4790/health` and logged to
   `scripts/asp-reconciler/logs/reconciler.log` (JSON lines: task detected, apply
   started/succeeded/failed, tx hash, retry attempts).

## Known limitation

This can only detect "daemon never created a binding for an on-chain-visible task." It
cannot yet distinguish "never applied" from "applied, but `onchainos agent status <jobId>`
is unavailable to confirm the on-chain application directly" — that CLI command is
currently broken in this environment with a persistent `code=3001` JWT error unrelated to
this script (see the bug report doc). Once that's fixed upstream, tighten step (2) to query
on-chain application state directly instead of the daemon's local table.

Requires `onchainos` on `PATH` and to be logged in (same account the daemon uses). One
instance enforced via a PID lock file (`logs/reconciler.pid`) — a second `node
reconcile.mjs` started while one is already running exits immediately rather than double-
applying.

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
also stop it directly (find the pid in `logs/reconciler.pid`) — the supervisor loop only
restarts `node`, it doesn't independently respawn itself once `/End`ed.

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
