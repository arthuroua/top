"""add local market listings

Revision ID: 20260425_000003
Revises: 20260423_000002
Create Date: 2026-04-25 00:00:03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260425_000003"
down_revision = "20260423_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())
    if "local_market_listings" in existing_tables:
        return

    op.create_table(
        "local_market_listings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("listing_id", sa.String(length=64), nullable=False),
        sa.Column("query_label", sa.String(length=128), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("make", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("price_usd", sa.Integer(), nullable=True),
        sa.Column("price_uah", sa.Integer(), nullable=True),
        sa.Column("price_eur", sa.Integer(), nullable=True),
        sa.Column("mileage_km", sa.Integer(), nullable=True),
        sa.Column("fuel_name", sa.String(length=64), nullable=True),
        sa.Column("gearbox_name", sa.String(length=64), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("photo_url", sa.String(length=1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_sold", sa.Boolean(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("sold_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "listing_id", name="uq_local_market_provider_listing"),
    )
    op.create_index(op.f("ix_local_market_listings_provider"), "local_market_listings", ["provider"], unique=False)
    op.create_index(op.f("ix_local_market_listings_listing_id"), "local_market_listings", ["listing_id"], unique=False)
    op.create_index(op.f("ix_local_market_listings_query_label"), "local_market_listings", ["query_label"], unique=False)
    op.create_index(op.f("ix_local_market_listings_query_hash"), "local_market_listings", ["query_hash"], unique=False)
    op.create_index(op.f("ix_local_market_listings_make"), "local_market_listings", ["make"], unique=False)
    op.create_index(op.f("ix_local_market_listings_model"), "local_market_listings", ["model"], unique=False)
    op.create_index(op.f("ix_local_market_listings_year"), "local_market_listings", ["year"], unique=False)
    op.create_index(op.f("ix_local_market_listings_price_usd"), "local_market_listings", ["price_usd"], unique=False)
    op.create_index(op.f("ix_local_market_listings_is_active"), "local_market_listings", ["is_active"], unique=False)
    op.create_index(op.f("ix_local_market_listings_is_sold"), "local_market_listings", ["is_sold"], unique=False)
    op.create_index(op.f("ix_local_market_listings_first_seen_at"), "local_market_listings", ["first_seen_at"], unique=False)
    op.create_index(op.f("ix_local_market_listings_last_seen_at"), "local_market_listings", ["last_seen_at"], unique=False)
    op.create_index(op.f("ix_local_market_listings_sold_detected_at"), "local_market_listings", ["sold_detected_at"], unique=False)


def downgrade() -> None:
    op.drop_table("local_market_listings")
