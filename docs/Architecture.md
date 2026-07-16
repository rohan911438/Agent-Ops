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

No queue broker runs in the MVP. The recommendation engine (`app/services/recommendation_service.py`) is invoked directly — from the seed script and from `POST /recommendations/refresh` — rather than on a Celery schedule. See `TechnicalDecisions.md` for why, and `app/jobs/tasks.py` for how this upgrades to a real scheduler later without changing the function bodies.

## Org scoping

Every table carries an `org_id` foreign key, indexed. Row-level scoping is enforced in the service layer (`app/api/deps.py:get_current_org`, then every service function takes `org_id`) — not Postgres RLS or schema-per-tenant. That's deliberately simple; see `FutureVision.md` for when it would need to change.

## Connector architecture (prepared, not implemented)

`app/services/connector_service.py` defines a `ConnectorAdapter` ABC and an empty `ADAPTER_REGISTRY`. The `connectors` table and `POST /api/v1/connectors` route exist and work — but `POST` returns `501 Not Implemented` for every connector type, because no adapter is registered. This is intentional: the architecture is real and testable, but nothing fakes a live GitHub/LangGraph/CrewAI integration. Phase 3 fills in adapters one at a time.

## AI provider abstraction

`app/services/llm/provider.py` defines `LLMProvider`. `OpenAIProvider` is the only implementation. Adding Anthropic, Gemini, DeepSeek, Groq, or OpenRouter means adding a new subclass — no other code changes.

## Frontend structure

Route groups split the public marketing site `(marketing)` from the authenticated app shell `(app)`, gated by Clerk middleware (`apps/web/middleware.ts`). Pages are React Server Components that fetch directly from the API (`lib/server-api.ts`); React Query is wired for client-side mutations (see `components/recommendation-actions.tsx` for the Apply/Dismiss flow). Design system primitives live in `packages/ui` and are never imported from shadcn directly inside `apps/web` — that indirection is what keeps the design system swappable later.

See `FolderStructure.md` for the full tree, `API_Design.md` for the route reference, and `Roadmap.md` for what's explicitly out of scope right now.
