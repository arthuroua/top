import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MarketWatch
from app.schemas import (
    AutoRiaSnapshotResponse,
    LocalMarketListingRead,
    LocalMarketSoldTodayResponse,
    LocalMarketStatsResponse,
    MarketWatchCreate,
    MarketWatchDetailResponse,
    MarketWatchRead,
)
from app.services.autoria_market import (
    active_watch_items,
    changed_watch_items,
    create_market_watch,
    local_market_items,
    local_market_stats,
    run_autoria_snapshot,
    run_market_watch,
    sold_or_removed_since,
)

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
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database error while saving Auto.RIA snapshot: {exc}") from exc


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


@router.get("/market", response_model=LocalMarketSoldTodayResponse)
def get_autoria_market_items(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    limit: int = Query(default=100, ge=1, le=500),
    status: str = Query(default="all", pattern="^(all|sold|removed)$"),
    db: Session = Depends(get_db),
) -> LocalMarketSoldTodayResponse:
    items = local_market_items(db, hours=hours, limit=limit, status=status)
    return LocalMarketSoldTodayResponse(
        items=[LocalMarketListingRead.model_validate(item) for item in items],
        total_count=len(items),
    )


@router.get("/stats", response_model=LocalMarketStatsResponse)
def get_autoria_market_stats(db: Session = Depends(get_db)) -> LocalMarketStatsResponse:
    return local_market_stats(db)


@router.get("/watches", response_model=list[MarketWatchRead])
def list_market_watches(
    _: None = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> list[MarketWatchRead]:
    watches = (
        db.execute(select(MarketWatch).where(MarketWatch.is_active.is_(True)).order_by(MarketWatch.created_at.desc()))
        .scalars()
        .all()
    )
    return [MarketWatchRead.model_validate(watch) for watch in watches]


@router.post("/watches", response_model=MarketWatchRead)
def create_watch(
    payload: MarketWatchCreate,
    _: None = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> MarketWatchRead:
    try:
        watch = create_market_watch(
            db,
            search_text=payload.search_text,
            name=payload.name,
            search_params=payload.search_params,
        )
        return MarketWatchRead.model_validate(watch)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/watches/{slug}", response_model=MarketWatchDetailResponse)
def get_watch(
    slug: str,
    _: None = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> MarketWatchDetailResponse:
    watch = db.execute(select(MarketWatch).where(MarketWatch.slug == slug, MarketWatch.is_active.is_(True))).scalars().first()
    if watch is None:
        raise HTTPException(status_code=404, detail="Market watch not found")
    return MarketWatchDetailResponse(
        watch=MarketWatchRead.model_validate(watch),
        stats=local_market_stats(db, query_hash=watch.query_hash),
        active_items=[LocalMarketListingRead.model_validate(item) for item in active_watch_items(db, watch)],
        changed_items=[LocalMarketListingRead.model_validate(item) for item in changed_watch_items(db, watch)],
    )


@router.post("/watches/{slug}/run", response_model=AutoRiaSnapshotResponse)
def run_watch(
    slug: str,
    max_pages: int | None = Query(default=None, ge=1, le=100),
    _: None = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> AutoRiaSnapshotResponse:
    watch = db.execute(select(MarketWatch).where(MarketWatch.slug == slug, MarketWatch.is_active.is_(True))).scalars().first()
    if watch is None:
        raise HTTPException(status_code=404, detail="Market watch not found")
    try:
        return run_market_watch(db, watch, max_pages=max_pages)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database error while saving Auto.RIA watch: {exc}") from exc
