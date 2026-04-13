# Car Import MVP (Bidfax + Max Bid Advisor)

This repository contains the first working skeleton for a service focused on importing cars from US auctions.

## What is included

- `apps/api`: FastAPI backend with core MVP endpoints
- `apps/web`: Next.js frontend with VIN search page
- `docs/outreach`: ready email templates for Copart and IAA data-access requests
- `docker-compose.yml`: local stack with API, web, PostgreSQL, Redis, and ingestion worker

## MVP API routes

- `GET /health`
- `GET /api/v1/search?vin=...`
- `GET /api/v1/vehicles/{vin}`
- `POST /api/v1/advisor/calculate`
- `POST /api/v1/reports`
- `GET /api/v1/reports/{id}`
- `GET /api/v1/reports/{id}/pdf`

### Ingestion skeleton routes

- `POST /api/v1/ingestion/jobs`
- `GET /api/v1/ingestion/queue-depth`
- `POST /api/v1/ingestion/process-one`

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
- Real data ingestion should be connected only through licensed Copart/IAA channels.
