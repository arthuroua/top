from app.db import SessionLocal, init_db
from app.services.ingestion_queue import pop_enrichment_job
from app.services.lot_enrichment import enrich_lot_images


def run_worker(poll_timeout: int = 5) -> None:
    init_db()
    print("[enrichment-worker] started")

    while True:
        job = pop_enrichment_job(timeout=poll_timeout)
        if job is None:
            continue

        db = SessionLocal()
        try:
            result = enrich_lot_images(
                db,
                source=str(job.get("source") or "copart"),
                lot_number=str(job.get("lot_number") or ""),
                vin=str(job.get("vin")) if job.get("vin") else None,
            )
            print(
                f"[enrichment-worker] processed source={result.get('source')} "
                f"lot={result.get('lot_number')} vin={result.get('vin')} "
                f"images_added={result.get('images_added')} message={result.get('message')}"
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            print(f"[enrichment-worker] processing error: {exc}")
        finally:
            db.close()


if __name__ == "__main__":
    run_worker()
