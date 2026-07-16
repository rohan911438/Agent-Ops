# Technical Decisions

This is the record of what was chosen and why. Update it when a decision changes — don't leave it stale.

| Area | Choice | Why |
|---|---|---|
| Monorepo orchestration | npm workspaces + Turborepo | Standard for Next.js multi-package repos; npm chosen over pnpm for zero extra tooling to install. |
| Python deps | plain `venv` + `pip -e .`, `pyproject.toml` for metadata | No Docker, no external package manager install required — works with whatever Python is already on the machine. `uv` is a drop-in upgrade later if install speed becomes a problem. |
| Database | **SQLite** (`sqlite+aiosqlite`), single file at `apps/api/data/agentops.db` | Originally scoped as PostgreSQL + Docker Compose. Changed mid-build: no Docker, no separate DB server to install — a file-based database that lives in a folder needs nothing running. SQLAlchemy + Alembic are unchanged; swapping back to Postgres later is a one-line `DATABASE_URL` change plus re-pointing `asyncpg` in `pyproject.toml`. |
| ORM/migrations | SQLAlchemy 2.0 (async, `aiosqlite`) + Alembic | Async-native, mature, swappable database backend. |
| Background jobs | Plain async functions (`app/jobs/tasks.py`), invoked directly by the seed script and by `POST /recommendations/refresh` | Originally scoped as Celery + Redis. Dropped for the MVP because there's no broker running (no Docker) and nothing in the MVP needs a queue — the recommendation engine runs synchronously over seeded data in well under a second. The function signatures are written so wrapping them as Celery tasks later doesn't change their bodies, only how they're invoked. |
| Auth | Clerk | First-class **Organizations**, mapping directly onto the "Workspace" concept. FastAPI verifies Clerk JWTs via JWKS — no session table. **Auth is skipped entirely when `CLERK_JWKS_URL`/`CLERK_ISSUER` are unset**, so the API and seeded UI run with zero Clerk setup in local dev. |
| AI abstraction | `LLMProvider` ABC (`app/services/llm/provider.py`), one concrete `OpenAIProvider` | Anthropic/Gemini/DeepSeek/Groq/OpenRouter become additional subclasses later with no call-site changes. |
| Blockchain | Base network; `wallets` table + nullable `tx_hash` on `activity_events` | Wallet *connection* only — no proof/anchoring logic. Reserved schema, not implemented. |
| Recommendation engine | Rule-based (`app/services/recommendation_service.py`), not ML | **State this plainly wherever the product is described.** The MVP engine is six explicit, explainable rules (unused agent, high cost, likely duplicate, high-risk permission, orphaned/no owner, model downgrade) run over real data. It is not a learned model. Swapping in one later only touches this module — the API and UI don't change. |
| Scan orchestration | FastAPI `BackgroundTasks`, no new broker (`app/services/scan_service.py`) | The Health Scan wizard needs genuine multi-step async progress (parse → ingest → analyze → generate report) that a request/response cycle can't show. `BackgroundTasks` gives real backgrounding without reintroducing Celery/Redis ahead of Phase 3 — `run_scan` opens its own session via the `async_session_factory` idiom already established in `app/jobs/tasks.py`. |
| Executive Report generation | `app/services/scan/report_service.py`, LLM with a deterministic fallback | Must render a complete report with **zero external config** — if `OPENAI_API_KEY` is unset, or the LLM call/JSON parse fails, it falls back to a template built directly from the same rule-engine data. Mirrors the "auth skipped when unconfigured" philosophy used elsewhere in this MVP. |
| Containerization | None for the MVP | Removed to keep local setup to "install Python + Node, run two commands." `infrastructure/` is reserved for when a real deploy target (not just local dev) needs Docker/Compose. |

## Deviations from the original architecture plan

The approved architecture assumed PostgreSQL, Docker Compose, pnpm, and Celery/Redis. Partway through the build the constraint changed ("don't have much time, avoid Docker and Postgres, use npm") and the plan was adapted live:

- pnpm → npm workspaces (no functional difference, `turbo.json` untouched)
- PostgreSQL → SQLite (schema, models, and API contract identical — only `DATABASE_URL` and the driver package differ)
- Docker Compose → removed (nothing to run besides `python` and `node`)
- Celery + Redis → removed as a hard dependency; the recommendation engine and any future scheduled job are plain async functions today, Celery-ready by structure

None of these changes the API surface, the database schema, or the frontend. They only change what you have to install to run it locally.
