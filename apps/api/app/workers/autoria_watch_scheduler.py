from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone

from app.db import SessionLocal
from app.services.autoria_market import run_all_market_watches


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


def _sleep_seconds() -> int:
    min_seconds = _env_int("AUTORIA_SCHEDULER_INTERVAL_MIN_SECONDS", 21_600, minimum=60)
    max_seconds = _env_int("AUTORIA_SCHEDULER_INTERVAL_MAX_SECONDS", 32_400, minimum=min_seconds)
    return random.randint(min_seconds, max_seconds)


def run_once() -> None:
    max_watches_raw = os.getenv("AUTORIA_SCHEDULER_MAX_WATCHES_PER_RUN", "").strip()
    max_watches = int(max_watches_raw) if max_watches_raw.isdigit() else None
    max_pages = _env_int("AUTORIA_SCHEDULER_MAX_PAGES_PER_WATCH", 1, minimum=1, maximum=100)
    sleep_min = _env_int("AUTORIA_SCHEDULER_WATCH_SLEEP_MIN_SECONDS", 45, minimum=0, maximum=3600)
    sleep_max = _env_int("AUTORIA_SCHEDULER_WATCH_SLEEP_MAX_SECONDS", 180, minimum=sleep_min, maximum=3600)

    db = SessionLocal()
    try:
        result = run_all_market_watches(
            db,
            max_watches=max_watches,
            max_pages=max_pages,
            sleep_min_seconds=sleep_min,
            sleep_max_seconds=sleep_max,
        )
        print(
            "[autoria-watch-scheduler]",
            datetime.now(timezone.utc).isoformat(),
            f"attempted={result.attempted}",
            f"succeeded={result.succeeded}",
            f"failed={result.failed}",
            flush=True,
        )
        for item in result.items:
            if item.success and item.result:
                print(
                    "[autoria-watch-scheduler]",
                    item.slug,
                    f"active={item.result.active_ids_seen}",
                    f"upserted={item.result.listings_upserted}",
                    f"changed={item.result.sold_or_removed_detected}",
                    flush=True,
                )
            else:
                print("[autoria-watch-scheduler]", item.slug, f"error={item.error}", flush=True)
    finally:
        db.close()


def main() -> None:
    if not _env_bool("AUTORIA_SCHEDULER_ENABLED", True):
        print("[autoria-watch-scheduler] disabled by AUTORIA_SCHEDULER_ENABLED", flush=True)
        return

    run_on_start = _env_bool("AUTORIA_SCHEDULER_RUN_ON_START", True)
    if run_on_start:
        run_once()

    while True:
        delay = _sleep_seconds()
        print(f"[autoria-watch-scheduler] sleeping {delay} seconds", flush=True)
        time.sleep(delay)
        run_once()


if __name__ == "__main__":
    main()
