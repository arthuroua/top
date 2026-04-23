# Railway Deploy

This project deploys cleanly to Railway using separate services.

## Recommended Railway services

1. `web` from `apps/web`
2. `api` from `apps/api`
3. PostgreSQL service
4. Redis service
5. optional `ingestion-worker` from `apps/api`
6. optional `copart-csv-scheduler` from `apps/api`

## 1. Web service

Source repo: your GitHub repo
Root directory: `apps/web`
Builder: Dockerfile

Required env vars:

- `NEXT_PUBLIC_API_BASE_URL=https://YOUR_API_DOMAIN`
- `API_INTERNAL_BASE_URL=https://YOUR_API_DOMAIN`
- `NEXT_PUBLIC_SITE_URL=https://YOUR_WEB_DOMAIN`
- `SEO_API_ENABLED=true`
- `MARKET_API_ENABLED=true`

## 2. API service

Source repo: your GitHub repo
Root directory: `apps/api`
Builder: Dockerfile

Required env vars:

- `DATABASE_URL=${{Postgres.DATABASE_URL}}`
- `REDIS_URL=${{Redis.REDIS_URL}}`
- `INGESTION_QUEUE_KEY=ingestion:jobs`
- `ADMIN_TOKEN=change-this-to-a-secret`
- `MEDIA_PROXY_ALLOWED_HOSTS=copart.com,iaai.com,riastatic.com`
- `HIDE_DATA_SOURCE=true`
- `PUBLIC_SOURCE_LABEL=market`
- `COPART_CONNECTOR_MODE=mock`
- `IAAI_CONNECTOR_MODE=mock`
- `COPART_CSV_ENABLED=false`

The API Docker image now respects Railway's dynamic `PORT`.

## 3. Worker service

Optional, but recommended if you want background ingestion.

Source repo: same repo
Root directory: `apps/api`
Builder: Dockerfile

Start command:

```bash
python -m app.workers.ingestion_worker
```

Env vars:

- same as API for `DATABASE_URL`, `REDIS_URL`, and connector settings

## 4. Copart CSV scheduler service

Optional. Turn it on only when you are ready to run regular imports.

Source repo: same repo
Root directory: `apps/api`
Builder: Dockerfile

Start command:

```bash
python -m app.workers.copart_csv_scheduler
```

Required env vars:

- `REDIS_URL=${{Redis.REDIS_URL}}`
- `INGESTION_QUEUE_KEY=ingestion:jobs`
- `COPART_CSV_ENABLED=true`
- `COPART_CSV_AUTH_KEY=YOUR_KEY`
- `COPART_CSV_URL_TEMPLATE=https://inventory.copart.io/FTPLSTDM/salesdata.cgi?authKey={auth_key}`
- `COPART_CSV_SCHEDULE_TIMES=09:17,21:43`
- `COPART_CSV_TIMEZONE=Europe/Kiev`
- `COPART_CSV_RUN_ON_START=false`

## First production-safe launch

If you want the cleanest first deploy, launch only:

- `web`
- `api`
- `postgres`
- `redis`

Then add:

- `ingestion-worker`
- `copart-csv-scheduler`

after the main site is confirmed live.

## Smoke check after deploy

Open:

- `/`
- `/search`
- `/auto/5YJ3E1EA3JF053140`
- `/watchlist`
- `/health`
- `/docs`
