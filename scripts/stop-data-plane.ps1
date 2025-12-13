$ErrorActionPreference = 'Stop'

$rootDir = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $rootDir 'infra/docker-compose.yml'

if (-not (Test-Path $composeFile)) {
    Write-Error 'infra/docker-compose.yml is missing. Run from repo root.'
}

Write-Host '🛑 Stopping Compass data plane...'
docker compose -f $composeFile down
