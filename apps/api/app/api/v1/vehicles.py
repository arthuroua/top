from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.privacy import hide_data_source, public_source_label
from app.data.mock_data import MOCK_VEHICLES
from app.db import get_db
from app.models import Lot, Vehicle
from app.schemas import LotImageItem, LotItem, PriceEventItem, VehicleCard

router = APIRouter(prefix="/api/v1", tags=["vehicles"])


def _is_direct_image_url(url: str) -> bool:
    lowered = url.lower().split("?", 1)[0].split("#", 1)[0]
    return lowered.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"))


def _to_lot_item(lot: Lot) -> LotItem:
    images = sorted(lot.images, key=lambda item: ((item.shot_order is None), (item.shot_order or 0), item.created_at))
    events = sorted(lot.price_events, key=lambda item: item.event_time, reverse=True)
    latest_snapshot = max(lot.import_snapshots, key=lambda item: item.imported_at, default=None)
    payload = latest_snapshot.payload_json if latest_snapshot else {}
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
        for index, image in enumerate(images):
            if not _is_direct_image_url(image.image_url):
                continue
            safe_images.append(
                LotImageItem(
                    image_url=f"/api/v1/media/vehicles/{lot.vin}/lots/{lot.lot_number}/images/{index}",
                    shot_order=image.shot_order,
                    checksum=image.checksum,
                )
            )
    else:
        safe_images = [
            LotImageItem(
                image_url=image.image_url,
                shot_order=image.shot_order,
                checksum=image.checksum,
            )
            for image in images
        ]

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
                .order_by(Lot.sale_date.desc(), Lot.fetched_at.desc())
            )
            .scalars()
            .all()
        )
        return VehicleCard(
            vin=vin_key,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year,
            title_brand=vehicle.title_brand,
            lots=[_to_lot_item(lot) for lot in lots],
        )

    fallback_vehicle = MOCK_VEHICLES.get(vin_key)
    if fallback_vehicle:
        if not hide_data_source():
            return VehicleCard(**fallback_vehicle)
        payload = deepcopy(fallback_vehicle)
        for lot in payload.get("lots", []):
            lot["source"] = public_source_label()
        return VehicleCard(**payload)

    raise HTTPException(status_code=404, detail="Vehicle not found")
