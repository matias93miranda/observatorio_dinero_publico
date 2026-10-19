#!/usr/bin/env bash
# Uso: scripts/run_linux.sh [setup|sync|test|serve|dev]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
cmd="${1:-serve}"
case "$cmd" in
  setup)
    python3 -m venv "$ROOT/.venv"
    "$PY" -m pip install -r "$ROOT/backend/requirements.txt"
    (cd "$ROOT/frontend" && npm ci && npm run build) ;;
  sync)  (cd "$ROOT/backend" && "$PY" -m observatorio.cli sync "${@:2}") ;;
  test)  (cd "$ROOT/backend" && "$PY" -m pytest -q) ;;
  serve) (cd "$ROOT/backend" && "$PY" -m uvicorn observatorio.api:app --host 127.0.0.1 --port 8000) ;;
  dev)   (cd "$ROOT/backend" && "$PY" -m uvicorn observatorio.api:app --reload --port 8000 &)
         (cd "$ROOT/frontend" && npm run dev) ;;
  *) echo "comando desconocido: $cmd"; exit 1 ;;
esac
