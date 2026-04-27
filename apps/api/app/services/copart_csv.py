from __future__ import annotations

import csv
import hashlib
import io
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import redis

from app.schemas import IngestionJobPayload, IngestionPriceEvent
from app.services.copart_gallery import fetch_copart_gallery_images
from app.services.ingestion_queue import enqueue_ingestion_job
from app.services.sales_status import is_confirmed_sale_status


DEFAULT_URL_TEMPLATE = "https://inventory.copart.io/FTPLSTDM/salesdata.cgi?authKey={auth_key}"


@dataclass(frozen=True)
class CopartCsvConfig:
    enabled: bool
    auth_key: str
    url_template: str
    timeout_seconds: float
    retry_count: int
    retry_backoff_ms: int
    max_rows_per_run: int
    dedupe_ttl_hours: int
    dedupe_prefix: str


@dataclass(frozen=True)
class CopartCsvIngestionStats:
    total_rows: int
    valid_rows: int
    enqueued_rows: int
    deduped_rows: int
    skipped_rows: int
    started_at: datetime
    finished_at: datetime


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, float(raw))
    except ValueError:
        return default


def load_copart_csv_config() -> CopartCsvConfig:
    return CopartCsvConfig(
        enabled=_env_bool("COPART_CSV_ENABLED", False),
        auth_key=os.getenv("COPART_CSV_AUTH_KEY", "").strip(),
        url_template=os.getenv("COPART_CSV_URL_TEMPLATE", DEFAULT_URL_TEMPLATE).strip() or DEFAULT_URL_TEMPLATE,
        timeout_seconds=_env_float("COPART_CSV_TIMEOUT_SECONDS", 180.0, minimum=5.0),
        retry_count=_env_int("COPART_CSV_RETRY_COUNT", 2, minimum=0),
        retry_backoff_ms=_env_int("COPART_CSV_RETRY_BACKOFF_MS", 2000, minimum=0),
        max_rows_per_run=_env_int("COPART_CSV_MAX_ROWS_PER_RUN", 0, minimum=0),
        dedupe_ttl_hours=_env_int("COPART_CSV_DEDUPE_TTL_HOURS", 168, minimum=1),
        dedupe_prefix=os.getenv("COPART_CSV_DEDUPE_KEY_PREFIX", "ingestion:copart:csv:seen").strip()
        or "ingestion:copart:csv:seen",
    )


def _redis_client() -> redis.Redis:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.Redis.from_url(redis_url, decode_responses=True)


def _build_download_url(config: CopartCsvConfig) -> str:
    if "{auth_key}" in config.url_template:
        return config.url_template.replace("{auth_key}", config.auth_key)
    if config.auth_key and "authKey=" not in config.url_template:
        sep = "&" if "?" in config.url_template else "?"
        return f"{config.url_template}{sep}authKey={config.auth_key}"
    return config.url_template


def _parse_money_to_int(value: Any) -> int | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw = raw.replace("$", "").replace(",", "")
    try:
        parsed = float(raw)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return int(round(parsed))


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    raw = str(value).strip().replace(",", "")
    if not raw:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _parse_sale_date(value: Any) -> date | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw == "0":
        return None

    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 8:
        try:
            if digits.startswith(("19", "20")):
                return datetime.strptime(digits, "%Y%m%d").date()
            return datetime.strptime(digits, "%m%d%Y").date()
        except ValueError:
            return None

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_event_time(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    raw = str(value).strip()
    if not raw:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return datetime.now(timezone.utc)


def _normalize_image_url(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.startswith("//"):
        return f"https:{raw}"
    if raw.startswith("http://"):
        return f"https://{raw[7:]}"
    if raw.startswith("https://"):
        return raw
    return f"https://{raw.lstrip('/')}"


def _is_direct_image_url(value: str) -> bool:
    lowered = value.lower().split("?", 1)[0].split("#", 1)[0]
    return lowered.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"))


def _to_job(row: dict[str, str]) -> IngestionJobPayload | None:
    vin = str(row.get("VIN") or "").strip().upper()
    if len(vin) != 17:
        return None

    lot_number = str(row.get("Lot number") or "").strip().upper()
    if not lot_number:
        return None

    location_city = str(row.get("Location city") or "").strip()
    location_state = str(row.get("Location state") or "").strip()
    location = ", ".join(part for part in [location_city, location_state] if part) or None

    image_primary = _normalize_image_url(row.get("Image URL"))
    image_thumb = _normalize_image_url(row.get("Image Thumbnail"))
    images = fetch_copart_gallery_images(lot_number, image_primary)
    if not images:
        images = [item for item in [image_primary, image_thumb] if item and _is_direct_image_url(item)]
    elif image_thumb and _is_direct_image_url(image_thumb) and image_thumb not in images:
        images.append(image_thumb)

    status = str(row.get("Sale Status") or "").strip() or None
    high_bid = _parse_money_to_int(row.get("High Bid =non-vix,Sealed=Vix"))
    hammer_price = high_bid if is_confirmed_sale_status(status) else None
    event_time = _parse_event_time(row.get("Last Updated Time"))
    price_events: list[IngestionPriceEvent] = []
    if high_bid is not None:
        price_events.append(
            IngestionPriceEvent(
                event_type="copart_high_bid",
                old_value=None,
                new_value=str(high_bid),
                event_time=event_time,
            )
        )

    source_url = str(row.get("Link") or row.get("URL") or "").strip() or None
    model_group = str(row.get("Model Group") or "").strip()
    model_detail = str(row.get("Model Detail") or "").strip()
    model = model_detail or model_group or str(row.get("Model") or "").strip() or None

    attributes = {
        "auction_phase": str(row.get("Auction Date Type") or "").strip() or None,
        "sale_status_label": status,
        "model_group": model_group or None,
        "model_detail": model_detail or None,
        "currency": "USD",
    }
    attributes = {key: value for key, value in attributes.items() if value is not None}

    return IngestionJobPayload(
        provider="copart",
        source="copart",
        vin=vin,
        lot_number=lot_number,
        source_record_id=f"copart:{lot_number}",
        source_url=source_url,
        sale_date=_parse_sale_date(row.get("Sale Date M/D/CY")),
        hammer_price_usd=hammer_price,
        status=status[:32] if status else None,
        location=location[:128] if location else None,
        title_brand=(str(row.get("Sale Title State") or "").strip() or None),
        primary_damage=(str(row.get("Damage Description") or "").strip() or None),
        odometer=_parse_money_to_int(row.get("Odometer")),
        make=(str(row.get("Make") or "").strip() or None),
        model=model,
        year=_parse_int(row.get("Year")),
        trim=(str(row.get("Trim") or "").strip() or None),
        body_style=(str(row.get("Body Style") or "").strip() or None),
        engine=(str(row.get("Engine") or "").strip() or None),
        transmission=(str(row.get("Transmission") or "").strip() or None),
        fuel_type=(str(row.get("Fuel") or row.get("Fuel Type") or "").strip() or None),
        drivetrain=(str(row.get("Drive") or row.get("Drive Train") or "").strip() or None),
        vehicle_type=(str(row.get("Vehicle Type") or "").strip() or None),
        exterior_color=(str(row.get("Color") or "").strip() or None),
        cylinders=_parse_int(row.get("Cylinders")),
        images=images,
        price_events=price_events,
        attributes=attributes,
    )


def _row_fingerprint(row: dict[str, str]) -> str:
    lot = str(row.get("Lot number") or "").strip().upper()
    updated = str(row.get("Last Updated Time") or "").strip()
    high_bid = str(row.get("High Bid =non-vix,Sealed=Vix") or "").strip()
    sale_status = str(row.get("Sale Status") or "").strip()
    digest = hashlib.sha1(f"{lot}|{updated}|{high_bid}|{sale_status}".encode("utf-8")).hexdigest()
    return digest


def _mark_if_new(redis_client: redis.Redis, key: str, ttl_seconds: int) -> bool:
    result = redis_client.set(name=key, value="1", nx=True, ex=ttl_seconds)
    return bool(result)


def run_copart_csv_ingestion(config: CopartCsvConfig | None = None, *, force: bool = False) -> CopartCsvIngestionStats:
    cfg = config or load_copart_csv_config()
    if not cfg.enabled:
        raise RuntimeError("COPART_CSV_ENABLED is false")
    if not cfg.auth_key and "{auth_key}" in cfg.url_template:
        raise RuntimeError("COPART_CSV_AUTH_KEY is empty")

    url = _build_download_url(cfg)
    started_at = datetime.now(timezone.utc)
    total_rows = 0
    valid_rows = 0
    enqueued_rows = 0
    deduped_rows = 0
    skipped_rows = 0

    redis_client = _redis_client()
    ttl_seconds = cfg.dedupe_ttl_hours * 3600

    attempts = 1 + cfg.retry_count
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(
                url=url,
                headers={
                    "Accept": "text/csv,application/octet-stream,*/*",
                    "User-Agent": "car-import-mvp/0.1 csv-ingestion",
                },
                method="GET",
            )
            with urlopen(request, timeout=cfg.timeout_seconds) as response:
                text_stream = io.TextIOWrapper(response, encoding="utf-8", errors="replace", newline="")
                reader = csv.DictReader(text_stream)

                for row in reader:
                    total_rows += 1
                    if cfg.max_rows_per_run > 0 and total_rows > cfg.max_rows_per_run:
                        break

                    job = _to_job(row)
                    if job is None:
                        skipped_rows += 1
                        continue
                    valid_rows += 1

                    row_hash = _row_fingerprint(row)
                    dedupe_key = f"{cfg.dedupe_prefix}:{row_hash}"
                    if not force and not _mark_if_new(redis_client, dedupe_key, ttl_seconds):
                        deduped_rows += 1
                        continue

                    enqueue_ingestion_job(job)
                    enqueued_rows += 1

            finished_at = datetime.now(timezone.utc)
            return CopartCsvIngestionStats(
                total_rows=total_rows,
                valid_rows=valid_rows,
                enqueued_rows=enqueued_rows,
                deduped_rows=deduped_rows,
                skipped_rows=skipped_rows,
                started_at=started_at,
                finished_at=finished_at,
            )
        except (HTTPError, URLError, TimeoutError, redis.RedisError, OSError, RuntimeError, ValueError) as exc:
            last_error = exc
            if attempt >= attempts - 1:
                break
            backoff_seconds = (cfg.retry_backoff_ms / 1000.0) * (2**attempt)
            time.sleep(backoff_seconds)

    raise RuntimeError(f"Copart CSV ingestion failed: {last_error}")
