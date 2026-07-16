# Roadmap

**Phase 1 — Enterprise Discovery.** Agent inventory, ownership, cost, risk, and a rule-based recommendation engine over manually seeded/entered data. Proves: an enterprise can see what agents it has and get a real, explainable optimization suggestion.

**Phase 2 — Enterprise Health Scan (this build).** The centerpiece workflow: Landing Page → Start Health Scan → Choose Data Source → Scan Progress → AI Analysis → Executive Report → Optimization Recommendations. Ingests agents from an upload (JSON/YAML) or a GitHub repo (real adapter, heuristic-based `sync_agents`), runs the (extended) rule-based recommendation engine, and synthesizes an AI-generated Executive Report — with a deterministic fallback so it works with zero external config. LangGraph, CrewAI, and OpenAI Agents SDK are shown as "coming soon" data sources — interfaces reserved, not implemented.

**Phase 2b — SDK.** Implement `packages/sdk/python` (`agentops-cloud`) and `packages/sdk/node` (`@agentops/sdk`) for real: `init()`, `heartbeat()`, automatic agent discovery, cost/tool-call tracking. This is what turns "manually entered/scanned agents" into "agents that show up on their own."

**Phase 3 — Observability.** Register real `ConnectorAdapter` implementations (`app/services/connector_service.py`) for the remaining connector types — LangGraph, CrewAI, OpenAI Agents SDK, MCP, Docker, Kubernetes, AWS, Azure, GCP (GitHub already landed in Phase 2). Background sync needs a real scheduler at this point — promote `app/jobs/tasks.py` functions to Celery tasks with Redis as the broker (see `TechnicalDecisions.md`).

**Phase 4 — Optimization Engine.** Recommendation engine grows from six rule-based checks into a broader, still-explainable system — likely a hybrid of rules and a learned model. Whatever it becomes, it should stay honest about which recommendations are rule-derived vs. model-derived vs. AI-narrated (the Executive Report already introduces this distinction — see `TechnicalDecisions.md`).

**Phase 5 — Enterprise Governance.** Permission graphs, audit trail depth, and the blockchain piece: immutable execution proofs and audit verification anchored on Base, using the `tx_hash` columns and `wallets` table already reserved in the schema.

**Phase 6 — Marketplace.** Explicitly out of scope for everything before this. Not a "later feature" of Phase 1-5 — a distinct phase with its own review.

## Milestones for Phase 1

- [x] M1 — Monorepo scaffold (npm workspaces, Turborepo, configs)
- [x] M2 — DB models + Alembic migration + seed script
- [x] M3 — FastAPI app with real route handlers + Clerk auth wiring (skippable in dev)
- [x] M4 — Next.js shell + design-system components
- [x] M5 — Six MVP pages wired to the real API against seeded data
- [x] M6 — Docs written

## Milestones for Phase 2 (this build)

- [x] M7 — `HealthScan` model/migration, scan orchestration (`scan_service.py`, `BackgroundTasks`)
- [x] M8 — Upload (JSON/YAML) + GitHub (real adapter, heuristic `sync_agents`) data sources
- [x] M9 — Recommendation engine extended with `orphaned_agent` + `model_downgrade` rules
- [x] M10 — Executive Report generation with LLM + deterministic fallback
- [x] M11 — Health Scan wizard UI (data source picker, progress stepper, report, recommendations)
- [x] M12 — Landing page repointed at Health Scan as the primary funnel

## Potential technical risks

- **Clerk org model vs. internal org model drift** — mitigated by webhook-driven sync (`POST /auth/webhook`); Clerk stays the source of truth for identity, SQLite/Postgres for product data.
- **Recommendation engine credibility** — explicitly rule-based, not ML. State this in-product eventually (a small "how this was generated" affordance), not just in docs.
- **Executive Report credibility** — the AI-narrated sections (`app/services/scan/report_service.py`) must never claim analysis they didn't do, especially the GitHub heuristic path (`needs_review: true`, static manifest scan only — no code execution). Always degrades to a deterministic template rather than fail or hallucinate when no LLM is configured.
- **Agent schema rigidity across frameworks** — mitigated by `agent_metadata` JSON column on `agents`; framework-specific fields don't force a migration.
- **Scan reliability without a queue broker** — a scan stuck mid-run because the dev process restarted has no auto-recovery in the MVP (`BackgroundTasks`, no Celery); acceptable for demo scope, revisit if Phase 3's real scheduler lands.
- **Scope creep** — SDK, remaining connectors, and blockchain proofs all exist as interfaces/placeholders only. Resist filling them in ahead of their phase.
