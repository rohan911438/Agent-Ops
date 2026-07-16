# Architecture

AgentOps Cloud is the enterprise control plane for AI agents: discovery, ownership, risk, and optimization for every agent running across a company — regardless of which framework built it.

## System diagram

```
                     ┌─────────────────────────┐
                     │        Browser            │
                     │  Next.js 15 (apps/web)    │
                     │  Clerk session, RQ, RHF   │
                     └────────────┬───────────────┘
                                  │ HTTPS (JWT from Clerk, or none in dev)
                                  ▼
                     ┌─────────────────────────┐
                     │   FastAPI (apps/api)      │
                     │  - Clerk JWT verify        │
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

## Health Scan flow

`app/services/scan_service.py` orchestrates the Enterprise Health Scan wizard: **Choose Data Source → Scan Progress → AI Analysis → Executive Report → Optimization Recommendations**. A scan is a `HealthScan` row moving through `PENDING → PARSING → ANALYZING → GENERATING_REPORT → COMPLETED` (or `FAILED`).

`POST /scans/{id}/start` schedules `run_scan` via FastAPI's `BackgroundTasks` — genuine multi-step async progress without a queue broker (see `TechnicalDecisions.md`). It opens its own DB session (the same `async_session_factory` idiom `app/jobs/tasks.py` already uses) and never depends on request-scoped auth.

Ingested agents become real `Agent` rows through the normal ingestion path (`source=connector`) — not a parallel "scanned agent" concept — so `/overview`, `/agents`, and `/recommendations` pick up scan results automatically. The recommendation engine gained two rules specifically for this (`orphaned_agent`, `model_downgrade`) rather than a separate scoring system. The Executive Report (`app/services/scan/report_service.py`) synthesizes those recommendations plus fleet summary stats into a narrative aimed at a non-technical exec — with a deterministic fallback so it works with zero external config (see `TechnicalDecisions.md`).

## Org scoping

Every table carries an `org_id` foreign key, indexed. Row-level scoping is enforced in the service layer (`app/api/deps.py:get_current_org`, then every service function takes `org_id`) — not Postgres RLS or schema-per-tenant. That's deliberately simple; see `FutureVision.md` for when it would need to change.

## Connector architecture

`app/services/connector_service.py` defines a `ConnectorAdapter` ABC and an `ADAPTER_REGISTRY`. The `connectors` table and `POST /api/v1/connectors` route exist and work.

`ConnectorType.GITHUB` is now a **real, registered adapter** (`app/services/connectors/github_adapter.py`), used by the Health Scan's GitHub data source: `test_connection` makes a real GitHub API call, and `sync_agents` does a real (not faked) static scan of root-level dependency manifests for known agent-framework markers — it does not execute or deeply parse the repo's code, and every agent it produces is tagged `needs_review: true`. Every other connector type (`LANGGRAPH`, `CREWAI`, `OPENAI_AGENTS_SDK`, `MCP`, `DOCKER`, `KUBERNETES`, `AWS`, `AZURE`, `GCP`) still returns `501 Not Implemented` — the architecture is real and testable, but nothing fakes those integrations yet. Phase 3 fills them in one at a time; the Health Scan wizard's "Choose Data Source" screen shows LangGraph/CrewAI/OpenAI Agents SDK as disabled "coming soon" options for the same reason.

## AI provider abstraction

`app/services/llm/provider.py` defines `LLMProvider`. `OpenAIProvider` is the only implementation. Adding Anthropic, Gemini, DeepSeek, Groq, or OpenRouter means adding a new subclass — no other code changes.

## Frontend structure

Route groups split the public marketing site `(marketing)` from the authenticated app shell `(app)`, gated by Clerk middleware (`apps/web/middleware.ts`). Pages are React Server Components that fetch directly from the API (`lib/server-api.ts`); React Query is wired for client-side mutations (see `components/recommendation-actions.tsx` for the Apply/Dismiss flow). Design system primitives live in `packages/ui` and are never imported from shadcn directly inside `apps/web` — that indirection is what keeps the design system swappable later.

See `FolderStructure.md` for the full tree, `API_Design.md` for the route reference, and `Roadmap.md` for what's explicitly out of scope right now.
