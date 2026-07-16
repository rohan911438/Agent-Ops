# Folder Structure

```
agentops-cloud/
├── apps/
│   ├── web/                       Next.js 15 app (App Router)
│   │   ├── app/
│   │   │   ├── (marketing)/       Public landing page (single primary CTA → Connect OKX Wallet)
│   │   │   └── (app)/             Session-gated shell: health-scan, overview, agents, recommendations, activity, settings
│   │   ├── components/            App-specific client components (sidebar nav, tabs, forms)
│   │   │   ├── auth/               connect-wallet-button.tsx, sign-out-button.tsx
│   │   │   └── health-scan/       data-source-picker.tsx, scan-status.tsx, optimization-plan.tsx
│   │   ├── lib/                   api-client.ts (browser fetch), server-api.ts (RSC fetch + cookie forwarding), okx-wallet.ts
│   │   └── middleware.ts          Session-cookie route protection (edge JWT verify via `jose`)
│   │
│   └── api/                       FastAPI app
│       ├── app/
│       │   ├── models/            SQLAlchemy models (incl. health_scan.py, auth_challenge.py) + enums
│       │   ├── schemas/           Pydantic request/response schemas (incl. auth.py)
│       │   ├── api/v1/            Route handlers, one file per resource (incl. scans.py, auth.py)
│       │   ├── services/          Business logic — agent, recommendation, activity, connector, settings, llm, scan_service
│       │   │   ├── scan/          parsers.py, cost_estimator.py, report_service.py, optimization_plan_service.py
│       │   │   └── connectors/    github_adapter.py — the one real, registered ConnectorAdapter
│       │   ├── auth/               session.py (JWT issue/verify), providers/wallet.py (OKX challenge-response)
│       │   ├── jobs/tasks.py      Background job entry points (plain functions today, Celery-ready)
│       │   ├── database.py, config.py, main.py
│       ├── alembic/                Migrations
│       ├── tests/                  pytest + httpx ASGI tests (auth flow, report/plan fallback shape)
│       └── data/                   SQLite database file lives here (gitignored)
│
├── packages/
│   ├── ui/                        Shared design system (Card, Table, Badge, StatusPill, MetricCard, Sidebar, Stepper, Button, Dialog, Alert)
│   ├── shared-types/               Zod schemas + TS types mirroring the API's Pydantic schemas
│   ├── config/                     Shared Tailwind preset + base tsconfig
│   └── sdk/
│       ├── python/                 agentops-cloud (pip) — reserved, later phase
│       └── node/                    @agentops/sdk (npm) — reserved, later phase
│
├── docs/                            You are here
├── scripts/                         bootstrap.sh, dev.sh, seed_db.py, fixtures/sample-agents.json
├── infrastructure/                  Reserved for a real deploy target (empty today — no Docker in the MVP)
├── turbo.json
└── package.json                     npm workspaces root
```

## Why `apps/api` isn't in the npm workspace graph

It has its own `pyproject.toml` and its own virtualenv (`apps/api/.venv`). Turborepo only orchestrates `apps/web` + `packages/*`. Root scripts (`scripts/dev.sh`, `scripts/bootstrap.sh`) shell out to the API's own tooling instead of trying to make one build tool understand two languages.
