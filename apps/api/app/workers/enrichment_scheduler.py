from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal, init_db
from app.models import Lot
from app.services.ingestion_queue import enqueue_enrichment_job, enrichment_queue_depth


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0, maximum: int | None = None) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        value = default
    else:
        try:
            value = int(raw)
        except ValueError:
            value = default
    value = max(minimum, value)
    return min(value, maximum) if maximum is not None else value


def _env_source(name: str, default: str = "all") -> str:
    value = (os.getenv(name, default) or default).strip().lower()
    return value if value in {"all", "copart", "iaai"} else default


def run_once() -> None:
    max_queue_depth = _env_int("ENRICHMENT_SCHEDULER_MAX_QUEUE_DEPTH", 2000, minimum=1, maximum=100_000)
    scan_limit = _env_int("ENRICHMENT_SCHEDULER_SCAN_LIMIT", 500, minimum=1, maximum=5000)
    enqueue_limit = _env_int("ENRICHMENT_SCHEDULER_ENQUEUE_LIMIT", 150, minimum=1, maximum=5000)
    max_existing_images = _env_int("ENRICHMENT_SCHEDULER_MAX_EXISTING_IMAGES", 0, minimum=0, maximum=10)
    source_filter = _env_source("ENRICHMENT_SCHEDULER_SOURCE", "all")

    current_depth = enrichment_queue_depth()
    if current_depth >= max_queue_depth:
        print(
            "[enrichment-scheduler]",
            datetime.now(timezone.utc).isoformat(),
            f"skip depth={current_depth} threshold={max_queue_depth}",
            flush=True,
        )
        return

    db = SessionLocal()
    try:
        query = (
            select(Lot)
            .options(selectinload(Lot.images))
            .order_by(Lot.fetched_at.desc())
            .limit(scan_limit)
        )
        if source_filter != "all":
            query = query.where(Lot.source == source_filter)

        lots = db.execute(query).scalars().all()

        enqueued = 0
        skipped_with_images = 0
        for lot in lots:
            if len(lot.images) > max_existing_images:
                skipped_with_images += 1
                continue
            enqueue_enrichment_job({"source": lot.source, "lot_number": lot.lot_number, "vin": lot.vin})
            enqueued += 1
            if enqueued >= enqueue_limit:
                break

        new_depth = enrichment_queue_depth()
        print(
            "[enrichment-scheduler]",
            datetime.now(timezone.utc).isoformat(),
            f"source={source_filter}",
            f"scanned={len(lots)}",
            f"enqueued={enqueued}",
            f"skipped_with_images={skipped_with_images}",
            f"queue_depth={new_depth}",
            flush=True,
        )
    finally:
        db.close()


def main() -> None:
    if not _env_bool("ENRICHMENT_SCHEDULER_ENABLED", True):
        print("[enrichment-scheduler] disabled by ENRICHMENT_SCHEDULER_ENABLED", flush=True)
        return

    init_db()
    interval_seconds = _env_int("ENRICHMENT_SCHEDULER_INTERVAL_SECONDS", 900, minimum=60, maximum=86400)
    run_on_start = _env_bool("ENRICHMENT_SCHEDULER_RUN_ON_START", True)

    if run_on_start:
        run_once()

    while True:
        print(f"[enrichment-scheduler] sleeping {interval_seconds} seconds", flush=True)
        time.sleep(interval_seconds)
        run_once()


if __name__ == "__main__":
    main()
