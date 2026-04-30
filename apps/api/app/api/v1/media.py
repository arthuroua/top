from __future__ import annotations

import mimetypes
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Lot, MediaAsset

router = APIRouter(prefix="/api/v1/media", tags=["media"])


def _allowed_hosts() -> tuple[str, ...]:
    raw = os.getenv("MEDIA_PROXY_ALLOWED_HOSTS", "copart.com,copart.io,iaai.com,vis.iaai.com,riastatic.com,auto.ria.com")
    values = {
        host.strip().lower().lstrip(".")
        for host in raw.split(",")
        if host.strip()
    }
    values.update({"copart.com", "copart.io", "iaai.com", "vis.iaai.com", "riastatic.com", "auto.ria.com"})
    return tuple(sorted(values))


def _is_host_allowed(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower().lstrip(".")
    if not hostname:
        return False
    for allowed in _allowed_hosts():
        if hostname == allowed or hostname.endswith(f".{allowed}"):
            return True
    return False


def _normalize_url(url: str) -> str:
    value = url.strip()
    if value.startswith("http://"):
        return f"https://{value[7:]}"
    return value


def _fetch_upstream_image(source_url: str, *, cache_seconds: int = 3600) -> Response:
    normalized_url = _normalize_url(source_url)
    if not _is_host_allowed(normalized_url):
        raise HTTPException(status_code=403, detail="Image host is not allowed")

    request = Request(
        normalized_url,
        headers={
            "Accept": "image/*,*/*;q=0.8",
            "User-Agent": "car-import-mvp/0.1 media-proxy",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=20) as upstream:
            payload = upstream.read()
            content_type = upstream.headers.get_content_type() or mimetypes.guess_type(normalized_url)[0] or "image/jpeg"
            return Response(
                content=payload,
                media_type=content_type,
                headers={"Cache-Control": f"public, max-age={cache_seconds}"},
            )
    except HTTPError as exc:
        status = exc.code if exc.code in {400, 401, 403, 404} else 502
        raise HTTPException(status_code=status, detail="Unable to fetch image from upstream") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=502, detail="Unable to fetch image from upstream") from exc


@router.get("/vehicles/{vin}/lots/{lot_number}/images/{image_index}")
def proxy_lot_image(vin: str, lot_number: str, image_index: int, db: Session = Depends(get_db)) -> Response:
    if image_index < 0:
        raise HTTPException(status_code=400, detail="image_index must be >= 0")

    lot = (
        db.execute(
            select(Lot)
            .options(selectinload(Lot.images))
            .where(Lot.vin == vin.upper(), Lot.lot_number == lot_number.upper())
            .order_by(Lot.fetched_at.desc())
        )
        .scalars()
        .first()
    )
    if lot is None:
        raise HTTPException(status_code=404, detail="Lot not found")

    images = sorted(lot.images, key=lambda item: ((item.shot_order is None), (item.shot_order or 0), item.created_at))
    if image_index >= len(images):
        raise HTTPException(status_code=404, detail="Image not found")

    source_url = _normalize_url(images[image_index].image_url)
    if source_url.startswith("/api/v1/media/archive/"):
        asset_id = source_url.rstrip("/").split("/")[-1]
        return get_archived_image(asset_id, db)
    return _fetch_upstream_image(source_url)


@router.get("/archive/{asset_id}")
def get_archived_image(asset_id: str, db: Session = Depends(get_db)) -> Response:
    asset = db.execute(select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.is_archived.is_(True))).scalars().first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Archived image not found")

    try:
        payload = open(asset.storage_path, "rb").read()
    except OSError as exc:
        if asset.source_url:
            return _fetch_upstream_image(asset.source_url)
        raise HTTPException(status_code=404, detail="Archived image file not found") from exc

    return Response(
        content=payload,
        media_type=asset.content_type or "image/jpeg",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        },
    )
