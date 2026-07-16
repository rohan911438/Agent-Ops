# API Design

Base URL: `/api/v1`. All routes except `/healthz` and `/auth/webhook` are org-scoped via the caller's resolved organization (`app/api/deps.py:get_current_org`).

Auth: Bearer JWT issued by Clerk, verified against Clerk's JWKS. When `CLERK_JWKS_URL`/`CLERK_ISSUER` are unset (local dev), verification is skipped and every request resolves to the seeded `dev-org` — no token required.

## Agents

| Method | Path | Notes |
|---|---|---|
| GET | `/agents` | List agents in the org |
| POST | `/agents` | Create an agent |
| GET | `/agents/{id}` | 404 if not found or wrong org |
| PATCH | `/agents/{id}` | Partial update |
| DELETE | `/agents/{id}` | 204 |

## Recommendations

| Method | Path | Notes |
|---|---|---|
| GET | `/recommendations` | Optional `?status_filter=open\|dismissed\|applied` |
| POST | `/recommendations/refresh` | Runs the rule-based engine synchronously, returns newly created recommendations |
| PATCH | `/recommendations/{id}` | Body `{ "status": "open"\|"dismissed"\|"applied" }` |

## Activity

| Method | Path | Notes |
|---|---|---|
| GET | `/activity` | Optional `?search=`, `?event_type=`, `?agent_id=` |

## Overview

| Method | Path | Notes |
|---|---|---|
| GET | `/overview/summary` | Aggregated counts + last 10 activity events, powers the 4 metric cards |

## Settings

| Method | Path | Notes |
|---|---|---|
| GET/PATCH | `/settings/workspace` | Org name/slug |
| GET/POST | `/settings/users` | List / invite |
| PATCH/DELETE | `/settings/users/{id}` | Change role / remove |
| GET/POST | `/settings/api-keys` | List / create — the raw key is returned **once**, at creation, then only its hash is stored |
| DELETE | `/settings/api-keys/{id}` | Revoke |
| GET/POST | `/settings/wallet` | Connect a Base wallet address — no on-chain interaction |

## Health Scans

| Method | Path | Notes |
|---|---|---|
| GET | `/scans` | List scans for the org, newest first |
| POST | `/scans/upload` | Multipart `file` (JSON/YAML agent manifest, 2MB cap). Parses synchronously; 422 on malformed input. Returns the scan `PENDING`. |
| POST | `/scans/github` | Body `{ "repo_url", "github_token"? }`. Tests the connection synchronously; 422 if unreachable. Returns the scan `PENDING`. |
| POST | `/scans/{id}/start` | 202. Schedules the scan (parse → ingest → recommend → report) via FastAPI `BackgroundTasks`; 409 if already started. |
| GET | `/scans/{id}` | Poll for status/progress/summary/executive_report. 404 if not found or wrong org. |

Scan-ingested agents become real `Agent` rows (`source=connector`) through the normal service layer — they show up in `/agents`, `/overview`, and `/recommendations` like any other agent. See `Architecture.md`'s "Health Scan flow" section.

## Connectors (architecture)

| Method | Path | Notes |
|---|---|---|
| GET | `/connectors` | List connector records for the org |
| POST | `/connectors` | `github` is a **real, registered adapter** (`app/services/connectors/github_adapter.py`) — this now works. Every other `ConnectorType` is still **501** — no adapter registered yet. See `Architecture.md`. |

## Auth

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/webhook` | Clerk webhook receiver; syncs `organization.created` and `user.created` events into local tables |

## Versioning

The `/api/v1` prefix is applied once in `app/main.py`. Breaking changes get a `/api/v2` prefix and a new router — old clients keep working against `/v1` until it's explicitly retired.

## Regenerating client types

`packages/shared-types` is hand-mirrored from `apps/api/app/schemas/*.py` today. Once the schema stabilizes, generate it instead:

```bash
# from apps/api, with the server running
openapi-typescript http://localhost:8000/openapi.json -o ../../packages/shared-types/src/generated.ts
```
