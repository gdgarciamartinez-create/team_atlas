#!/usr/bin/env bash
set -e
if [ -f .env ]; then set -a; source .env; set +a; fi
cd src/atlas/frontend
npm install
npm run dev -- --port "${ATLAS_UI_PORT:-3000}"