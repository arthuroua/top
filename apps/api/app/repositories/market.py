from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean, median

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import IngestionConnectorRun, Lot, Vehicle
from app.schemas import (
    MarketCompItem,
    MarketCompsResponse,
    MarketCompsSummary,
    MarketDataHealthResponse,
    MarketProviderHealth,
)
from app.services.connectors import connector_statuses
from app.services.public_lots import is_public_real_lot
from app.services.sales_status import confirmed_sale_status_clause


def _percentile(values: list[int], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    q = min(1.0, max(0.0, q))
    idx = q * (len(ordered) - 1)
    lo = int(idx)
    hi = min(len(ordered) - 1, lo + 1)
    frac = idx - lo
    return round(ordered[lo] * (1 - frac) + ordered[hi] * frac, 2)


def _resolve_target_profile(
    db: Session,
    *,
    vin: str | None,
    make: str | None,
    model: str | None,
    year: int | None,
) -> tuple[str | None, str | None, str | None, int | None]:
    vin_value = vin.upper() if vin else None
    make_value = make
    model_value = model
    year_value = year

    if vin_value:
        db_vehicle = db.get(Vehicle, vin_value)
        if db_vehicle is not None:
            make_value = make_value or db_vehicle.make
            model_value = model_value or db_vehicle.model
            year_value = year_value or db_vehicle.year

    return (vin_value, make_value, model_value, year_value)


def _similarity_score(target_year: int | None, candidate_year: int | None) -> float:
    if target_year is None or candidate_year is None:
        return 80.0
    diff = abs(target_year - candidate_year)
    return max(40.0, 100.0 - diff * 12.5)


def get_market_comps(
    db: Session,
    *,
    vin: str | None,
    make: str | None,
    model: str | None,
    year: int | None,
    source: str | None,
    limit: int,
) -> MarketCompsResponse:
    vin_value, make_value, model_value, year_value = _resolve_target_profile(
        db,
        vin=vin,
        make=make,
        model=model,
        year=year,
    )

    query = (
        select(Lot, Vehicle)
        .join(Vehicle, Lot.vin == Vehicle.vin)
        .options(selectinload(Lot.import_snapshots))
        .where(Lot.hammer_price_usd.is_not(None), Lot.hammer_price_usd > 0, confirmed_sale_status_clause(Lot.status))
    )
    if vin_value:
        query = query.where(Lot.vin != vin_value)
    if make_value:
        query = query.where(func.lower(func.coalesce(Vehicle.make, "")) == make_value.lower())
    if model_value:
        query = query.where(func.lower(func.coalesce(Vehicle.model, "")) == model_value.lower())
    if year_value is not None:
        query = query.where(Vehicle.year >= year_value - 2, Vehicle.year <= year_value + 2)
    if source:
        query = query.where(func.lower(Lot.source) == source.lower())

    rows = db.execute(
        query.order_by(Lot.sale_date.desc(), Lot.fetched_at.desc()).limit(max(40, limit * 6))
    ).all()

    if not rows and year_value is not None:
        query_without_year = (
            select(Lot, Vehicle)
            .join(Vehicle, Lot.vin == Vehicle.vin)
            .options(selectinload(Lot.import_snapshots))
            .where(Lot.hammer_price_usd.is_not(None), Lot.hammer_price_usd > 0, confirmed_sale_status_clause(Lot.status))
        )
        if vin_value:
            query_without_year = query_without_year.where(Lot.vin != vin_value)
        if make_value:
            query_without_year = query_without_year.where(
                func.lower(func.coalesce(Vehicle.make, "")) == make_value.lower()
            )
        if model_value:
            query_without_year = query_without_year.where(
                func.lower(func.coalesce(Vehicle.model, "")) == model_value.lower()
            )
        if source:
            query_without_year = query_without_year.where(func.lower(Lot.source) == source.lower())
        rows = db.execute(
            query_without_year.order_by(Lot.sale_date.desc(), Lot.fetched_at.desc()).limit(max(40, limit * 6))
        ).all()

    items: list[MarketCompItem] = []
    for lot, vehicle in rows:
        if lot.hammer_price_usd is None:
            continue
        if not is_public_real_lot(lot):
            continue
        score = _similarity_score(year_value, vehicle.year)
        items.append(
            MarketCompItem(
                vin=lot.vin,
                make=vehicle.make,
                model=vehicle.model,
                year=vehicle.year,
                source=lot.source,
                lot_number=lot.lot_number,
                sale_date=lot.sale_date.isoformat() if lot.sale_date else None,
                hammer_price_usd=lot.hammer_price_usd,
                location=lot.location,
                similarity_score=round(score, 2),
            )
        )
    items.sort(
        key=lambda item: (
            item.similarity_score,
            item.sale_date or "",
        ),
        reverse=True,
    )
    top_items = items[:limit]

    prices = [item.hammer_price_usd for item in top_items]
    summary = MarketCompsSummary(
        count=len(top_items),
        avg_hammer_price_usd=round(mean(prices), 2) if prices else None,
        median_hammer_price_usd=round(median(prices), 2) if prices else None,
        p25_hammer_price_usd=_percentile(prices, 0.25),
        p75_hammer_price_usd=_percentile(prices, 0.75),
    )

    return MarketCompsResponse(
        target={
            "vin": vin_value,
            "make": make_value,
            "model": model_value,
            "year": year_value,
            "source": source.lower() if source else None,
        },
        summary=summary,
        items=top_items,
    )


def get_market_data_health(db: Session, *, window_hours: int) -> MarketDataHealthResponse:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    total_lots = int(db.execute(select(func.count()).select_from(Lot)).scalar() or 0)
    priced_lots = int(db.execute(select(func.count()).select_from(Lot).where(Lot.hammer_price_usd.is_not(None))).scalar() or 0)
    sold_lots = int(
        db.execute(
            select(func.count()).select_from(Lot).where(confirmed_sale_status_clause(Lot.status))
        ).scalar()
        or 0
    )
    updated_lots_window = int(
        db.execute(select(func.count()).select_from(Lot).where(Lot.fetched_at >= window_start)).scalar() or 0
    )

    status_map = {item.provider: item for item in connector_statuses()}

    providers: list[MarketProviderHealth] = []
    for provider in ("copart", "iaai"):
        row = db.execute(
            select(
                func.count(),
                func.sum(case((IngestionConnectorRun.success.is_(True), 1), else_=0)),
                func.avg(IngestionConnectorRun.latency_ms),
                func.max(IngestionConnectorRun.created_at),
                func.max(case((IngestionConnectorRun.success.is_(True), IngestionConnectorRun.created_at), else_=None)),
            ).where(
                IngestionConnectorRun.provider == provider,
                IngestionConnectorRun.created_at >= window_start,
            )
        ).one()

        total_runs = int(row[0] or 0)
        successful_runs = int(row[1] or 0)
        success_rate = round((successful_runs / total_runs) * 100, 2) if total_runs > 0 else None
        avg_latency = round(float(row[2]), 2) if row[2] is not None else None
        status = status_map.get(provider)

        providers.append(
            MarketProviderHealth(
                provider=provider,
                mode=status.mode if status else "unknown",
                ready=bool(status.ready) if status else False,
                note=status.note if status else "No connector status",
                total_runs_window=total_runs,
                successful_runs_window=successful_runs,
                success_rate_percent=success_rate,
                avg_latency_ms=avg_latency,
                last_run_at=row[3],
                last_success_at=row[4],
            )
        )

    return MarketDataHealthResponse(
        window_hours=window_hours,
        total_lots=total_lots,
        priced_lots=priced_lots,
        sold_lots=sold_lots,
        updated_lots_window=updated_lots_window,
        providers=providers,
    )
