"""add market watches

Revision ID: 20260425_000005
Revises: 20260425_000004
Create Date: 2026-04-25 00:00:05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260425_000005"
down_revision = "20260425_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "market_watches" in set(inspect(bind).get_table_names()):
        return

    op.create_table(
        "market_watches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("search_text", sa.String(length=255), nullable=False),
        sa.Column("search_params", sa.String(length=4000), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_ids_seen", sa.Integer(), nullable=False),
        sa.Column("last_listings_upserted", sa.Integer(), nullable=False),
        sa.Column("last_sold_or_removed_detected", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_market_watch_slug"),
    )
    op.create_index(op.f("ix_market_watches_provider"), "market_watches", ["provider"], unique=False)
    op.create_index(op.f("ix_market_watches_slug"), "market_watches", ["slug"], unique=False)
    op.create_index(op.f("ix_market_watches_query_hash"), "market_watches", ["query_hash"], unique=False)
    op.create_index(op.f("ix_market_watches_is_active"), "market_watches", ["is_active"], unique=False)
    op.create_index(op.f("ix_market_watches_last_run_at"), "market_watches", ["last_run_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if "market_watches" in set(inspect(bind).get_table_names()):
        op.drop_table("market_watches")
