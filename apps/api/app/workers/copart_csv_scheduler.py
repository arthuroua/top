from __future__ import annotations

import os
import time
from datetime import datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.copart_csv import load_copart_csv_config, run_copart_csv_ingestion


def _parse_schedule_times(raw: str) -> list[dtime]:
    tokens = [token.strip() for token in raw.split(",") if token.strip()]
    parsed: list[dtime] = []
    for token in tokens:
        try:
            hour_str, minute_str = token.split(":", 1)
            hour = int(hour_str)
            minute = int(minute_str)
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                continue
            parsed.append(dtime(hour=hour, minute=minute))
        except ValueError:
            continue
    if not parsed:
        parsed = [dtime(hour=9, minute=17), dtime(hour=21, minute=43)]
    parsed.sort()
    return parsed


def _scheduler_timezone() -> ZoneInfo:
    tz_name = os.getenv("COPART_CSV_TIMEZONE", "Europe/Kiev").strip() or "Europe/Kiev"
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        print(f"[copart-csv-scheduler] timezone '{tz_name}' not found, fallback to UTC")
        return ZoneInfo("UTC")


def _next_run_after(now_local: datetime, schedule: list[dtime]) -> datetime:
    for item in schedule:
        candidate = now_local.replace(hour=item.hour, minute=item.minute, second=0, microsecond=0)
        if candidate > now_local:
            return candidate
    tomorrow = now_local + timedelta(days=1)
    first = schedule[0]
    return tomorrow.replace(hour=first.hour, minute=first.minute, second=0, microsecond=0)


def _run_once() -> None:
    config = load_copart_csv_config()
    if not config.enabled:
        print("[copart-csv-scheduler] disabled via COPART_CSV_ENABLED=false")
        return

    try:
        stats = run_copart_csv_ingestion(config)
        duration = (stats.finished_at - stats.started_at).total_seconds()
        print(
            "[copart-csv-scheduler] done "
            f"rows={stats.total_rows} valid={stats.valid_rows} enqueued={stats.enqueued_rows} "
            f"deduped={stats.deduped_rows} skipped={stats.skipped_rows} duration_sec={duration:.1f}"
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[copart-csv-scheduler] error: {exc}")


def run_scheduler() -> None:
    schedule_raw = os.getenv("COPART_CSV_SCHEDULE_TIMES", "09:17,21:43")
    run_on_start = os.getenv("COPART_CSV_RUN_ON_START", "false").strip().lower() in {"1", "true", "yes", "on"}

    schedule = _parse_schedule_times(schedule_raw)
    timezone_local = _scheduler_timezone()
    print(
        "[copart-csv-scheduler] started "
        f"times={[item.strftime('%H:%M') for item in schedule]} timezone={timezone_local.key}"
    )

    if run_on_start:
        print("[copart-csv-scheduler] run on start")
        _run_once()

    while True:
        now_local = datetime.now(timezone.utc).astimezone(timezone_local)
        next_local = _next_run_after(now_local, schedule)
        wait_seconds = max(1, int((next_local - now_local).total_seconds()))
        print(
            "[copart-csv-scheduler] next run "
            f"{next_local.strftime('%Y-%m-%d %H:%M:%S %Z')} (in {wait_seconds}s)"
        )
        time.sleep(wait_seconds)
        _run_once()


if __name__ == "__main__":
    run_scheduler()
