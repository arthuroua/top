import csv
import hashlib
import io
import json
import os
import secrets
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import Response
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Lot
from app.repositories.ingestion import apply_ingestion_job
from app.repositories.ingestion_history import count_ingestion_snapshots, list_ingestion_snapshots
from app.repositories.ingestion_runs import count_ingestion_runs, create_ingestion_run, list_ingestion_runs
from app.schemas import (
    IngestionConnectorFetchRequest,
    IngestionConnectorFetchResponse,
    IngestionConnectorRunRead,
    IngestionConnectorRunsPage,
    IngestionImportHistoryPage,
    IngestionImportSnapshotRead,
    IngestionConnectorStatus,
    IngestionEnqueueResponse,
    IngestionJobPayload,
    IngestionProcessResult,
    IngestionQueueDepth,
)
from app.services.connectors import connector_statuses, fetch_from_connector
from app.services.copart_csv import load_copart_csv_config, run_copart_csv_ingestion
from app.services.ingestion_queue import (
    enrichment_queue_depth,
    enqueue_enrichment_job,
    enqueue_ingestion_job,
    pop_enrichment_job,
    pop_ingestion_job,
    queue_depth,
)
from app.services.lot_enrichment import enrich_lot_images

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


def _admin_token() -> str:
    value = os.getenv("ADMIN_TOKEN", "").strip()
    if not value or value == "change-me-admin":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin token is not configured",
        )
    return value


def _require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token or not secrets.compare_digest(x_admin_token, _admin_token()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


def _hash_payload(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _to_run_read_model(record) -> IngestionConnectorRunRead:
    return IngestionConnectorRunRead(
        id=record.id,
        provider=record.provider,
        mode=record.mode,
        selector=record.selector_json,
        request_hash=record.request_hash,
        source_record_id=record.source_record_id,
        response_hash=record.response_hash,
        success=record.success,
        error_message=record.error_message,
        latency_ms=record.latency_ms,
        enqueued=record.enqueued,
        queue_depth=record.queue_depth,
        job=record.job_json,
        created_at=record.created_at,
    )


def _to_import_snapshot_read_model(record) -> IngestionImportSnapshotRead:
    payload = record.payload_json or {}
    return IngestionImportSnapshotRead(
        id=record.id,
        lot_id=record.lot_id,
        provider=payload.get("provider"),
        source=record.source,
        lot_number=record.lot_number,
        vin=record.vin,
        source_record_id=payload.get("source_record_id"),
        source_url=payload.get("source_url"),
        sale_date=record.sale_date,
        hammer_price_usd=record.hammer_price_usd,
        status=record.status,
        location=record.location,
        title_brand=payload.get("title_brand"),
        primary_damage=payload.get("primary_damage"),
        secondary_damage=payload.get("secondary_damage"),
        odometer=payload.get("odometer"),
        run_and_drive=payload.get("run_and_drive"),
        keys_present=payload.get("keys_present"),
        make=payload.get("make"),
        model=payload.get("model"),
        year=payload.get("year"),
        trim=payload.get("trim"),
        series=payload.get("series"),
        body_style=payload.get("body_style"),
        engine=payload.get("engine"),
        transmission=payload.get("transmission"),
        fuel_type=payload.get("fuel_type"),
        drivetrain=payload.get("drivetrain"),
        vehicle_type=payload.get("vehicle_type"),
        exterior_color=payload.get("exterior_color"),
        interior_color=payload.get("interior_color"),
        cylinders=payload.get("cylinders"),
        images=record.images_json or [],
        price_events=record.price_events_json or [],
        attributes=payload.get("attributes") or {},
        payload=payload,
        imported_at=record.imported_at,
    )


def _write_failed_run(
    db: Session,
    *,
    provider: str,
    mode: str,
    selector: dict[str, str | bool | None],
    request_hash: str,
    source_record_id: str | None,
    response_hash: str | None,
    error_message: str,
    latency_ms: int,
    enqueued: bool,
    queue_depth_value: int | None,
    job_json: dict | None,
) -> None:
    create_ingestion_run(
        db,
        provider=provider,
        mode=mode,
        selector=selector,
        request_hash=request_hash,
        source_record_id=source_record_id,
        response_hash=response_hash,
        success=False,
        error_message=error_message,
        latency_ms=latency_ms,
        enqueued=enqueued,
        queue_depth=queue_depth_value,
        job_json=job_json,
    )


def _normalize_runs_filters(
    *,
    provider: str | None,
    failed_only: bool,
    q: str | None,
    sort_by: str,
    sort_order: str,
) -> tuple[str | None, bool | None, str | None]:
    provider_filter = provider.lower() if provider else None
    if provider_filter is not None and provider_filter not in {"copart", "iaai"}:
        raise HTTPException(status_code=400, detail="provider must be copart or iaai")
    if sort_by not in {"created_at", "latency_ms"}:
        raise HTTPException(status_code=400, detail="sort_by must be created_at or latency_ms")
    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="sort_order must be asc or desc")

    success_filter = False if failed_only else None
    query_text = q.strip() if q else None
    if query_text == "":
        query_text = None
    return provider_filter, success_filter, query_text


@router.post("/jobs", response_model=IngestionEnqueueResponse, dependencies=[Depends(_require_admin)])
def enqueue_job(payload: IngestionJobPayload) -> IngestionEnqueueResponse:
    try:
        depth = enqueue_ingestion_job(payload)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}") from exc

    return IngestionEnqueueResponse(accepted=True, queue_depth=depth)


@router.get("/connectors", response_model=list[IngestionConnectorStatus])
def list_connectors() -> list[IngestionConnectorStatus]:
    return connector_statuses()


@router.get("/runs", response_model=IngestionConnectorRunsPage)
def get_runs(
    provider: str | None = Query(default=None),
    failed_only: bool = Query(default=False),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
) -> IngestionConnectorRunsPage:
    provider_filter, success_filter, query_text = _normalize_runs_filters(
        provider=provider,
        failed_only=failed_only,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total_count = count_ingestion_runs(
        db,
        provider=provider_filter,
        success=success_filter,
        query_text=query_text,
    )
    offset = (page - 1) * page_size
    runs = list_ingestion_runs(
        db,
        provider=provider_filter,
        success=success_filter,
        query_text=query_text,
        limit=page_size,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    items = [_to_run_read_model(run) for run in runs]
    has_next = offset + len(items) < total_count
    return IngestionConnectorRunsPage(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_next=has_next,
    )


@router.get("/history", response_model=IngestionImportHistoryPage)
def get_import_history(
    vin: str | None = Query(default=None, min_length=17, max_length=17),
    lot_number: str | None = Query(default=None, min_length=1, max_length=32),
    source: str | None = Query(default=None, min_length=1, max_length=16),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> IngestionImportHistoryPage:
    normalized_vin = vin.strip().upper() if vin else None
    normalized_lot = lot_number.strip().upper() if lot_number else None
    normalized_source = source.strip() if source else None

    total_count = count_ingestion_snapshots(
        db,
        vin=normalized_vin,
        lot_number=normalized_lot,
        source=normalized_source,
    )
    snapshots = list_ingestion_snapshots(
        db,
        vin=normalized_vin,
        lot_number=normalized_lot,
        source=normalized_source,
        page=page,
        page_size=page_size,
    )
    items = [_to_import_snapshot_read_model(item) for item in snapshots]
    has_next = (page * page_size) < total_count
    return IngestionImportHistoryPage(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_next=has_next,
    )


@router.get("/runs/export.csv", dependencies=[Depends(_require_admin)])
def export_runs_csv(
    provider: str | None = Query(default=None),
    failed_only: bool = Query(default=False),
    q: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    max_rows: int = Query(default=5000, ge=1, le=20000),
    db: Session = Depends(get_db),
) -> Response:
    provider_filter, success_filter, query_text = _normalize_runs_filters(
        provider=provider,
        failed_only=failed_only,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    runs = list_ingestion_runs(
        db,
        provider=provider_filter,
        success=success_filter,
        query_text=query_text,
        limit=max_rows,
        offset=0,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "run_id",
            "created_at",
            "provider",
            "mode",
            "success",
            "error_message",
            "latency_ms",
            "enqueued",
            "queue_depth",
            "vin",
            "lot_number",
            "source_record_id",
            "request_hash",
            "response_hash",
            "selector_provider",
            "selector_enqueue",
        ]
    )

    for run in runs:
        selector = run.selector_json or {}
        job = run.job_json or {}
        writer.writerow(
            [
                run.id,
                run.created_at.isoformat() if run.created_at else "",
                run.provider,
                run.mode,
                str(run.success),
                run.error_message or "",
                run.latency_ms,
                str(run.enqueued),
                run.queue_depth if run.queue_depth is not None else "",
                job.get("vin") or selector.get("vin") or "",
                job.get("lot_number") or selector.get("lot_number") or "",
                run.source_record_id or "",
                run.request_hash,
                run.response_hash or "",
                selector.get("provider") or "",
                selector.get("enqueue"),
            ]
        )

    filename = f"ingestion-runs-{int(time.time())}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/fetch-and-enqueue", response_model=IngestionConnectorFetchResponse, dependencies=[Depends(_require_admin)])
def fetch_and_enqueue(
    payload: IngestionConnectorFetchRequest,
    db: Session = Depends(get_db),
) -> IngestionConnectorFetchResponse:
    started_at = time.perf_counter()
    selector = {
        "provider": payload.provider,
        "vin": payload.vin,
        "lot_number": payload.lot_number,
        "enqueue": payload.enqueue,
    }
    request_hash = _hash_payload(selector)

    mode = "unknown"
    source_record_id: str | None = None
    job_json: dict | None = None
    response_hash: str | None = None
    enqueued = False
    queue_depth_value: int | None = None

    try:
        fetched = fetch_from_connector(payload)
        mode = fetched.mode
        source_record_id = fetched.source_record_id
        job_json = fetched.job.model_dump(mode="json")

        if payload.enqueue:
            queue_depth_value = enqueue_ingestion_job(fetched.job)
            enqueued = True

        final_response = IngestionConnectorFetchResponse(
            provider=fetched.provider,
            mode=fetched.mode,
            source_record_id=fetched.source_record_id,
            enqueued=enqueued,
            queue_depth=queue_depth_value,
            run_id=None,
            job=fetched.job,
        )

        response_hash = _hash_payload(final_response.model_dump(mode="json"))
        run = create_ingestion_run(
            db,
            provider=payload.provider,
            mode=mode,
            selector=selector,
            request_hash=request_hash,
            source_record_id=source_record_id,
            response_hash=response_hash,
            success=True,
            error_message=None,
            latency_ms=_elapsed_ms(started_at),
            enqueued=enqueued,
            queue_depth=queue_depth_value,
            job_json=job_json,
        )

        final_response.run_id = run.id
        return final_response
    except ValueError as exc:
        _write_failed_run(
            db,
            provider=payload.provider,
            mode=mode,
            selector=selector,
            request_hash=request_hash,
            source_record_id=source_record_id,
            response_hash=response_hash,
            error_message=str(exc),
            latency_ms=_elapsed_ms(started_at),
            enqueued=enqueued,
            queue_depth_value=queue_depth_value,
            job_json=job_json,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotImplementedError as exc:
        _write_failed_run(
            db,
            provider=payload.provider,
            mode=mode,
            selector=selector,
            request_hash=request_hash,
            source_record_id=source_record_id,
            response_hash=response_hash,
            error_message=str(exc),
            latency_ms=_elapsed_ms(started_at),
            enqueued=enqueued,
            queue_depth_value=queue_depth_value,
            job_json=job_json,
        )
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except RedisError as exc:
        message = f"Queue unavailable: {exc}"
        _write_failed_run(
            db,
            provider=payload.provider,
            mode=mode,
            selector=selector,
            request_hash=request_hash,
            source_record_id=source_record_id,
            response_hash=response_hash,
            error_message=message,
            latency_ms=_elapsed_ms(started_at),
            enqueued=False,
            queue_depth_value=None,
            job_json=job_json,
        )
        raise HTTPException(status_code=503, detail=message) from exc
    except RuntimeError as exc:
        _write_failed_run(
            db,
            provider=payload.provider,
            mode=mode,
            selector=selector,
            request_hash=request_hash,
            source_record_id=source_record_id,
            response_hash=response_hash,
            error_message=str(exc),
            latency_ms=_elapsed_ms(started_at),
            enqueued=enqueued,
            queue_depth_value=queue_depth_value,
            job_json=job_json,
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/queue-depth", response_model=IngestionQueueDepth)
def get_queue_depth() -> IngestionQueueDepth:
    try:
        depth = queue_depth()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}") from exc

    return IngestionQueueDepth(queue_depth=depth)


@router.get("/enrichment/queue-depth")
def get_enrichment_queue_depth() -> dict:
    try:
        depth = enrichment_queue_depth()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}") from exc
    return {"queue_depth": depth}


@router.post("/enrichment/enqueue-recent", dependencies=[Depends(_require_admin)])
def enqueue_recent_enrichment(
    limit: int = Query(default=500, ge=1, le=5000),
    only_single_image: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> dict:
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

    enqueued = 0
    last_depth = 0
    for lot in lots:
        if only_single_image and len(lot.images) != 1:
            continue
        if not lot.images:
            continue
        last_depth = enqueue_enrichment_job({"source": lot.source, "lot_number": lot.lot_number, "vin": lot.vin})
        enqueued += 1

    return {"enqueued": enqueued, "queue_depth": last_depth}


@router.post("/enrichment/process-one", dependencies=[Depends(_require_admin)])
def process_one_enrichment(db: Session = Depends(get_db)) -> dict:
    try:
        job = pop_enrichment_job(timeout=1)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}") from exc

    if job is None:
        return {"processed": False, "message": "No enrichment jobs in queue", "images_added": 0}

    return enrich_lot_images(
        db,
        source=str(job.get("source") or "copart"),
        lot_number=str(job.get("lot_number") or ""),
        vin=str(job.get("vin")) if job.get("vin") else None,
    )


@router.post("/copart-csv/run-once", dependencies=[Depends(_require_admin)])
def run_copart_csv_once(
    process_immediately: bool = Query(default=True),
    max_process: int = Query(default=100, ge=0, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    try:
        stats = run_copart_csv_ingestion(load_copart_csv_config())
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    processed = 0
    processing_errors: list[str] = []
    if process_immediately and max_process > 0:
        for _ in range(max_process):
            try:
                job = pop_ingestion_job(timeout=1)
            except RedisError as exc:
                raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}") from exc
            if job is None:
                break
            try:
                apply_ingestion_job(db, job)
                processed += 1
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                processing_errors.append(str(exc)[:300])
                if len(processing_errors) >= 5:
                    break

    try:
        depth = queue_depth()
    except RedisError:
        depth = -1

    return {
        "source": "copart_csv",
        "downloaded_rows": stats.total_rows,
        "valid_rows": stats.valid_rows,
        "enqueued_rows": stats.enqueued_rows,
        "deduped_rows": stats.deduped_rows,
        "skipped_rows": stats.skipped_rows,
        "processed_rows": processed,
        "queue_depth": depth,
        "processing_errors": processing_errors,
        "started_at": stats.started_at.isoformat(),
        "finished_at": stats.finished_at.isoformat(),
    }


@router.post("/process-one", response_model=IngestionProcessResult, dependencies=[Depends(_require_admin)])
def process_one(db: Session = Depends(get_db)) -> IngestionProcessResult:
    try:
        job = pop_ingestion_job(timeout=1)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}") from exc

    if job is None:
        return IngestionProcessResult(processed=False, message="No jobs in queue")

    return apply_ingestion_job(db, job)
