#!/usr/bin/env bash
set -e
export PYTHONUNBUFFERED=1
if [ -f .env ]; then set -a; source .env; set +a; fi
HOST="${ATLAS_HOST:-127.0.0.1}"
PORT="${ATLAS_PORT:-8001}"
uvicorn atlas.main:app --host "$HOST" --port "$PORT" --reload