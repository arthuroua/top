from __future__ import annotations

from app.models import Lot, LotImportSnapshot


def latest_import_snapshot(lot: Lot) -> LotImportSnapshot | None:
    return max(lot.import_snapshots, key=lambda item: item.imported_at, default=None)


def latest_import_payload(lot: Lot) -> dict:
    snapshot = latest_import_snapshot(lot)
    return snapshot.payload_json if snapshot and snapshot.payload_json else {}


def is_public_real_lot(lot: Lot) -> bool:
    payload = latest_import_payload(lot)
    attributes = payload.get("attributes") or {}
    connector_mode = str(attributes.get("connector_mode") or "").strip().lower()
    source_url = str(payload.get("source_url") or "").strip().lower()

    if connector_mode == "mock":
        return False
    if "example.invalid" in source_url or "cdn.example.com" in source_url:
        return False
    return True
