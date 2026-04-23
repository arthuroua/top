import type { Metadata } from "next";
import Link from "next/link";
import { cache } from "react";

import { WatchlistToggle } from "../../../components/watchlist-toggle";
import { assessVehicleRisk } from "../../../lib/risk";
import { getServerDictionary } from "../../../lib/server-locale";

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
  source: string;
  lot_number: string;
  status: string | null;
  hammer_price_usd: number | null;
  imported_at: string;
};

type HistoryPage = {
  items: HistorySnapshot[];
  total_count: number;
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

type PageProps = {
  params: Promise<{ vin: string }>;
};

const apiPublicBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const apiInternalBase = process.env.API_INTERNAL_BASE_URL || apiPublicBase;
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

function normalizeVin(rawVin: string): string {
  return rawVin.trim().toUpperCase();
}

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function toVehicleName(vehicle: VehicleResponse): string {
  const parts = [vehicle.year?.toString(), vehicle.make, vehicle.model].filter(Boolean);
  return parts.length > 0 ? parts.join(" ") : "Vehicle";
}

function toMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(
    value
  );
}

function toDate(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function toDisplayImageUrl(value: string): string {
  if (value.startsWith("/api/")) return `${apiPublicBase}${value}`;
  if (value.startsWith("http://")) return value.replace("http://", "https://");
  return value;
}

function isDirectImageUrl(value: string): boolean {
  const normalized = toDisplayImageUrl(value).toLowerCase();
  if (normalized.includes("/api/v1/media/vehicles/")) return true;
  const pathOnly = normalized.split(/[?#]/, 1)[0];
  return [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"].some((ext) => pathOnly.endsWith(ext));
}

function collectImages(lots: LotResponse[]): string[] {
  const seen = new Set<string>();
  const urls: string[] = [];
  for (const lot of lots) {
    for (const image of lot.images) {
      const resolved = toDisplayImageUrl(image.image_url);
      if (!isDirectImageUrl(resolved) || seen.has(resolved)) continue;
      seen.add(resolved);
      urls.push(resolved);
      if (urls.length >= 10) return urls;
    }
  }
  return urls;
}

async function safeJsonFetch<T>(url: string, revalidate: number): Promise<T | null> {
  try {
    const response = await fetch(url, { next: { revalidate } });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

const getVehicle = cache(async (vin: string) => safeJsonFetch<VehicleResponse>(`${apiInternalBase}/api/v1/vehicles/${vin}`, 900));
const getHistory = cache(async (vin: string) => {
  const data = await safeJsonFetch<HistoryPage>(`${apiInternalBase}/api/v1/ingestion/history?vin=${vin}&page=1&page_size=20`, 900);
  return data || { items: [], total_count: 0 };
});
const getDecoded = cache(async (vin: string) =>
  safeJsonFetch<VinDecodeResponse>(`${apiInternalBase}/api/v1/vin-decoder/${vin}`, 86400)
);
const getMarket = cache(async (vin: string) =>
  safeJsonFetch<MarketCompsResponse>(`${apiInternalBase}/api/v1/market/comps?vin=${vin}&limit=8`, 3600)
);

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { vin: vinParam } = await params;
  const vin = normalizeVin(vinParam);
  const vehicle = await getVehicle(vin);
  if (!vehicle) {
    return {
      title: `VIN ${vin} unavailable`,
      description: `Vehicle data for VIN ${vin} is temporarily unavailable.`,
      robots: { index: false, follow: true },
      alternates: { canonical: `/auto/${vin}` }
    };
  }
  const vehicleName = toVehicleName(vehicle);
  return {
    title: `${vehicleName} VIN ${vin}`,
    description: `${vehicleName}. Auction history, photos, NHTSA specs, and import timeline for VIN ${vin}.`,
    alternates: { canonical: `/auto/${vin}` },
    openGraph: {
      type: "article",
      locale: "en_US",
      url: `${siteUrl}/auto/${vin}`,
      title: `${vehicleName} VIN ${vin}`,
      description: `${vehicleName}. Auction history, photos, NHTSA specs, and import timeline.`
    }
  };
}

export default async function AutoSeoPage({ params }: PageProps) {
  const { vin: vinParam } = await params;
  const vin = normalizeVin(vinParam);
  const { dict, locale } = await getServerDictionary();
  const vehicle = await getVehicle(vin);

  if (!vehicle) {
    return (
      <main className="shell autoSeoShell">
        <article className="panel autoSeoHero iaaiHero">
          <div className="heroFrame">
            <div className="heroCopy">
              <p className="chip">{dict.auto.pageChip}</p>
              <h1>{dict.auto.pageUnavailable}</h1>
              <p className="lead">{dict.auto.pageUnavailableLead}</p>
              <div className="actions">
                <Link href={`/search?vin=${vin}`} className="button">
                  {dict.auto.openSearch}
                </Link>
                <Link href="/cars" className="ghostButton">
                  {dict.auto.openCatalog}
                </Link>
              </div>
            </div>
          </div>
        </article>
      </main>
    );
  }

  const history = await getHistory(vin);
  const decoded = await getDecoded(vin);
  const market = await getMarket(vin);
  const vehicleName = toVehicleName(vehicle);
  const lots = vehicle.lots || [];
  const images = collectImages(lots);
  const latestLot = lots[0];
  const latestLotImages = latestLot ? collectImages([latestLot]).slice(0, 6) : [];
  const relatedClusterHref =
    vehicle.make && vehicle.model && vehicle.year
      ? `/cars/${slugify(vehicle.make)}/${slugify(vehicle.model)}/${vehicle.year}`
      : null;
  const averagePrice = lots.filter((lot) => lot.hammer_price_usd !== null).reduce((sum, lot, _, array) => {
    return sum + (lot.hammer_price_usd || 0) / array.length;
  }, 0);
  const lowerBound = market?.summary.p25_hammer_price_usd ?? null;
  const medianPrice = market?.summary.median_hammer_price_usd ?? null;
  const riskAssessment = assessVehicleRisk(vehicle, latestLot || null);
  const riskText = riskAssessment
    ? {
        title:
          riskAssessment.level === "high"
            ? dict.search.risk.high
            : riskAssessment.level === "medium"
              ? dict.search.risk.medium
              : dict.search.risk.low,
        reasons: riskAssessment.reasons.map((reason) => {
          const mapping = {
            title: dict.search.risk.titleReason,
            status: dict.search.risk.statusReason,
            multipleRuns: dict.search.risk.multipleRunsReason,
            priceRunup: dict.search.risk.priceRunupReason,
            missingImages: dict.search.risk.missingImagesReason,
            highBid: dict.search.risk.highBidReason
          } as const;
          return mapping[reason];
        })
      }
    : null;

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Vehicle",
        "@id": `${siteUrl}/auto/${vin}#vehicle`,
        name: `${vehicleName} (${vin})`,
        vehicleIdentificationNumber: vin,
        brand: vehicle.make || undefined,
        model: vehicle.model || undefined,
        productionDate: vehicle.year ? String(vehicle.year) : undefined,
        url: `${siteUrl}/auto/${vin}`
      },
      {
        "@type": "WebPage",
        "@id": `${siteUrl}/auto/${vin}#webpage`,
        url: `${siteUrl}/auto/${vin}`,
        name: `${vehicleName} VIN ${vin}`,
        inLanguage: locale
      }
    ]
  };

  return (
    <main className="shell autoSeoShell">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <article className="panel autoSeoHero iaaiHero">
        <div className="heroFrame">
          <div className="heroCopy">
            <p className="chip">{dict.auto.heroChip}</p>
            <h1>{vehicleName}</h1>
            <p className="lead">VIN: {vin}. {dict.auto.heroLead}</p>
            <div className="actions">
              <Link href={`/search?vin=${vin}`} className="button">
                {dict.auto.openAnalysis}
              </Link>
              <WatchlistToggle
                snapshot={{
                  vin,
                  label: vehicleName,
                  titleBrand: vehicle.title_brand,
                  latestLotNumber: latestLot?.lot_number || null,
                  latestStatus: latestLot?.status || null,
                  latestBidUsd: latestLot?.hammer_price_usd || null,
                  imageCount: latestLot?.images?.length || 0,
                  savedAt: new Date().toISOString()
                }}
              />
              {relatedClusterHref && (
                <Link href={relatedClusterHref} className="ghostButton">
                  {dict.auto.toCluster}
                </Link>
              )}
            </div>
          </div>

          <div className="heroSignal">
            <div className="auctionBoard">
              <p className="label">VIN Snapshot</p>
              <div className="auctionRow">
                <span>{dict.auto.lotsInBase}</span>
                <strong>{lots.length}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.auto.averagePrice}</span>
                <strong>{Number.isFinite(averagePrice) ? toMoney(averagePrice) : "-"}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.auto.title}</span>
                <strong>{vehicle.title_brand || "-"}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.auto.images}</span>
                <strong>{images.length}</strong>
              </div>
            </div>
          </div>
        </div>
      </article>

      <section className="panel autoSeoSection">
        <div className="autoJumpNav">
          <a href="#vin-overview">{dict.auto.knowTitle}</a>
          <a href="#vin-market">{dict.auto.marketTitle}</a>
          <a href="#vin-specs">{dict.auto.decoderTitle}</a>
          <a href="#vin-lots">{dict.auto.lotsTitle}</a>
          <a href="#vin-history">{dict.auto.updateLogTitle}</a>
          <a href="#vin-profit">{dict.auto.openCalculator}</a>
        </div>
        <div className="autoSeoQuickFacts">
          <div>
            <p className="label">VIN</p>
            <strong>{vin}</strong>
          </div>
          <div>
            <p className="label">{dict.search.finalBid}</p>
            <strong>{toMoney(latestLot?.hammer_price_usd)}</strong>
          </div>
          <div>
            <p className="label">{dict.search.market.lowerBound}</p>
            <strong>{toMoney(lowerBound)}</strong>
          </div>
          <div>
            <p className="label">{dict.search.market.median}</p>
            <strong>{toMoney(medianPrice)}</strong>
          </div>
          <div>
            <p className="label">{dict.search.kpiStatus}</p>
            <strong>{latestLot?.status || "-"}</strong>
          </div>
          <div>
            <p className="label">{dict.search.location}</p>
            <strong>{latestLot?.location || "-"}</strong>
          </div>
        </div>
      </section>

      {latestLot && (
        <section className="panel lotSpotlight" id="vin-overview">
          <div className="sectionHead">
            <div>
              <h2>{dict.auto.knowTitle}</h2>
              <p className="muted">Latest lot spotlight with the fastest way to judge whether the car still makes sense.</p>
            </div>
          </div>
          <div className="lotSpotlightGrid">
            <div className="lotSpotlightGallery">
              {latestLotImages.length > 0 ? (
                <>
                  <a href={latestLotImages[0]} target="_blank" rel="noreferrer" className="mainPhotoLink">
                    <img src={latestLotImages[0]} alt={`${vehicleName} latest lot main`} className="mainPhoto" />
                  </a>
                  {latestLotImages.length > 1 && (
                    <div className="thumbGrid">
                      {latestLotImages.slice(1).map((url, imageIndex) => (
                        <a key={`${url}-${imageIndex}`} href={url} target="_blank" rel="noreferrer" className="thumbLink">
                          <img src={url} alt={`${vehicleName} latest lot ${imageIndex + 2}`} className="thumbPhoto" loading="lazy" />
                        </a>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div className="spotlightEmpty">
                  <p>{dict.search.noPhotos}</p>
                </div>
              )}
            </div>
            <div className="lotSpotlightFacts">
              <div className="spotlightFactCard">
                <p className="label">{dict.search.source}</p>
                <h3>{latestLot.source}</h3>
                <p>#{latestLot.lot_number}</p>
              </div>
              <div className="spotlightFactCard">
                <p className="label">{dict.search.saleDate}</p>
                <h3>{latestLot.sale_date || "-"}</h3>
                <p>{dict.search.location}: {latestLot.location || "-"}</p>
              </div>
              <div className="spotlightFactCard">
                <p className="label">{dict.search.finalBid}</p>
                <h3>{toMoney(latestLot.hammer_price_usd)}</h3>
                <p>{dict.search.market.lowerBound}: {toMoney(lowerBound)}</p>
              </div>
              <div className="spotlightFactCard">
                <p className="label">{dict.search.kpiStatus}</p>
                <h3>{latestLot.status || "-"}</h3>
                <p>{dict.auto.images}: {latestLotImages.length}</p>
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="panel autoSeoSection">
        <h2>{dict.auto.knowTitle}</h2>
        <p>{latestLot ? `${latestLot.source} #${latestLot.lot_number}` : "-"}</p>
        <p>
          Status: {latestLot?.status || "-"}. Sale date: {latestLot?.sale_date || "-"}. Location: {latestLot?.location || "-"}.
        </p>
      </section>

      {riskAssessment && riskText && (
        <section className="panel riskPanel">
          <div className="sectionHead">
            <div>
              <h2>{dict.auto.riskTitle}</h2>
              <p className="muted">{dict.auto.riskLead}</p>
            </div>
            <div className={`riskBadge risk-${riskAssessment.level}`}>{riskText.title}</div>
          </div>
          <div className="riskGrid">
            <article className="riskCard">
              <p className="label">{dict.search.risk.score}</p>
              <h3>{riskAssessment.score}/100</h3>
            </article>
            <article className="riskCard">
              <p className="label">{dict.search.risk.level}</p>
              <h3>{riskText.title}</h3>
            </article>
          </div>
          {riskText.reasons.length > 0 && (
            <>
              <p className="label riskReasonsLabel">{dict.search.risk.reasons}</p>
              <div className="riskReasons">
                {riskText.reasons.map((reason) => (
                  <article key={reason} className="riskReasonCard">
                    <p>{reason}</p>
                  </article>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {market && market.summary.count > 0 && (
        <section className="panel marketPanel" id="vin-market">
          <div className="sectionHead">
            <div>
              <h2>{dict.auto.marketTitle}</h2>
              <p className="muted">{dict.auto.marketLead}</p>
            </div>
          </div>
          <div className="marketSummaryGrid">
            <article className="marketCard">
              <p className="label">{dict.search.market.lowerBound}</p>
              <h3>{toMoney(market.summary.p25_hammer_price_usd)}</h3>
            </article>
            <article className="marketCard">
              <p className="label">{dict.search.market.median}</p>
              <h3>{toMoney(market.summary.median_hammer_price_usd)}</h3>
            </article>
            <article className="marketCard">
              <p className="label">{dict.search.market.average}</p>
              <h3>{toMoney(market.summary.avg_hammer_price_usd)}</h3>
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
                <h3>{toMoney(item.hammer_price_usd)}</h3>
                <p>VIN: {item.vin}</p>
                <p>{dict.search.market.similarity}: {Math.round(item.similarity_score)}%</p>
              </article>
            ))}
          </div>
        </section>
      )}

      {decoded && (
        <section className="panel decoderPanel" id="vin-specs">
          <div className="sectionHead">
            <div>
              <h2>{dict.auto.decoderTitle}</h2>
              <p className="muted">{dict.auto.decoderLead}</p>
            </div>
            <a href={decoded.source_url} className="ghostButton" target="_blank" rel="noreferrer">
              {decoded.source}
            </a>
          </div>
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

      <section className="panel autoSeoSection" id="vin-lots">
        <h2>{dict.auto.lotsTitle}</h2>
        {lots.length === 0 ? (
          <p>No lots found for this VIN.</p>
        ) : (
          <div className="autoSeoLotGrid">
            {lots.map((lot, index) => {
              const lotImages = collectImages([lot]).slice(0, 3);
              return (
                <article key={`${lot.source}-${lot.lot_number}-${index}`} className="autoSeoLotCard">
                  <p className="label">
                    {lot.source} #{lot.lot_number}
                  </p>
                  <h3>{toMoney(lot.hammer_price_usd)}</h3>
                  <p>Status: {lot.status || "-"}</p>
                  <p>Date: {lot.sale_date || "-"}</p>
                  <p>Location: {lot.location || "-"}</p>
                  {lotImages.length > 0 && (
                    <div className="autoSeoThumbs">
                      {lotImages.map((url, imageIndex) => (
                        <a key={`${url}-${imageIndex}`} href={url} target="_blank" rel="noreferrer">
                          <img src={url} alt={`Lot ${lot.lot_number} photo ${imageIndex + 1}`} loading="lazy" />
                        </a>
                      ))}
                    </div>
                  )}
                  {lot.price_events.length > 0 && (
                    <ul className="miniList">
                      {lot.price_events.slice(0, 3).map((event, eventIndex) => (
                        <li key={`${event.event_type}-${event.event_time}-${eventIndex}`}>
                          {event.event_type}: {event.old_value ? `${event.old_value} -> ` : ""}
                          {event.new_value} ({toDate(event.event_time)})
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section className="panel autoSeoSection" id="vin-history">
        <h2>{dict.auto.updateLogTitle}</h2>
        {history.items.length > 0 ? (
          <div className="autoSeoHistory">
            {history.items.map((item) => (
              <article key={item.id} className="autoSeoHistoryItem">
                <p className="label">
                  {item.source} #{item.lot_number}
                </p>
                <h3>{toDate(item.imported_at)}</h3>
                <p>Status: {item.status || "-"}</p>
                <p>Price: {toMoney(item.hammer_price_usd)}</p>
              </article>
            ))}
          </div>
        ) : (
          <p>No import records yet for this VIN.</p>
        )}
      </section>

      <section className="panel autoSeoSection" id="vin-profit">
        <h2>{dict.auto.practicalTitle}</h2>
        <p>
          Do not evaluate the vehicle only by auction price. The real decision starts after logistics, customs, repair,
          certification, and local costs are added to the scenario.
        </p>
        <div className="actions">
          <Link href={`/search?vin=${vin}#toolkit`} className="button">
            {dict.auto.openCalculator}
          </Link>
        </div>
      </section>
    </main>
  );
}
