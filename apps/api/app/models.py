import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    vin: Mapped[str] = mapped_column(String(17), primary_key=True)
    make: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title_brand: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lots: Mapped[list["Lot"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")


class Lot(Base):
    __tablename__ = "lots"
    __table_args__ = (UniqueConstraint("source", "lot_number", name="uq_lot_source_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(16), index=True)
    lot_number: Mapped[str] = mapped_column(String(32), index=True)
    vin: Mapped[str] = mapped_column(String(17), ForeignKey("vehicles.vin", ondelete="CASCADE"), index=True)
    sale_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    hammer_price_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vehicle: Mapped[Vehicle] = relationship(back_populates="lots")
    images: Mapped[list["LotImage"]] = relationship(back_populates="lot", cascade="all, delete-orphan")
    price_events: Mapped[list["PriceEvent"]] = relationship(back_populates="lot", cascade="all, delete-orphan")
    import_snapshots: Mapped[list["LotImportSnapshot"]] = relationship(
        back_populates="lot",
        cascade="all, delete-orphan",
    )


class LotImage(Base):
    __tablename__ = "lot_images"
    __table_args__ = (UniqueConstraint("lot_id", "image_url", name="uq_lot_image"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lot_id: Mapped[str] = mapped_column(String(36), ForeignKey("lots.id", ondelete="CASCADE"), index=True)
    image_url: Mapped[str] = mapped_column(String(512))
    shot_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lot: Mapped[Lot] = relationship(back_populates="images")


class PriceEvent(Base):
    __tablename__ = "price_events"
    __table_args__ = (
        UniqueConstraint("lot_id", "event_type", "event_time", "new_value", name="uq_lot_price_event"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lot_id: Mapped[str] = mapped_column(String(36), ForeignKey("lots.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    old_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    new_value: Mapped[str] = mapped_column(String(128))
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lot: Mapped[Lot] = relationship(back_populates="price_events")


class LotImportSnapshot(Base):
    __tablename__ = "lot_import_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lot_id: Mapped[str] = mapped_column(String(36), ForeignKey("lots.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    lot_number: Mapped[str] = mapped_column(String(32), index=True)
    vin: Mapped[str] = mapped_column(String(17), index=True)
    sale_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    hammer_price_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    images_json: Mapped[list[str]] = mapped_column(JSON)
    price_events_json: Mapped[list[dict]] = mapped_column(JSON)
    payload_json: Mapped[dict] = mapped_column(JSON)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    lot: Mapped[Lot] = relationship(back_populates="import_snapshots")


class AdvisorReport(Base):
    __tablename__ = "advisor_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vin: Mapped[str] = mapped_column(String(17), index=True)
    assumptions_json: Mapped[dict] = mapped_column(JSON)
    result_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    shares: Mapped[list["AdvisorReportShare"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
    )
    pipeline_state: Mapped["ReportPipelineState | None"] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        uselist=False,
    )


class AdvisorReportShare(Base):
    __tablename__ = "advisor_report_shares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("advisor_reports.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    report: Mapped[AdvisorReport] = relationship(back_populates="shares")


class ReportPipelineState(Base):
    __tablename__ = "report_pipeline_states"

    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("advisor_reports.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stage: Mapped[str] = mapped_column(String(32), index=True, default="lead")
    note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    report: Mapped[AdvisorReport] = relationship(back_populates="pipeline_state")


class IngestionConnectorRun(Base):
    __tablename__ = "ingestion_connector_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(16), index=True)
    mode: Mapped[str] = mapped_column(String(16), index=True)
    selector_json: Mapped[dict] = mapped_column(JSON)
    request_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_record_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    response_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, index=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer)
    enqueued: Mapped[bool] = mapped_column(Boolean, default=False)
    queue_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class LocalMarketListing(Base):
    __tablename__ = "local_market_listings"
    __table_args__ = (
        UniqueConstraint("provider", "listing_id", name="uq_local_market_provider_listing"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(32), index=True)
    listing_id: Mapped[str] = mapped_column(String(64), index=True)
    query_label: Mapped[str] = mapped_column(String(128), index=True, default="default")
    query_hash: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    make: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    price_usd: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    price_uah: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mileage_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuel_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gearbox_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    image_urls_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, index=True, default=True)
    is_sold: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    removal_status: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    sold_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MarketWatch(Base):
    __tablename__ = "market_watches"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_market_watch_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(32), index=True, default="autoria")
    slug: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(160))
    search_text: Mapped[str] = mapped_column(String(255))
    search_params: Mapped[str] = mapped_column(String(4000))
    query_hash: Mapped[str] = mapped_column(String(64), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_active_ids_seen: Mapped[int] = mapped_column(Integer, default=0)
    last_listings_upserted: Mapped[int] = mapped_column(Integer, default=0)
    last_sold_or_removed_detected: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SeoPage(Base):
    __tablename__ = "seo_pages"
    __table_args__ = (UniqueConstraint("slug_path", name="uq_seo_page_slug_path"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    page_type: Mapped[str] = mapped_column(String(16), index=True)
    slug_path: Mapped[str] = mapped_column(String(255), index=True)
    make: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    teaser: Mapped[str] = mapped_column(String(512))
    body: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    faq_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    teaser_en: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_en: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    faq_json_en: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    title_uk: Mapped[str | None] = mapped_column(String(255), nullable=True)
    teaser_uk: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_uk: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    faq_json_uk: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    title_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    teaser_ru: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_ru: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    faq_json_ru: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
