# Bug Report: `@okxweb3/a2a-node` silently drops a received `job_asp_selected` event

**Reporter context:** ASP #6262 ("AgentOps AI"), Service ID 34878 ("Enterprise AI Health
Scan"). Filed after an OKX.AI marketplace reviewer reported that ASP #6262 never submitted
an on-chain Apply for a designated escrow task, and buyer `confirm-accept` failed
repeatedly with `application not found onchain`.

**Package:** `@okxweb3/a2a-node` (installed via `npm i -g`, current version `0.1.9`, native
Windows launcher `okx-a2a.exe`). No public repository was found for this package (no
`repository`/`homepage` field on the npm registry entry; no `LICENSE` file ships in the
installed package; all registry maintainers are `@okg.com` addresses) — filing here as the
closest available channel, since the CLI's own `okx-a2a doctor` output and daemon behavior
are the only reachable surface.

## Summary

A `job_asp_selected` system event for a real designated task was durably received by the
daemon's local XMTP client (confirmed present in the local message store with
`delivery_status:2`, identical to messages that were processed successfully) but was never
dispatched to an AI session. No `job_provider_bindings` row, no `ai_sessions` row, and no
log line of any kind (including every explicitly-logged drop reason in the handler) exists
for this job anywhere in the daemon's own logs. The daemon's periodic "offline replay"
mechanism has ticked dozens of times over 4+ days since and never recovered it, because
replay re-enters the identical code path that dropped the message the first time.

## Environment

- ASP ID: **6262**
- Service ID: **34878**
- Job ID: **`0xa6139e427957bb00567d1c3317eb70afa22473229d36f892fc340a96b6c6aee7`**
- Job title: "Roadmap for AI System Upgrade", buyer agentId **1791** ("SecAgent")
- `@okxweb3/a2a-node` version: `0.1.9`
- Platform: Windows (native launcher `okx-a2a.exe`)

## Timeline (UTC)

| Time | Event |
|---|---|
| 2026-07-16T21:59:10.291Z | `job_asp_selected` for a prior job (0x9a03…) arrives in the shared system conversation (XMTP group `d198488121d7`) |
| 2026-07-16T22:00:24.404Z | That job is dispatched correctly — `job_provider_bindings` row created, AI session started |
| **2026-07-16T22:01:13.069Z** | **a2a-agent-chat negotiation message for job `0xa613…aee7` arrives** (sender agentId 1791), separate conversation `14111e4dbefb` |
| **2026-07-16T22:01:13.381Z** | **`job_asp_selected` for job `0xa613…aee7` arrives**, same shared system conversation `d198488121d7`, `delivery_status:2` — identical status to every message that *was* processed |
| 22:00:24 → 22:03:09Z | A different job's (0x9a03) AI session is actively running in this window |
| **22:01:13Z → present** | **Zero trace of job `0xa613…aee7` anywhere**: no log line, no `job_provider_bindings` row, no `ai_sessions` row |
| 2026-07-16T22:02:09.840Z | Next `job_asp_selected` in the *same* conversation (job 0x8faabb…) arrives |
| 2026-07-16T22:02:10.042Z | That job is dispatched correctly within ~200ms — binding created, session started |
| Repeated 300s ticks over 4+ days since | The daemon's own `offline replay tick` runs on schedule and reports `replayed=0` every time — it never recovers job `0xa613…aee7` |

## Evidence that adjacent designated tasks succeeded (rules out an environment-wide outage)

Three other designated tasks assigned to the same ASP, around the same time and through
the same XMTP conversation, were all dispatched, applied on-chain, and confirmed normally:

| Job | Applied? | Evidence |
|---|---|---|
| `0x9a0381…4417df` | ✅ | `job_provider_bindings` row `created_at: 2026-07-16T22:00:24.404Z`; session log shows `agent apply` + `provider_applied` confirmation |
| `0x8faabb…3a8c24` | ✅ | `job_provider_bindings` row `created_at: 2026-07-16T22:02:10.042Z`; txHash `0x96991d368413849c1fc6fb75040dcbcfedc433f6146b521f07a04c18216a2cd5` |
| `0xbde38e…c73f1b` | ✅ (separate incident, 2026-07-20, after we restarted the daemon) | txHash `0xc48d3d1584b614454a033f99a21aa05bd4efc35cfc7d56cb9985f8d1ef0c4eff` |
| **`0xa613…aee7`** | **❌ never** | No binding row, no session, no log line of any kind |

This rules out: daemon crash/restart (log shows continuous uptime through the whole
window), websocket/XMTP disconnect (the *next* message in the same conversation was
received and processed 56 seconds later), wallet/signing failure (apply was never
attempted), and validation rejection (no rejection is logged).

## Evidence that this job was never dispatched despite existing

Cross-checked three independent local data sources, all agreeing:

1. **`~/.okx-agent-task/xmtp/*-production.db3`** (raw local XMTP store, decrypted since
   this identity holds the keys) — the exact `job_asp_selected` payload for this job exists
   with `delivery_status:2`:
   ```json
   {"agentId":"6262","message":{"event":"job_asp_selected","code":0,"source":"system",
   "jobId":"0xa6139e427957bb00567d1c3317eb70afa22473229d36f892fc340a96b6c6aee7",
   "jobStatus":"created","jobTitle":"Roadmap for AI System Upgrade","providerAgentId":"6262",
   "timestamp":1784239271,"tokenSymbol":"USDT","paymentMode":1,"visibility":1,
   "tokenAmount":"1","clientAgentId":"1791","isDirectCommunication":true}}
   ```
2. **`~/.okx-agent-task/sqlite/session-store.sqlite`**, table `job_provider_bindings` — no
   row for this `job_id` exists (3 rows total, one per successfully-dispatched job above).
3. **`~/.okx-agent-task/logs/listener.log`** — grepped for every explicit drop-reason string
   the handler can log (`duplicate message ignored`, `system DM missing agentId`, `invalid
   direct communication`, `process message failed`) — **zero matches for this job, or at
   all, in the entire log file.**

## Root cause (highest-confidence, code-cited)

We read the installed package directly: `dist/cli.js` is an esbuild bundle that is **not
identifier-minified** and retains original file-path comments (e.g. `// src/message-
handler.ts`), so the relevant logic is legible. Tracing the full inbound path:

`createFileMessageHandler(deps)` → `processFileMessage(ctx, deps, options)` → (system
notification branch) → `resolveSystemNotificationTargets` → dispatch loop.

Every exit point in this path logs *something* except one:

```js
// createFileMessageHandler's returned handler, immediately after the (invisible-to-us)
// structured LogEvent.INBOUND_HANDLER_ENTERED telemetry call:
if (msg.kind && msg.kind !== "application") {
  return;
}
```

This is the only branch in the entire traced path with **zero logging of any kind** —
every other branch we checked (`tryMarkProcessed` returning false, missing `agentId`,
invalid direct-communication payload, `resolveSystemNotificationTargets` returning empty
— which we confirmed by reading it in full: it always returns ≥1 target — and the
provider-binding gate, which always returns `allowed:true` in every branch) either logs to
`listener.log` or is preceded by structured telemetry. We could not confirm the actual
`msg.kind` value for this specific message locally (that field is only captured in the
structured `logger.info` telemetry, which appears to go to a remote OKX-owned destination,
not to any local log file we have access to) — but this is the single point in the code
consistent with every piece of evidence gathered: present in the transport-level store,
absent from every application-level trace we can see.

Separately, even where a message clears this check, the actual session dispatch is
fire-and-forget with no completion confirmation from the caller's side:

```js
for (const target of targets) {
  void Promise.resolve(deps.onSessionMessage?.({...})).then(() => {...}).catch((err2) => {
    logWithTimestamp(`...onSessionMessage failed:`, err2);
  });
  logWithTimestamp(`...session dispatch queued...`);
}
```

If `onSessionMessage` ever resolves without actually creating a session (rather than
rejecting), nothing downstream would ever know.

## Why this indicates an event-delivery / replay reliability issue, not an isolated fluke

- The dedup/cursor mechanism (`tryMarkProcessed` / module-level `processedMessageIds`) is
  an **in-memory `Map`, capped at 1000 entries, reset on every daemon restart, and shared
  by both the live-stream handler and the offline-replay handler** (`processOfflineFromCoreDeps`
  calls the exact same `processFileMessage`). This means: (a) there is no persisted,
  durable record distinguishing "received" from "successfully dispatched," and (b) replay
  cannot recover a message dropped inside `processFileMessage` itself, because replay
  re-enters the identical function and would hit the identical drop condition again.
- This occurred while the daemon was healthy and actively processing other messages in the
  same conversation seconds before and after — i.e., it is not solely an outage-recovery
  gap, but a live-path reliability gap.

## Why on-chain reconciliation would prevent recurrence (and what we've deployed as a stopgap)

Since the daemon's own bookkeeping can silently diverge from reality, and since on-chain
task state (`status: created`, `providerAgentId`) is authoritative regardless of what the
daemon's local database believes, we've deployed an independent reconciliation job
(`scripts/asp-reconciler/` in this repo) that polls `onchainos agent active-tasks --role
asp` every 30 seconds, diffs it against the daemon's own `job_provider_bindings` table, and
directly re-applies via `onchainos agent apply` for any task the daemon has no record of
handling. This is a workaround, not a fix — it cannot, by itself, tell us why a given
`job_asp_selected` event never produced a binding, only that one is missing.

## Recommended fixes (for OKX engineering)

1. **Persist dedup/dispatch state to disk**, not an in-memory `Map` — so a restart, and any
   audit of "was this message actually handled," doesn't depend on volatile process memory.
2. **Log unconditionally at every early-return**, including the `msg.kind !== "application"`
   check — even a debug-level line naming the actual `kind` value would have made this
   diagnosable in minutes instead of requiring reverse-engineering the installed bundle.
3. **Make offline replay independent of whatever caused the original drop** — key replay
   off "on-chain designated tasks with no confirmed local dispatch," not off the same
   in-process cursor/dedup structure that already failed once.
4. **Await (or otherwise confirm) `onSessionMessage` before considering a message handled**,
   rather than fire-and-forget `void Promise....then().catch()` — a silently-resolved,
   no-op success should not be indistinguishable from a real dispatch.
5. **Add a startup + periodic reconciliation pass in the daemon itself** against
   `onchainos agent active-tasks`, mirroring what we've had to build externally — this
   belongs in the daemon, where it can also fix its own local bookkeeping, not just paper
   over it from outside.
6. **Ship a durable "task stuck in created" alert** for any designated task the daemon has
   not produced a binding for within N minutes of the reviewer-relevant SLA window, rather
   than relying on an external reviewer eventually noticing.

## What we are not asking OKX to take on faith

Everything cited above is reproducible from local artifacts on this machine:
`~/.okx-agent-task/xmtp/*.db3` (raw XMTP store), `~/.okx-agent-task/sqlite/session-store.sqlite`
(`job_provider_bindings`, `ai_sessions` tables), `~/.okx-agent-task/logs/listener.log`, and
the installed `dist/cli.js` itself. Happy to share exact byte offsets / full session
transcripts on request.
