from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Lot, LotImportSnapshot
from app.schemas import IngestionJobPayload


def create_ingestion_snapshot(db: Session, *, lot: Lot, job: IngestionJobPayload) -> LotImportSnapshot:
    snapshot = LotImportSnapshot(
        lot_id=lot.id,
        source=job.source,
        lot_number=job.lot_number,
        vin=job.vin.upper(),
        sale_date=job.sale_date,
        hammer_price_usd=job.hammer_price_usd,
        status=job.status,
        location=job.location,
        images_json=list(job.images),
        price_events_json=[event.model_dump(mode="json") for event in job.price_events],
        payload_json=job.model_dump(mode="json"),
    )
    db.add(snapshot)
    return snapshot


def _apply_snapshot_filters(
    query: Select,
    *,
    vin: str | None,
    lot_number: str | None,
    source: str | None,
) -> Select:
    if vin:
        query = query.where(LotImportSnapshot.vin == vin.upper())
    if lot_number:
        query = query.where(LotImportSnapshot.lot_number == lot_number.upper())
    if source:
        query = query.where(func.lower(LotImportSnapshot.source) == source.lower())
    return query


def count_ingestion_snapshots(
    db: Session,
    *,
    vin: str | None = None,
    lot_number: str | None = None,
    source: str | None = None,
) -> int:
    query = select(func.count()).select_from(LotImportSnapshot)
    query = _apply_snapshot_filters(
        query,
        vin=vin,
        lot_number=lot_number,
        source=source,
    )
    result = db.execute(query).scalar()
    return int(result or 0)


def list_ingestion_snapshots(
    db: Session,
    *,
    vin: str | None = None,
    lot_number: str | None = None,
    source: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> list[LotImportSnapshot]:
    query = select(LotImportSnapshot)
    query = _apply_snapshot_filters(
        query,
        vin=vin,
        lot_number=lot_number,
        source=source,
    )
    safe_page = max(1, page)
    safe_page_size = max(1, page_size)
    offset = (safe_page - 1) * safe_page_size
    query = query.order_by(LotImportSnapshot.imported_at.desc()).offset(offset).limit(safe_page_size)
    return list(db.execute(query).scalars().all())
