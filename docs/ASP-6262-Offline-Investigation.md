# ASP #6262 — "Reviewer still sees offline" Investigation

**Date:** 2026-07-18
**Trigger:** Assistant-provided diagnostic (pasted by user) hypothesizing the ASP heartbeat is fine but the *endpoint* is unreachable — wrong registered URL, Railway not public, wallet-identity mismatch, or the reviewer hitting `/api/v1/marketplace/invoke` instead of the heartbeat. This doc runs all 5 requested checks directly against the live on-chain record, the local `onchainos` CLI, and the deployed URLs, then evaluates each hypothesis with evidence instead of guesswork.

**Bottom line up front:** all 5 network/endpoint hypotheses in the pasted diagnostic are **ruled out by live evidence**. The heartbeat is working, has been working reliably for ~19 hours, and both public URLs are reachable from outside your network. The far more likely explanation is that the ASP's **marketplace listing itself is still "not listed" / "Listing under review"** — a manual OKX approval gate that is unrelated to heartbeat/network health and won't change no matter how well the heartbeat runs.

---

## Check 1 — `onchainos agent get-agents --agent-ids 6262`

Ran directly. Key fields from the live response:

| Field | Value |
|---|---|
| `onlineStatus` | `1` (online) |
| `lastOnlineTime` | `1784383439029` → **2026-07-18 14:03:59 UTC** |
| `updatedAt` | same, `14:03:59 UTC` |
| `status` / `statusLabel` | `2` / **"not listed"** |
| `approvalDisplayStatus` / `approvalLabel` | `2` / **"Listing under review"**, remark: "AI quality review suggested pass" |
| `communicationAddress` | `0x70799564678fdad08FF8F996E058cB68716a2ea5` |
| `serviceList` | `[]` in this call (populated separately, see Check via `service-list`) |

This command was run at **14:13:09 UTC** — `lastOnlineTime` is only **~9 minutes stale**, exactly what you'd expect from a cron that fires every 10 minutes. **The heartbeat is working right now.**

`communicationAddress` is a 20-byte wallet-style address, not an HTTP URL — this is the on-chain A2A messaging identity, not a REST endpoint. It has nothing to do with the Railway URL and nothing in this repo listens on it (this matches finding **C-1** in `docs/ASP-6262-Production-Readiness-Audit.md`: no A2A message handler exists yet — a real, separate gap, but not the "offline" symptom being chased here).

`onchainos agent service-list --agent-id 6262` was also run: all 4 registered services show `"endpoint": null` / `"Endpoint": "—"` — expected and correct, since these are negotiated A2A services with no HTTP endpoint field, not REST services with a URL to misconfigure.

**Verdict: Possibility 1 (wrong registered endpoint) does not apply.** There is no HTTP endpoint field on the registration to get wrong — the only address field present is the A2A `communicationAddress`, which is correctly a wallet address, not a URL.

---

## Check 2 & 5 — Is Railway actually public? (`/health`, `/healthz`, `curl`)

Ran `curl` against the live Railway URL from this environment (an independent network, not your laptop's Wi-Fi):

```
GET /healthz  → HTTP 200  (1.2s)
GET /health   → HTTP 200  (alias route, see below)
GET /docs     → HTTP 200  (0.8s)  — FastAPI Swagger loads
GET (web app) → HTTP 200  (1.9s) — agentops-cloud-web.vercel.app
POST /api/v1/marketplace/invoke (no auth) → HTTP 401 (correct — auth required, not a crash/404/500)
```

Every one of these resolved cleanly from outside your home network. **Possibility 2 (Railway isn't actually public) is ruled out** — the backend, its docs, the health route, and the web frontend are all publicly reachable.

Small note unrelated to the "offline" bug: `apps/api/app/main.py:60-62` already defines `/health` as an explicit alias of `/healthz` specifically "for callers that probe the more conventional `/health` path (e.g. the OnchainOS ASP reviewer)" — so the diagnostic's `/health` vs `/healthz` distinction was already handled in code before this check ran.

---

## Check 3 — `/docs` (Swagger)

Confirmed above: `HTTP 200`, Swagger UI is live at `https://agentops-api-production.up.railway.app/docs`.

---

## Check 4 — What URL is actually registered on the ASP?

There isn't one to check, per Check 1 — the 4 registered A2A services all carry `endpoint: null`. The only address on the on-chain record is `communicationAddress` (an XMTP/A2A-style wallet address, not a Railway/localhost URL). So **Possibility 1's entire premise (a `localhost`/`192.168.x.x`/`127.0.0.1` URL baked into the registration) doesn't exist as a field to be wrong.**

---

## Possibility 3 — wallet identity mismatch

`onchainos wallet whoami` doesn't exist in this CLI version (`onchainos 4.2.4` locally vs `v4.2.6` pinned in the workflow — `error: unrecognized subcommand 'whoami'`). But this is moot: `get-agents` already returned data scoped to agent 6262 successfully under the currently-logged-in identity, and `ownerAddress`/`agentWalletAddress` both match `0xe0bbee...a276`, consistent with `docs/ASP-6262-Service-Status.md`'s recorded address. No evidence of a wallet-identity split.

---

## Possibility 4 — reviewer hits `/marketplace/invoke`, not the heartbeat

Tested above: unauthenticated `POST /api/v1/marketplace/invoke` returns a clean `401`, not a 404/500/timeout. That's the correct, intentional behavior (per the Resolution Log in `docs/ASP-6262-Production-Readiness-Audit.md` — it requires an `Authorization: Bearer aoc_...` API key). A reviewer without a key would get 401, not a crash — this would not present as "offline" in any log I can see, though it's worth confirming what exact response the OKX reviewer's probe expects (this repo doesn't control that side).

---

## GitHub Actions heartbeat run history (the actual mechanism)

Pulled all 15 runs of `.github/workflows/heartbeat.yml` via the public Actions API:

| Run | Trigger | Time (UTC) | Conclusion |
|---|---|---|---|
| 1 | `workflow_dispatch` (manual, right after creating the workflow) | 07-17 17:15 | ❌ failure |
| 2–15 | `schedule` | 07-17 18:17 → 07-18 13:12 | ✅ success (all 14) |

Only the very first manual test run failed — almost certainly because the `OKX_API_KEY`/`OKX_SECRET_KEY`/`OKX_PASSPHRASE` repo secrets weren't added yet at that moment. **Every scheduled run since (14 in a row, spanning ~19 hours) has succeeded.** This lines up exactly with the fresh `lastOnlineTime` from Check 1.

(Side note, not a bug: the cron is `*/10 * * * *` but GitHub's scheduler visibly throttles this to roughly hourly during low-traffic periods — normal GitHub Actions behavior for scheduled workflows, not a sign anything is broken.)

---

## What's actually going on

Every technical layer the pasted diagnostic asked about checks out clean:

- ✅ Heartbeat mechanism: running every ~1hr via GitHub Actions, 14/14 recent scheduled runs succeeded
- ✅ On-chain `onlineStatus`: `1` (online), `lastOnlineTime` 9 minutes old at check time
- ✅ Railway backend: publicly reachable (`/health`, `/healthz`, `/docs` all 200 from an external network)
- ✅ Vercel frontend: publicly reachable (200)
- ✅ Wallet identity: consistent, no mismatch found
- ✅ `/marketplace/invoke`: exists, correctly gated behind auth (401, not a crash)
- N/A Registered "endpoint": there isn't one to misconfigure — these are A2A services with `endpoint: null` by design, and `communicationAddress` is a wallet address, not a URL

The one thing that **is** flashing red in the live data and matches "reviewer still sees offline": the **listing itself**.

```
status:               2  → statusLabel: "not listed"
approvalDisplayStatus: 2  → approvalLabel: "Listing under review"
approvalRemark:        "AI quality review suggested pass"
```

`onlineStatus` (heartbeat liveness) and listing `status`/`approvalDisplayStatus` (OKX's manual marketplace review queue) are **two independent fields**. A heartbeat can be perfectly healthy while the listing itself is still sitting in "under review" / "not listed" — which is exactly what a reviewer or the marketplace UI would likely surface as unavailable, regardless of how fresh the heartbeat is. This would explain why fixing the heartbeat (which genuinely needed fixing, and is now genuinely fixed) hasn't changed what the reviewer sees: **they may not be looking at heartbeat status at all.**

## Recommended next step

Stop chasing endpoint/network theories — they're now all falsified by direct evidence. Instead:

1. Confirm with whoever is doing the marketplace review whether they're checking `onlineStatus` (already ✅) or the listing's approval state (still "Listing under review", not yet flipped to listed/approved).
2. If it's the latter, this is on OKX's review queue, not fixable from this repo's side — re-running the heartbeat harder won't move `approvalDisplayStatus`.
3. Separately (unrelated to "offline," but a real gap from the production-readiness audit): **C-1** in `docs/ASP-6262-Production-Readiness-Audit.md` still stands — nothing in this repo listens on `communicationAddress` for an inbound A2A negotiation. If the reviewer's check *is* an actual A2A invocation attempt against that address (not `/marketplace/invoke`), there is genuinely nothing to answer it yet.
