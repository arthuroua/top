from __future__ import annotations

from sqlalchemy import and_, func, not_, or_
from sqlalchemy.sql.elements import ColumnElement


CONFIRMED_SALE_KEYWORDS = ("sold", "closed", "paid", "won / to be paid", "won")
EXCLUDED_SALE_KEYWORDS = ("on approval", "on minimum bid", "minimum bid", "pure sale")


def is_confirmed_sale_status(status: str | None) -> bool:
    normalized = (status or "").strip().lower()
    if any(keyword in normalized for keyword in EXCLUDED_SALE_KEYWORDS):
        return False
    return any(keyword in normalized for keyword in CONFIRMED_SALE_KEYWORDS)


def confirmed_sale_status_clause(status_column: ColumnElement[str | None]) -> ColumnElement[bool]:
    normalized = func.lower(func.coalesce(status_column, ""))
    return and_(
        or_(*(normalized.like(f"%{keyword}%") for keyword in CONFIRMED_SALE_KEYWORDS)),
        not_(or_(*(normalized.like(f"%{keyword}%") for keyword in EXCLUDED_SALE_KEYWORDS))),
    )
