#!/usr/bin/env bash
set -e
if [ -f .env ]; then set -a; source .env; set +a; fi
HOST="${ATLAS_HOST:-127.0.0.1}"
PORT="${ATLAS_PORT:-8001}"
echo "status:"; curl -s "http://${HOST}:${PORT}/api/status"; echo
echo "snapshot:"; curl -s "http://${HOST}:${PORT}/api/snapshot" | head -c 1200; echo
echo "ok"