from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models import IngestionConnectorRun


def create_ingestion_run(
    db: Session,
    *,
    provider: str,
    mode: str,
    selector: dict[str, str | bool | None],
    request_hash: str,
    source_record_id: str | None,
    response_hash: str | None,
    success: bool,
    error_message: str | None,
    latency_ms: int,
    enqueued: bool,
    queue_depth: int | None,
    job_json: dict | None,
) -> IngestionConnectorRun:
    run = IngestionConnectorRun(
        provider=provider,
        mode=mode,
        selector_json=selector,
        request_hash=request_hash,
        source_record_id=source_record_id,
        response_hash=response_hash,
        success=success,
        error_message=error_message,
        latency_ms=latency_ms,
        enqueued=enqueued,
        queue_depth=queue_depth,
        job_json=job_json,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _apply_run_filters(
    query: Select,
    *,
    provider: str | None,
    success: bool | None,
    query_text: str | None,
) -> Select:
    if provider:
        query = query.where(IngestionConnectorRun.provider == provider)
    if success is not None:
        query = query.where(IngestionConnectorRun.success == success)
    if query_text:
        needle = f"%{query_text.lower()}%"
        query = query.where(
            or_(
                func.lower(func.coalesce(IngestionConnectorRun.source_record_id, "")).like(needle),
                func.lower(func.coalesce(IngestionConnectorRun.error_message, "")).like(needle),
                func.lower(cast(IngestionConnectorRun.selector_json, String)).like(needle),
                func.lower(cast(IngestionConnectorRun.job_json, String)).like(needle),
            )
        )
    return query


def count_ingestion_runs(
    db: Session,
    *,
    provider: str | None = None,
    success: bool | None = None,
    query_text: str | None = None,
) -> int:
    query = select(func.count()).select_from(IngestionConnectorRun)
    query = _apply_run_filters(
        query,
        provider=provider,
        success=success,
        query_text=query_text,
    )
    result = db.execute(query).scalar()
    return int(result or 0)


def list_ingestion_runs(
    db: Session,
    *,
    provider: str | None = None,
    success: bool | None = None,
    query_text: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> list[IngestionConnectorRun]:
    query = select(IngestionConnectorRun)
    query = _apply_run_filters(
        query,
        provider=provider,
        success=success,
        query_text=query_text,
    )

    sort_map = {
        "created_at": IngestionConnectorRun.created_at,
        "latency_ms": IngestionConnectorRun.latency_ms,
    }
    sort_column = sort_map.get(sort_by, IngestionConnectorRun.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset(max(0, offset)).limit(limit)
    return list(db.execute(query).scalars().all())
