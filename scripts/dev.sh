#!/usr/bin/env bash
# Runs the API and the web app together for local dev. No Docker involved —
# the API talks to a local SQLite file, so this is the only script needed.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
VENV_PY="$API_DIR/.venv/Scripts/python.exe"
[ -x "$VENV_PY" ] || VENV_PY="$API_DIR/.venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
  echo "No virtualenv found at apps/api/.venv — create one first:"
  echo "  cd apps/api && python -m venv .venv && .venv/Scripts/pip install -e ."
  exit 1
fi

cleanup() { kill 0; }
trap cleanup EXIT

(cd "$API_DIR" && "$VENV_PY" -m alembic upgrade head && "$VENV_PY" -m uvicorn app.main:app --reload --port 8000) &
(cd "$ROOT_DIR" && npm run dev --workspace=@agentops/web) &

wait
