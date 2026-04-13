from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lot, LotImage, PriceEvent, Vehicle
from app.schemas import IngestionJobPayload, IngestionProcessResult


def apply_ingestion_job(db: Session, job: IngestionJobPayload) -> IngestionProcessResult:
    vin = job.vin.upper()

    vehicle = db.get(Vehicle, vin)
    if vehicle is None:
        vehicle = Vehicle(vin=vin)
        db.add(vehicle)
        db.flush()

    lot = db.execute(select(Lot).where(Lot.source == job.source, Lot.lot_number == job.lot_number)).scalar_one_or_none()
    if lot is None:
        lot = Lot(source=job.source, lot_number=job.lot_number, vin=vin)
        db.add(lot)
        db.flush()
    else:
        lot.vin = vin

    if job.sale_date is not None:
        lot.sale_date = job.sale_date
    if job.hammer_price_usd is not None:
        lot.hammer_price_usd = job.hammer_price_usd
    if job.status is not None:
        lot.status = job.status
    if job.location is not None:
        lot.location = job.location

    lot.fetched_at = datetime.now(timezone.utc)

    images_upserted = 0
    for idx, image_url in enumerate(job.images, start=1):
        existing_image = db.execute(
            select(LotImage).where(LotImage.lot_id == lot.id, LotImage.image_url == image_url)
        ).scalar_one_or_none()

        if existing_image is None:
            db.add(LotImage(lot_id=lot.id, image_url=image_url, shot_order=idx))
            images_upserted += 1
        else:
            existing_image.shot_order = idx

    price_events_added = 0
    for event in job.price_events:
        existing_event = db.execute(
            select(PriceEvent).where(
                PriceEvent.lot_id == lot.id,
                PriceEvent.event_type == event.event_type,
                PriceEvent.event_time == event.event_time,
                PriceEvent.new_value == event.new_value,
            )
        ).scalar_one_or_none()

        if existing_event is None:
            db.add(
                PriceEvent(
                    lot_id=lot.id,
                    event_type=event.event_type,
                    old_value=event.old_value,
                    new_value=event.new_value,
                    event_time=event.event_time,
                )
            )
            price_events_added += 1

    db.commit()
    db.refresh(lot)

    return IngestionProcessResult(
        processed=True,
        message="Job processed successfully",
        lot_id=lot.id,
        vin=vin,
        source=lot.source,
        lot_number=lot.lot_number,
        images_upserted=images_upserted,
        price_events_added=price_events_added,
    )
