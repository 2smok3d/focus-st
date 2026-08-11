#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
mkdir -p runtime-data/inbox runtime-data/raw runtime-data/normalized runtime-data/manual-index
docker compose -f docker-compose.turnkey.yml up -d --build
printf '%s\n' 'Digital Garage API: http://localhost:8080/docs' 'Dashboard: http://localhost:8090/dashboard.html'
