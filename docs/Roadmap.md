# Roadmap

**Phase 1 — Enterprise Discovery (this build).** Agent inventory, ownership, cost, risk, and a rule-based recommendation engine over manually seeded/entered data. Proves: an enterprise can see what agents it has and get a real, explainable optimization suggestion.

**Phase 2 — SDK.** Implement `packages/sdk/python` (`agentops-cloud`) and `packages/sdk/node` (`@agentops/sdk`) for real: `init()`, `heartbeat()`, automatic agent discovery, cost/tool-call tracking. This is what turns "manually entered agents" into "agents that show up on their own."

**Phase 3 — Observability.** Register real `ConnectorAdapter` implementations (`app/services/connector_service.py`) for GitHub, LangGraph, CrewAI, OpenAI Agents SDK, MCP, Docker, Kubernetes, AWS, Azure, GCP. Background sync needs a real scheduler at this point — promote `app/jobs/tasks.py` functions to Celery tasks with Redis as the broker (see `TechnicalDecisions.md`).

**Phase 4 — Optimization Engine.** Recommendation engine grows from four rule-based checks into a broader, still-explainable system — likely a hybrid of rules and a learned model. Whatever it becomes, it should stay honest about which recommendations are rule-derived vs. model-derived.

**Phase 5 — Enterprise Governance.** Permission graphs, audit trail depth, and the blockchain piece: immutable execution proofs and audit verification anchored on Base, using the `tx_hash` columns and `wallets` table already reserved in the schema.

**Phase 6 — Marketplace.** Explicitly out of scope for everything before this. Not a "later feature" of Phase 1-5 — a distinct phase with its own review.

## Milestones for Phase 1 (this build)

- [x] M1 — Monorepo scaffold (npm workspaces, Turborepo, configs)
- [x] M2 — DB models + Alembic migration + seed script
- [x] M3 — FastAPI app with real route handlers + Clerk auth wiring (skippable in dev)
- [x] M4 — Next.js shell + design-system components
- [x] M5 — Six MVP pages wired to the real API against seeded data
- [x] M6 — Docs written

## Potential technical risks

- **Clerk org model vs. internal org model drift** — mitigated by webhook-driven sync (`POST /auth/webhook`); Clerk stays the source of truth for identity, SQLite/Postgres for product data.
- **Recommendation engine credibility** — explicitly rule-based, not ML. State this in-product eventually (a small "how this was generated" affordance), not just in docs.
- **Agent schema rigidity across frameworks** — mitigated by `agent_metadata` JSON column on `agents`; framework-specific fields don't force a migration.
- **Scope creep** — SDK, connectors, and blockchain proofs all exist as interfaces/placeholders only. Resist filling them in ahead of their phase.
