# Architecture

AgentOps Cloud is the enterprise control plane for AI agents: discovery, ownership, risk, and optimization for every agent running across a company — regardless of which framework built it. As of Phase 3 it's also one Agentic Service Provider (ASP): a single intelligent enterprise consultant experience, accessed through OKX Wallet-first authentication.

## System diagram

```
                     ┌─────────────────────────┐
                     │        Browser            │
                     │  Next.js 15 (apps/web)    │
                     │  Session cookie, RQ, RHF  │
                     └────────────┬───────────────┘
                                  │ HTTPS (session cookie forwarded)
                                  ▼
                     ┌─────────────────────────┐
                     │   FastAPI (apps/api)      │
                     │  - Wallet signature verify │
                     │  - Session JWT issue/verify│
                     │  - REST /api/v1/*          │
                     │  - Service layer           │
                     └──────────────┬─────────────┘
                                    │
                          SQLAlchemy (async)
                                    │
                     ┌──────────────▼─────────────┐
                     │  SQLite (apps/api/data/)    │
                     │  org-scoped tables          │
                     └─────────────────────────────┘
```

No queue broker runs in the MVP. The recommendation engine (`app/services/recommendation_service.py`) is invoked directly — from the seed script, from `POST /recommendations/refresh`, and from a running Health Scan — rather than on a Celery schedule. See `TechnicalDecisions.md` for why, and `app/jobs/tasks.py` for how this upgrades to a real scheduler later without changing the function bodies.

## Authentication

Clerk (Phase 1/2's placeholder auth) has been fully replaced with wallet-first, challenge-response authentication. The abstraction point is deliberately narrow: OAuth-redirect providers (Google, Microsoft, GitHub, Okta, SAML — reserved in `AuthProviderType`, `app/models/enums.py`) and wallet challenge-response don't share a connect flow shape, so there's no forced single `AuthProvider.authenticate()` interface. Instead, every provider module produces the same small `WorkspaceAuthResult` (user id, org id, whether a new workspace was created), and that's the only thing `app/auth/session.py` and `app/api/deps.py` ever see. Adding a future provider means one new module under `app/auth/providers/` and one new route in `app/api/v1/auth.py` — no changes to session issuance, `get_current_org`/`get_current_user`, or any existing router.

**Flow**: Landing page → `ConnectWalletButton` detects `window.okxwallet` → `POST /auth/wallet/nonce` issues a DB-backed, single-use nonce (`app/models/auth_challenge.py`) embedded in a human-readable message → the wallet signs it (`personal_sign`) → `POST /auth/wallet/verify` recovers the signer address (`eth_account`) and checks it matches the claimed address and an unexpired, unconsumed challenge → finds-or-creates the `Organization` (workspace) + `User` (`role=OWNER` the first time) → issues an HS256 session JWT and sets it as an httpOnly cookie directly on the API's own response. The wallet is only used once, at login — normal navigation never re-prompts it.

**Session, not wallet, on every request**: the cookie (`agentops_session`) is what authorizes subsequent requests, verified in `app/api/deps.py:get_current_identity`. Because the API sets the cookie itself (not a Next.js-side cookie), and `localhost:3000`/`localhost:8000` (and prod subdomains of one apex domain) are same-*site*, `SameSite=Lax` is enough — no BFF proxy route needed. `apps/web/lib/server-api.ts` forwards the incoming request's cookie header on RSC fetches; `apps/web/lib/api-client.ts` sends `credentials: "include"` for client-side fetches. `apps/web/middleware.ts` independently verifies the same JWT at the edge with `jose` (shared HMAC secret) to gate `(app)` routes without a round-trip to the API.

**Local dev bypass**: wallet auth needs no third-party config (unlike Clerk), so `AUTH_DISABLED=true` (both apps, default in `.env.example`) is the explicit opt-out that reproduces the old "Clerk env vars unset" experience — every request resolves to the fixed seeded `dev-org`/`dev-user`, no login required. Flip it to `false` in both `apps/api/.env` and `apps/web/.env` (same `SESSION_SECRET_KEY` / `SESSION_JWT_SECRET`) to exercise the real flow.

**One wallet = one workspace owner** today (`users.wallet_address`, unique). The org-scoped `wallets` table (reserved since Phase 2 for Base wallet connection) is upserted alongside the user at login and is what Settings → Wallet displays (short address, chain, connection status, last verification) — the wallet address is never shown anywhere else in the app shell. Teams / multiple users per workspace stay explicitly out of scope, same as before.

## ASP architecture — one intelligent service, several internal layers

Externally, AgentOps Cloud is one Agentic Service Provider: a user runs a Health Scan and gets back an executive assessment and an implementation plan, the way they'd get a deliverable from a consulting engagement — not "pick an agent to talk to." Internally, `app/services/scan_service.py` orchestrates six layers, each independently swappable:

| Layer | Module | What it does |
|---|---|---|
| Discovery | `_fetch_raw_agents` / `_ingest_agents` (`scan_service.py`) | Parse the source (upload or GitHub) and ingest agents as real `Agent` rows |
| Analysis | `app/services/scan/cost_estimator.py` | Cost estimation, computed during ingestion |
| Reasoning | `app/services/recommendation_service.py` | The swappable, explicitly rule-based engine — see `TechnicalDecisions.md`. Nothing else in the ASP pipeline needs to change when this becomes a learned model later |
| Optimization | `app/services/scan/optimization_plan_service.py` | Turns findings into a phased, dependency-aware implementation roadmap (Immediate Wins / 30-Day / 90-Day / Long-Term Architecture) |
| Reporting | `app/services/scan/report_service.py` | The nine-section Executive Report + overall health score |
| Presentation | `ScanRead` schema, `components/health-scan/scan-status.tsx` | What the user actually sees |

`HealthScan.current_step` narrates progress across these layers in plain language ("Discovering AI Assets", "Evaluating Cost Efficiency", "Detecting Risks", "Mapping Agent Relationships", "Generating Executive Report", "Building Optimization Plan") — friendlier labels laid over the same real work `run_scan` has always done; no stage claims analysis that isn't actually happening.

## Health Scan flow

`app/services/scan_service.py` orchestrates the Enterprise Health Scan wizard: **Choose Data Source → Scan Progress → AI Analysis → Executive Report → Optimization Plan**. A scan is a `HealthScan` row moving through `PENDING → PARSING → ANALYZING → GENERATING_REPORT → COMPLETED` (or `FAILED`).

`POST /scans/{id}/start` schedules `run_scan` via FastAPI's `BackgroundTasks` — genuine multi-step async progress without a queue broker (see `TechnicalDecisions.md`). It opens its own DB session (the same `async_session_factory` idiom `app/jobs/tasks.py` already uses) and never depends on request-scoped auth.

Ingested agents become real `Agent` rows through the normal ingestion path (`source=connector`) — not a parallel "scanned agent" concept — so `/overview`, `/agents`, and `/recommendations` pick up scan results automatically. The Executive Report (`app/services/scan/report_service.py`) synthesizes those recommendations plus fleet summary stats into a nine-section narrative aimed at a non-technical exec (executive summary, organization overview, cost analysis, security risks, operational risks, optimization opportunities, business impact, priority actions, overall health score), and the Optimization Plan (`app/services/scan/optimization_plan_service.py`) turns the same findings into a phased, actionable roadmap — both with a deterministic fallback so the whole pipeline works with zero external config (see `TechnicalDecisions.md`).

## Org scoping

Every table carries an `org_id` foreign key, indexed. Row-level scoping is enforced in the service layer (`app/api/deps.py:get_current_org`, then every service function takes `org_id`) — not Postgres RLS or schema-per-tenant. That's deliberately simple; see `FutureVision.md` for when it would need to change.

## Connector architecture

`app/services/connector_service.py` defines a `ConnectorAdapter` ABC and an `ADAPTER_REGISTRY`. The `connectors` table and `POST /api/v1/connectors` route exist and work.

`ConnectorType.GITHUB` is now a **real, registered adapter** (`app/services/connectors/github_adapter.py`), used by the Health Scan's GitHub data source: `test_connection` makes a real GitHub API call, and `sync_agents` does a real (not faked) static scan of root-level dependency manifests for known agent-framework markers — it does not execute or deeply parse the repo's code, and every agent it produces is tagged `needs_review: true`. Every other connector type (`LANGGRAPH`, `CREWAI`, `OPENAI_AGENTS_SDK`, `MCP`, `DOCKER`, `KUBERNETES`, `AWS`, `AZURE`, `GCP`) still returns `501 Not Implemented` — the architecture is real and testable, but nothing fakes those integrations yet.

## AI provider abstraction

`app/services/llm/provider.py` defines `LLMProvider`. `OpenAIProvider` is the only implementation. Adding Anthropic, Gemini, DeepSeek, Groq, or OpenRouter means adding a new subclass — no other code changes.

## Frontend structure

Route groups split the public marketing site `(marketing)` from the authenticated app shell `(app)`, gated by session-verifying middleware (`apps/web/middleware.ts`) — Clerk is gone. Pages are React Server Components that fetch directly from the API (`lib/server-api.ts`); React Query is wired for client-side mutations (see `components/recommendation-actions.tsx` for the Apply/Dismiss flow). Design system primitives live in `packages/ui` and are never imported from shadcn directly inside `apps/web` — that indirection is what keeps the design system swappable later.

See `FolderStructure.md` for the full tree, `API_Design.md` for the route reference, and `Roadmap.md` for what's explicitly out of scope right now.
