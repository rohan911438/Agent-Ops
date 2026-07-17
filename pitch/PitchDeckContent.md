# Pitch Deck Content — AgentOps Cloud (Team Brotherhood)

Source-of-truth facts for the 6–7 slide deck, pulled from the live repo (`README.md`, `docs/`). Use this to fact-check whatever the AI deck tool in `PitchDeckPrompt.md` produces.

---

## Slide 1 — Cover
- **Product**: AgentOps Cloud
- **Tagline**: The Enterprise Control Plane for AI Agents
- **Team**: Brotherhood
- **Proof-of-life line**: Live on Vercel (web) + Railway (API) + Base Sepolia (trust layer)
- Live links: `agentops-cloud-web.vercel.app` / `agentops-api-production.up.railway.app`

## Slide 2 — Problem
**Headline:** Every company has an AI agent sprawl problem — and no one can see it.

As companies adopt AI, agents pile up across LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, n8n, MCP servers, and custom code — built by different teams, for different purposes, with no shared system of record.

Nobody can confidently answer:
1. What AI agents do we actually have?
2. What are they doing, and what do they cost?
3. Who owns each one, and what can it access?
4. What's the highest-leverage thing to fix first?

## Slide 3 — Solution
**Headline:** One control plane, above every framework — not another one to replace them.

- **Discover** — inventory every agent across frameworks in one place
- **Diagnose** — AI-generated Executive Report scoring cost, security, and operational risk
- **Act** — a ranked, explainable Optimization Plan (Immediate Wins / 30-Day / 90-Day / Long-Term Architecture)

Every recommendation and every plan rating (priority, effort, risk, confidence) comes from an explicit, inspectable rule — never a black box.

## Slide 4 — Product / How It Works
**Headline:** From zero to a full fleet report in minutes.

1. **Connect** — upload a JSON/YAML agent manifest, or connect a GitHub repo
2. **Scan** — Enterprise Health Scan discovers, analyzes, and reasons over the fleet in real time
3. **Report** — nine-section Executive Report: executive summary, org overview, cost analysis, security risks, operational risks, optimization opportunities, business impact, priority actions, overall health score
4. **Verify** — the report is hashed and sealed on-chain

Auth is wallet-native: OKX Wallet challenge-response sign-in, no passwords, no third-party identity provider (Google/Microsoft/Okta/SAML reserved as future sibling providers).

Also live: a searchable activity timeline and an at-a-glance overview (agents found, monthly cost, open risks, optimization opportunities).

## Slide 5 — Architecture
**Headline:** Built as real infrastructure, not a demo.

```
Browser (Next.js 15, Vercel)
        │  same-origin — /api/v1/* rewritten server-side
        ▼
FastAPI /api/v1 (Railway) → Postgres (prod) / SQLite (local), org-scoped
        │                  ↘ Rule-based recommendation engine
        │  hash only, after report generation — never blocks the scan
        ▼
Base Sepolia: EnterpriseReportRegistry · ServicePricing · AgentOpsRegistry
```

- **Trust layer**: only a hash + small metadata ever reach the chain — report content and org data never leave the database. A chain failure never blocks a scan; the report view just omits the integrity card.
- **Pluggable connectors**: GitHub is live today (scans root-level `requirements.txt` / `pyproject.toml` / `package.json` for framework markers). LangGraph, CrewAI, MCP, Kubernetes, cloud-provider connectors, and an SDK for automatic agent discovery are architected in for later phases.
- **Stack**: Next.js 15 · TypeScript · Tailwind · shadcn/ui · FastAPI · SQLAlchemy 2.0 (async) · Alembic · Postgres/SQLite · Solidity `^0.8.24` + OpenZeppelin + Hardhat · web3.py · Base Sepolia · Turborepo.

**Deployed contracts (Base Sepolia):**
| Contract | Purpose |
|---|---|
| `EnterpriseReportRegistry` | anchors report hashes |
| `ServicePricing` | serves live pricing on-chain |
| `AgentOpsRegistry` | registry layer |

## Slide 6 — GTM / Business Model
**Headline:** Land with platform teams, expand into the enterprise control plane.

- **Phase 1 (now)**: free, self-serve Health Scan targeting AI-forward engineering teams and Web3-native orgs already in the OKX/Base ecosystem. GitHub connector is the low-friction hook — no token, no setup, results in one scan.
- **Phase 2**: enterprise pilots with platform/security teams who need an agent inventory for compliance, cost control, and risk visibility. Land via a single Health Scan, expand into continuous monitoring.
- **Monetization**: tiered plans (Free / Team / Enterprise). Pricing is already served live from an on-chain `ServicePricing` contract today (everything shows FREE — "future enterprise plans may introduce paid services"), and a `PaymentProvider` abstraction is scaffolded for a future x402 integration — metering and billing rails exist before the paywall does.
- **Moat**: framework-agnostic by design (sits above LangGraph, CrewAI, AutoGen, custom code alike) + a cryptographically verifiable audit trail no competitor currently offers.

## Slide 7 — Roadmap / Team / Ask (optional 7th slide; fold into Slide 6 if only 6 are needed)
- **Roadmap**: Phase 3 — real connectors (LangGraph, CrewAI, MCP, Kubernetes, cloud providers) + auto-discovery SDK → Phase 5 — continuous monitoring & alerting → Phase 6 — mainnet + paid plans live.
- **Team**: Brotherhood.
- **The ask**: pilot design partners, funding, or hackathon judging criteria — fill in based on the actual audience before presenting; not fixed in the product itself.

---

### What this product deliberately is NOT (useful for Q&A)
No marketplace, no chat interface, no billing yet, no notification center, no vanity dashboards. Six pages, one job: give an enterprise a clear picture of its AI agent fleet and a ranked list of what to do about it.
