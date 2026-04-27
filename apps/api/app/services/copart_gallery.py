from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_GALLERY_URL_TEMPLATE = "https://inventoryv2.copart.io/v1/lotImages/{lot_number}?country=us&brand=cprt"


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


def copart_gallery_enabled() -> bool:
    return _env_bool("COPART_GALLERY_ENABLED", True)


def copart_gallery_max_images() -> int:
    return _env_int("COPART_GALLERY_MAX_IMAGES_PER_LOT", 8, minimum=1, maximum=40)


def copart_gallery_url(lot_number: str, image_url: str | None = None) -> str:
    value = (image_url or "").strip().replace("http://", "https://")
    if value.startswith("https://inventoryv2.copart.io/") and "/lotImages/" in value:
        return value
    template = os.getenv("COPART_GALLERY_URL_TEMPLATE", DEFAULT_GALLERY_URL_TEMPLATE).strip() or DEFAULT_GALLERY_URL_TEMPLATE
    return template.replace("{lot_number}", lot_number.strip())


def _normalize_image_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    url = value.strip()
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("http://"):
        return f"https://{url[7:]}"
    if url.startswith("https://"):
        return url
    return f"https://{url.lstrip('/')}"


def _best_link(links: list[dict[str, Any]]) -> str | None:
    for predicate in (
        lambda item: item.get("isHdImage") is False and item.get("isThumbNail") is False,
        lambda item: item.get("isHdImage") is True and item.get("isThumbNail") is False,
        lambda item: item.get("isThumbNail") is False,
        lambda item: True,
    ):
        for item in links:
            if predicate(item):
                url = _normalize_image_url(item.get("url"))
                if url:
                    return url
    return None


def extract_gallery_image_urls(payload: dict[str, Any], *, max_images: int | None = None) -> list[str]:
    limit = max_images or copart_gallery_max_images()
    images: list[str] = []
    seen: set[str] = set()
    lot_images = payload.get("lotImages")
    if not isinstance(lot_images, list):
        return images

    sorted_items = sorted(
        (item for item in lot_images if isinstance(item, dict)),
        key=lambda item: item.get("sequence") if isinstance(item.get("sequence"), int) else 9999,
    )
    for item in sorted_items:
        links = item.get("link")
        if not isinstance(links, list):
            continue
        url = _best_link([link for link in links if isinstance(link, dict)])
        if not url or url in seen:
            continue
        seen.add(url)
        images.append(url)
        if len(images) >= limit:
            break
    return images


def fetch_copart_gallery_images(lot_number: str, image_url: str | None = None) -> list[str]:
    if not copart_gallery_enabled():
        return []

    url = copart_gallery_url(lot_number, image_url)
    timeout = _env_int("COPART_GALLERY_TIMEOUT_SECONDS", 12, minimum=2, maximum=60)
    retry_count = _env_int("COPART_GALLERY_RETRY_COUNT", 1, minimum=0, maximum=5)
    delay_ms = _env_int("COPART_GALLERY_RETRY_BACKOFF_MS", 300, minimum=0, maximum=10_000)
    last_error: Exception | None = None

    for attempt in range(retry_count + 1):
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/json,text/plain,*/*",
                    "User-Agent": "auto-import-hub/0.1 copart-gallery",
                },
            )
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            if isinstance(payload, dict):
                return extract_gallery_image_urls(payload)
            return []
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retry_count and delay_ms > 0:
                time.sleep(delay_ms / 1000)

    return [] if last_error else []
