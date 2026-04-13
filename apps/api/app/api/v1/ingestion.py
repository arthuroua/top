from fastapi import APIRouter, Depends, HTTPException
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories.ingestion import apply_ingestion_job
from app.schemas import IngestionEnqueueResponse, IngestionJobPayload, IngestionProcessResult, IngestionQueueDepth
from app.services.ingestion_queue import enqueue_ingestion_job, pop_ingestion_job, queue_depth

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


@router.post("/jobs", response_model=IngestionEnqueueResponse)
def enqueue_job(payload: IngestionJobPayload) -> IngestionEnqueueResponse:
    try:
        depth = enqueue_ingestion_job(payload)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}") from exc

    return IngestionEnqueueResponse(accepted=True, queue_depth=depth)


@router.get("/queue-depth", response_model=IngestionQueueDepth)
def get_queue_depth() -> IngestionQueueDepth:
    try:
        depth = queue_depth()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}") from exc

    return IngestionQueueDepth(queue_depth=depth)


@router.post("/process-one", response_model=IngestionProcessResult)
def process_one(db: Session = Depends(get_db)) -> IngestionProcessResult:
    try:
        job = pop_ingestion_job(timeout=1)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}") from exc

    if job is None:
        return IngestionProcessResult(processed=False, message="No jobs in queue")

    return apply_ingestion_job(db, job)
