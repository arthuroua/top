import type { Metadata } from "next";
import Link from "next/link";
import { cache } from "react";
import { notFound } from "next/navigation";

import { fetchBrandClusters, readableMakeFromSlug, readableModelFromSlugs } from "../../../../lib/seoApi";
import { getServerDictionary } from "../../../../lib/server-locale";

type MarketCompItem = {
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
};

type MarketCompsResponse = {
  summary: {
    count: number;
    avg_hammer_price_usd: number | null;
    median_hammer_price_usd: number | null;
  };
  items: MarketCompItem[];
};

type PageProps = {
  params: Promise<{
    make: string;
    model: string;
  }>;
};

const apiInternalBase =
  process.env.API_INTERNAL_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
const marketApiEnabled = process.env.MARKET_API_ENABLED !== "false";

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
  return parsed.toLocaleDateString();
}

async function safeJsonFetch<T>(url: string, revalidate: number): Promise<T | null> {
  if (!marketApiEnabled) return null;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 4000);
  try {
    const response = await fetch(url, { next: { revalidate }, signal: controller.signal });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  } finally {
    clearTimeout(timeoutId);
  }
}

const fetchComps = cache(async (make: string, model: string) => {
  const params = new URLSearchParams({ make, model, limit: "24" });
  return safeJsonFetch<MarketCompsResponse>(`${apiInternalBase}/api/v1/market/comps?${params.toString()}`, 1800);
});

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { make: makeSlug, model: modelSlug } = await params;
  const make = readableMakeFromSlug(makeSlug);
  const model = readableModelFromSlugs(makeSlug, modelSlug);
  const canonical = `/cars/${makeSlug}/${modelSlug}`;
  return {
    title: `${make} ${model} from the U.S. - auction prices and VIN pages`,
    description: `${make} ${model}: auction lots, price guidance, model years, and VIN-level import analysis.`,
    alternates: { canonical },
    openGraph: {
      type: "website",
      locale: "en_US",
      url: `${siteUrl}${canonical}`,
      title: `${make} ${model} from the U.S.`,
      description: `${make} ${model}: auction prices, model years, and VIN analysis.`
    }
  };
}

export default async function ModelPage({ params }: PageProps) {
  const { make: makeSlug, model: modelSlug } = await params;
  const { dict, locale } = await getServerDictionary();
  const make = readableMakeFromSlug(makeSlug);
  const model = readableModelFromSlugs(makeSlug, modelSlug);
  const clusters = (await fetchBrandClusters(make)).filter(
    (item) => item.model?.toLowerCase() === model.toLowerCase()
  );
  const market = await fetchComps(make, model);

  if (!model) notFound();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    url: `${siteUrl}/cars/${makeSlug}/${modelSlug}`,
    name: `${make} ${model}`,
    inLanguage: locale
  };

  return (
    <main className="shell carsClusterShell">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <section className="panel carsClusterHero iaaiHero">
        <div className="heroFrame">
          <div className="heroCopy">
            <p className="chip">{dict.cars.modelChip}</p>
            <h1>
              {make} {model}
            </h1>
            <p className="lead">{dict.cars.modelLead}</p>
            <div className="actions">
              <Link href="/search" className="button">
                {dict.cars.openSearch}
              </Link>
              <Link href={`/cars/${makeSlug}`} className="ghostButton">
                {dict.cars.goBrand}
              </Link>
            </div>
          </div>

          <div className="heroSignal">
            <div className="auctionBoard">
              <p className="label">{dict.cars.marketSnapshot}</p>
              <div className="auctionRow">
                <span>{dict.cars.median}</span>
                <strong>{toMoney(market?.summary.median_hammer_price_usd)}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.cars.average}</span>
                <strong>{toMoney(market?.summary.avg_hammer_price_usd)}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.cars.comps}</span>
                <strong>{market?.summary.count ?? 0}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.cars.modelPages}</span>
                <strong>{clusters.length}</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="panel carsClusterSection">
        <h2>{dict.cars.yearPages}</h2>
        {clusters.length > 0 ? (
          <div className="modelMenuGrid">
            {clusters.map((cluster) => (
              <Link key={cluster.id} href={`/cars/${cluster.slug_path}`} className="modelMenuCard">
                <span>
                  {cluster.make} {cluster.model}
                </span>
                <strong>{cluster.year}</strong>
              </Link>
            ))}
          </div>
        ) : (
          <p>{dict.cars.noYearPages}</p>
        )}
      </section>

      <section className="panel carsClusterSection">
        <h2>{dict.cars.marketSales}</h2>
        {!market || market.items.length === 0 ? (
          <p>{dict.cars.noMarketSales}</p>
        ) : (
          <div className="carsClusterGrid">
            {market.items.map((item) => (
              <article key={`${item.source}-${item.lot_number}-${item.vin}`} className="carsClusterCard">
                <p className="label">
                  {item.source} #{item.lot_number}
                </p>
                <h3>{toMoney(item.hammer_price_usd)}</h3>
                <p>VIN: {item.vin}</p>
                <p>Date: {toDate(item.sale_date)}</p>
                <p>Location: {item.location || "-"}</p>
                <div className="actions compactActions">
                  <Link href={`/auto/${item.vin}`} className="button">
                    {dict.cars.openVin}
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
