from datetime import datetime

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
