from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.sql.elements import ColumnElement


CONFIRMED_SALE_KEYWORDS = ("sold", "closed", "paid", "won")


def is_confirmed_sale_status(status: str | None) -> bool:
    normalized = (status or "").strip().lower()
    return any(keyword in normalized for keyword in CONFIRMED_SALE_KEYWORDS)


def confirmed_sale_status_clause(status_column: ColumnElement[str | None]) -> ColumnElement[bool]:
    normalized = func.lower(func.coalesce(status_column, ""))
    return or_(*(normalized.like(f"%{keyword}%") for keyword in CONFIRMED_SALE_KEYWORDS))
