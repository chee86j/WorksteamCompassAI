$ErrorActionPreference = 'Stop'

Write-Host '🔍 Checking Qdrant health...'
curl http://localhost:6333/healthz | Out-Null
Write-Host 'Qdrant responded OK.'

Write-Host '🔍 Checking Redis health...'
$redisPing = redis-cli -p 6379 ping
Write-Host $redisPing
