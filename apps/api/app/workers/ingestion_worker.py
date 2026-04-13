from app.db import SessionLocal, init_db
from app.repositories.ingestion import apply_ingestion_job
from app.services.ingestion_queue import pop_ingestion_job


def run_worker(poll_timeout: int = 5) -> None:
    init_db()
    print("[ingestion-worker] started")

    while True:
        job = pop_ingestion_job(timeout=poll_timeout)
        if job is None:
            continue

        db = SessionLocal()
        try:
            result = apply_ingestion_job(db, job)
            print(
                f"[ingestion-worker] processed source={result.source} lot={result.lot_number} "
                f"vin={result.vin} images={result.images_upserted} events={result.price_events_added}"
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            print(f"[ingestion-worker] processing error: {exc}")
        finally:
            db.close()


if __name__ == "__main__":
    run_worker()
