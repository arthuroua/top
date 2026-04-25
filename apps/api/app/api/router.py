from fastapi import APIRouter

from app.api.v1 import advisor, autoria, health, ingestion, market, media, reports, search, seo_pages, vehicles, vin_decoder

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(search.router)
api_router.include_router(vehicles.router)
api_router.include_router(media.router)
api_router.include_router(advisor.router)
api_router.include_router(reports.router)
api_router.include_router(ingestion.router)
api_router.include_router(market.router)
api_router.include_router(seo_pages.router)
api_router.include_router(vin_decoder.router)
api_router.include_router(autoria.router)
