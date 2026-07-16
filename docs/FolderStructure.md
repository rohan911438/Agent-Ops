# Folder Structure

```
agentops-cloud/
├── apps/
│   ├── web/                       Next.js 15 app (App Router)
│   │   ├── app/
│   │   │   ├── (marketing)/       Public landing page (primary CTA → Health Scan)
│   │   │   └── (app)/             Clerk-gated shell: health-scan, overview, agents, recommendations, activity, settings
│   │   ├── components/            App-specific client components (sidebar nav, tabs, forms)
│   │   │   └── health-scan/       data-source-picker.tsx, scan-status.tsx
│   │   ├── lib/                   api-client.ts (browser fetch), server-api.ts (RSC fetch + Clerk token)
│   │   └── middleware.ts          Clerk route protection
│   │
│   └── api/                       FastAPI app
│       ├── app/
│       │   ├── models/            SQLAlchemy models (10 tables, incl. health_scan.py) + enums
│       │   ├── schemas/           Pydantic request/response schemas
│       │   ├── api/v1/            Route handlers, one file per resource (incl. scans.py)
│       │   ├── services/          Business logic — agent, recommendation, activity, connector, settings, llm, scan_service
│       │   │   ├── scan/          parsers.py, cost_estimator.py, report_service.py
│       │   │   └── connectors/    github_adapter.py — the one real, registered ConnectorAdapter
│       │   ├── auth/clerk.py      JWKS-based JWT verification (skipped if unconfigured)
│       │   ├── jobs/tasks.py      Background job entry points (plain functions today, Celery-ready)
│       │   ├── database.py, config.py, main.py
│       ├── alembic/                Migrations
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
