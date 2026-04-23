"""add localized seo fields

Revision ID: 20260423_000002
Revises: 20260422_000001
Create Date: 2026-04-23 00:00:02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260423_000002"
down_revision = "20260422_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in inspect(bind).get_columns("seo_pages")}

    def add_if_missing(name: str, column: sa.Column) -> None:
        if name not in existing_columns:
            op.add_column("seo_pages", column)

    add_if_missing("title_en", sa.Column("title_en", sa.String(length=255), nullable=True))
    add_if_missing("teaser_en", sa.Column("teaser_en", sa.String(length=512), nullable=True))
    add_if_missing("body_en", sa.Column("body_en", sa.String(length=4000), nullable=True))
    add_if_missing("faq_json_en", sa.Column("faq_json_en", sa.JSON(), nullable=True))
    add_if_missing("title_uk", sa.Column("title_uk", sa.String(length=255), nullable=True))
    add_if_missing("teaser_uk", sa.Column("teaser_uk", sa.String(length=512), nullable=True))
    add_if_missing("body_uk", sa.Column("body_uk", sa.String(length=4000), nullable=True))
    add_if_missing("faq_json_uk", sa.Column("faq_json_uk", sa.JSON(), nullable=True))
    add_if_missing("title_ru", sa.Column("title_ru", sa.String(length=255), nullable=True))
    add_if_missing("teaser_ru", sa.Column("teaser_ru", sa.String(length=512), nullable=True))
    add_if_missing("body_ru", sa.Column("body_ru", sa.String(length=4000), nullable=True))
    add_if_missing("faq_json_ru", sa.Column("faq_json_ru", sa.JSON(), nullable=True))

    op.execute("UPDATE seo_pages SET title_uk = title WHERE title_uk IS NULL")
    op.execute("UPDATE seo_pages SET teaser_uk = teaser WHERE teaser_uk IS NULL")
    op.execute("UPDATE seo_pages SET body_uk = body WHERE body_uk IS NULL")
    op.execute("UPDATE seo_pages SET faq_json_uk = faq_json WHERE faq_json_uk IS NULL")


def downgrade() -> None:
    op.drop_column("seo_pages", "faq_json_ru")
    op.drop_column("seo_pages", "body_ru")
    op.drop_column("seo_pages", "teaser_ru")
    op.drop_column("seo_pages", "title_ru")
    op.drop_column("seo_pages", "faq_json_uk")
    op.drop_column("seo_pages", "body_uk")
    op.drop_column("seo_pages", "teaser_uk")
    op.drop_column("seo_pages", "title_uk")
    op.drop_column("seo_pages", "faq_json_en")
    op.drop_column("seo_pages", "body_en")
    op.drop_column("seo_pages", "teaser_en")
    op.drop_column("seo_pages", "title_en")
