# Folder Structure

```
agentops-cloud/
├── apps/
│   ├── web/                       Next.js 15 app (App Router)
│   │   ├── app/
│   │   │   ├── (marketing)/       Public landing page
│   │   │   └── (app)/             Clerk-gated shell: overview, agents, recommendations, activity, settings
│   │   ├── components/            App-specific client components (sidebar nav, tabs, forms)
│   │   ├── lib/                   api-client.ts (browser fetch), server-api.ts (RSC fetch + Clerk token)
│   │   └── middleware.ts          Clerk route protection
│   │
│   └── api/                       FastAPI app
│       ├── app/
│       │   ├── models/            SQLAlchemy models (9 tables) + enums
│       │   ├── schemas/           Pydantic request/response schemas
│       │   ├── api/v1/            Route handlers, one file per resource
│       │   ├── services/          Business logic — agent, recommendation, activity, connector, settings, llm
│       │   ├── auth/clerk.py      JWKS-based JWT verification (skipped if unconfigured)
│       │   ├── jobs/tasks.py      Background job entry points (plain functions today, Celery-ready)
│       │   ├── database.py, config.py, main.py
│       ├── alembic/                Migrations
│       └── data/                   SQLite database file lives here (gitignored)
│
├── packages/
│   ├── ui/                        Shared design system (Card, Table, Badge, StatusPill, MetricCard, Sidebar, Button, Dialog, Alert)
│   ├── shared-types/               Zod schemas + TS types mirroring the API's Pydantic schemas
│   ├── config/                     Shared Tailwind preset + base tsconfig
│   └── sdk/
│       ├── python/                 agentops-cloud (pip) — reserved, Phase 2
│       └── node/                    @agentops/sdk (npm) — reserved, Phase 2
│
├── docs/                            You are here
├── scripts/                         bootstrap.sh, dev.sh, seed_db.py
├── infrastructure/                  Reserved for a real deploy target (empty today — no Docker in the MVP)
├── turbo.json
└── package.json                     npm workspaces root
```

## Why `apps/api` isn't in the npm workspace graph

It has its own `pyproject.toml` and its own virtualenv (`apps/api/.venv`). Turborepo only orchestrates `apps/web` + `packages/*`. Root scripts (`scripts/dev.sh`, `scripts/bootstrap.sh`) shell out to the API's own tooling instead of trying to make one build tool understand two languages.
