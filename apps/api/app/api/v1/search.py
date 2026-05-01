import re
from urllib.parse import parse_qs, unquote, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.privacy import hide_data_source
from app.db import get_db
from app.models import Lot, Vehicle
from app.schemas import SearchResolveResult, SearchResult
from app.services.public_lots import is_public_real_lot
from app.services.sales_status import confirmed_sale_status_clause

router = APIRouter(prefix="/api/v1", tags=["search"])

VIN_TOKEN_RE = re.compile(r"[A-HJ-NPR-Z0-9]{17}", re.IGNORECASE)
LOT_STOPWORDS = {
    "COPART",
    "IAAI",
    "LOT",
    "DETAILS",
    "DETAIL",
    "VEHICLE",
    "AUCTION",
    "EN",
    "US",
    "AUTO",
}
LOT_PARAM_KEYS = {"lot", "lot_number", "lotnumber", "lot_num", "lotid", "lot_id"}
VIN_PARAM_KEYS = {"vin", "vehicle_vin", "vehiclevin"}


def _extract_source_hint(hostname: str) -> str | None:
    host = hostname.lower()
    if "copart" in host:
        return "copart"
    if "iaai" in host or "impactauto" in host:
        return "iaai"
    return None


def _normalize_lot_token(value: str) -> str | None:
    token = value.strip().upper()
    if not token or token in LOT_STOPWORDS:
        return None
    if len(token) < 6 or len(token) > 12:
        return None
    if not token.isalnum():
        return None
    if not any(char.isdigit() for char in token):
        return None
    return token


def _extract_query_payload(query: str) -> tuple[str, str, str, str | None, str | None]:
    raw = query.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Provide VIN, lot number, or URL")

    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        source_hint = _extract_source_hint(parsed.netloc)
        query_params = parse_qs(parsed.query)

        for key in VIN_PARAM_KEYS:
            values = query_params.get(key)
            if not values:
                continue
            candidate = values[0].strip().upper()
            if len(candidate) == 17 and VIN_TOKEN_RE.fullmatch(candidate):
                return ("url", "vin", candidate, source_hint, None)

        for key in LOT_PARAM_KEYS:
            values = query_params.get(key)
            if not values:
                continue
            normalized_lot = _normalize_lot_token(values[0])
            if normalized_lot:
                return ("url", "lot", normalized_lot, source_hint, normalized_lot)

        token_bag = re.split(r"[^A-Z0-9]+", unquote(f"{parsed.path} {parsed.query}").upper())
        for token in token_bag:
            if len(token) == 17 and VIN_TOKEN_RE.fullmatch(token):
                return ("url", "vin", token, source_hint, None)

        for token in token_bag:
            normalized_lot = _normalize_lot_token(token)
            if normalized_lot:
                return ("url", "lot", normalized_lot, source_hint, normalized_lot)

        raise HTTPException(status_code=400, detail="Could not extract VIN or lot number from URL")

    normalized = raw.upper()
    if len(normalized) == 17 and VIN_TOKEN_RE.fullmatch(normalized):
        return ("vin", "vin", normalized, None, None)

    normalized_lot = _normalize_lot_token(normalized)
    if normalized_lot:
        return ("lot", "lot", normalized_lot, None, normalized_lot)

    raise HTTPException(status_code=400, detail="Provide valid VIN, lot number, or URL")


def _search_vin_in_db(db: Session, vin_key: str) -> SearchResult | None:
    vehicle = db.get(Vehicle, vin_key)
    if vehicle is None:
        return None
    lots = (
        db.execute(
            select(Lot)
            .options(selectinload(Lot.import_snapshots))
            .where(Lot.vin == vin_key)
            .where(Lot.hammer_price_usd.is_not(None), Lot.hammer_price_usd > 0, confirmed_sale_status_clause(Lot.status))
            .order_by(Lot.sale_date.desc(), Lot.fetched_at.desc())
        )
        .scalars()
        .all()
    )
    lots = [lot for lot in lots if is_public_real_lot(lot)]
    if not lots:
        return None
    latest_status = lots[0].status if lots and lots[0].status else "Unknown"
    return SearchResult(vin=vin_key, lots_found=len(lots), latest_status=latest_status)


def _find_vin_by_lot_in_db(db: Session, lot_number: str, source_hint: str | None) -> tuple[str, str | None] | None:
    query = (
        select(Lot)
        .options(selectinload(Lot.import_snapshots))
        .where(func.upper(Lot.lot_number) == lot_number)
        .where(Lot.hammer_price_usd.is_not(None), Lot.hammer_price_usd > 0, confirmed_sale_status_clause(Lot.status))
    )
    if source_hint:
        query = query.where(func.lower(Lot.source) == source_hint)
    query = query.order_by(Lot.sale_date.desc(), Lot.fetched_at.desc())
    lots = db.execute(query).scalars().all()
    for lot in lots:
        if is_public_real_lot(lot):
            return (lot.vin, lot.source.lower())
    return None


@router.get("/search", response_model=SearchResult)
def search(vin: str = Query(min_length=17, max_length=17), db: Session = Depends(get_db)) -> SearchResult:
    vin_key = vin.upper()

    db_result = _search_vin_in_db(db, vin_key)
    if db_result is not None:
        return db_result

    raise HTTPException(status_code=404, detail="VIN not found")


@router.get("/search/resolve", response_model=SearchResolveResult)
def resolve_search(query: str = Query(min_length=1, max_length=1024), db: Session = Depends(get_db)) -> SearchResolveResult:
    query_type, matched_by, normalized_query, source_hint, lot_number = _extract_query_payload(query)

    vin_key: str | None = None
    matched_source: str | None = source_hint
    if matched_by == "vin":
        vin_key = normalized_query
    else:
        lot_result = _find_vin_by_lot_in_db(db, normalized_query, source_hint)
        if lot_result is None:
            raise HTTPException(status_code=404, detail="Lot not found")
        vin_key, matched_source = lot_result

    db_result = _search_vin_in_db(db, vin_key)
    result = db_result
    if result is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    return SearchResolveResult(
        query=query,
        normalized_query=normalized_query,
        query_type=query_type,
        matched_by=matched_by,
        vin=result.vin,
        lots_found=result.lots_found,
        latest_status=result.latest_status,
        lot_number=lot_number,
        source=None if hide_data_source() else matched_source,
    )
