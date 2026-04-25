"""add autoria status and images

Revision ID: 20260425_000004
Revises: 20260425_000003
Create Date: 2026-04-25 00:00:04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260425_000004"
down_revision = "20260425_000003"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    return any(column["name"] == column_name for column in inspect(bind).get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    if "local_market_listings" not in set(inspect(bind).get_table_names()):
        return

    if not _has_column("local_market_listings", "image_urls_json"):
        op.add_column(
            "local_market_listings",
            sa.Column("image_urls_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )
        op.alter_column("local_market_listings", "image_urls_json", server_default=None)

    if not _has_column("local_market_listings", "removal_status"):
        op.add_column("local_market_listings", sa.Column("removal_status", sa.String(length=16), nullable=True))
        op.create_index(
            op.f("ix_local_market_listings_removal_status"),
            "local_market_listings",
            ["removal_status"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "local_market_listings" not in set(inspect(bind).get_table_names()):
        return
    if _has_column("local_market_listings", "removal_status"):
        op.drop_index(op.f("ix_local_market_listings_removal_status"), table_name="local_market_listings")
        op.drop_column("local_market_listings", "removal_status")
    if _has_column("local_market_listings", "image_urls_json"):
        op.drop_column("local_market_listings", "image_urls_json")
