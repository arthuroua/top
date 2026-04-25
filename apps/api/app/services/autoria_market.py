from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LocalMarketListing
from app.schemas import AutoRiaSnapshotResponse, LocalMarketBucket, LocalMarketPeriodStats, LocalMarketStatsResponse


DEFAULT_SEARCH_PARAMS = "category_id=1&with_photo=1&currency=1&abroad=2&custom=1"


@dataclass(frozen=True)
class AutoRiaConfig:
    enabled: bool
    api_key: str
    base_url: str
    timeout_seconds: float
    delay_ms: int
    countpage: int
    max_pages: int
    max_details_per_run: int
    default_search_params: str


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0, maximum: int | None = None) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        value = default
    else:
        try:
            value = int(raw)
        except ValueError:
            value = default
    value = max(minimum, value)
    return min(value, maximum) if maximum is not None else value


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, float(raw))
    except ValueError:
        return default


def load_autoria_config() -> AutoRiaConfig:
    return AutoRiaConfig(
        enabled=_env_bool("AUTORIA_ENABLED", False),
        api_key=os.getenv("AUTORIA_API_KEY", "").strip(),
        base_url=os.getenv("AUTORIA_BASE_URL", "https://developers.ria.com").strip().rstrip("/"),
        timeout_seconds=_env_float("AUTORIA_TIMEOUT_SECONDS", 20.0, minimum=3.0),
        delay_ms=_env_int("AUTORIA_REQUEST_DELAY_MS", 250, minimum=0),
        countpage=_env_int("AUTORIA_COUNTPAGE", 50, minimum=1, maximum=100),
        max_pages=_env_int("AUTORIA_MAX_PAGES", 1, minimum=1, maximum=100),
        max_details_per_run=_env_int("AUTORIA_MAX_DETAILS_PER_RUN", 100, minimum=0, maximum=5000),
        default_search_params=os.getenv("AUTORIA_DEFAULT_SEARCH_PARAMS", DEFAULT_SEARCH_PARAMS).strip()
        or DEFAULT_SEARCH_PARAMS,
    )


def _query_hash(search_params: str) -> str:
    pairs = parse_qsl(search_params, keep_blank_values=True)
    normalized = urlencode(sorted(pairs), doseq=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _get_json(url: str, timeout: float) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "auto-import-hub/0.1 local-market",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:500]
        except OSError:
            body = ""
        raise RuntimeError(f"Auto.RIA API returned HTTP {exc.code}: {body or exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Auto.RIA API connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("Auto.RIA API request timed out") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Auto.RIA API returned invalid JSON") from exc


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _absolute_autoria_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urljoin("https://auto.ria.com", path)


def _collect_image_urls(value: Any) -> list[str]:
    found: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, str):
            if item.startswith("//"):
                found.append(f"https:{item}")
            elif item.startswith("http://") or item.startswith("https://"):
                found.append(item.replace("http://", "https://"))
            elif item.startswith("/"):
                found.append(_absolute_autoria_url(item) or item)
            return
        if isinstance(item, dict):
            for child in item.values():
                visit(child)
            return
        if isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    unique: list[str] = []
    for url in found:
        if url not in unique:
            unique.append(url)
    return unique[:24]


def _extract_ids(payload: Any) -> tuple[list[str], int]:
    if isinstance(payload, list) and payload:
        payload = payload[0]
    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    search_result = result.get("search_result", {}) if isinstance(result, dict) else {}
    ids = [str(item) for item in search_result.get("ids", [])]
    return ids, _as_int(search_result.get("count")) or len(ids)


def _extract_listing(info: dict[str, Any], *, listing_id: str, query_label: str, query_hash: str, now: datetime) -> dict[str, Any]:
    auto_data = info.get("autoData") or {}
    state_data = info.get("stateData") or {}
    photo_data = info.get("photoData") or {}
    image_urls = _collect_image_urls(photo_data)
    primary_photo = photo_data.get("seoLinkM") or photo_data.get("seoLinkB") or photo_data.get("seoLinkF")
    if primary_photo:
        primary_photo = primary_photo.replace("http://", "https://")
    is_sold = bool(auto_data.get("isSold"))
    return {
        "provider": "autoria",
        "listing_id": listing_id,
        "query_label": query_label,
        "query_hash": query_hash,
        "title": info.get("title"),
        "make": info.get("markName"),
        "model": info.get("modelName"),
        "year": _as_int(auto_data.get("year")),
        "price_usd": _as_int(info.get("USD")),
        "price_uah": _as_int(info.get("UAH")),
        "price_eur": _as_int(info.get("EUR")),
        "mileage_km": _as_int(auto_data.get("raceInt")),
        "fuel_name": auto_data.get("fuelName"),
        "gearbox_name": auto_data.get("gearboxName"),
        "city": info.get("locationCityName") or state_data.get("name"),
        "region": state_data.get("regionName"),
        "url": _absolute_autoria_url(info.get("linkToView")),
        "photo_url": primary_photo or (image_urls[0] if image_urls else None),
        "image_urls_json": image_urls,
        "is_active": not is_sold,
        "is_sold": is_sold,
        "removal_status": "sold" if is_sold else None,
        "sold_detected_at": now if is_sold else None,
        "last_seen_at": now,
        "payload_json": info,
    }


def _upsert_listing(db: Session, values: dict[str, Any]) -> None:
    record = db.execute(
        select(LocalMarketListing).where(
            LocalMarketListing.provider == values["provider"],
            LocalMarketListing.listing_id == values["listing_id"],
        )
    ).scalars().first()
    if record is None:
        db.add(LocalMarketListing(**values))
        return

    for key, value in values.items():
        setattr(record, key, value)
    if values["is_active"]:
        record.sold_detected_at = None
        record.removal_status = None


def _search_url(config: AutoRiaConfig, *, page: int, search_params: str) -> str:
    params = f"api_key={config.api_key}&countpage={config.countpage}&page={page}"
    if search_params:
        params = f"{params}&{search_params.lstrip('&')}"
    return f"{config.base_url}/auto/search?{params}"


def _info_url(config: AutoRiaConfig, listing_id: str) -> str:
    return f"{config.base_url}/auto/info?{urlencode({'api_key': config.api_key, 'auto_id': listing_id})}"


def run_autoria_snapshot(
    db: Session,
    *,
    search_params: str | None = None,
    query_label: str = "default",
    max_pages: int | None = None,
) -> AutoRiaSnapshotResponse:
    config = load_autoria_config()
    if not config.enabled:
        raise RuntimeError("AUTORIA_ENABLED is not enabled")
    if not config.api_key:
        raise RuntimeError("AUTORIA_API_KEY is not configured")

    effective_params = search_params if search_params is not None else config.default_search_params
    effective_hash = _query_hash(effective_params)
    pages = min(max_pages or config.max_pages, config.max_pages)
    now = datetime.now(timezone.utc)

    active_ids: list[str] = []
    total_count = 0
    for page in range(pages):
        payload = _get_json(_search_url(config, page=page, search_params=effective_params), config.timeout_seconds)
        page_ids, count = _extract_ids(payload)
        total_count = max(total_count, count)
        active_ids.extend(page_ids)
        if config.delay_ms:
            time.sleep(config.delay_ms / 1000)
        if not page_ids or len(active_ids) >= total_count:
            break

    unique_ids = list(dict.fromkeys(active_ids))
    details_limit = min(len(unique_ids), config.max_details_per_run)
    upserted = 0
    for listing_id in unique_ids[:details_limit]:
        try:
            info = _get_json(_info_url(config, listing_id), config.timeout_seconds)
        except RuntimeError:
            continue
        if isinstance(info, list) and info:
            info = info[0]
        if not isinstance(info, dict):
            continue
        _upsert_listing(
            db,
            _extract_listing(info, listing_id=listing_id, query_label=query_label, query_hash=effective_hash, now=now),
        )
        upserted += 1
        if config.delay_ms:
            time.sleep(config.delay_ms / 1000)

    sold_or_removed = 0
    if unique_ids:
        active_id_set = set(unique_ids)
        stale_records = db.execute(
            select(LocalMarketListing).where(
                LocalMarketListing.provider == "autoria",
                LocalMarketListing.query_hash == effective_hash,
                LocalMarketListing.is_active.is_(True),
                LocalMarketListing.listing_id.notin_(list(active_id_set)),
            )
        ).scalars().all()
        for record in stale_records:
            record.is_active = False
            record.is_sold = False
            record.removal_status = "removed"
            record.sold_detected_at = now
            record.last_seen_at = now
            sold_or_removed += 1

    db.commit()
    return AutoRiaSnapshotResponse(
        query_label=query_label,
        active_ids_seen=len(unique_ids),
        listings_upserted=upserted,
        sold_or_removed_detected=sold_or_removed,
        skipped_details=max(0, len(unique_ids) - details_limit),
    )


def sold_or_removed_since(db: Session, *, hours: int = 24, limit: int = 100) -> list[LocalMarketListing]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    return (
        db.execute(
            select(LocalMarketListing)
            .where(
                LocalMarketListing.provider == "autoria",
                LocalMarketListing.is_active.is_(False),
                LocalMarketListing.sold_detected_at.is_not(None),
                LocalMarketListing.sold_detected_at >= since,
            )
            .order_by(LocalMarketListing.sold_detected_at.desc(), LocalMarketListing.price_usd.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


def local_market_items(
    db: Session,
    *,
    hours: int = 24,
    limit: int = 100,
    status: str = "all",
) -> list[LocalMarketListing]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    statement = select(LocalMarketListing).where(
        LocalMarketListing.provider == "autoria",
        LocalMarketListing.is_active.is_(False),
        LocalMarketListing.sold_detected_at.is_not(None),
        LocalMarketListing.sold_detected_at >= since,
    )
    if status in {"sold", "removed"}:
        statement = statement.where(LocalMarketListing.removal_status == status)
    return (
        db.execute(statement.order_by(LocalMarketListing.sold_detected_at.desc(), LocalMarketListing.price_usd.asc()).limit(limit))
        .scalars()
        .all()
    )


PRICE_BUCKETS: list[tuple[str, int | None, int | None]] = [
    ("до $5k", None, 5000),
    ("$5k-$10k", 5000, 10000),
    ("$10k-$15k", 10000, 15000),
    ("$15k-$20k", 15000, 20000),
    ("$20k-$25k", 20000, 25000),
    ("$25k-$30k", 25000, 30000),
    ("$30k-$40k", 30000, 40000),
    ("$40k+", 40000, None),
]


def _median(values: list[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return float((ordered[midpoint - 1] + ordered[midpoint]) / 2)


def _avg(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _bucket_matches(price: int | None, min_usd: int | None, max_usd: int | None) -> bool:
    if price is None:
        return False
    if min_usd is not None and price < min_usd:
        return False
    if max_usd is not None and price >= max_usd:
        return False
    return True


def _period_stats(items: list[LocalMarketListing], days: int) -> LocalMarketPeriodStats:
    prices = [item.price_usd for item in items if item.price_usd is not None]
    buckets: list[LocalMarketBucket] = []
    for label, min_usd, max_usd in PRICE_BUCKETS:
        bucket_items = [item for item in items if _bucket_matches(item.price_usd, min_usd, max_usd)]
        bucket_prices = [item.price_usd for item in bucket_items if item.price_usd is not None]
        buckets.append(
            LocalMarketBucket(
                label=label,
                min_usd=min_usd,
                max_usd=max_usd,
                total_count=len(bucket_items),
                sold_count=sum(1 for item in bucket_items if item.removal_status == "sold"),
                removed_count=sum(1 for item in bucket_items if item.removal_status == "removed"),
                avg_price_usd=_avg(bucket_prices),
                median_price_usd=_median(bucket_prices),
            )
        )
    return LocalMarketPeriodStats(
        days=days,
        total_count=len(items),
        sold_count=sum(1 for item in items if item.removal_status == "sold"),
        removed_count=sum(1 for item in items if item.removal_status == "removed"),
        avg_price_usd=_avg(prices),
        median_price_usd=_median(prices),
        buckets=buckets,
    )


def local_market_stats(db: Session, *, periods: tuple[int, ...] = (1, 7, 30)) -> LocalMarketStatsResponse:
    max_days = max(periods)
    since = datetime.now(timezone.utc) - timedelta(days=max_days)
    records = (
        db.execute(
            select(LocalMarketListing)
            .where(
                LocalMarketListing.provider == "autoria",
                LocalMarketListing.is_active.is_(False),
                LocalMarketListing.sold_detected_at.is_not(None),
                LocalMarketListing.sold_detected_at >= since,
            )
            .order_by(LocalMarketListing.sold_detected_at.desc())
        )
        .scalars()
        .all()
    )
    now = datetime.now(timezone.utc)
    return LocalMarketStatsResponse(
        periods=[
            _period_stats(
                [item for item in records if item.sold_detected_at and item.sold_detected_at >= now - timedelta(days=days)],
                days,
            )
            for days in periods
        ]
    )
