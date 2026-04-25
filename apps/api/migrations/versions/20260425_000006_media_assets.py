"""add media assets

Revision ID: 20260425_000006
Revises: 20260425_000005
Create Date: 2026-04-25 00:00:06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260425_000006"
down_revision = "20260425_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "media_assets" in set(inspect(bind).get_table_names()):
        return

    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("owner_type", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("source_url_hash", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url_hash", name="uq_media_asset_source_url_hash"),
    )
    op.create_index(op.f("ix_media_assets_provider"), "media_assets", ["provider"], unique=False)
    op.create_index(op.f("ix_media_assets_owner_type"), "media_assets", ["owner_type"], unique=False)
    op.create_index(op.f("ix_media_assets_owner_id"), "media_assets", ["owner_id"], unique=False)
    op.create_index(op.f("ix_media_assets_source_url_hash"), "media_assets", ["source_url_hash"], unique=False)
    op.create_index(op.f("ix_media_assets_checksum"), "media_assets", ["checksum"], unique=False)
    op.create_index(op.f("ix_media_assets_is_archived"), "media_assets", ["is_archived"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if "media_assets" in set(inspect(bind).get_table_names()):
        op.drop_table("media_assets")
