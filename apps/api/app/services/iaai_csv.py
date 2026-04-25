import csv
import io
import re
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.ingestion import apply_ingestion_job
from app.schemas import IngestionJobPayload, IngestionPriceEvent


SENSITIVE_FIELDS = {
    "Pickup PIN",
    "Bidder",
    "PaymentReferenceHeader",
    "Payment Reference",
    "ReceiptNo",
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\ufeff", "").strip().strip('"').strip()


def _pick(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = _clean(row.get(name))
        if value:
            return value
    return ""


def _parse_money(value: str) -> int | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    normalized = re.sub(r"[^0-9.\-]", "", cleaned)
    if normalized in {"", "-", "."}:
        return None
    try:
        return int(Decimal(normalized).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: str) -> date | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    for pattern in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(cleaned, pattern).date()
        except ValueError:
            continue
    return None


def _event_time(sale_date: date | None) -> datetime:
    if sale_date is None:
        return datetime.now(timezone.utc)
    return datetime.combine(sale_date, time.min, tzinfo=timezone.utc)


def _parse_description(description: str, series: str = "") -> tuple[int | None, str | None, str | None, str | None]:
    text = " ".join(_clean(description).split())
    if not text:
        return None, None, None, _clean(series) or None

    parts = text.split()
    year = None
    year_index = -1
    for idx, part in enumerate(parts):
        if re.fullmatch(r"\d{4}", part):
            candidate = int(part)
            if 1900 <= candidate <= 2100:
                year = candidate
                year_index = idx
                break

    if year_index < 0 or year_index + 1 >= len(parts):
        return year, None, None, _clean(series) or None

    make = parts[year_index + 1]
    model_parts = parts[year_index + 2 :]
    trim = _clean(series) or None
    if trim and model_parts:
        trim_parts = trim.upper().split()
        while model_parts and trim_parts and model_parts[-1].upper() == trim_parts[-1]:
            model_parts.pop()
            trim_parts.pop()
    model = " ".join(model_parts).strip() or None
    return year, make[:64] or None, model[:64] if model else None, trim[:128] if trim else None


def _detect_type(fieldnames: list[str]) -> str:
    fields = set(fieldnames)
    if {"StockNumber", "DateWon", "TotalPaid"}.issubset(fields):
        return "purchase_history"
    if {"Stock#", "Date Won", "Balance Due"}.issubset(fields):
        return "won_to_be_paid"
    return "unknown"


def _decode_csv(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _public_attributes(row: dict[str, str], csv_type: str) -> dict[str, str | int | float | bool | None]:
    attributes: dict[str, str | int | float | bool | None] = {"iaai_csv_type": csv_type}
    keep_text_fields = [
        "Description",
        "Series",
        "Color",
        "BidType",
        "Bid Type",
        "Branch",
        "Selling Branch",
        "Lane",
        "ItemNumber",
        "Item#",
        "DatePaid",
        "DatePickedUp",
        "Payment Due",
        "Pick up By",
    ]
    keep_money_fields = [
        "BidAmount",
        "Bid Amount",
        "FeesAndTax",
        "TotalPaid",
        "Buyer Fee",
        "Internet Fee",
        "Premium Vehicle Report Fee",
        "Fedex Fee",
        "Title Handling Fee",
        "Late Fee",
        "Yard Fee",
        "Service Fee",
        "Storage Fee",
        "Tow Fee",
        "Document Fee",
        "Renege Fee",
        "Title Processing Fee",
        "Key Fee",
        "Financing Fee",
        "Buyer DMV Fee",
        "Miscellaneous Fee",
        "Other Fees",
        "Transaction Tax",
        "Sales Tax",
        "IAA Transport Fee",
        "IAA Transport - Dry Run Fee",
        "IAA Transport - Miscellaneous Fee",
        "Total",
        "Partially Paid",
        "Balance Due",
        "VAT",
        "Environmental Fee",
    ]

    for field in keep_text_fields:
        if field in SENSITIVE_FIELDS:
            continue
        value = _clean(row.get(field))
        if value:
            attributes[_attribute_key(field)] = value[:256]

    for field in keep_money_fields:
        value = _parse_money(row.get(field, ""))
        if value is not None:
            attributes[f"{_attribute_key(field)}_usd"] = value

    return attributes


def _attribute_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _build_job(row: dict[str, str], csv_type: str) -> IngestionJobPayload | None:
    stock = _pick(row, "StockNumber", "Stock#")
    vin = _pick(row, "VIN").upper()
    if not stock or len(vin) != 17:
        return None

    description = _pick(row, "Description")
    series = _pick(row, "Series")
    year, make, model, trim = _parse_description(description, series)
    sale_date = _parse_date(_pick(row, "DateWon", "Date Won"))
    bid_amount = _parse_money(_pick(row, "BidAmount", "Bid Amount"))
    total_paid = _parse_money(_pick(row, "TotalPaid", "Total"))
    fees_and_tax = _parse_money(_pick(row, "FeesAndTax"))
    branch = _pick(row, "Branch", "Selling Branch")
    bid_type = _pick(row, "BidType", "Bid Type")
    date_paid = _pick(row, "DatePaid")
    status = "Paid" if date_paid else ("Won / To Be Paid" if csv_type == "won_to_be_paid" else "Won")

    events: list[IngestionPriceEvent] = []
    event_at = _event_time(sale_date)
    if bid_amount is not None:
        events.append(IngestionPriceEvent(event_type="iaai_bid_amount", new_value=str(bid_amount), event_time=event_at))
    if total_paid is not None:
        events.append(IngestionPriceEvent(event_type="iaai_total_paid", new_value=str(total_paid), event_time=event_at))
    if fees_and_tax is not None:
        events.append(IngestionPriceEvent(event_type="iaai_fees_and_tax", new_value=str(fees_and_tax), event_time=event_at))

    return IngestionJobPayload(
        provider="iaai",
        source="iaai",
        vin=vin,
        lot_number=stock,
        source_record_id=f"iaai:{stock}",
        source_url=f"https://www.iaai.com/Search?Keyword={stock}",
        sale_date=sale_date,
        hammer_price_usd=bid_amount,
        status=status,
        location=branch[:128] if branch else None,
        make=make,
        model=model,
        year=year,
        trim=trim,
        series=series[:128] if series else None,
        exterior_color=_pick(row, "Color")[:64] or None,
        images=[],
        price_events=events,
        attributes={
            **_public_attributes(row, csv_type),
            "iaai_stock_number": stock,
            "iaai_bid_type": bid_type[:128] if bid_type else None,
            "iaai_total_paid_usd": total_paid,
        },
    )


def import_iaai_csv(db: Session, content: bytes, filename: str) -> dict[str, Any]:
    text = _decode_csv(content)
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = [field or "" for field in (reader.fieldnames or [])]
    csv_type = _detect_type(fieldnames)
    if csv_type == "unknown":
        return {
            "filename": filename,
            "csv_type": csv_type,
            "rows_total": 0,
            "imported": 0,
            "skipped": 0,
            "errors": ["Unsupported IAA CSV format"],
        }

    rows_total = 0
    imported = 0
    skipped = 0
    errors: list[str] = []

    for row_number, row in enumerate(reader, start=2):
        rows_total += 1
        job = _build_job(row, csv_type)
        if job is None:
            skipped += 1
            errors.append(f"Row {row_number}: missing Stock/StockNumber or valid VIN")
            continue
        try:
            apply_ingestion_job(db, job)
            imported += 1
        except Exception as exc:  # pragma: no cover - keep import resilient for admin uploads.
            db.rollback()
            skipped += 1
            errors.append(f"Row {row_number} stock {job.lot_number}: {exc}")

    return {
        "filename": filename,
        "csv_type": csv_type,
        "rows_total": rows_total,
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:25],
    }
