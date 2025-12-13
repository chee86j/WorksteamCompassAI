#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/infra/docker-compose.yml"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "infra/docker-compose.yml is missing. Run from repo root."
  exit 1
fi

echo "🚀 Starting Compass data plane (Qdrant + Redis)..."
docker compose -f "${COMPOSE_FILE}" up -d

echo "⏱  Waiting for containers to report healthy..."
docker compose -f "${COMPOSE_FILE}" ps

echo "🔎 Check health once they settle:"
echo "    curl http://localhost:6333/healthz"
echo "    redis-cli -p 6379 ping"
