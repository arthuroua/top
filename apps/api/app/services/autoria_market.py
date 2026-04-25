from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LocalMarketListing, MarketWatch
from app.schemas import AutoRiaSnapshotResponse, LocalMarketBucket, LocalMarketPeriodStats, LocalMarketStatsResponse
from app.services.media_archive import archive_image, public_media_url


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


def _media_archive_enabled() -> bool:
    raw = os.getenv("MEDIA_ARCHIVE_ENABLED", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}
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


def public_query_hash(search_params: str) -> str:
    return _query_hash(search_params)


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


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or f"watch-{hashlib.sha1(value.encode('utf-8')).hexdigest()[:8]}"


def _normalize_watch_text(value: str) -> str:
    replacements = {
        "форд": "ford",
        "форд edge": "ford edge",
        "едж": "edge",
        "эдж": "edge",
        "бмв": "bmw",
        "мерседес": "mercedes-benz",
        "тойота": "toyota",
        "тесла": "tesla",
        "ауді": "audi",
        "ауди": "audi",
    }
    clean = value.lower().strip()
    for source, target in replacements.items():
        clean = clean.replace(source, target)
    return re.sub(r"\s+", " ", clean)


def _extract_year(value: str) -> int | None:
    match = re.search(r"\b(19[8-9]\d|20[0-3]\d)\b", value)
    return int(match.group(1)) if match else None


def _list_payload_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("result", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _item_name(item: dict[str, Any]) -> str:
    for key in ("name", "value", "title"):
        value = item.get(key)
        if isinstance(value, str):
            return value.lower()
    return ""


def _item_id(item: dict[str, Any]) -> int | None:
    for key in ("id", "marka_id", "model_id", "value"):
        value = _as_int(item.get(key))
        if value is not None:
            return value
    return None


def _resolve_autoria_search_params(search_text: str, explicit_params: str | None = None) -> str:
    if explicit_params:
        return explicit_params.strip().lstrip("?")

    config = load_autoria_config()
    if not config.enabled or not config.api_key:
        raise RuntimeError("AUTORIA_API_KEY is required to resolve text filters. Or pass raw Auto.RIA search_params.")

    normalized = _normalize_watch_text(search_text)
    year = _extract_year(normalized)
    words = [word for word in re.sub(r"\b(19[8-9]\d|20[0-3]\d)\b", "", normalized).split(" ") if word]
    if not words:
        raise RuntimeError("Enter at least make/model, for example: Ford Edge 2020")

    marks_url = f"{config.base_url}/auto/categories/1/marks?{urlencode({'api_key': config.api_key})}"
    marks = _list_payload_items(_get_json(marks_url, config.timeout_seconds))
    make_item = next((item for item in marks if _item_name(item) == words[0]), None)
    if make_item is None:
        make_item = next((item for item in marks if words[0] in _item_name(item)), None)
    make_id = _item_id(make_item or {})
    if make_id is None:
        raise RuntimeError(f"Could not resolve Auto.RIA make from '{words[0]}'")

    params: dict[str, str | int] = {
        "category_id": 1,
        "marka_id[0]": make_id,
        "with_photo": 1,
        "currency": 1,
        "abroad": 2,
        "custom": 1,
    }
    if year is not None:
        params["s_yers[0]"] = year
        params["po_yers[0]"] = year

    if len(words) > 1:
        model_query = " ".join(words[1:])
        models_url = f"{config.base_url}/auto/categories/1/marks/{make_id}/models?{urlencode({'api_key': config.api_key})}"
        models = _list_payload_items(_get_json(models_url, config.timeout_seconds))
        model_item = next((item for item in models if _item_name(item) == model_query), None)
        if model_item is None:
            model_item = next((item for item in models if model_query in _item_name(item) or _item_name(item) in model_query), None)
        model_id = _item_id(model_item or {})
        if model_id is not None:
            params["model_id[0]"] = model_id

    return urlencode(params)


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


def _archive_listing_images(db: Session, *, listing_id: str, image_urls: list[str]) -> list[str]:
    if not _media_archive_enabled():
        return image_urls
    max_images = _env_int("MEDIA_ARCHIVE_MAX_IMAGES_PER_LISTING", 6, minimum=0, maximum=24)
    archived: list[str] = []
    for url in image_urls[:max_images]:
        asset = archive_image(db, provider="autoria", owner_type="local_market_listing", owner_id=listing_id, source_url=url)
        if asset is not None and asset.is_archived:
            archived.append(public_media_url(asset))
    return archived or image_urls


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
        values = _extract_listing(info, listing_id=listing_id, query_label=query_label, query_hash=effective_hash, now=now)
        values["image_urls_json"] = _archive_listing_images(db, listing_id=listing_id, image_urls=values["image_urls_json"])
        values["photo_url"] = values["image_urls_json"][0] if values["image_urls_json"] else values["photo_url"]
        _upsert_listing(db, values)
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


def create_market_watch(db: Session, *, search_text: str, name: str | None = None, search_params: str | None = None) -> MarketWatch:
    resolved_params = _resolve_autoria_search_params(search_text, search_params)
    watch_name = (name or search_text).strip()
    base_slug = _slugify(watch_name)
    slug = base_slug
    suffix = 2
    while db.execute(select(MarketWatch).where(MarketWatch.slug == slug)).scalars().first() is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    watch = MarketWatch(
        slug=slug,
        name=watch_name,
        search_text=search_text.strip(),
        search_params=resolved_params,
        query_hash=_query_hash(resolved_params),
        is_active=True,
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


def run_market_watch(db: Session, watch: MarketWatch, *, max_pages: int | None = None) -> AutoRiaSnapshotResponse:
    result = run_autoria_snapshot(
        db,
        search_params=watch.search_params,
        query_label=watch.slug,
        max_pages=max_pages,
    )
    watch.last_run_at = datetime.now(timezone.utc)
    watch.last_active_ids_seen = result.active_ids_seen
    watch.last_listings_upserted = result.listings_upserted
    watch.last_sold_or_removed_detected = result.sold_or_removed_detected
    db.commit()
    db.refresh(watch)
    return result


def active_watch_items(db: Session, watch: MarketWatch, *, limit: int = 80) -> list[LocalMarketListing]:
    return (
        db.execute(
            select(LocalMarketListing)
            .where(
                LocalMarketListing.provider == "autoria",
                LocalMarketListing.query_hash == watch.query_hash,
                LocalMarketListing.is_active.is_(True),
            )
            .order_by(LocalMarketListing.price_usd.asc().nulls_last(), LocalMarketListing.last_seen_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


def changed_watch_items(db: Session, watch: MarketWatch, *, days: int = 30, limit: int = 80) -> list[LocalMarketListing]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.execute(
            select(LocalMarketListing)
            .where(
                LocalMarketListing.provider == "autoria",
                LocalMarketListing.query_hash == watch.query_hash,
                LocalMarketListing.is_active.is_(False),
                LocalMarketListing.sold_detected_at.is_not(None),
                LocalMarketListing.sold_detected_at >= since,
            )
            .order_by(LocalMarketListing.sold_detected_at.desc(), LocalMarketListing.price_usd.asc().nulls_last())
            .limit(limit)
        )
        .scalars()
        .all()
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


def local_market_stats(
    db: Session,
    *,
    periods: tuple[int, ...] = (1, 7, 30),
    query_hash: str | None = None,
) -> LocalMarketStatsResponse:
    max_days = max(periods)
    since = datetime.now(timezone.utc) - timedelta(days=max_days)
    statement = select(LocalMarketListing).where(
        LocalMarketListing.provider == "autoria",
        LocalMarketListing.is_active.is_(False),
        LocalMarketListing.sold_detected_at.is_not(None),
        LocalMarketListing.sold_detected_at >= since,
    )
    if query_hash:
        statement = statement.where(LocalMarketListing.query_hash == query_hash)
    records = db.execute(statement.order_by(LocalMarketListing.sold_detected_at.desc())).scalars().all()
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
