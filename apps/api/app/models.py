import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
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


class AdvisorReport(Base):
    __tablename__ = "advisor_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vin: Mapped[str] = mapped_column(String(17), index=True)
    assumptions_json: Mapped[dict] = mapped_column(JSON)
    result_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
