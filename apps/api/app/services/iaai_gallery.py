from __future__ import annotations

import html
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


_SEARCH_URL_TEMPLATE = "https://www.iaai.com/Search?Keyword={query}"
_ENLARGE_URL_TEMPLATE = (
    "https://www.iaai.com/VehicleDetail/EnlargeImages/{salvage_id}"
    "?stockNumber={stock_number}&branchCode={branch_code}&yearMakeModel={year_make_model}"
)
_SEARCH_CARD_PATTERN = re.compile(
    r'<a href="/VehicleDetail/(?P<salvage>[^"]+)"[^>]*>.*?'
    r'<img[^>]+data-src="(?P<thumb>https://vis\.iaai\.com/resizer\?imageKeys=[^"]+)"[^>]*>.*?'
    r"ImageModalClicked\('(?P<stock>[^']+)'\s*,\s*'(?P<modal_salvage>[^']+)'\s*,\s*'(?P<vin>[^']*)'\s*,\s*"
    r"'(?P<branch>[^']*)'\s*,\s*'(?P<year>[^']*)'\s*,\s*'(?P<make>[^']*)'\s*,\s*'(?P<model>[^']*)'\s*,\s*"
    r"'(?P<series>[^']*)'",
    re.IGNORECASE | re.DOTALL,
)
_JSON_PARSE_PATTERN = re.compile(r"JSON\.parse\('(?P<payload>\{.*?\})'\)", re.DOTALL)
_PRODUCT_DETAILS_PATTERN = re.compile(
    r'<script type="application/json" id="ProductDetailsVM">\s*(?P<payload>\{.*?\})\s*</script>',
    re.DOTALL,
)


@dataclass(frozen=True)
class IaaiSearchMatch:
    stock_number: str
    salvage_id: str
    vin_masked: str
    branch_code: str
    year_make_model: str
    thumbnail_url: str


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


def _request_text(url: str) -> str:
    timeout = _env_int("IAAI_GALLERY_TIMEOUT_SECONDS", 15, minimum=2, maximum=60)
    retry_count = _env_int("IAAI_GALLERY_RETRY_COUNT", 1, minimum=0, maximum=5)
    delay_ms = _env_int("IAAI_GALLERY_RETRY_BACKOFF_MS", 300, minimum=0, maximum=10_000)
    last_error: Exception | None = None

    for attempt in range(retry_count + 1):
        try:
            request = Request(
                url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "User-Agent": "auto-import-hub/0.1 iaai-gallery",
                },
            )
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retry_count and delay_ms > 0:
                time.sleep(delay_ms / 1000)

    return "" if last_error else ""


def _search_html(query: str) -> str:
    clean_query = query.strip().upper()
    if not clean_query:
        return ""
    url = _SEARCH_URL_TEMPLATE.format(query=quote(clean_query))
    return _request_text(url)


def _extract_search_matches(payload: str) -> list[IaaiSearchMatch]:
    matches: list[IaaiSearchMatch] = []
    for item in _SEARCH_CARD_PATTERN.finditer(payload):
        year = item.group("year").strip()
        make = item.group("make").strip()
        model = item.group("model").strip()
        series = item.group("series").strip()
        parts = [piece for piece in (year, make, model, series) if piece]
        matches.append(
            IaaiSearchMatch(
                stock_number=item.group("stock").strip().upper(),
                salvage_id=item.group("modal_salvage").strip(),
                vin_masked=item.group("vin").strip().upper(),
                branch_code=item.group("branch").strip(),
                year_make_model=" ".join(parts),
                thumbnail_url=html.unescape(item.group("thumb").strip()),
            )
        )
    return matches


def _matching_search_result(payload: str, *, lot_number: str, vin: str | None = None) -> IaaiSearchMatch | None:
    desired_lot = lot_number.strip().upper()
    desired_vin = (vin or "").strip().upper()
    for match in _extract_search_matches(payload):
        if match.stock_number == desired_lot:
            return match
        if desired_vin and desired_vin.startswith(match.vin_masked.replace("*", "")):
            return match
    return None


def _enlarge_html(match: IaaiSearchMatch) -> str:
    url = _ENLARGE_URL_TEMPLATE.format(
        salvage_id=quote(match.salvage_id, safe="~"),
        stock_number=quote(match.stock_number),
        branch_code=quote(match.branch_code),
        year_make_model=quote(match.year_make_model),
    )
    return _request_text(url)


def _parse_enlarge_payload(payload: str) -> dict[str, Any] | None:
    found = _JSON_PARSE_PATTERN.search(payload)
    if not found:
        return None
    try:
        return json.loads(found.group("payload"))
    except json.JSONDecodeError:
        return None


def _parse_product_details_payload(payload: str) -> dict[str, Any] | None:
    found = _PRODUCT_DETAILS_PATTERN.search(payload)
    if not found:
        return None
    try:
        return json.loads(found.group("payload"))
    except json.JSONDecodeError:
        return None


def _nested_get(payload: dict[str, Any], *path: str) -> Any:
    current: Any = payload
    for segment in path:
        if isinstance(current, dict) and segment in current:
            current = current[segment]
            continue
        return None
    return current


def _unwrap_values(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        values = payload.get("$values")
        if isinstance(values, list):
            return [item for item in values if isinstance(item, dict)]
    return []


def _resizer_url(key: str, *, width: int, height: int) -> str:
    return f"https://vis.iaai.com/resizer?imageKeys={quote(key, safe='~')}&width={width}&height={height}"


def extract_iaai_gallery_images(payload: dict[str, Any], *, max_images: int = 40) -> list[str]:
    keys = _unwrap_values(payload.get("keys"))
    if not keys:
        return []

    images: list[str] = []
    seen: set[str] = set()
    for item in keys:
        if not isinstance(item, dict):
            continue
        key = str(item.get("k") or "").strip()
        if not key:
            continue
        width = int(item.get("w") or 1600)
        height = int(item.get("h") or 1200)
        url = _resizer_url(key, width=min(width, 1600), height=min(height, 1200))
        if url in seen:
            continue
        seen.add(url)
        images.append(url)
        if len(images) >= max_images:
            break
    return images


def fetch_iaai_gallery_images(lot_number: str, vin: str | None = None) -> list[str]:
    max_images = _env_int("IAAI_GALLERY_MAX_IMAGES_PER_LOT", 20, minimum=1, maximum=60)
    search_payload = _search_html(lot_number or vin or "")
    if not search_payload:
        return []

    product_details = _parse_product_details_payload(search_payload)
    if product_details:
        image_dimensions = _nested_get(product_details, "inventoryView", "imageDimensions")
        if isinstance(image_dimensions, dict):
            direct_images = extract_iaai_gallery_images(image_dimensions, max_images=max_images)
            if direct_images:
                return direct_images

    match = _matching_search_result(search_payload, lot_number=lot_number, vin=vin)
    if match is None:
        return []

    enlarge_payload = _enlarge_html(match)
    if not enlarge_payload:
        return [match.thumbnail_url] if match.thumbnail_url else []

    details = _parse_enlarge_payload(enlarge_payload)
    if not details:
        return [match.thumbnail_url] if match.thumbnail_url else []

    images = extract_iaai_gallery_images(details, max_images=max_images)
    if images:
        return images
    return [match.thumbnail_url] if match.thumbnail_url else []
