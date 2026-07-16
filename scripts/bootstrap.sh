#!/usr/bin/env bash
# One-time local setup: Python venv + API deps, npm workspace install, DB migration.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== apps/api: creating virtualenv and installing dependencies =="
cd "$ROOT_DIR/apps/api"
python -m venv .venv || python3 -m venv .venv
VENV_PY=".venv/Scripts/python.exe"
[ -x "$VENV_PY" ] || VENV_PY=".venv/bin/python"
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -e .
[ -f .env ] || cp .env.example .env
mkdir -p data

echo "== apps/api: running migrations =="
"$VENV_PY" -m alembic upgrade head

echo "== root: installing npm workspaces =="
cd "$ROOT_DIR"
npm install
[ -f apps/web/.env.local ] || cp apps/web/.env.example apps/web/.env.local

echo "== seeding dev data =="
"$ROOT_DIR/apps/api/.venv/Scripts/python.exe" "$ROOT_DIR/scripts/seed_db.py" 2>/dev/null \
  || "$ROOT_DIR/apps/api/.venv/bin/python" "$ROOT_DIR/scripts/seed_db.py"

echo ""
echo "Done. Run ./scripts/dev.sh to start the API + web app."
