from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Lot
from app.services.media_archive import archive_image, public_media_url


def archive_existing_copart_images(db: Session, *, limit: int = 200) -> dict:
    lots = (
        db.execute(
            select(Lot)
            .options(selectinload(Lot.images))
            .where(Lot.source == "copart")
            .order_by(Lot.fetched_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    lots_seen = 0
    images_seen = 0
    images_archived = 0
    images_failed = 0
    for lot in lots:
        lots_seen += 1
        for image in lot.images:
            images_seen += 1
            if image.image_url.startswith("/api/v1/media/archive/"):
                images_archived += 1
                continue
            asset = archive_image(
                db,
                provider="copart",
                owner_type="lot",
                owner_id=f"copart:{lot.lot_number}",
                source_url=image.image_url,
            )
            if asset is None or not asset.is_archived:
                images_failed += 1
                continue
            image.image_url = public_media_url(asset)
            image.checksum = asset.checksum
            images_archived += 1

    db.commit()
    return {
        "lots_seen": lots_seen,
        "images_seen": images_seen,
        "images_archived": images_archived,
        "images_failed": images_failed,
    }
