# Car Import MVP (Bidfax + Max Bid Advisor)

This repository contains the first working skeleton for a service focused on importing cars from US auctions.

## What is included

- `apps/api`: FastAPI backend with core MVP endpoints
- `apps/web`: Next.js frontend with VIN search page
- `docs/outreach`: ready email templates for Copart and IAA data-access requests
- `docker-compose.yml`: local stack with API, web, PostgreSQL, and Redis

## MVP API routes

- `GET /health`
- `GET /api/v1/search?vin=...`
- `GET /api/v1/vehicles/{vin}`
- `POST /api/v1/advisor/calculate`
- `POST /api/v1/reports`
- `GET /api/v1/reports/{id}`
- `GET /api/v1/reports/{id}/pdf`

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

## Notes

- This skeleton uses mock vehicle/lot data to unblock product and UI development.
- Advisor reports are persisted in `advisor_reports` and linked to VIN.
- Real data ingestion should be connected only through licensed Copart/IAA channels.
