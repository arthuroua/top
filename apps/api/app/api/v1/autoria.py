import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AutoRiaSnapshotResponse, LocalMarketListingRead, LocalMarketSoldTodayResponse
from app.services.autoria_market import run_autoria_snapshot, sold_or_removed_since

router = APIRouter(prefix="/api/v1/autoria", tags=["autoria"])


def _admin_token() -> str:
    value = os.getenv("ADMIN_TOKEN", "").strip()
    if not value or value == "change-me-admin":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin token is not configured",
        )
    return value


def _require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token or not secrets.compare_digest(x_admin_token, _admin_token()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


@router.post("/snapshot", response_model=AutoRiaSnapshotResponse)
def create_autoria_snapshot(
    query_label: str = Query(default="default", min_length=1, max_length=128),
    search_params: str | None = Query(default=None, max_length=4000),
    max_pages: int | None = Query(default=None, ge=1, le=100),
    _: None = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> AutoRiaSnapshotResponse:
    try:
        return run_autoria_snapshot(
            db,
            search_params=search_params,
            query_label=query_label,
            max_pages=max_pages,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/sold-today", response_model=LocalMarketSoldTodayResponse)
def get_autoria_sold_today(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=500),
    _: None = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> LocalMarketSoldTodayResponse:
    items = sold_or_removed_since(db, hours=hours, limit=limit)
    return LocalMarketSoldTodayResponse(
        items=[LocalMarketListingRead.model_validate(item) for item in items],
        total_count=len(items),
    )
