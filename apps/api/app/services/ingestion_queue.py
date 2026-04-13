import os

import redis

from app.schemas import IngestionJobPayload

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
INGESTION_QUEUE_KEY = os.getenv("INGESTION_QUEUE_KEY", "ingestion:jobs")


def _client() -> redis.Redis:
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def enqueue_ingestion_job(job: IngestionJobPayload) -> int:
    client = _client()
    client.lpush(INGESTION_QUEUE_KEY, job.model_dump_json())
    return int(client.llen(INGESTION_QUEUE_KEY))


def pop_ingestion_job(timeout: int = 1) -> IngestionJobPayload | None:
    client = _client()
    item = client.brpop(INGESTION_QUEUE_KEY, timeout=timeout)
    if item is None:
        return None

    _, raw_payload = item
    return IngestionJobPayload.model_validate_json(raw_payload)


def queue_depth() -> int:
    client = _client()
    return int(client.llen(INGESTION_QUEUE_KEY))
