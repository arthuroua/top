"""initial schema

Revision ID: 20260422_000001
Revises: None
Create Date: 2026-04-22 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260422_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "advisor_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("vin", sa.String(length=17), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_advisor_reports_vin"), "advisor_reports", ["vin"], unique=False)

    op.create_table(
        "ingestion_connector_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("selector_json", sa.JSON(), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=128), nullable=True),
        sa.Column("response_hash", sa.String(length=64), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("enqueued", sa.Boolean(), nullable=False),
        sa.Column("queue_depth", sa.Integer(), nullable=True),
        sa.Column("job_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingestion_connector_runs_created_at"), "ingestion_connector_runs", ["created_at"], unique=False)
    op.create_index(op.f("ix_ingestion_connector_runs_mode"), "ingestion_connector_runs", ["mode"], unique=False)
    op.create_index(op.f("ix_ingestion_connector_runs_provider"), "ingestion_connector_runs", ["provider"], unique=False)
    op.create_index(op.f("ix_ingestion_connector_runs_request_hash"), "ingestion_connector_runs", ["request_hash"], unique=False)
    op.create_index(op.f("ix_ingestion_connector_runs_success"), "ingestion_connector_runs", ["success"], unique=False)

    op.create_table(
        "seo_pages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("page_type", sa.String(length=16), nullable=False),
        sa.Column("slug_path", sa.String(length=255), nullable=False),
        sa.Column("make", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("teaser", sa.String(length=512), nullable=False),
        sa.Column("body", sa.String(length=4000), nullable=True),
        sa.Column("faq_json", sa.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug_path", name="uq_seo_page_slug_path"),
    )
    op.create_index(op.f("ix_seo_pages_deleted_at"), "seo_pages", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_seo_pages_is_active"), "seo_pages", ["is_active"], unique=False)
    op.create_index(op.f("ix_seo_pages_page_type"), "seo_pages", ["page_type"], unique=False)
    op.create_index(op.f("ix_seo_pages_slug_path"), "seo_pages", ["slug_path"], unique=False)
    op.create_index(op.f("ix_seo_pages_sort_order"), "seo_pages", ["sort_order"], unique=False)

    op.create_table(
        "vehicles",
        sa.Column("vin", sa.String(length=17), nullable=False),
        sa.Column("make", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("title_brand", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("vin"),
    )

    op.create_table(
        "advisor_report_shares",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.String(length=36), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["report_id"], ["advisor_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_advisor_report_shares_report_id"), "advisor_report_shares", ["report_id"], unique=False)
    op.create_index(op.f("ix_advisor_report_shares_token"), "advisor_report_shares", ["token"], unique=True)

    op.create_table(
        "lots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("lot_number", sa.String(length=32), nullable=False),
        sa.Column("vin", sa.String(length=17), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=True),
        sa.Column("hammer_price_usd", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("location", sa.String(length=128), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["vin"], ["vehicles.vin"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "lot_number", name="uq_lot_source_number"),
    )
    op.create_index(op.f("ix_lots_lot_number"), "lots", ["lot_number"], unique=False)
    op.create_index(op.f("ix_lots_source"), "lots", ["source"], unique=False)
    op.create_index(op.f("ix_lots_vin"), "lots", ["vin"], unique=False)

    op.create_table(
        "report_pipeline_states",
        sa.Column("report_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("note", sa.String(length=512), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["advisor_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("report_id"),
    )
    op.create_index(op.f("ix_report_pipeline_states_stage"), "report_pipeline_states", ["stage"], unique=False)

    op.create_table(
        "lot_images",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lot_id", sa.String(length=36), nullable=False),
        sa.Column("image_url", sa.String(length=512), nullable=False),
        sa.Column("shot_order", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lot_id", "image_url", name="uq_lot_image"),
    )
    op.create_index(op.f("ix_lot_images_lot_id"), "lot_images", ["lot_id"], unique=False)

    op.create_table(
        "lot_import_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lot_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("lot_number", sa.String(length=32), nullable=False),
        sa.Column("vin", sa.String(length=17), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=True),
        sa.Column("hammer_price_usd", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("location", sa.String(length=128), nullable=True),
        sa.Column("images_json", sa.JSON(), nullable=False),
        sa.Column("price_events_json", sa.JSON(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lot_import_snapshots_imported_at"), "lot_import_snapshots", ["imported_at"], unique=False)
    op.create_index(op.f("ix_lot_import_snapshots_lot_id"), "lot_import_snapshots", ["lot_id"], unique=False)
    op.create_index(op.f("ix_lot_import_snapshots_lot_number"), "lot_import_snapshots", ["lot_number"], unique=False)
    op.create_index(op.f("ix_lot_import_snapshots_source"), "lot_import_snapshots", ["source"], unique=False)
    op.create_index(op.f("ix_lot_import_snapshots_vin"), "lot_import_snapshots", ["vin"], unique=False)

    op.create_table(
        "price_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lot_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("old_value", sa.String(length=128), nullable=True),
        sa.Column("new_value", sa.String(length=128), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lot_id", "event_type", "event_time", "new_value", name="uq_lot_price_event"),
    )
    op.create_index(op.f("ix_price_events_event_time"), "price_events", ["event_time"], unique=False)
    op.create_index(op.f("ix_price_events_event_type"), "price_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_price_events_lot_id"), "price_events", ["lot_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_price_events_lot_id"), table_name="price_events")
    op.drop_index(op.f("ix_price_events_event_type"), table_name="price_events")
    op.drop_index(op.f("ix_price_events_event_time"), table_name="price_events")
    op.drop_table("price_events")

    op.drop_index(op.f("ix_lot_import_snapshots_vin"), table_name="lot_import_snapshots")
    op.drop_index(op.f("ix_lot_import_snapshots_source"), table_name="lot_import_snapshots")
    op.drop_index(op.f("ix_lot_import_snapshots_lot_number"), table_name="lot_import_snapshots")
    op.drop_index(op.f("ix_lot_import_snapshots_lot_id"), table_name="lot_import_snapshots")
    op.drop_index(op.f("ix_lot_import_snapshots_imported_at"), table_name="lot_import_snapshots")
    op.drop_table("lot_import_snapshots")

    op.drop_index(op.f("ix_lot_images_lot_id"), table_name="lot_images")
    op.drop_table("lot_images")

    op.drop_index(op.f("ix_report_pipeline_states_stage"), table_name="report_pipeline_states")
    op.drop_table("report_pipeline_states")

    op.drop_index(op.f("ix_lots_vin"), table_name="lots")
    op.drop_index(op.f("ix_lots_source"), table_name="lots")
    op.drop_index(op.f("ix_lots_lot_number"), table_name="lots")
    op.drop_table("lots")

    op.drop_index(op.f("ix_advisor_report_shares_token"), table_name="advisor_report_shares")
    op.drop_index(op.f("ix_advisor_report_shares_report_id"), table_name="advisor_report_shares")
    op.drop_table("advisor_report_shares")

    op.drop_table("vehicles")

    op.drop_index(op.f("ix_seo_pages_sort_order"), table_name="seo_pages")
    op.drop_index(op.f("ix_seo_pages_slug_path"), table_name="seo_pages")
    op.drop_index(op.f("ix_seo_pages_page_type"), table_name="seo_pages")
    op.drop_index(op.f("ix_seo_pages_is_active"), table_name="seo_pages")
    op.drop_index(op.f("ix_seo_pages_deleted_at"), table_name="seo_pages")
    op.drop_table("seo_pages")

    op.drop_index(op.f("ix_ingestion_connector_runs_success"), table_name="ingestion_connector_runs")
    op.drop_index(op.f("ix_ingestion_connector_runs_request_hash"), table_name="ingestion_connector_runs")
    op.drop_index(op.f("ix_ingestion_connector_runs_provider"), table_name="ingestion_connector_runs")
    op.drop_index(op.f("ix_ingestion_connector_runs_mode"), table_name="ingestion_connector_runs")
    op.drop_index(op.f("ix_ingestion_connector_runs_created_at"), table_name="ingestion_connector_runs")
    op.drop_table("ingestion_connector_runs")

    op.drop_index(op.f("ix_advisor_reports_vin"), table_name="advisor_reports")
    op.drop_table("advisor_reports")
