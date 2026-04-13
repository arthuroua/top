from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SearchResult(BaseModel):
    vin: str
    lots_found: int
    latest_status: str


class LotItem(BaseModel):
    source: str
    lot_number: str
    sale_date: str
    hammer_price_usd: int
    status: str
    location: str


class VehicleCard(BaseModel):
    vin: str
    make: str
    model: str
    year: int
    title_brand: str
    lots: list[LotItem]


class AdvisorInput(BaseModel):
    target_sell_price_usd: float = Field(gt=0)
    desired_margin_usd: float = Field(ge=0)
    fees_usd: float = Field(ge=0)
    logistics_usd: float = Field(ge=0)
    customs_usd: float = Field(ge=0)
    repair_usd: float = Field(ge=0)
    local_costs_usd: float = Field(ge=0)
    risk_buffer_usd: float = Field(ge=0)


class AdvisorScenario(BaseModel):
    name: str
    max_bid_usd: float


class AdvisorOutput(BaseModel):
    total_no_bid_usd: float
    max_bid_usd: float
    scenarios: list[AdvisorScenario]


class AdvisorReportCreate(BaseModel):
    vin: str = Field(min_length=17, max_length=17)
    assumptions: AdvisorInput
    result: AdvisorOutput


class AdvisorReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vin: str
    assumptions: AdvisorInput
    result: AdvisorOutput
    created_at: datetime


class IngestionPriceEvent(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    old_value: str | None = Field(default=None, max_length=128)
    new_value: str = Field(min_length=1, max_length=128)
    event_time: datetime


class IngestionJobPayload(BaseModel):
    source: str = Field(min_length=1, max_length=16)
    vin: str = Field(min_length=17, max_length=17)
    lot_number: str = Field(min_length=1, max_length=32)
    sale_date: date | None = None
    hammer_price_usd: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=128)
    images: list[str] = Field(default_factory=list)
    price_events: list[IngestionPriceEvent] = Field(default_factory=list)


class IngestionEnqueueResponse(BaseModel):
    accepted: bool
    queue_depth: int


class IngestionQueueDepth(BaseModel):
    queue_depth: int


class IngestionProcessResult(BaseModel):
    processed: bool
    message: str
    lot_id: str | None = None
    vin: str | None = None
    source: str | None = None
    lot_number: str | None = None
    images_upserted: int = 0
    price_events_added: int = 0
