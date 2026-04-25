from __future__ import annotations

import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Lot, LotImage, MediaAsset
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
        .options(selectinload(Lot.images))
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
    for image in source_images:
        source_url = _source_url_for_image(db, image.image_url)
        existing_urls.add(source_url)
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
            db.add(LotImage(lot_id=lot.id, image_url=stored_url, shot_order=next_order, checksum=checksum))
            existing_urls.add(candidate_url)
            existing_urls.add(stored_url)
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
