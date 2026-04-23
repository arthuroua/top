from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.market import calculate_landed_cost
from app.core.privacy import hide_data_source, public_source_label
from app.db import get_db
from app.repositories.market import get_market_comps, get_market_data_health
from app.schemas import (
    LandedCostInput,
    LandedCostOutput,
    MarketCompsResponse,
    MarketDataHealthResponse,
)

router = APIRouter(prefix="/api/v1/market", tags=["market"])


@router.post("/landed-cost/calculate", response_model=LandedCostOutput)
def calculate_landed(payload: LandedCostInput) -> LandedCostOutput:
    result = calculate_landed_cost(payload)
    if hide_data_source():
        return result.model_copy(update={"auction_provider": "other"})
    return result


@router.get("/comps", response_model=MarketCompsResponse)
def comps(
    vin: str | None = Query(default=None, min_length=17, max_length=17),
    make: str | None = Query(default=None, min_length=1, max_length=64),
    model: str | None = Query(default=None, min_length=1, max_length=64),
    year: int | None = Query(default=None, ge=1980, le=2035),
    source: str | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
) -> MarketCompsResponse:
    result = get_market_comps(
        db,
        vin=vin.upper() if vin else None,
        make=make,
        model=model,
        year=year,
        source=source.lower() if source else None,
        limit=limit,
    )
    if not hide_data_source():
        return result
    masked_items = [item.model_copy(update={"source": public_source_label()}) for item in result.items]
    masked_target = {**result.target, "source": None}
    return result.model_copy(update={"target": masked_target, "items": masked_items})


@router.get("/data-health", response_model=MarketDataHealthResponse)
def data_health(
    window_hours: int = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db),
) -> MarketDataHealthResponse:
    result = get_market_data_health(db, window_hours=window_hours)
    if hide_data_source():
        return result.model_copy(update={"providers": []})
    return result
