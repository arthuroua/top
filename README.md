# Car Import MVP (Bidfax + Max Bid Advisor)

This repository contains the first working skeleton for a service focused on importing cars from US auctions.

## What is included

- `apps/api`: FastAPI backend with core MVP endpoints
- `apps/web`: Next.js frontend with VIN search page
- `docs/outreach`: ready email templates for Copart and IAA data-access requests
- `docker-compose.yml`: local stack with API, web, PostgreSQL, Redis, and ingestion worker
- `docs/DEPLOY.md`: deployment guide for production setup

## MVP API routes

- `GET /health`
- `GET /api/v1/search?vin=...`
- `GET /api/v1/vehicles/{vin}`
- `POST /api/v1/advisor/calculate`
- `POST /api/v1/reports`
- `GET /api/v1/reports?vin=...&limit=...`
- `GET /api/v1/reports/{id}`
- `GET /api/v1/reports/{id}/pdf`
- `POST /api/v1/reports/{id}/share`
- `GET /api/v1/reports/{id}/share`
- `GET /api/v1/reports/shared/{token}`

### Ingestion skeleton routes

- `POST /api/v1/ingestion/jobs`
- `GET /api/v1/ingestion/connectors`
- `POST /api/v1/ingestion/fetch-and-enqueue`
- `GET /api/v1/ingestion/runs?provider=...&failed_only=true&q=...&page=1&page_size=20&sort_by=created_at&sort_order=desc`
- `GET /api/v1/ingestion/runs/export.csv?provider=...&failed_only=true&q=...&sort_by=created_at&sort_order=desc&max_rows=5000`
- `GET /api/v1/ingestion/queue-depth`
- `POST /api/v1/ingestion/process-one`

### Connector modes

- `mock`: deterministic offline data for MVP/UI flow.
- `official`: HTTP adapter skeleton with:
  - auth headers (`*_API_AUTH_HEADER`, `*_API_TOKEN`, `*_API_KEY`)
  - retry/backoff (`*_API_RETRY_COUNT`, `*_API_RETRY_BACKOFF_MS`)
  - basic client-side rate limiting (`*_API_RATE_LIMIT_PER_SECOND`)
  - flexible mapping from provider payload to internal `IngestionJobPayload`

### Copart CSV scheduler

- Optional worker `copart-csv-scheduler` downloads Copart CSV and enqueues ingestion jobs.
- Default schedule is 2 fixed runs/day: `09:17,21:43` in `Europe/Kiev`.
- Configure via `.env`:
  - `COPART_CSV_ENABLED=true`
  - `COPART_CSV_AUTH_KEY=...`
  - `COPART_CSV_SCHEDULE_TIMES=09:17,21:43`
  - `COPART_CSV_TIMEZONE=Europe/Kiev`
  - `COPART_CSV_RUN_ON_START=false`
  - `COPART_CSV_MAX_ROWS_PER_RUN=0` (`0` = full file)
  - `COPART_CSV_DEDUPE_TTL_HOURS=168`

## Quick start (Docker)

1. Copy env file:

```bash
cp .env.example .env
```

2. Start stack:

```bash
docker compose up --build
```

3. Open:

- Web: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

## Production deploy

See [`docs/DEPLOY.md`](docs/DEPLOY.md).

## Database migrations

- The API container now runs `alembic upgrade head` automatically before starting Uvicorn.
- Existing databases without `alembic_version` are safely stamped during API startup via [`apps/api/app/db.py`](apps/api/app/db.py).
- Apply migrations from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate-api.ps1
```

- Create a new migration from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\make-migration.ps1 -Message "add new seo fields"
```

- Or use API-local scripts:

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\api\scripts\create-migration.ps1 -Message "add new seo fields"
```

```bash
cd apps/api
./scripts/create-migration.sh "add new seo fields"
```

- Verify Docker API startup and migration logs:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify-api-docker.ps1
```

- `GET /health` now returns the current migration revision.

## Quick ingestion demo

1. Enqueue a job:

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "Copart",
    "vin": "1HGCM82633A004352",
    "lot_number": "12345678",
    "sale_date": "2026-04-12",
    "hammer_price_usd": 5200,
    "status": "Sold",
    "location": "CA - Los Angeles",
    "images": ["https://img.example/1.jpg"],
    "price_events": [
      {
        "event_type": "sold_price",
        "old_value": "5000",
        "new_value": "5200",
        "event_time": "2026-04-12T10:00:00Z"
      }
    ]
  }'
```

2. Process one queued job via API (dev mode):

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/process-one
```

## Notes

- This skeleton uses mock vehicle/lot data to unblock product and UI development.
- Advisor reports are persisted in `advisor_reports` and linked to VIN.
- Ingestion worker writes to `vehicles`, `lots`, `lot_images`, and `price_events` tables.
- `GET /api/v1/search` and `GET /api/v1/vehicles/{vin}` read DB ingestion data first, then fallback to mock data.
- Vehicle card includes lot image links and price-event timeline when ingestion data contains them.
- Connector scaffolding is included for `copart` and `iaai` with `mock` mode via env:
  - `COPART_CONNECTOR_MODE=mock`
  - `IAAI_CONNECTOR_MODE=mock`
- In `official` mode, configure provider env vars in `.env`:
  - `*_API_BASE_URL`, `*_API_ENDPOINT_PATH`
  - `*_VIN_QUERY_PARAM`, `*_LOT_QUERY_PARAM`
  - `*_API_AUTH_HEADER`, `*_API_TOKEN` and/or `*_API_KEY`
  - `*_API_TIMEOUT_SECONDS`, `*_API_RETRY_COUNT`, `*_API_RETRY_BACKOFF_MS`, `*_API_RATE_LIMIT_PER_SECOND`
- If required official settings are missing, API returns clear config errors.
- Connector fetch calls are logged in `ingestion_connector_runs` (success/failure, latency, hashes, selector, queue result).
- Ingestion admin audit trail supports filters, pagination, CSV export, and optional auto-refresh.
- Frontend now includes:
  - `/reports` workspace with report history, VIN filter, PDF export, and share-link generation
  - `/shared/[token]` public client view for shared reports
- Real data ingestion should be connected only through licensed Copart/IAA channels.
