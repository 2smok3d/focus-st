$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (!(Test-Path .env)) { Copy-Item .env.example .env }
New-Item -ItemType Directory -Force runtime-data/inbox,runtime-data/raw,runtime-data/normalized,runtime-data/manual-index | Out-Null
docker compose -f docker-compose.turnkey.yml up -d --build
Write-Host 'Digital Garage API: http://localhost:8080/docs'
Write-Host 'Dashboard: http://localhost:8090/dashboard.html'
