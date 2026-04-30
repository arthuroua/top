from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MediaAsset


def media_archive_root() -> Path:
    return Path(os.getenv("MEDIA_ARCHIVE_DIR", "/app/media-cache")).resolve()


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


def _allowed_hosts() -> tuple[str, ...]:
    raw = os.getenv("MEDIA_ARCHIVE_ALLOWED_HOSTS", "copart.com,copart.io,iaai.com,vis.iaai.com,riastatic.com,auto.ria.com")
    values = {host.strip().lower().lstrip(".") for host in raw.split(",") if host.strip()}
    values.update({"copart.com", "copart.io", "iaai.com", "vis.iaai.com", "riastatic.com", "auto.ria.com"})
    return tuple(sorted(values))


def _is_host_allowed(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower().lstrip(".")
    if not hostname:
        return False
    return any(hostname == allowed or hostname.endswith(f".{allowed}") for allowed in _allowed_hosts())


def source_url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def _extension(content_type: str, source_url: str) -> str:
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
    if guessed:
        return guessed
    path_suffix = Path(urlparse(source_url).path).suffix.lower()
    return path_suffix if path_suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def public_media_url(asset: MediaAsset) -> str:
    return f"/api/v1/media/archive/{asset.id}"


def archive_image(
    db: Session,
    *,
    provider: str,
    owner_type: str,
    owner_id: str,
    source_url: str,
) -> MediaAsset | None:
    clean_url = source_url.strip().replace("http://", "https://")
    if not clean_url or not _is_host_allowed(clean_url):
        return None

    url_hash = source_url_hash(clean_url)
    existing = db.execute(select(MediaAsset).where(MediaAsset.source_url_hash == url_hash)).scalars().first()
    if existing and existing.is_archived and Path(existing.storage_path).exists():
        return existing

    root = media_archive_root()
    root.mkdir(parents=True, exist_ok=True)
    request = Request(
        clean_url,
        headers={
            "Accept": "image/*,*/*;q=0.8",
            "User-Agent": "auto-import-hub/0.1 media-archive",
        },
    )
    max_bytes = _env_int("MEDIA_ARCHIVE_MAX_BYTES", 5_000_000, minimum=100_000, maximum=25_000_000)
    timeout = _env_int("MEDIA_ARCHIVE_TIMEOUT_SECONDS", 20, minimum=3, maximum=120)

    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type() or mimetypes.guess_type(clean_url)[0] or "image/jpeg"
            if not content_type.startswith("image/"):
                raise RuntimeError(f"Unexpected content type: {content_type}")
            payload = response.read(max_bytes + 1)
            if len(payload) > max_bytes:
                raise RuntimeError("Image is larger than MEDIA_ARCHIVE_MAX_BYTES")
    except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as exc:
        if existing:
            existing.error_message = str(exc)[:512]
            db.commit()
        return existing

    checksum = hashlib.sha256(payload).hexdigest()
    ext = _extension(content_type, clean_url)
    relative_path = Path(provider) / owner_type / f"{url_hash[:2]}" / f"{url_hash}{ext}"
    storage_path = root / relative_path
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(payload)

    if existing is None:
        existing = MediaAsset(
            provider=provider,
            owner_type=owner_type,
            owner_id=owner_id,
            source_url=clean_url,
            source_url_hash=url_hash,
            content_type=content_type,
            storage_path=str(storage_path),
            size_bytes=len(payload),
            checksum=checksum,
            is_archived=True,
            error_message=None,
        )
        db.add(existing)
    else:
        existing.provider = provider
        existing.owner_type = owner_type
        existing.owner_id = owner_id
        existing.content_type = content_type
        existing.storage_path = str(storage_path)
        existing.size_bytes = len(payload)
        existing.checksum = checksum
        existing.is_archived = True
        existing.error_message = None
    db.commit()
    db.refresh(existing)
    return existing


def archived_url_for_source(db: Session, source_url: str) -> str | None:
    record = db.execute(select(MediaAsset).where(MediaAsset.source_url_hash == source_url_hash(source_url))).scalars().first()
    if not record or not record.is_archived:
        return None
    return public_media_url(record)
