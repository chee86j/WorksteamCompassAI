$ErrorActionPreference = 'Stop'

$rootDir = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $rootDir 'infra/docker-compose.yml'

if (-not (Test-Path $composeFile)) {
    Write-Error 'infra/docker-compose.yml is missing. Run from repo root.'
}

Write-Host '🚀 Starting Compass data plane (Qdrant + Redis)...'
docker compose -f $composeFile up -d

Write-Host '⏱  Waiting for containers to report healthy...'
docker compose -f $composeFile ps

Write-Host '🔎 Check health once they settle:'
Write-Host '    curl http://localhost:6333/healthz'
Write-Host '    redis-cli -p 6379 ping'
