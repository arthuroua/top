import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.privacy import hide_data_source, public_source_label
from app.db import get_db
from app.models import Lot, LotImage, Vehicle
from app.schemas import LotImageItem, LotItem, PriceEventItem, RecentVehicleItem, RecentVehiclesResponse, VehicleCard
from app.services.public_lots import is_public_real_lot, latest_import_payload
from app.services.sales_status import EXCLUDED_SALE_KEYWORDS, confirmed_sale_status_clause

router = APIRouter(prefix="/api/v1", tags=["vehicles"])


@router.get("/vehicles/stats")
def get_vehicle_stats(db: Session = Depends(get_db)) -> dict:
    source_rows = db.execute(select(Lot.source, func.count(Lot.id)).group_by(Lot.source)).all()
    return {
        "vehicles": db.scalar(select(func.count(Vehicle.vin))) or 0,
        "lots": db.scalar(select(func.count(Lot.id))) or 0,
        "images": db.scalar(select(func.count(LotImage.id))) or 0,
        "lots_with_price": db.scalar(select(func.count(Lot.id)).where(Lot.hammer_price_usd.is_not(None))) or 0,
        "lots_with_images": db.scalar(
            select(func.count(func.distinct(LotImage.lot_id)))
        )
        or 0,
        "sources": {
            (public_source_label() if hide_data_source() else source): count
            for source, count in source_rows
        },
        "raw_sources": {source: count for source, count in source_rows} if not hide_data_source() else None,
    }


def _is_direct_image_url(url: str) -> bool:
    if url.startswith("/api/v1/media/archive/"):
        return True
    if url.startswith("/api/v1/media/vehicles/"):
        return True
    lowered = url.lower().split("?", 1)[0].split("#", 1)[0]
    return lowered.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"))


def _public_media_allowed_hosts() -> tuple[str, ...]:
    raw = os.getenv("MEDIA_PROXY_ALLOWED_HOSTS", "copart.com,iaai.com,riastatic.com,auto.ria.com")
    return tuple(host.strip().lower().lstrip(".") for host in raw.split(",") if host.strip())


def _is_allowed_public_host(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower().lstrip(".")
    if not hostname:
        return False
    return any(hostname == allowed or hostname.endswith(f".{allowed}") for allowed in _public_media_allowed_hosts())


def _is_public_proxyable_image_url(url: str) -> bool:
    if url.startswith("/api/v1/media/archive/"):
        return True
    if _is_allowed_public_host(url):
        return True
    return _is_direct_image_url(url)


def _sorted_lot_images(lot: Lot) -> list[LotImage]:
    return sorted(lot.images, key=lambda item: ((item.shot_order is None), (item.shot_order or 0), item.created_at))


def _preferred_lot_images(lot: Lot) -> list[LotImage]:
    images = [image for image in _sorted_lot_images(lot) if _is_public_proxyable_image_url(image.image_url)]
    archived_images = [image for image in images if image.image_url.startswith("/api/v1/media/archive/")]
    return archived_images or images


def _to_lot_item(lot: Lot) -> LotItem:
    images = _sorted_lot_images(lot)
    events = sorted(lot.price_events, key=lambda item: item.event_time, reverse=True)
    payload = latest_import_payload(lot)
    auction_specs = {
        key: value
        for key, value in {
            "trim": payload.get("trim"),
            "series": payload.get("series"),
            "body_style": payload.get("body_style"),
            "engine": payload.get("engine"),
            "transmission": payload.get("transmission"),
            "fuel_type": payload.get("fuel_type"),
            "drivetrain": payload.get("drivetrain"),
            "vehicle_type": payload.get("vehicle_type"),
            "exterior_color": payload.get("exterior_color"),
            "interior_color": payload.get("interior_color"),
            "cylinders": payload.get("cylinders"),
            **(payload.get("attributes") or {}),
        }.items()
        if value not in (None, "")
    }

    if hide_data_source():
        safe_images: list[LotImageItem] = []
        seen_images: set[str] = set()
        preferred_images = _preferred_lot_images(lot)
        image_indexes = {image.id: index for index, image in enumerate(images)}
        for image in preferred_images:
            image_key = f"checksum:{image.checksum}" if image.checksum else f"url:{image.image_url}"
            if image_key in seen_images:
                continue
            seen_images.add(image_key)
            if image.image_url.startswith("/api/v1/media/archive/"):
                safe_images.append(
                    LotImageItem(
                        image_url=image.image_url,
                        shot_order=image.shot_order,
                        checksum=image.checksum,
                    )
                )
                continue
            index = image_indexes.get(image.id, 0)
            public_url = f"/api/v1/media/vehicles/{lot.vin}/lots/{lot.lot_number}/images/{index}"
            safe_images.append(
                LotImageItem(
                    image_url=public_url,
                    shot_order=image.shot_order,
                    checksum=image.checksum,
                )
            )
    else:
        safe_images = []
        seen_images = set()
        for image in images:
            image_key = f"checksum:{image.checksum}" if image.checksum else f"url:{image.image_url}"
            if image_key in seen_images:
                continue
            seen_images.add(image_key)
            safe_images.append(
                LotImageItem(
                    image_url=image.image_url,
                    shot_order=image.shot_order,
                    checksum=image.checksum,
                )
            )

    return LotItem(
        source=public_source_label() if hide_data_source() else lot.source,
        lot_number=lot.lot_number,
        sale_date=lot.sale_date.isoformat() if lot.sale_date else None,
        hammer_price_usd=lot.hammer_price_usd,
        status=lot.status,
        location=lot.location,
        title_brand=payload.get("title_brand"),
        primary_damage=payload.get("primary_damage"),
        secondary_damage=payload.get("secondary_damage"),
        odometer=payload.get("odometer"),
        run_and_drive=payload.get("run_and_drive"),
        keys_present=payload.get("keys_present"),
        auction_specs=auction_specs,
        images=safe_images,
        price_events=[
            PriceEventItem(
                event_type=event.event_type,
                old_value=event.old_value,
                new_value=event.new_value,
                event_time=event.event_time.isoformat(),
            )
            for event in events
        ],
    )


def _first_safe_image(lot: Lot) -> str | None:
    images = _sorted_lot_images(lot)
    preferred_images = _preferred_lot_images(lot)
    image_indexes = {image.id: index for index, image in enumerate(images)}
    for image in preferred_images:
        if image.image_url.startswith("/api/v1/media/archive/"):
            return image.image_url
        if hide_data_source():
            index = image_indexes.get(image.id, 0)
            return f"/api/v1/media/vehicles/{lot.vin}/lots/{lot.lot_number}/images/{index}"
        return image.image_url
    return None


def _not_excluded_sale_status_clause():
    normalized = func.lower(func.coalesce(Lot.status, ""))
    return ~(
        normalized.like(f"%{EXCLUDED_SALE_KEYWORDS[0]}%")
        | normalized.like(f"%{EXCLUDED_SALE_KEYWORDS[1]}%")
        | normalized.like(f"%{EXCLUDED_SALE_KEYWORDS[2]}%")
        | normalized.like(f"%{EXCLUDED_SALE_KEYWORDS[3]}%")
    )


@router.get("/vehicles/recent", response_model=RecentVehiclesResponse)
def list_recent_vehicles(
    limit: int = 12,
    final_only: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> RecentVehiclesResponse:
    safe_limit = min(max(limit, 1), 24)
    base_query = (
        select(Lot)
        .options(selectinload(Lot.images), selectinload(Lot.vehicle), selectinload(Lot.import_snapshots))
        .where(Lot.hammer_price_usd.is_not(None), Lot.hammer_price_usd > 0)
    )
    if final_only:
        base_query = base_query.where(confirmed_sale_status_clause(Lot.status))

    photo_first_query = (
        base_query.join(LotImage, LotImage.lot_id == Lot.id)
        .order_by(Lot.sale_date.desc(), Lot.fetched_at.desc())
        .limit(max(safe_limit * 200, 4000))
    )
    photo_first_lots = db.execute(photo_first_query).scalars().unique().all()
    public_lots = [lot for lot in photo_first_lots if is_public_real_lot(lot) and _first_safe_image(lot)]

    if len(public_lots) < safe_limit:
        fetch_window = max(safe_limit * 250, 3000) if final_only else max(safe_limit * 20, 240)
        lots = db.execute(base_query.order_by(Lot.sale_date.desc(), Lot.fetched_at.desc()).limit(fetch_window)).scalars().all()
        seen_lot_ids = {lot.id for lot in public_lots}
        public_lots.extend(
            lot
            for lot in lots
            if is_public_real_lot(lot) and lot.id not in seen_lot_ids
        )

    public_lots.sort(key=lambda lot: (_first_safe_image(lot) is not None, lot.fetched_at), reverse=True)
    if len([lot for lot in public_lots if _first_safe_image(lot)]) < safe_limit:
        relaxed_query = (
            select(Lot)
            .options(selectinload(Lot.images), selectinload(Lot.vehicle), selectinload(Lot.import_snapshots))
            .join(LotImage, LotImage.lot_id == Lot.id)
            .where(Lot.hammer_price_usd.is_not(None), Lot.hammer_price_usd > 0)
            .where(_not_excluded_sale_status_clause())
            .order_by(Lot.sale_date.desc(), Lot.fetched_at.desc())
            .limit(max(safe_limit * 200, 4000))
        )
        relaxed_lots = db.execute(relaxed_query).scalars().unique().all()
        seen_lot_ids = {lot.id for lot in public_lots}
        public_lots.extend(
            lot
            for lot in relaxed_lots
            if is_public_real_lot(lot) and _first_safe_image(lot) and lot.id not in seen_lot_ids
        )
        public_lots.sort(key=lambda lot: (_first_safe_image(lot) is not None, lot.fetched_at), reverse=True)
    public_lots = public_lots[:safe_limit]
    return RecentVehiclesResponse(
        items=[
            RecentVehicleItem(
                vin=lot.vin,
                make=lot.vehicle.make if lot.vehicle else None,
                model=lot.vehicle.model if lot.vehicle else None,
                year=lot.vehicle.year if lot.vehicle else None,
                title_brand=lot.vehicle.title_brand if lot.vehicle else None,
                lot_number=lot.lot_number,
                sale_date=lot.sale_date.isoformat() if lot.sale_date else None,
                hammer_price_usd=lot.hammer_price_usd,
                status=lot.status,
                location=lot.location,
                image_url=_first_safe_image(lot),
                updated_at=lot.fetched_at,
            )
            for lot in public_lots
        ]
    )


@router.get("/vehicles/{vin}", response_model=VehicleCard)
def get_vehicle(vin: str, db: Session = Depends(get_db)) -> VehicleCard:
    vin_key = vin.upper()

    vehicle = db.get(Vehicle, vin_key)
    if vehicle is not None:
        lots = (
            db.execute(
                select(Lot)
                .options(selectinload(Lot.images), selectinload(Lot.price_events), selectinload(Lot.import_snapshots))
                .where(Lot.vin == vin_key)
                .where(Lot.hammer_price_usd.is_not(None), Lot.hammer_price_usd > 0, confirmed_sale_status_clause(Lot.status))
                .order_by(Lot.sale_date.desc(), Lot.fetched_at.desc())
            )
            .scalars()
            .all()
        )
        public_lots = [lot for lot in lots if is_public_real_lot(lot)]
        if not public_lots:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        return VehicleCard(
            vin=vin_key,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year,
            title_brand=vehicle.title_brand,
            lots=[_to_lot_item(lot) for lot in public_lots],
        )

    raise HTTPException(status_code=404, detail="Vehicle not found")
