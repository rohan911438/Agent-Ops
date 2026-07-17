# Contract Architecture

## System diagram

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│   Browser (apps/web)         │        │   FastAPI (apps/api)          │
│                                │        │                                │
│  Executive Report page        │◀──────▶│  GET /scans/{id}/verification │
│  "Report Integrity" card      │  REST  │  GET /pricing                 │
│  (VerificationCard.tsx)       │        │                                │
└─────────────────────────────┘        └───────────────┬────────────────┘
                                                            │
                                        after Executive Report is generated
                                        (scan_service.run_scan, always wrapped
                                         so a chain failure never fails a scan)
                                                            │
                                                            ▼
                                        ┌────────────────────────────────┐
                                        │  verification_service.py        │
                                        │  sha256(json.dumps(report,      │
                                        │  sort_keys=True))                │
                                        └───────────────┬────────────────┘
                                                            │ hash only
                                                            ▼
                                        ┌────────────────────────────────┐
                                        │  ChainProvider (ABC)             │
                                        │  → Web3ChainProvider (web3.py)   │
                                        └───────────────┬────────────────┘
                                                            │ signed tx
                                                            ▼
                              ┌─────────────────────────────────────────────┐
                              │              Base Sepolia (testnet)          │
                              │                                               │
                              │  EnterpriseReportRegistry   ServicePricing    │
                              │  (hash + workspace id +     (service prices,  │
                              │   timestamp + version)       owner-updatable) │
                              │                                               │
                              │              AgentOpsRegistry                 │
                              │       (backend/frontend/contract versions)    │
                              └─────────────────────────────────────────────┘
                                                            ▲
                                                            │ never touches this
                              ┌─────────────────────────────────────────────┐
                              │  SQLite (apps/api/data/)                     │
                              │  org data, agents, reports, recommendations  │
                              │  — the actual product data, entirely off-chain│
                              └─────────────────────────────────────────────┘
```

## The one rule this whole layer follows

**Enterprise data stays off-chain. Always.** Organization names, repositories, agent inventories, executive reports, prompts, recommendations, and customer information live in SQLite (`apps/api/data/`) exactly as they did before this phase — nothing about their storage changed. The blockchain layer only ever sees:

- A SHA-256 hash of a report's canonical JSON
- An opaque workspace identifier (`org_id`, never an org name)
- A timestamp and a version string
- Pricing metadata (service names, prices, currency — no customer data)
- Product version labels

## Why hashes, not content

Three reasons, all load-bearing:

1. **Base Sepolia (and Base Mainnet) are public.** Anything written to a contract is permanently, globally readable. Report contents include cost figures, security findings, and organizational structure — exactly the kind of information an enterprise customer would never accept on a public ledger.
2. **A hash is sufficient for the actual guarantee being made.** The point isn't "here is the report, trust the chain" — it's "here is proof this exact report existed, unmodified, at this time." A hash proves that precisely; the content adds nothing to the proof and everything to the exposure.
3. **Gas cost.** Storing even a modest JSON document on-chain costs orders of magnitude more than storing one `bytes32`. This isn't the primary reason (reason 1 alone would rule it out), but it reinforces the same design.

## Why not "on-chain application" at all

This is explicitly **not** an on-chain application — the product's actual workflows (Health Scan, Executive Report, Optimization Planner, Agent Registry, Enterprise Dashboard) run exactly as they did before this phase, entirely off-chain. Blockchain is a supporting layer bolted onto an existing SaaS product for three narrow purposes:

- **Trust** — a report's integrity can be independently verified by anyone, not just trusted because AgentOps Cloud says so (`VerificationGuide.md`).
- **Transparency** — pricing changes are auditable on a public ledger, not a silent database update (`FutureMonetization.md`).
- **Future monetization** — the pricing and payment-provider interfaces are ready for a paid tier without a redesign, whenever that's decided.

If a future phase wants agent identity or execution proofs on-chain (see `docs/Roadmap.md`'s Phase 5), it follows the same rule: hash and metadata on-chain, everything else stays in SQLite.

## Chain configuration

Base Sepolia today (`chain_id=84532`), Base Mainnet reserved (`chain_id=8453`, see `DeploymentGuide.md`). Every chain interaction goes through the `ChainProvider` ABC (`apps/api/app/services/chain/provider.py`) — mirrors the existing `LLMProvider` pattern (`app/services/llm/provider.py`) so a different chain client library, or a second network, is a new subclass, not a rewrite.
