#!/usr/bin/env bash

set -euo pipefail

echo '🔍 Checking Qdrant health...'
curl -sf http://localhost:6333/healthz
echo

echo '🔍 Checking Redis health...'
redis-cli -p 6379 ping
