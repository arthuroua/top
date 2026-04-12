from fastapi import APIRouter

from app.api.v1 import advisor, health, reports, search, vehicles

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(search.router)
api_router.include_router(vehicles.router)
api_router.include_router(advisor.router)
api_router.include_router(reports.router)
