"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { WatchlistToggle } from "../../components/watchlist-toggle";
import { useI18n } from "../../components/i18n-provider";
import { assessVehicleRisk } from "../../lib/risk";

type SearchResolveResponse = {
  query: string;
  normalized_query: string;
  query_type: "vin" | "lot" | "url";
  matched_by: "vin" | "lot";
  vin: string;
  lots_found: number;
  latest_status: string;
  lot_number: string | null;
  source: string | null;
};

type PriceEvent = {
  event_type: string;
  old_value: string | null;
  new_value: string;
  event_time: string;
};

type LotResponse = {
  source: string;
  lot_number: string;
  sale_date: string | null;
  hammer_price_usd: number | null;
  status: string | null;
  location: string | null;
  title_brand: string | null;
  primary_damage: string | null;
  secondary_damage: string | null;
  odometer: number | null;
  run_and_drive: boolean | null;
  keys_present: boolean | null;
  auction_specs: Record<string, string | number | boolean | null>;
  images: Array<{
    image_url: string;
    shot_order: number | null;
    checksum: string | null;
  }>;
  price_events: PriceEvent[];
};

type VehicleResponse = {
  vin: string;
  make: string | null;
  model: string | null;
  year: number | null;
  title_brand: string | null;
  lots: LotResponse[];
};

type HistorySnapshot = {
  id: string;
  lot_id: string;
  source: string;
  lot_number: string;
  vin: string;
  sale_date: string | null;
  hammer_price_usd: number | null;
  status: string | null;
  location: string | null;
  images: string[];
  price_events: PriceEvent[];
  payload: Record<string, unknown>;
  imported_at: string;
};

type HistoryPage = {
  items: HistorySnapshot[];
  total_count: number;
  page: number;
  page_size: number;
  has_next: boolean;
};

type PriceLike = {
  hammer_price_usd: number | null;
  status: string | null;
};

type ToolForm = {
  expectedSellUsd: string;
  targetMarginUsd: string;
  auctionFeesUsd: string;
  logisticsUsd: string;
  customsUsd: string;
  repairUsd: string;
  localCostsUsd: string;
};

type VinDecodeItem = {
  key: string;
  label: string;
  value: string;
};

type VinDecodeSection = {
  title: string;
  items: VinDecodeItem[];
};

type VinDecodeResponse = {
  vin: string;
  source: string;
  source_url: string;
  note: string | null;
  summary: VinDecodeItem[];
  sections: VinDecodeSection[];
};

type MarketCompsResponse = {
  summary: {
    count: number;
    avg_hammer_price_usd: number | null;
    median_hammer_price_usd: number | null;
    p25_hammer_price_usd: number | null;
    p75_hammer_price_usd: number | null;
  };
  items: Array<{
    vin: string;
    make: string | null;
    model: string | null;
    year: number | null;
    source: string;
    lot_number: string;
    sale_date: string | null;
    hammer_price_usd: number;
    location: string | null;
    similarity_score: number;
  }>;
};

const API_BASE = "/api/backend";

const DEFAULT_TOOL_FORM: ToolForm = {
  expectedSellUsd: "17000",
  targetMarginUsd: "1800",
  auctionFeesUsd: "1100",
  logisticsUsd: "1650",
  customsUsd: "1350",
  repairUsd: "2800",
  localCostsUsd: "600"
};

function toMoney(value: number | null | undefined, currency: "USD" | "UAH" | "EUR" = "USD"): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0
  }).format(value);
}

function toDisplayDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function readNumber(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function toDisplayImageUrl(value: string): string {
  const trimmed = value.trim();
  if (trimmed.startsWith("/api/")) return `${API_BASE}${trimmed}`;
  if (trimmed.startsWith("http://")) return trimmed.replace("http://", "https://");
  return trimmed;
}

function isDirectImageUrl(value: string): boolean {
  const normalized = toDisplayImageUrl(value).toLowerCase();
  if (normalized.includes("/api/v1/media/vehicles/")) return true;
  const pathOnly = normalized.split(/[?#]/, 1)[0];
  return [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"].some((ext) => pathOnly.endsWith(ext));
}

function extractDirectImageUrls(images: Array<{ image_url: string }>): string[] {
  const seen = new Set<string>();
  return images
    .map((item) => toDisplayImageUrl(item.image_url))
    .filter((url) => isDirectImageUrl(url))
    .filter((url) => {
      if (seen.has(url)) return false;
      seen.add(url);
      return true;
    });
}

function getVehicleName(vehicle: VehicleResponse | null): string {
  if (!vehicle) return "-";
  const parts = [vehicle.year?.toString(), vehicle.make, vehicle.model].filter(Boolean);
  return parts.length > 0 ? parts.join(" ") : "Unknown vehicle";
}

function toYesNo(value: boolean | null | undefined): string {
  if (value === true) return "Yes";
  if (value === false) return "No";
  return "-";
}

function isSoldStatus(status: string | null | undefined): boolean {
  const normalized = (status || "").toLowerCase();
  return normalized.includes("sold") || normalized.includes("closed");
}

function priceLabel(lot: PriceLike | null, dict: ReturnType<typeof useI18n>["dict"]): string {
  if (!lot) return dict.search.kpiStatus;
  if (lot.hammer_price_usd && isSoldStatus(lot.status)) return dict.search.boughtFor;
  if (lot.hammer_price_usd) return dict.search.stats.currentBid;
  return dict.search.kpiStatus;
}

function priceValue(lot: PriceLike | null): string {
  if (!lot) return "-";
  if (lot.hammer_price_usd) return toMoney(lot.hammer_price_usd, "USD");
  return lot.status || "-";
}

function lotPriceLine(lot: LotResponse, dict: ReturnType<typeof useI18n>["dict"]): string {
  return `${priceLabel(lot, dict)}: ${priceValue(lot)}`;
}

function buildAuctionSpecRows(lot: LotResponse | null): Array<[string, string]> {
  if (!lot) return [];
  const rows: Array<[string, string]> = [
    ["Title", lot.title_brand || "-"],
    ["Primary damage", lot.primary_damage || "-"],
    ["Secondary damage", lot.secondary_damage || "-"],
    ["Odometer", lot.odometer ? `${lot.odometer.toLocaleString("en-US")} mi` : "-"],
    ["Run & drive", toYesNo(lot.run_and_drive)],
    ["Keys", toYesNo(lot.keys_present)]
  ];
  const specLabels: Record<string, string> = {
    trim: "Trim",
    series: "Series",
    body_style: "Body style",
    engine: "Engine",
    transmission: "Transmission",
    fuel_type: "Fuel",
    drivetrain: "Drivetrain",
    vehicle_type: "Vehicle type",
    exterior_color: "Exterior color",
    interior_color: "Interior color",
    cylinders: "Cylinders"
  };
  for (const [key, label] of Object.entries(specLabels)) {
    const value = lot.auction_specs?.[key];
    if (value !== null && value !== undefined && value !== "") rows.push([label, String(value)]);
  }
  return rows.filter(([, value]) => value !== "-");
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  try {
    const json = (await response.json()) as { detail?: unknown };
    if (typeof json.detail === "string" && json.detail.trim()) return json.detail;
  } catch {
    // ignore parsing issues
  }
  return fallback;
}

export default function SearchPage() {
  const { dict } = useI18n();
  const [queryInput, setQueryInput] = useState("5YJ3E1EA3JF053140");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [resolved, setResolved] = useState<SearchResolveResponse | null>(null);
  const [vehicle, setVehicle] = useState<VehicleResponse | null>(null);
  const [history, setHistory] = useState<HistoryPage | null>(null);
  const [decoded, setDecoded] = useState<VinDecodeResponse | null>(null);
  const [market, setMarket] = useState<MarketCompsResponse | null>(null);
  const [selectedLotIndex, setSelectedLotIndex] = useState(0);
  const [toolForm, setToolForm] = useState<ToolForm>(DEFAULT_TOOL_FORM);

  const lots = vehicle?.lots || [];
  const safeLotIndex = lots.length === 0 ? 0 : Math.min(selectedLotIndex, lots.length - 1);
  const activeLot = lots[safeLotIndex] || null;

  const galleryImages = useMemo(() => {
    if (!activeLot) return [] as string[];
    return extractDirectImageUrls(activeLot.images).slice(0, 12);
  }, [activeLot]);

  const toolSummary = useMemo(() => {
    const expectedSell = readNumber(toolForm.expectedSellUsd);
    const targetMargin = readNumber(toolForm.targetMarginUsd);
    const auctionFees = readNumber(toolForm.auctionFeesUsd);
    const logistics = readNumber(toolForm.logisticsUsd);
    const customs = readNumber(toolForm.customsUsd);
    const repair = readNumber(toolForm.repairUsd);
    const localCosts = readNumber(toolForm.localCostsUsd);

    const bidNow = activeLot?.hammer_price_usd || 0;
    const costWithoutBid = auctionFees + logistics + customs + repair + localCosts;
    const landedAtCurrentBid = bidNow + costWithoutBid;
    const profitAtCurrentBid = expectedSell - landedAtCurrentBid;
    const safeMaxBid = expectedSell - costWithoutBid - targetMargin;
    const deltaVsCurrent = safeMaxBid - bidNow;

    return {
      bidNow,
      costWithoutBid,
      landedAtCurrentBid,
      profitAtCurrentBid,
      safeMaxBid,
      deltaVsCurrent
    };
  }, [activeLot?.hammer_price_usd, toolForm]);

  const riskAssessment = useMemo(() => assessVehicleRisk(vehicle, activeLot), [vehicle, activeLot]);
  const auctionSpecRows = useMemo(() => buildAuctionSpecRows(activeLot), [activeLot]);

  const riskReasonText = useMemo(() => {
    if (!riskAssessment) return [];

    const mapping = {
      title: dict.search.risk.titleReason,
      status: dict.search.risk.statusReason,
      multipleRuns: dict.search.risk.multipleRunsReason,
      priceRunup: dict.search.risk.priceRunupReason,
      missingImages: dict.search.risk.missingImagesReason,
      highBid: dict.search.risk.highBidReason
    } as const;

    return riskAssessment.reasons.map((reason) => mapping[reason]);
  }, [dict.search.risk, riskAssessment]);

  async function executeSearch(rawQuery: string) {
    const query = rawQuery.trim();
    if (!query) {
      setError(dict.search.empty);
      return;
    }

    setLoading(true);
    setError("");
    setResolved(null);
    setVehicle(null);
    setHistory(null);
    setDecoded(null);
    setMarket(null);
    setSelectedLotIndex(0);

    try {
      const resolveResponse = await fetch(`${API_BASE}/api/v1/search/resolve?query=${encodeURIComponent(query)}`);
      if (!resolveResponse.ok) {
        throw new Error(await readApiError(resolveResponse, dict.search.searchFailed));
      }
      const resolvedJson = (await resolveResponse.json()) as SearchResolveResponse;
      setResolved(resolvedJson);

      const [vehicleResponse, historyResponse, decoderResponse, marketResponse] = await Promise.all([
        fetch(`${API_BASE}/api/v1/vehicles/${resolvedJson.vin}`),
        fetch(`${API_BASE}/api/v1/ingestion/history?vin=${resolvedJson.vin}&page=1&page_size=30`),
        fetch(`${API_BASE}/api/v1/vin-decoder/${resolvedJson.vin}`),
        fetch(`${API_BASE}/api/v1/market/comps?vin=${resolvedJson.vin}&limit=8`)
      ]);

      if (!vehicleResponse.ok) {
        throw new Error(await readApiError(vehicleResponse, dict.search.vehicleFailed));
      }

      const vehicleJson = (await vehicleResponse.json()) as VehicleResponse;
      setVehicle(vehicleJson);

      if (historyResponse.ok) {
        const historyJson = (await historyResponse.json()) as HistoryPage;
        setHistory(historyJson);
      } else {
        setHistory({ items: [], total_count: 0, page: 1, page_size: 30, has_next: false });
      }

      if (decoderResponse.ok) {
        setDecoded((await decoderResponse.json()) as VinDecodeResponse);
      }

      if (marketResponse.ok) {
        setMarket((await marketResponse.json()) as MarketCompsResponse);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : dict.search.requestError);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const preset = params.get("query") || params.get("vin");
    if (!preset) return;
    setQueryInput(preset);
    void executeSearch(preset);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    await executeSearch(queryInput);
  }

  function setToolField<K extends keyof ToolForm>(key: K, value: string) {
    setToolForm((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <main className="shell searchShell">
      <section className="panel marketHero iaaiHero">
        <div className="heroFrame">
          <div className="heroCopy">
            <p className="chip">{dict.search.chip}</p>
            <h1>{dict.search.title}</h1>
            <p className="lead">{dict.search.lead}</p>
            <div className="actions">
              <Link href="/" className="ghostButton">
                {dict.search.toHome}
              </Link>
              <Link href="/cars" className="ghostButton">
                {dict.search.toCatalog}
              </Link>
            </div>
          </div>
          <div className="heroSignal">
            <div className="auctionBoard">
              <p className="label">Live Analysis</p>
              <div className="auctionRow">
                <span>Search</span>
                <strong>VIN / Lot / URL</strong>
              </div>
              <div className="auctionRow">
                <span>NHTSA</span>
                <strong>Decoder</strong>
              </div>
              <div className="auctionRow">
                <span>History</span>
                <strong>Stored</strong>
              </div>
              <div className="auctionRow">
                <span>Decision</span>
                <strong>Margin-based</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="panel searchPanelUltra">
        <form className="searchForm" onSubmit={onSearchSubmit}>
          <label htmlFor="searchInput">{dict.search.label}</label>
          <div className="searchRow">
            <input
              id="searchInput"
              placeholder={dict.search.placeholder}
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
            />
            <button type="submit" disabled={loading}>
              {loading ? dict.search.searching : dict.search.submit}
            </button>
          </div>
        </form>
        <p className="lead muted">{dict.search.helper}</p>
        {error && (
          <div className="errorPanel inlineError panel">
            <p>{error}</p>
          </div>
        )}
      </section>

      {resolved && (
        <section className="panel kpiPanelUltra">
          <div className="kpiStrip">
            <article className="kpiCard">
              <p className="label">VIN</p>
              <h3>{resolved.vin}</h3>
            </article>
            <article className="kpiCard">
              <p className="label">{dict.search.kpiLots}</p>
              <h3>{resolved.lots_found}</h3>
            </article>
            <article className="kpiCard">
              <p className="label">{dict.search.kpiStatus}</p>
              <h3>{resolved.latest_status || "-"}</h3>
            </article>
            <article className="kpiCard">
              <p className="label">{dict.search.kpiLatestLot}</p>
              <h3>{resolved.lot_number || "-"}</h3>
            </article>
          </div>
          <div className="actions compactActions">
            <Link href={`/auto/${resolved.vin}`} className="button">
              {dict.search.openVinPage}
            </Link>
            {vehicle && (
              <WatchlistToggle
                snapshot={{
                  vin: vehicle.vin,
                  label: getVehicleName(vehicle),
                  titleBrand: vehicle.title_brand,
                  latestLotNumber: activeLot?.lot_number || null,
                  latestStatus: activeLot?.status || null,
                  latestBidUsd: activeLot?.hammer_price_usd || null,
                  imageCount: activeLot?.images?.length || 0,
                  savedAt: new Date().toISOString()
                }}
              />
            )}
          </div>
        </section>
      )}

      {riskAssessment && (
        <section className="panel riskPanel">
          <div className="sectionHead">
            <div>
              <h2>{dict.search.risk.title}</h2>
              <p className="muted">{dict.search.risk.lead}</p>
            </div>
            <div className={`riskBadge risk-${riskAssessment.level}`}>
              {riskAssessment.level === "high"
                ? dict.search.risk.high
                : riskAssessment.level === "medium"
                  ? dict.search.risk.medium
                  : dict.search.risk.low}
            </div>
          </div>
          <div className="riskGrid">
            <article className="riskCard">
              <p className="label">{dict.search.risk.score}</p>
              <h3>{riskAssessment.score}/100</h3>
            </article>
            <article className="riskCard">
              <p className="label">{dict.search.risk.level}</p>
              <h3>
                {riskAssessment.level === "high"
                  ? dict.search.risk.high
                  : riskAssessment.level === "medium"
                    ? dict.search.risk.medium
                    : dict.search.risk.low}
              </h3>
            </article>
          </div>
          {riskReasonText.length > 0 && (
            <>
              <p className="label riskReasonsLabel">{dict.search.risk.reasons}</p>
              <div className="riskReasons">
                {riskReasonText.map((reason) => (
                  <article key={reason} className="riskReasonCard">
                    <p>{reason}</p>
                  </article>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {decoded && (
        <section className="panel decoderPanel">
          <div className="sectionHead">
            <div>
              <h2>{dict.search.decoder.title}</h2>
              <p className="muted">{dict.search.decoder.lead}</p>
            </div>
            <a href={decoded.source_url} className="ghostButton" target="_blank" rel="noreferrer">
              {dict.search.decoder.source}
            </a>
          </div>
          {decoded.note && (
            <div className="signalBanner decoderNote">
              <strong>{dict.search.decoder.note}:</strong> {decoded.note}
            </div>
          )}
          <div className="decoderSummary">
            {decoded.summary.map((item) => (
              <article key={item.key} className="decoderSummaryCard">
                <p className="label">{item.label}</p>
                <h3>{item.value}</h3>
              </article>
            ))}
          </div>
          <div className="decoderGrid">
            {decoded.sections.map((section) => (
              <article key={section.title} className="decoderCard">
                <h3>{section.title}</h3>
                <dl className="decoderList">
                  {section.items.map((item) => (
                    <div key={item.key}>
                      <dt>{item.label}</dt>
                      <dd>{item.value}</dd>
                    </div>
                  ))}
                </dl>
              </article>
            ))}
          </div>
        </section>
      )}

      {resolved && !decoded && !loading && (
        <section className="panel decoderPanel">
          <h2>{dict.search.decoder.title}</h2>
          <p className="muted">{dict.search.decoder.unavailable}</p>
        </section>
      )}

      {market && market.summary.count > 0 ? (
        <section className="panel marketPanel">
          <div className="sectionHead">
            <div>
              <h2>{dict.search.market.title}</h2>
              <p className="muted">{dict.search.market.lead}</p>
            </div>
          </div>
          <div className="marketSummaryGrid">
            <article className="marketCard">
              <p className="label">{dict.search.market.lowerBound}</p>
              <h3>{toMoney(market.summary.p25_hammer_price_usd, "USD")}</h3>
            </article>
            <article className="marketCard">
              <p className="label">{dict.search.market.median}</p>
              <h3>{toMoney(market.summary.median_hammer_price_usd, "USD")}</h3>
            </article>
            <article className="marketCard">
              <p className="label">{dict.search.market.average}</p>
              <h3>{toMoney(market.summary.avg_hammer_price_usd, "USD")}</h3>
            </article>
            <article className="marketCard">
              <p className="label">{dict.search.market.comps}</p>
              <h3>{market.summary.count}</h3>
            </article>
          </div>
          <div className="marketCompList">
            {market.items.slice(0, 6).map((item) => (
              <article key={`${item.source}-${item.lot_number}-${item.vin}`} className="marketCompCard">
                <p className="label">
                  {item.year || "-"} {item.make || ""} {item.model || ""}
                </p>
                <h3>{toMoney(item.hammer_price_usd, "USD")}</h3>
                <p>VIN: {item.vin}</p>
                <p>{dict.search.market.similarity}: {Math.round(item.similarity_score)}%</p>
              </article>
            ))}
          </div>
        </section>
      ) : resolved && !loading ? (
        <section className="panel marketPanel">
          <h2>{dict.search.market.title}</h2>
          <p className="muted">{dict.search.market.noData}</p>
        </section>
      ) : null}

      {vehicle && (
        <>
          <section className="panel vehicleHero vehicleHeroUltra">
            <div className="vehicleHeader">
              <div>
                <p className="label">{dict.search.vehicleLabel}</p>
                <h2>{getVehicleName(vehicle)}</h2>
                <p className="lead">VIN: {vehicle.vin}</p>
              </div>
              <div>
                <p className="label">{dict.search.titleBrand}</p>
                <h3>{vehicle.title_brand || dict.search.noTitle}</h3>
              </div>
            </div>

            <div className="resultGrid">
              <section className="galleryBlock">
                <p className="label">{dict.search.lotPhotos}</p>
                {galleryImages.length > 0 ? (
                  <>
                    <a href={galleryImages[0]} target="_blank" rel="noreferrer" className="mainPhotoLink">
                      <img src={galleryImages[0]} alt="Lot main photo" className="mainPhoto" />
                    </a>
                    <div className="thumbGrid">
                      {galleryImages.slice(1).map((url, idx) => (
                        <a key={`${url}-${idx}`} href={url} target="_blank" rel="noreferrer" className="thumbLink">
                          <img src={url} alt={`Lot photo ${idx + 2}`} className="thumbPhoto" loading="lazy" />
                        </a>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="lead muted">{dict.search.noPhotos}</p>
                )}
              </section>

              <section className="factSheet">
                <p className="label">{dict.search.lotCard}</p>
                {activeLot ? (
                  <>
                    <div className="purchasePriceHero">
                      <p>{priceLabel(activeLot, dict)}</p>
                      <strong>{priceValue(activeLot)}</strong>
                      <span>
                        #{activeLot.lot_number} · {activeLot.status || "-"}
                      </span>
                    </div>
                    <dl className="factList">
                      <div>
                        <dt>{dict.search.source}</dt>
                        <dd>{activeLot.source}</dd>
                      </div>
                      <div>
                        <dt>{dict.search.lot}</dt>
                        <dd>#{activeLot.lot_number}</dd>
                      </div>
                      <div>
                        <dt>{dict.search.saleDate}</dt>
                        <dd>{activeLot.sale_date || "-"}</dd>
                      </div>
                      <div>
                        <dt>{dict.search.kpiStatus}</dt>
                        <dd>{activeLot.status || "-"}</dd>
                      </div>
                      <div>
                        <dt>{dict.search.location}</dt>
                        <dd>{activeLot.location || "-"}</dd>
                      </div>
                      {activeLot.primary_damage && (
                      <div>
                        <dt>Damage</dt>
                        <dd>{activeLot.primary_damage}</dd>
                      </div>
                      )}
                      {activeLot.odometer && (
                      <div>
                        <dt>Odometer</dt>
                        <dd>{activeLot.odometer.toLocaleString("en-US")} mi</dd>
                      </div>
                      )}
                    </dl>
                  </>
                ) : (
                  <p className="lead muted">{dict.search.noLots}</p>
                )}
              </section>
            </div>
          </section>

          {auctionSpecRows.length > 0 && (
            <section className="panel auctionSpecsPanel">
              <div className="sectionHead">
                <div>
                  <h2>{dict.search.auctionSpecs.title}</h2>
                  <p className="muted">{dict.search.auctionSpecs.lead}</p>
                </div>
              </div>
              <dl className="auctionSpecsGrid">
                {auctionSpecRows.map(([label, value]) => (
                  <div key={`${label}-${value}`}>
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          <section className="panel timelinePanelUltra">
            <div className="sectionHead">
              <h2>{dict.search.auctionHistoryTitle}</h2>
              <p className="muted">{dict.search.auctionHistoryLead}</p>
            </div>
            {lots.length === 0 ? (
              <p className="lead muted">{dict.search.noAuctionHistory}</p>
            ) : (
              <div className="lotTimeline">
                {lots.map((lot, idx) => (
                  <button
                    key={`${lot.source}-${lot.lot_number}-${idx}`}
                    type="button"
                    className={`timelineCard ${idx === safeLotIndex ? "active" : ""}`}
                    onClick={() => setSelectedLotIndex(idx)}
                  >
                    <p className="label">{lot.source}</p>
                    <h3>#{lot.lot_number}</h3>
                    <p>{dict.search.saleDate}: {lot.sale_date || "-"}</p>
                    <p>{lotPriceLine(lot, dict)}</p>
                    <p>{dict.search.kpiStatus}: {lot.status || "-"}</p>
                    {lot.price_events.length > 0 && (
                      <ul className="miniList">
                        {lot.price_events.slice(0, 3).map((event, eventIndex) => (
                          <li key={`${event.event_type}-${event.event_time}-${eventIndex}`}>
                            {event.event_type}: {event.old_value ? `${event.old_value} -> ` : ""}
                            {event.new_value}
                          </li>
                        ))}
                      </ul>
                    )}
                  </button>
                ))}
              </div>
            )}
          </section>

          <section className="panel historyPanelUltra">
            <div className="sectionHead">
              <h2>{dict.search.importHistoryTitle}</h2>
              <p className="muted">
                {dict.search.importHistoryLead} {history?.total_count ?? 0}
              </p>
            </div>
            {history && history.items.length > 0 ? (
              <div className="importHistoryList">
                {history.items.map((item) => (
                  <article key={item.id} className="historyRow">
                    <p className="label">
                      {item.source} #{item.lot_number}
                    </p>
                    <h3>{toDisplayDate(item.imported_at)}</h3>
                    <p>{dict.search.kpiStatus}: {item.status || "-"}</p>
                    <p>
                      {priceLabel(item, dict)}: {priceValue(item)}
                    </p>
                    <p>{dict.search.location}: {item.location || "-"}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="lead muted">{dict.search.noImportHistory}</p>
            )}
          </section>

          <section className="panel toolPanel iaaiToolPanel" id="toolkit">
            <p className="chip">{dict.search.toolkitChip}</p>
            <h2>{dict.search.toolkitTitle}</h2>
            <p className="lead">{dict.search.toolkitLead}</p>

            <div className="toolGrid">
              {(Object.keys(dict.search.fields) as Array<keyof typeof dict.search.fields>).map((fieldKey) => (
                <label key={fieldKey}>
                  {dict.search.fields[fieldKey]}
                  <input
                    type="number"
                    min={0}
                    value={toolForm[fieldKey]}
                    onChange={(e) => setToolField(fieldKey, e.target.value)}
                  />
                </label>
              ))}
            </div>

            <div className="stats">
              <article className="panel statCard">
                <p className="label">{dict.search.stats.currentBid}</p>
                <h3>{toMoney(toolSummary.bidNow, "USD")}</h3>
              </article>
              <article className="panel statCard">
                <p className="label">{dict.search.stats.landedCost}</p>
                <h3>{toMoney(toolSummary.landedAtCurrentBid, "USD")}</h3>
              </article>
              <article className="panel statCard">
                <p className="label">{dict.search.stats.profit}</p>
                <h3>{toMoney(toolSummary.profitAtCurrentBid, "USD")}</h3>
              </article>
            </div>

            <div className="stats">
              <article className="panel statCard">
                <p className="label">{dict.search.stats.costsWithoutBid}</p>
                <h3>{toMoney(toolSummary.costWithoutBid, "USD")}</h3>
              </article>
              <article className="panel statCard">
                <p className="label">{dict.search.stats.safeMaxBid}</p>
                <h3>{toMoney(toolSummary.safeMaxBid, "USD")}</h3>
              </article>
              <article className="panel statCard">
                <p className="label">{dict.search.stats.delta}</p>
                <h3>{toMoney(toolSummary.deltaVsCurrent, "USD")}</h3>
              </article>
            </div>

            <div className={`signalBanner ${toolSummary.deltaVsCurrent < 0 ? "toolAlert" : ""}`}>
              {toolSummary.deltaVsCurrent < 0 ? dict.search.badSignal : dict.search.goodSignal}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
