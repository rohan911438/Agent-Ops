# Future Vision

AgentOps Cloud becomes the operating system for enterprise AI the same way Okta became the operating system for enterprise identity: not by doing everything, but by being the one place that knows about *everything else*.

## What this MVP deliberately does not decide

- **Multi-tenancy model.** `org_id`-scoped rows in a single database are enough until an enterprise customer requires physical data isolation. Graduating to schema-per-tenant or row-level security is an infrastructure change behind the same service-layer API — no route or frontend change needed when it happens.
- **Recommendation engine architecture.** Rule-based today. Whether Phase 4 makes it a learned model, a hybrid, or an LLM-judge over agent traces is not decided — the engine's output contract (`Recommendation` rows with a `type`, `title`, `description`, `impact_estimate`) is stable regardless of what generates them.
- **Blockchain's actual role.** The report-hash anchoring piece is now real (`EnterpriseReportRegistry` on Base Sepolia — see `docs/ContractArchitecture.md`), using the `wallets` table and `tx_hash` columns reserved since Phase 2/3. Agent identity and execution-proof anchoring beyond report hashes remain future work (Phase 5). Still not payments, not tokens, not a marketplace currency — `ServicePricing.sol` and the `PaymentProvider` ABC exist as prepared architecture only (`docs/FutureMonetization.md`); nothing charges anyone today.

## What "millions of agents" implies architecturally (not built yet, but not precluded)

- Connector sync and recommendation runs move off the request path entirely (Celery/Redis, per `TechnicalDecisions.md`) once Phase 3 connectors are real and running on a schedule across many orgs.
- `agents` and `activity_events` are the two tables that will actually see volume. Both are already indexed on `org_id`; partitioning or a time-series store for `activity_events` is the first place to look if scale becomes a problem, not a rewrite of the API.
- The connector adapter pattern (`ConnectorAdapter` ABC) is what lets "millions of agents" mean "many orgs, each with a manageable number of agents, syncing independently" rather than one monolithic crawl.

## Deliberately not on this roadmap

Marketplace, chat interface, AI assistant page, billing/subscriptions, notification center, CRM, project management. If a future phase wants one of these, it should get its own spec and review — not slide in as a "small addition" to an existing phase.
