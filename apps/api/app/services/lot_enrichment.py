from __future__ import annotations

import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Lot, LotImage, LotImportSnapshot, MediaAsset
from app.services.copart_gallery import fetch_copart_gallery_images
from app.services.iaai_gallery import fetch_iaai_gallery_images
from app.services.media_archive import archive_image, public_media_url


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


def _candidate_image_urls(url: str) -> list[str]:
    value = url.strip()
    if not value:
        return []
    candidates: list[str] = []
    if "_thb." in value:
        candidates.extend([value.replace("_thb.", "_ful."), value.replace("_thb.", "_hrs.")])
    if "_THB." in value:
        candidates.extend([value.replace("_THB.", "_FUL."), value.replace("_THB.", "_HRS.")])
    if "thumbnail" in value.lower():
        candidates.extend([
            value.replace("thumbnail", "full").replace("Thumbnail", "Full"),
            value.replace("thumbnail", "highres").replace("Thumbnail", "HighRes"),
        ])
    return [item for item in candidates if item != value]


def _normalize_remote_image_url(value: str) -> str | None:
    url = value.strip()
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("http://"):
        return f"https://{url[7:]}"
    if url.startswith("https://"):
        return url
    return None


def _looks_like_image_url(value: str) -> bool:
    normalized = _normalize_remote_image_url(value)
    if not normalized:
        return False
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    query = parsed.query.lower()
    if "imagekeys=" in query:
        return True
    if any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
        return True
    return any(
        token in host or token in path
        for token in ("copart", "iaai", "vis.", "image", "photo", "img", "thumbnail", "resizer")
    )


def _extract_image_urls_from_data(payload: Any) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def visit(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            if not _looks_like_image_url(value):
                return
            normalized = _normalize_remote_image_url(value)
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            found.append(normalized)
            return
        if isinstance(value, dict):
            for nested in value.values():
                visit(nested)
            return
        if isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(payload)
    return found


def _snapshot_candidates(snapshot: LotImportSnapshot) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for candidate in snapshot.images_json or []:
        normalized = _normalize_remote_image_url(candidate) if isinstance(candidate, str) else None
        if normalized and normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)
    for candidate in _extract_image_urls_from_data(snapshot.payload_json or {}):
        if candidate not in seen:
            seen.add(candidate)
            urls.append(candidate)
    return urls


def _sort_snapshot_key(snapshot: LotImportSnapshot) -> tuple[float, float]:
    imported_ts = snapshot.imported_at.timestamp() if snapshot.imported_at else 0.0
    sale_ts = time.mktime(snapshot.sale_date.timetuple()) if snapshot.sale_date else 0.0
    return imported_ts, sale_ts


def _provider_candidates(db: Session, lot: Lot) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []

    def add_many(items: list[str]) -> None:
        for item in items:
            normalized = _normalize_remote_image_url(item)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            urls.append(normalized)

    if lot.source.lower() == "copart":
        add_many(fetch_copart_gallery_images(lot.lot_number))
    elif lot.source.lower() == "iaai":
        add_many(fetch_iaai_gallery_images(lot.lot_number, vin=lot.vin))

    snapshots = sorted(lot.import_snapshots, key=_sort_snapshot_key, reverse=True)
    for snapshot in snapshots:
        add_many(_snapshot_candidates(snapshot))

    return urls


def _source_url_for_image(db: Session, image_url: str) -> str:
    prefix = "/api/v1/media/archive/"
    if not image_url.startswith(prefix):
        return image_url
    asset_id = image_url.removeprefix(prefix).split("/", 1)[0].strip()
    if not asset_id:
        return image_url
    asset = db.get(MediaAsset, asset_id)
    if asset is None or not asset.source_url:
        return image_url
    return asset.source_url


def _url_exists(url: str) -> bool:
    request = Request(
        url,
        headers={
            "Accept": "image/*,*/*;q=0.8",
            "User-Agent": "car-import-mvp/0.1 enrichment",
        },
        method="HEAD",
    )
    try:
        with urlopen(request, timeout=_env_int("ENRICHMENT_IMAGE_HEAD_TIMEOUT_SECONDS", 8, minimum=1)) as response:
            content_type = response.headers.get_content_type() or ""
            return response.status < 400 and content_type.startswith("image/")
    except HTTPError as exc:
        return 200 <= exc.code < 400
    except (URLError, TimeoutError, OSError):
        return False


def enrich_lot_images(db: Session, *, source: str, lot_number: str, vin: str | None = None) -> dict:
    query = (
        select(Lot)
        .options(selectinload(Lot.images), selectinload(Lot.import_snapshots))
        .where(Lot.source == source.lower(), Lot.lot_number == lot_number.upper())
    )
    if vin:
        query = query.where(Lot.vin == vin.upper())

    lot = db.execute(query).scalars().first()
    if lot is None:
        return {"processed": False, "message": "Lot not found", "images_added": 0}

    existing_urls = {image.image_url for image in lot.images}
    source_images = sorted(lot.images, key=lambda item: ((item.shot_order is None), item.shot_order or 0))
    max_add = _env_int("ENRICHMENT_MAX_IMAGES_PER_LOT", 8, minimum=0)
    verify_urls = _env_bool("ENRICHMENT_VERIFY_IMAGE_URLS", True)
    sleep_ms = _env_int("ENRICHMENT_REQUEST_DELAY_MS", 250, minimum=0)

    added = 0
    next_order = max((image.shot_order or 0 for image in source_images), default=0) + 1
    for candidate_url in _provider_candidates(db, lot):
        if added >= max_add:
            break
        if candidate_url in existing_urls:
            continue
        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000)
        asset = archive_image(
            db,
            provider=lot.source.lower(),
            owner_type="lot",
            owner_id=f"{lot.source.lower()}:{lot.lot_number}",
            source_url=candidate_url,
        )
        stored_url = public_media_url(asset) if asset is not None and asset.is_archived else candidate_url
        checksum = asset.checksum if asset is not None and asset.is_archived else None
        checksum_key = f"checksum:{checksum}" if checksum else ""
        if stored_url in existing_urls or (checksum_key and checksum_key in existing_urls):
            continue
        db.add(LotImage(lot_id=lot.id, image_url=stored_url, shot_order=next_order, checksum=checksum))
        existing_urls.add(candidate_url)
        existing_urls.add(stored_url)
        if checksum_key:
            existing_urls.add(checksum_key)
        next_order += 1
        added += 1

    for image in source_images:
        source_url = _source_url_for_image(db, image.image_url)
        existing_urls.add(source_url)
        if image.checksum:
            existing_urls.add(f"checksum:{image.checksum}")
        for candidate_url in _candidate_image_urls(source_url):
            if added >= max_add:
                break
            if candidate_url in existing_urls:
                continue
            if sleep_ms > 0:
                time.sleep(sleep_ms / 1000)
            if verify_urls and not _url_exists(candidate_url):
                continue

            asset = archive_image(
                db,
                provider=lot.source.lower(),
                owner_type="lot",
                owner_id=f"{lot.source.lower()}:{lot.lot_number}",
                source_url=candidate_url,
            )
            stored_url = public_media_url(asset) if asset is not None and asset.is_archived else candidate_url
            checksum = asset.checksum if asset is not None and asset.is_archived else None
            checksum_key = f"checksum:{checksum}" if checksum else ""
            if stored_url in existing_urls or (checksum_key and checksum_key in existing_urls):
                continue
            db.add(LotImage(lot_id=lot.id, image_url=stored_url, shot_order=next_order, checksum=checksum))
            existing_urls.add(candidate_url)
            existing_urls.add(stored_url)
            if checksum_key:
                existing_urls.add(checksum_key)
            next_order += 1
            added += 1
        if added >= max_add:
            break

    db.commit()
    return {
        "processed": True,
        "message": "Lot enriched",
        "vin": lot.vin,
        "source": lot.source,
        "lot_number": lot.lot_number,
        "images_added": added,
    }
