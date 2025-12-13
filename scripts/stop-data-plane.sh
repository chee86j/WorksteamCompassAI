#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/infra/docker-compose.yml"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "infra/docker-compose.yml is missing. Run from repo root."
  exit 1
fi

echo "🛑 Stopping Compass data plane..."
docker compose -f "${COMPOSE_FILE}" down
