# Turn-Key Deployment

## Windows
Prerequisites: Docker Desktop + Git. Clone the repo, checkout `openai/digital-garage`, enter `digital-garage-openai`, and run `powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1`.

## Linux/WSL
Install Docker Engine/Compose plugin + Git. Clone/checkout the branch, then `chmod +x scripts/bootstrap.sh && ./scripts/bootstrap.sh`.

## Services
- API/OpenAPI: `http://localhost:8080/docs`
- Dashboard: `http://localhost:8090/dashboard.html`
- PostgreSQL: internal `db:5432`
- MCP: stdio via `python -m garage.mcp_server` inside the garage service.

## Diagnostic ingest
Copy a FORScan/candump file to `runtime-data/inbox/`, then:
`docker compose -f docker-compose.turnkey.yml exec garage python -m garage.persist /data/inbox/FILE`
Raw bytes are copied to hash-addressed raw storage and a normalized JSON derivative is created; duplicate hashes for the same vehicle are rejected by the persistence layer.

## Manuals
Point `python -m garage.manual_index` at a local directory containing legitimately owned service/wiring files. The output contains filenames, MIME/extension, size and SHA-256 only; the tool does not redistribute manual content.

## Backup
Back up the PostgreSQL volume plus `runtime-data/raw`, `runtime-data/normalized`, generated service-library index files and the Drive garage folder. Source code is already versioned in GitHub.
