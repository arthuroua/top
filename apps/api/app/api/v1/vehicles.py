from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.data.mock_data import MOCK_VEHICLES
from app.db import get_db
from app.models import Lot, Vehicle
from app.schemas import LotImageItem, LotItem, PriceEventItem, VehicleCard

router = APIRouter(prefix="/api/v1", tags=["vehicles"])


def _to_lot_item(lot: Lot) -> LotItem:
    images = sorted(lot.images, key=lambda item: ((item.shot_order is None), (item.shot_order or 0), item.created_at))
    events = sorted(lot.price_events, key=lambda item: item.event_time, reverse=True)

    return LotItem(
        source=lot.source,
        lot_number=lot.lot_number,
        sale_date=lot.sale_date.isoformat() if lot.sale_date else None,
        hammer_price_usd=lot.hammer_price_usd,
        status=lot.status,
        location=lot.location,
        images=[
            LotImageItem(
                image_url=image.image_url,
                shot_order=image.shot_order,
                checksum=image.checksum,
            )
            for image in images
        ],
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
                .options(selectinload(Lot.images), selectinload(Lot.price_events))
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
        return VehicleCard(**fallback_vehicle)

    raise HTTPException(status_code=404, detail="Vehicle not found")
