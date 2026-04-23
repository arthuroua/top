from __future__ import annotations

import os


def hide_data_source() -> bool:
    raw = os.getenv("HIDE_DATA_SOURCE", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def public_source_label() -> str:
    value = os.getenv("PUBLIC_SOURCE_LABEL", "market").strip()
    return value[:16] if value else "market"
