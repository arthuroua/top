# Deploy Guide

This project is ready to deploy with the following recommended topology:

- `web`: Next.js 15 frontend
- `api`: FastAPI backend
- `db`: PostgreSQL
- `redis`: Redis
- `ingestion-worker`: background worker
- `copart-csv-scheduler`: optional scheduler for CSV imports
- `enrichment-worker`: background worker for photo enrichment
- `enrichment-scheduler`: optional scheduler that auto-enqueues lots missing photos

## Recommended stack

For the cleanest first production deploy, use one platform for the full backend stack:

- Render or Railway for `api`, `db`, `redis`, `worker`, and `scheduler`
- Render, Railway, or Coolify for `web`

If you want the simplest first launch, keep both `web` and `api` on the same platform.

## Web deploy

Directory: `apps/web`

Build:

```bash
npm ci
npm run build
```

Start:

```bash
node .next/standalone/server.js
```

Required env vars:

- `NEXT_PUBLIC_API_BASE_URL=https://YOUR-API-DOMAIN`
- `API_INTERNAL_BASE_URL=https://YOUR-API-DOMAIN`
- `NEXT_PUBLIC_SITE_URL=https://YOUR-WEB-DOMAIN`
- `SEO_API_ENABLED=true`
- `MARKET_API_ENABLED=true`

## API deploy

Directory: `apps/api`

The API Docker image already applies Alembic migrations automatically before startup.

Required env vars:

- `DATABASE_URL`
- `REDIS_URL`
- `INGESTION_QUEUE_KEY`
- `API_PORT=8000`
- `ADMIN_TOKEN`
- `MEDIA_PROXY_ALLOWED_HOSTS`
- `HIDE_DATA_SOURCE=true`
- `PUBLIC_SOURCE_LABEL=market`

Optional but important env vars:

- `COPART_CONNECTOR_MODE=mock|official`
- `IAAI_CONNECTOR_MODE=mock|official`
- `COPART_CSV_ENABLED=true|false`
- `COPART_CSV_AUTH_KEY=...`
- `COPART_CSV_URL_TEMPLATE=https://inventory.copart.io/FTPLSTDM/salesdata.cgi?authKey={auth_key}`

Health endpoint:

- `GET /health`

## Worker deploy

Use the same image as `apps/api`.

Command:

```bash
python -m app.workers.ingestion_worker
```

Env vars:

- same as API for `DATABASE_URL`, `REDIS_URL`, and connector settings

## Enrichment worker deploy

Use the same image as `apps/api`.

Command:

```bash
python -m app.workers.enrichment_worker
```

Env vars:

- `DATABASE_URL`
- `REDIS_URL`
- `ENRICHMENT_QUEUE_KEY`
- `MEDIA_ARCHIVE_ALLOWED_HOSTS`
- `MEDIA_ARCHIVE_DIR`
- `MEDIA_ARCHIVE_MAX_BYTES`
- `MEDIA_ARCHIVE_TIMEOUT_SECONDS`
- `ENRICHMENT_MAX_IMAGES_PER_LOT`
- `ENRICHMENT_VERIFY_IMAGE_URLS`
- `ENRICHMENT_IMAGE_HEAD_TIMEOUT_SECONDS`
- `ENRICHMENT_REQUEST_DELAY_MS`
- `IAAI_GALLERY_TIMEOUT_SECONDS`
- `IAAI_GALLERY_RETRY_COUNT`
- `IAAI_GALLERY_RETRY_BACKOFF_MS`
- `IAAI_GALLERY_MAX_IMAGES_PER_LOT`

## Enrichment scheduler deploy

Use the same image as `apps/api`.

Command:

```bash
python -m app.workers.enrichment_scheduler
```

Recommended env vars:

- `DATABASE_URL`
- `REDIS_URL`
- `ENRICHMENT_QUEUE_KEY`
- `ENRICHMENT_SCHEDULER_ENABLED=true`
- `ENRICHMENT_SCHEDULER_RUN_ON_START=true`
- `ENRICHMENT_SCHEDULER_INTERVAL_SECONDS=900`
- `ENRICHMENT_SCHEDULER_SOURCE=all`
- `ENRICHMENT_SCHEDULER_SCAN_LIMIT=500`
- `ENRICHMENT_SCHEDULER_ENQUEUE_LIMIT=150`
- `ENRICHMENT_SCHEDULER_MAX_EXISTING_IMAGES=0`
- `ENRICHMENT_SCHEDULER_MAX_QUEUE_DEPTH=2000`

How it works:

- Scheduler scans the latest lots.
- Lots with `<= ENRICHMENT_SCHEDULER_MAX_EXISTING_IMAGES` photos are added to Redis queue.
- If queue depth is already high, scheduler skips the cycle so it does not flood Redis.
- `enrichment-worker` consumes the queue continuously and writes real photos into DB/media archive.

## Scheduler deploy

Use the same image as `apps/api`.

Command:

```bash
python -m app.workers.copart_csv_scheduler
```

Env vars:

- `REDIS_URL`
- `INGESTION_QUEUE_KEY`
- `COPART_CSV_ENABLED=true`
- `COPART_CSV_AUTH_KEY`
- `COPART_CSV_URL_TEMPLATE`
- `COPART_CSV_SCHEDULE_TIMES`
- `COPART_CSV_TIMEZONE`
- `COPART_CSV_RUN_ON_START=false`

## Production checklist

1. Set a real `ADMIN_TOKEN`
2. Point `NEXT_PUBLIC_SITE_URL` to the final domain
3. Point both `NEXT_PUBLIC_API_BASE_URL` and `API_INTERNAL_BASE_URL` to the live API URL
4. Keep `HIDE_DATA_SOURCE=true` if you do not want to reveal source branding in the UI
5. Verify these URLs after deploy:
   - `/`
   - `/search`
   - `/auto/5YJ3E1EA3JF053140`
   - `/cars`
   - `/watchlist`
   - `/health`
   - `/docs`

## Fast local smoke test

```bash
cd J:\car-import-mvp
```

API:

```bash
cd apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Web:

```bash
cd apps/web
npm run build
node .next/standalone/server.js
```
