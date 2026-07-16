# Contributing

## Local setup

```bash
./scripts/bootstrap.sh   # one-time: venv + pip install, npm install, migrate, seed
./scripts/dev.sh          # every time: runs API (port 8000) + web (port 3000)
```

No Docker, no Postgres, no Redis to install — see `docs/TechnicalDecisions.md` for why.

Manual setup, if you'd rather not use the scripts:

```bash
# API
cd apps/api
python -m venv .venv
.venv/Scripts/pip install -e .          # .venv/bin/pip on macOS/Linux
cp .env.example .env
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn app.main:app --reload

# Web (separate terminal, from repo root)
npm install
cp apps/web/.env.example apps/web/.env.local
npm run dev --workspace=@agentops/web
```

## Conventions

- **Service layer owns business logic.** Route handlers in `apps/api/app/api/v1/*.py` stay thin — they resolve the org, call a service function, return the result. Put logic in `apps/api/app/services/`, not in routes.
- **Org scoping is not optional.** Every new table gets an `org_id` FK and an index on it. Every new service function takes `org_id` as an explicit argument — never infer it from anything other than `get_current_org`.
- **Don't fake unimplemented features.** If a phase-2+ capability doesn't exist yet (a connector adapter, an SDK method), the code should say so explicitly (a `NotImplementedError`, a 501, a docstring pointing at `docs/Roadmap.md`) rather than a UI element that looks live but does nothing.
- **Design system first.** New UI primitives go in `packages/ui`, not directly in `apps/web`. `apps/web` should never import shadcn directly.
- **Shared types stay in sync.** If you change a Pydantic schema in `apps/api/app/schemas/`, update the matching Zod schema in `packages/shared-types/src/index.ts` in the same change.

## Before opening a PR

- `apps/api`: routes you touched still return what `docs/API_Design.md` says they do
- `apps/web`: `npm run typecheck --workspace=@agentops/web`
- New tables: an Alembic migration, not a hand-edited `alembic_version`
