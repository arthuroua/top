from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SearchResult(BaseModel):
    vin: str
    lots_found: int
    latest_status: str


class SearchResolveResult(BaseModel):
    query: str
    normalized_query: str
    query_type: Literal["vin", "lot", "url"]
    matched_by: Literal["vin", "lot"]
    vin: str
    lots_found: int
    latest_status: str
    lot_number: str | None = None
    source: str | None = None


class LotImageItem(BaseModel):
    image_url: str
    shot_order: int | None = None
    checksum: str | None = None


class PriceEventItem(BaseModel):
    event_type: str
    old_value: str | None = None
    new_value: str
    event_time: str


class LotItem(BaseModel):
    source: str
    lot_number: str
    sale_date: str | None = None
    hammer_price_usd: int | None = None
    status: str | None = None
    location: str | None = None
    title_brand: str | None = None
    primary_damage: str | None = None
    secondary_damage: str | None = None
    odometer: int | None = None
    run_and_drive: bool | None = None
    keys_present: bool | None = None
    auction_specs: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    images: list[LotImageItem] = Field(default_factory=list)
    price_events: list[PriceEventItem] = Field(default_factory=list)


class VehicleCard(BaseModel):
    vin: str
    make: str | None = None
    model: str | None = None
    year: int | None = None
    title_brand: str | None = None
    lots: list[LotItem]


class RecentVehicleItem(BaseModel):
    vin: str
    make: str | None = None
    model: str | None = None
    year: int | None = None
    title_brand: str | None = None
    lot_number: str
    sale_date: str | None = None
    hammer_price_usd: int | None = None
    status: str | None = None
    location: str | None = None
    image_url: str | None = None
    updated_at: datetime


class RecentVehiclesResponse(BaseModel):
    items: list[RecentVehicleItem]


class VinDecodeItem(BaseModel):
    key: str
    label: str
    value: str


class VinDecodeSection(BaseModel):
    title: str
    items: list[VinDecodeItem] = Field(default_factory=list)


class VinDecodeResponse(BaseModel):
    vin: str
    source: str
    source_url: str
    note: str | None = None
    summary: list[VinDecodeItem] = Field(default_factory=list)
    sections: list[VinDecodeSection] = Field(default_factory=list)


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


class LandedCostInput(BaseModel):
    bid_price_usd: float = Field(gt=0)
    auction_provider: Literal["copart", "iaai", "other"] = "other"
    shipping_usd: float = Field(default=0, ge=0)
    inland_usd: float = Field(default=0, ge=0)
    port_usd: float = Field(default=0, ge=0)
    broker_usd: float = Field(default=0, ge=0)
    insurance_usd: float = Field(default=0, ge=0)
    repair_usd: float = Field(default=0, ge=0)
    local_costs_usd: float = Field(default=0, ge=0)
    other_usd: float = Field(default=0, ge=0)
    duty_rate_percent: float = Field(default=10, ge=0, le=100)
    vat_rate_percent: float = Field(default=20, ge=0, le=100)
    excise_usd: float = Field(default=0, ge=0)
    manual_auction_fee_usd: float | None = Field(default=None, ge=0)
    usd_to_uah: float = Field(default=40, gt=0)
    usd_to_eur: float = Field(default=0.92, gt=0)
    expected_sell_price_usd: float | None = Field(default=None, ge=0)
    target_margin_usd: float | None = Field(default=None, ge=0)


class LandedCostOutput(BaseModel):
    formula_version: str
    auction_provider: str
    auction_fee_usd: float
    duty_usd: float
    vat_usd: float
    pre_tax_total_usd: float
    tax_base_usd: float
    landed_total_usd: float
    landed_total_uah: float
    landed_total_eur: float
    projected_margin_usd: float | None = None
    recommended_max_bid_usd: float | None = None
    notes: list[str] = Field(default_factory=list)


class MarketCompItem(BaseModel):
    vin: str
    make: str | None = None
    model: str | None = None
    year: int | None = None
    source: str
    lot_number: str
    sale_date: str | None = None
    hammer_price_usd: int
    location: str | None = None
    similarity_score: float


class MarketCompsSummary(BaseModel):
    count: int
    avg_hammer_price_usd: float | None = None
    median_hammer_price_usd: float | None = None
    p25_hammer_price_usd: float | None = None
    p75_hammer_price_usd: float | None = None


class MarketCompsResponse(BaseModel):
    target: dict[str, str | int | None]
    summary: MarketCompsSummary
    items: list[MarketCompItem]


class MarketProviderHealth(BaseModel):
    provider: Literal["copart", "iaai"]
    mode: str
    ready: bool
    note: str
    total_runs_window: int
    successful_runs_window: int
    success_rate_percent: float | None = None
    avg_latency_ms: float | None = None
    last_run_at: datetime | None = None
    last_success_at: datetime | None = None


class MarketDataHealthResponse(BaseModel):
    window_hours: int
    total_lots: int
    priced_lots: int
    sold_lots: int
    updated_lots_window: int
    providers: list[MarketProviderHealth]


class LocalMarketListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    listing_id: str
    title: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    price_usd: int | None = None
    price_uah: int | None = None
    mileage_km: int | None = None
    fuel_name: str | None = None
    gearbox_name: str | None = None
    city: str | None = None
    region: str | None = None
    url: str | None = None
    photo_url: str | None = None
    image_urls_json: list[str] = Field(default_factory=list)
    is_active: bool
    is_sold: bool | None = None
    removal_status: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    sold_detected_at: datetime | None = None


class AutoRiaSnapshotResponse(BaseModel):
    provider: str = "autoria"
    query_label: str
    active_ids_seen: int
    listings_upserted: int
    sold_or_removed_detected: int
    skipped_details: int


class LocalMarketSoldTodayResponse(BaseModel):
    items: list[LocalMarketListingRead]
    total_count: int


class LocalMarketBucket(BaseModel):
    label: str
    min_usd: int | None = None
    max_usd: int | None = None
    total_count: int
    sold_count: int
    removed_count: int
    avg_price_usd: float | None = None
    median_price_usd: float | None = None


class LocalMarketPeriodStats(BaseModel):
    days: int
    total_count: int
    sold_count: int
    removed_count: int
    avg_price_usd: float | None = None
    median_price_usd: float | None = None
    buckets: list[LocalMarketBucket]


class LocalMarketStatsResponse(BaseModel):
    provider: str = "autoria"
    periods: list[LocalMarketPeriodStats]


class MarketWatchCreate(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    search_text: str = Field(min_length=2, max_length=255)
    search_params: str | None = Field(default=None, max_length=4000)


class MarketWatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    slug: str
    name: str
    search_text: str
    search_params: str
    query_hash: str
    is_active: bool
    last_run_at: datetime | None = None
    last_active_ids_seen: int
    last_listings_upserted: int
    last_sold_or_removed_detected: int
    created_at: datetime
    updated_at: datetime


class MarketWatchDetailResponse(BaseModel):
    watch: MarketWatchRead
    stats: LocalMarketStatsResponse
    active_items: list[LocalMarketListingRead]
    changed_items: list[LocalMarketListingRead]


class AdvisorReportCreate(BaseModel):
    vin: str = Field(min_length=17, max_length=17)
    assumptions: AdvisorInput
    result: AdvisorOutput


ReportPipelineStage = Literal["lead", "bid", "won", "in_transit", "customs", "delivered"]


class ReportPipelineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: str
    stage: ReportPipelineStage
    note: str | None = None
    updated_at: datetime


class ReportPipelineUpdate(BaseModel):
    stage: ReportPipelineStage
    note: str | None = Field(default=None, max_length=512)


class AdvisorReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vin: str
    assumptions: AdvisorInput
    result: AdvisorOutput
    created_at: datetime
    pipeline: ReportPipelineRead | None = None


class AdvisorReportShareCreate(BaseModel):
    expires_in_days: int | None = Field(default=30, ge=1, le=365)


class AdvisorReportShareRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_id: str
    token: str
    created_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


class SharedAdvisorReportRead(BaseModel):
    share: AdvisorReportShareRead
    report: AdvisorReportRead


class IngestionPriceEvent(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    old_value: str | None = Field(default=None, max_length=128)
    new_value: str = Field(min_length=1, max_length=128)
    event_time: datetime


MarketProviderCode = Literal["copart", "iaai"]
IngestionAttributeValue = str | int | float | bool | None


class IngestionJobPayload(BaseModel):
    provider: MarketProviderCode | None = None
    source: str = Field(min_length=1, max_length=16)
    vin: str = Field(min_length=17, max_length=17)
    lot_number: str = Field(min_length=1, max_length=32)
    source_record_id: str | None = Field(default=None, max_length=128)
    source_url: str | None = Field(default=None, max_length=1024)
    sale_date: date | None = None
    hammer_price_usd: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=128)
    title_brand: str | None = Field(default=None, max_length=128)
    primary_damage: str | None = Field(default=None, max_length=128)
    secondary_damage: str | None = Field(default=None, max_length=128)
    odometer: int | None = Field(default=None, ge=0)
    run_and_drive: bool | None = None
    keys_present: bool | None = None
    make: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=64)
    year: int | None = Field(default=None, ge=1900, le=2100)
    trim: str | None = Field(default=None, max_length=128)
    series: str | None = Field(default=None, max_length=128)
    body_style: str | None = Field(default=None, max_length=128)
    engine: str | None = Field(default=None, max_length=128)
    transmission: str | None = Field(default=None, max_length=128)
    fuel_type: str | None = Field(default=None, max_length=64)
    drivetrain: str | None = Field(default=None, max_length=64)
    vehicle_type: str | None = Field(default=None, max_length=128)
    exterior_color: str | None = Field(default=None, max_length=64)
    interior_color: str | None = Field(default=None, max_length=64)
    cylinders: int | None = Field(default=None, ge=0)
    images: list[str] = Field(default_factory=list)
    price_events: list[IngestionPriceEvent] = Field(default_factory=list)
    attributes: dict[str, IngestionAttributeValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_provider_source(self) -> "IngestionJobPayload":
        inferred = (self.provider or self.source).strip().lower()
        if inferred not in {"copart", "iaai"}:
            raise ValueError("source/provider must be either 'copart' or 'iaai'")
        self.provider = inferred
        self.source = inferred
        self.vin = self.vin.upper()
        self.lot_number = self.lot_number.upper()
        return self


class IngestionConnectorStatus(BaseModel):
    provider: Literal["copart", "iaai"]
    mode: str
    ready: bool
    note: str


class IngestionConnectorFetchRequest(BaseModel):
    provider: Literal["copart", "iaai"]
    vin: str | None = Field(default=None, min_length=17, max_length=17)
    lot_number: str | None = Field(default=None, min_length=1, max_length=32)
    enqueue: bool = True

    @model_validator(mode="after")
    def validate_selector(self) -> "IngestionConnectorFetchRequest":
        if not self.vin and not self.lot_number:
            raise ValueError("Provide either vin or lot_number")
        return self


class IngestionConnectorFetchResponse(BaseModel):
    provider: Literal["copart", "iaai"]
    mode: str
    source_record_id: str
    enqueued: bool
    queue_depth: int | None = None
    run_id: str | None = None
    job: IngestionJobPayload


class IngestionConnectorRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    mode: str
    selector: dict[str, str | bool | None]
    request_hash: str
    source_record_id: str | None = None
    response_hash: str | None = None
    success: bool
    error_message: str | None = None
    latency_ms: int
    enqueued: bool
    queue_depth: int | None = None
    job: IngestionJobPayload | None = None
    created_at: datetime


class IngestionConnectorRunsPage(BaseModel):
    items: list[IngestionConnectorRunRead]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class IngestionEnqueueResponse(BaseModel):
    accepted: bool
    queue_depth: int


class IngestionQueueDepth(BaseModel):
    queue_depth: int


class IngestionImportSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lot_id: str
    provider: MarketProviderCode | None = None
    source: str
    lot_number: str
    vin: str
    source_record_id: str | None = None
    source_url: str | None = None
    sale_date: date | None = None
    hammer_price_usd: int | None = None
    status: str | None = None
    location: str | None = None
    title_brand: str | None = None
    primary_damage: str | None = None
    secondary_damage: str | None = None
    odometer: int | None = None
    run_and_drive: bool | None = None
    keys_present: bool | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    trim: str | None = None
    series: str | None = None
    body_style: str | None = None
    engine: str | None = None
    transmission: str | None = None
    fuel_type: str | None = None
    drivetrain: str | None = None
    vehicle_type: str | None = None
    exterior_color: str | None = None
    interior_color: str | None = None
    cylinders: int | None = None
    images: list[str] = Field(default_factory=list)
    price_events: list[IngestionPriceEvent] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    imported_at: datetime


class IngestionImportHistoryPage(BaseModel):
    items: list[IngestionImportSnapshotRead]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class IngestionProcessResult(BaseModel):
    processed: bool
    message: str
    lot_id: str | None = None
    vin: str | None = None
    source: str | None = None
    lot_number: str | None = None
    images_upserted: int = 0
    price_events_added: int = 0


SeoPageType = Literal["brand", "cluster"]
SeoLocaleCode = Literal["en", "uk", "ru"]


class SeoFaqItem(BaseModel):
    question: str = Field(min_length=1, max_length=255)
    answer: str = Field(min_length=1, max_length=2000)


class SeoLocaleContent(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    teaser: str | None = Field(default=None, max_length=512)
    body: str | None = Field(default=None, max_length=4000)
    faq: list[SeoFaqItem] = Field(default_factory=list)


class SeoLocalizedContent(BaseModel):
    en: SeoLocaleContent = Field(default_factory=SeoLocaleContent)
    uk: SeoLocaleContent = Field(default_factory=SeoLocaleContent)
    ru: SeoLocaleContent = Field(default_factory=SeoLocaleContent)


class SeoPageBase(BaseModel):
    page_type: SeoPageType
    slug_path: str = Field(min_length=1, max_length=255)
    make: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=64)
    year: int | None = Field(default=None, ge=1900, le=2100)
    title: str = Field(min_length=1, max_length=255)
    teaser: str = Field(min_length=1, max_length=512)
    body: str | None = Field(default=None, max_length=4000)
    faq: list[SeoFaqItem] = Field(default_factory=list)
    localized: SeoLocalizedContent = Field(default_factory=SeoLocalizedContent)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class SeoPageCreate(SeoPageBase):
    pass


class SeoPageUpdate(SeoPageBase):
    pass


class SeoPageToggle(BaseModel):
    is_active: bool


class SeoPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    page_type: SeoPageType
    slug_path: str
    make: str | None = None
    model: str | None = None
    year: int | None = None
    title: str
    teaser: str
    body: str | None = None
    faq: list[SeoFaqItem] = Field(default_factory=list)
    localized: SeoLocalizedContent = Field(default_factory=SeoLocalizedContent)
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SeoPageListResponse(BaseModel):
    items: list[SeoPageRead]
