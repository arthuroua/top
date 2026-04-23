import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.schemas import (
    IngestionConnectorFetchRequest,
    IngestionConnectorFetchResponse,
    IngestionConnectorStatus,
    IngestionJobPayload,
    IngestionPriceEvent,
)


Provider = Literal["copart", "iaai"]
_TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}
_RATE_LIMIT_LOCK = threading.Lock()
_LAST_REQUEST_AT: dict[Provider, float] = {"copart": 0.0, "iaai": 0.0}


class ConnectorConfigurationError(ValueError):
    pass


class ConnectorUpstreamError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConnectorRuntimeConfig:
    provider: Provider
    mode: str
    base_url: str
    endpoint_path: str
    vin_query_param: str
    lot_query_param: str
    timeout_seconds: float
    retry_count: int
    retry_backoff_ms: int
    rate_limit_per_second: float
    auth_header: str
    api_key: str
    api_token: str


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


def _provider_mode(provider: Provider) -> str:
    env_key = f"{provider.upper()}_CONNECTOR_MODE"
    return os.getenv(env_key, "mock").strip().lower()


def _runtime_config(provider: Provider) -> ConnectorRuntimeConfig:
    prefix = provider.upper()
    return ConnectorRuntimeConfig(
        provider=provider,
        mode=_provider_mode(provider),
        base_url=os.getenv(f"{prefix}_API_BASE_URL", "").strip(),
        endpoint_path=os.getenv(f"{prefix}_API_ENDPOINT_PATH", "/v1/lots").strip(),
        vin_query_param=os.getenv(f"{prefix}_VIN_QUERY_PARAM", "vin").strip() or "vin",
        lot_query_param=os.getenv(f"{prefix}_LOT_QUERY_PARAM", "lot_number").strip() or "lot_number",
        timeout_seconds=_env_float(f"{prefix}_API_TIMEOUT_SECONDS", default=15.0, minimum=1.0),
        retry_count=_env_int(f"{prefix}_API_RETRY_COUNT", default=2, minimum=0),
        retry_backoff_ms=_env_int(f"{prefix}_API_RETRY_BACKOFF_MS", default=400, minimum=0),
        rate_limit_per_second=_env_float(f"{prefix}_API_RATE_LIMIT_PER_SECOND", default=2.0, minimum=0.0),
        auth_header=os.getenv(f"{prefix}_API_AUTH_HEADER", "Authorization").strip() or "Authorization",
        api_key=os.getenv(f"{prefix}_API_KEY", "").strip(),
        api_token=os.getenv(f"{prefix}_API_TOKEN", "").strip(),
    )


def _provider_label(provider: Provider) -> str:
    return "Copart" if provider == "copart" else "IAAI"


def _seed_int(provider: Provider, vin: str, lot_number: str) -> int:
    key = f"{provider}:{vin}:{lot_number}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _fallback_vin(provider: Provider, lot_number: str | None) -> str:
    seed = _seed_int(provider, "JHMCM56557C404453", lot_number or "A1000000")
    tail = str(100000 + (seed % 900000))
    return f"JHMCM56557C{tail}"


def _fallback_lot(provider: Provider, vin: str | None) -> str:
    vin_seed = (vin or "JHMCM56557C404453").upper()
    seed = _seed_int(provider, vin_seed, "A1000000")
    letter = chr(ord("A") + (seed % 20))
    number = str(1000000 + (seed % 8999999))
    return f"{letter}{number}"


def _mock_job(provider: Provider, vin: str | None, lot_number: str | None) -> IngestionJobPayload:
    vin_value = (vin or _fallback_vin(provider, lot_number)).upper()
    lot_value = (lot_number or _fallback_lot(provider, vin_value)).upper()

    seed = _seed_int(provider, vin_value, lot_value)
    hammer_price = 3500 + (seed % 9000)
    status = "Sold"
    location_options = {
        "copart": ["FL - Miami", "TX - Houston", "CA - Los Angeles"],
        "iaai": ["NJ - Port Newark", "IL - Chicago", "GA - Atlanta East"],
    }
    location = location_options[provider][seed % len(location_options[provider])]

    now = datetime.now(timezone.utc)
    event = IngestionPriceEvent(
        event_type="sold_price",
        old_value=str(max(0, hammer_price - 400)),
        new_value=str(hammer_price),
        event_time=now,
    )

    return IngestionJobPayload(
        source=_provider_label(provider),
        vin=vin_value,
        lot_number=lot_value,
        sale_date=date.today(),
        hammer_price_usd=hammer_price,
        status=status,
        location=location,
        images=[
            f"https://cdn.example.com/{provider}/{lot_value}/1.jpg",
            f"https://cdn.example.com/{provider}/{lot_value}/2.jpg",
        ],
        price_events=[event],
    )


def _is_official_ready(config: ConnectorRuntimeConfig) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not config.base_url:
        missing.append(f"{config.provider.upper()}_API_BASE_URL")
    if not config.api_key and not config.api_token:
        missing.append(f"{config.provider.upper()}_API_KEY or {config.provider.upper()}_API_TOKEN")
    return (len(missing) == 0, missing)


def connector_statuses() -> list[IngestionConnectorStatus]:
    statuses: list[IngestionConnectorStatus] = []
    for provider in ("copart", "iaai"):
        config = _runtime_config(provider)
        mode = config.mode

        if mode == "mock":
            statuses.append(
                IngestionConnectorStatus(
                    provider=provider,
                    mode=mode,
                    ready=True,
                    note="Mock connector enabled for offline MVP development.",
                )
            )
            continue

        if mode == "official":
            ready, missing = _is_official_ready(config)
            note = "Official connector adapter configured." if ready else f"Missing: {', '.join(missing)}"
            statuses.append(
                IngestionConnectorStatus(
                    provider=provider,
                    mode=mode,
                    ready=ready,
                    note=note,
                )
            )
            continue

        statuses.append(
            IngestionConnectorStatus(
                provider=provider,
                mode=mode,
                ready=False,
                note="Unsupported connector mode. Use 'mock' or 'official'.",
            )
        )

    return statuses


def _apply_rate_limit(provider: Provider, rate_limit_per_second: float) -> None:
    if rate_limit_per_second <= 0:
        return

    min_interval = 1.0 / rate_limit_per_second

    with _RATE_LIMIT_LOCK:
        now = time.monotonic()
        elapsed = now - _LAST_REQUEST_AT[provider]
        wait_seconds = max(0.0, min_interval - elapsed)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
            now = time.monotonic()
        _LAST_REQUEST_AT[provider] = now


def _request_headers(config: ConnectorRuntimeConfig) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "car-import-mvp/0.1 connector",
    }

    if config.api_token:
        headers[config.auth_header] = config.api_token
    if config.api_key:
        headers[f"X-{config.provider.upper()}-API-KEY"] = config.api_key

    return headers


def _http_get_json(config: ConnectorRuntimeConfig, payload: IngestionConnectorFetchRequest) -> dict[str, Any]:
    base = config.base_url.rstrip("/")
    endpoint = config.endpoint_path.lstrip("/")

    query_params: dict[str, str] = {}
    if payload.vin:
        query_params[config.vin_query_param] = payload.vin.upper()
    if payload.lot_number:
        query_params[config.lot_query_param] = payload.lot_number.upper()

    query_string = urlencode(query_params)
    url = f"{base}/{endpoint}"
    if query_string:
        url = f"{url}?{query_string}"

    headers = _request_headers(config)
    attempts = 1 + config.retry_count
    last_error: Exception | None = None

    for attempt in range(attempts):
        _apply_rate_limit(config.provider, config.rate_limit_per_second)

        request = Request(url=url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=config.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
            decoded = json.loads(raw_body)
            if not isinstance(decoded, dict):
                raise ConnectorUpstreamError("Connector returned non-object JSON payload")
            return decoded
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            last_error = ConnectorUpstreamError(f"HTTP {exc.code}: {body[:500]}")
            should_retry = exc.code in _TRANSIENT_HTTP_CODES and attempt < attempts - 1
            if should_retry:
                backoff = (config.retry_backoff_ms / 1000.0) * (2**attempt)
                time.sleep(backoff)
                continue
            raise last_error from exc
        except (URLError, TimeoutError, json.JSONDecodeError, ConnectorUpstreamError) as exc:
            last_error = exc
            if attempt < attempts - 1:
                backoff = (config.retry_backoff_ms / 1000.0) * (2**attempt)
                time.sleep(backoff)
                continue
            raise ConnectorUpstreamError(f"Failed to fetch {config.provider} connector payload: {exc}") from exc

    raise ConnectorUpstreamError(f"Failed to fetch {config.provider} connector payload: {last_error}")


def _lookup_path(record: dict[str, Any], path: str) -> Any:
    current: Any = record
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _first_value(record: dict[str, Any], paths: list[str]) -> Any:
    for path in paths:
        value = _lookup_path(record, path)
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return None


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        clean = value.strip()
        if not clean:
            return None
        try:
            if "T" in clean:
                return datetime.fromisoformat(clean.replace("Z", "+00:00")).date()
            return date.fromisoformat(clean)
        except ValueError:
            return None
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        clean = value.strip()
        if not clean:
            return None
        try:
            parsed = datetime.fromisoformat(clean.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None
    return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    if isinstance(value, str):
        clean = value.strip().replace("$", "").replace(",", "")
        if not clean:
            return None
        try:
            return int(round(float(clean)))
        except ValueError:
            return None
    return None


def _normalize_images(value: Any) -> list[str]:
    if value is None:
        return []

    raw_items: list[Any]
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, dict):
        nested = _first_value(value, ["items", "photos", "images"])
        raw_items = nested if isinstance(nested, list) else []
    else:
        return []

    urls: list[str] = []
    for item in raw_items:
        if isinstance(item, str) and item.strip():
            urls.append(item.strip())
            continue
        if isinstance(item, dict):
            url = _first_value(item, ["url", "image_url", "src", "href", "full"])
            if isinstance(url, str) and url.strip():
                urls.append(url.strip())

    # Preserve order while deduplicating
    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def _normalize_events(value: Any, hammer_price: int | None) -> list[IngestionPriceEvent]:
    events: list[IngestionPriceEvent] = []

    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            event_time = _parse_datetime(
                _first_value(item, ["event_time", "eventTime", "created_at", "timestamp", "time"])
            ) or datetime.now(timezone.utc)
            event_type = str(_first_value(item, ["event_type", "eventType", "type"]) or "price_update")
            old_value = _first_value(item, ["old_value", "oldValue", "previous", "from"])
            new_value = _first_value(item, ["new_value", "newValue", "value", "to"])
            if new_value is None:
                continue
            events.append(
                IngestionPriceEvent(
                    event_type=event_type[:64],
                    old_value=str(old_value)[:128] if old_value is not None else None,
                    new_value=str(new_value)[:128],
                    event_time=event_time,
                )
            )

    if not events and hammer_price is not None:
        events.append(
            IngestionPriceEvent(
                event_type="sold_price",
                old_value=None,
                new_value=str(hammer_price),
                event_time=datetime.now(timezone.utc),
            )
        )

    return events


def _extract_record(raw_payload: dict[str, Any]) -> dict[str, Any]:
    direct_candidate = _first_value(raw_payload, ["record", "lot", "item", "result", "data"])
    if isinstance(direct_candidate, dict):
        return direct_candidate

    if isinstance(direct_candidate, list) and direct_candidate and isinstance(direct_candidate[0], dict):
        return direct_candidate[0]

    return raw_payload


def _map_official_payload(
    provider: Provider,
    payload: IngestionConnectorFetchRequest,
    raw_payload: dict[str, Any],
) -> tuple[str, IngestionJobPayload]:
    record = _extract_record(raw_payload)

    vin_value = str(
        _first_value(record, ["vin", "vehicle.vin", "vehicleVin", "VIN"])
        or (payload.vin or _fallback_vin(provider, payload.lot_number))
    ).upper()
    lot_value = str(
        _first_value(record, ["lot_number", "lotNumber", "lot.id", "lotId"])
        or (payload.lot_number or _fallback_lot(provider, vin_value))
    ).upper()

    if len(vin_value) != 17:
        raise ConnectorUpstreamError(f"Connector returned invalid VIN '{vin_value}'")

    hammer_price = _to_int(_first_value(record, ["hammer_price_usd", "finalBid", "soldAmount", "price"]))
    status = _first_value(record, ["status", "saleStatus", "state"]) or "Unknown"
    location = _first_value(record, ["location", "yard", "branch", "saleLocation"])
    sale_date_value = _parse_date(_first_value(record, ["sale_date", "saleDate", "closeDate", "auctionDate"]))

    images_value = _first_value(record, ["images", "photoUrls", "photos", "media.images"])
    events_value = _first_value(record, ["price_events", "events", "timeline", "history"])

    images = _normalize_images(images_value)
    events = _normalize_events(events_value, hammer_price)

    job = IngestionJobPayload(
        source=_provider_label(provider),
        vin=vin_value,
        lot_number=lot_value,
        sale_date=sale_date_value,
        hammer_price_usd=hammer_price,
        status=str(status)[:32] if status is not None else None,
        location=str(location)[:128] if location is not None else None,
        images=images,
        price_events=events,
    )

    source_record_id = str(
        _first_value(record, ["id", "record_id", "lot_id", "lot.id", "lotNumber", "lot_number"]) or lot_value
    )

    return source_record_id, job


def _validate_official_configuration(config: ConnectorRuntimeConfig) -> None:
    ready, missing = _is_official_ready(config)
    if not ready:
        raise ConnectorConfigurationError(f"{config.provider} official connector is not configured: {', '.join(missing)}")


def fetch_from_connector(payload: IngestionConnectorFetchRequest) -> IngestionConnectorFetchResponse:
    provider: Provider = payload.provider
    config = _runtime_config(provider)
    mode = config.mode

    if mode == "mock":
        job = _mock_job(provider=provider, vin=payload.vin, lot_number=payload.lot_number)
        source_record_id = f"{provider}:{job.lot_number}"
        return IngestionConnectorFetchResponse(
            provider=provider,
            mode=mode,
            source_record_id=source_record_id,
            enqueued=False,
            queue_depth=None,
            job=job,
        )

    if mode == "official":
        _validate_official_configuration(config)
        raw_payload = _http_get_json(config, payload)
        source_record_id, job = _map_official_payload(provider, payload, raw_payload)
        return IngestionConnectorFetchResponse(
            provider=provider,
            mode=mode,
            source_record_id=f"{provider}:{source_record_id}",
            enqueued=False,
            queue_depth=None,
            job=job,
        )

    raise NotImplementedError(
        f"{provider} connector mode '{mode}' is not supported. Use 'mock' or 'official'."
    )
