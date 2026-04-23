import type { Metadata } from "next";
import Link from "next/link";
import { cache } from "react";
import { notFound } from "next/navigation";

import { fetchSeoPageBySlug, readableMakeFromSlug, resolveSeoCopy } from "../../../../../lib/seoApi";
import { getServerDictionary } from "../../../../../lib/server-locale";

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
    year: string;
  }>;
};

const apiInternalBase =
  process.env.API_INTERNAL_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
const marketApiEnabled = process.env.MARKET_API_ENABLED === "true";

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

const fetchCompsRaw = cache(async (make: string, model: string, year?: number): Promise<MarketCompsResponse | null> => {
  const params = new URLSearchParams({ make, model, limit: "24" });
  if (year !== undefined) params.set("year", String(year));
  return safeJsonFetch<MarketCompsResponse>(`${apiInternalBase}/api/v1/market/comps?${params.toString()}`, 1800);
});

async function fetchCompsWithFallback(make: string, model: string, year: number) {
  const strict = await fetchCompsRaw(make, model, year);
  if (strict && strict.items.length > 0) return { data: strict, relaxed: false };
  const relaxed = await fetchCompsRaw(make, model);
  if (relaxed && relaxed.items.length > 0) return { data: relaxed, relaxed: true };
  return { data: null, relaxed: false };
}

const fetchComps = cache(async (make: string, model: string, year: number) => fetchCompsWithFallback(make, model, year));

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { make: makeSlug, model: modelSlug, year: yearRaw } = await params;
  const year = Number(yearRaw);
  if (!Number.isInteger(year) || year < 1900 || year > 2100) {
    return { title: "Model page unavailable", robots: { index: false, follow: false } };
  }
  const slugPath = `${makeSlug}/${modelSlug}/${year}`;
  const page = await fetchSeoPageBySlug(slugPath);
  const make = page?.make || readableMakeFromSlug(makeSlug);
  const model = page?.model || modelSlug.replace(/-/g, " ");
  return {
    title: `${make} ${model} ${year} from the U.S.`,
    description: `${make} ${model} ${year}: market comps, pricing guidance, and direct links to VIN pages.`,
    alternates: { canonical: `/cars/${slugPath}` },
    openGraph: {
      type: "article",
      locale: "en_US",
      url: `${siteUrl}/cars/${slugPath}`,
      title: `${make} ${model} ${year} from the U.S.`,
      description: `${make} ${model} ${year}: comps, prices, and VIN-level navigation.`
    }
  };
}

export default async function ClusterPage({ params }: PageProps) {
  const { make: makeSlug, model: modelSlug, year: yearRaw } = await params;
  const year = Number(yearRaw);
  if (!Number.isInteger(year) || year < 1900 || year > 2100) notFound();

  const { dict, locale } = await getServerDictionary();
  const slugPath = `${makeSlug}/${modelSlug}/${year}`;
  const page = await fetchSeoPageBySlug(slugPath);
  if (!page || page.page_type !== "cluster") notFound();
  const copy = resolveSeoCopy(page, locale);

  const make = page.make || readableMakeFromSlug(makeSlug);
  const model = page.model || modelSlug.replace(/-/g, " ");
  const { data, relaxed } = await fetchComps(make, model, year);

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebPage",
        "@id": `${siteUrl}/cars/${slugPath}#page`,
        url: `${siteUrl}/cars/${slugPath}`,
        name: copy.title,
        inLanguage: locale
      }
    ]
  };

  return (
    <main className="shell carsClusterShell">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <section className="panel carsClusterHero iaaiHero">
        <div className="heroFrame">
          <div className="heroCopy">
            <p className="chip">{dict.cars.clusterChip}</p>
            <h1>{copy.title}</h1>
            <p className="lead">{copy.body || copy.teaser}</p>
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
                <strong>{toMoney(data?.summary.median_hammer_price_usd)}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.cars.average}</span>
                <strong>{toMoney(data?.summary.avg_hammer_price_usd)}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.cars.comps}</span>
                <strong>{data?.summary.count ?? 0}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.cars.mode}</span>
                <strong>{relaxed ? dict.cars.expanded : dict.cars.exact}</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="panel carsClusterSection">
        <h2>{dict.cars.marketSales}</h2>
        {!data || data.items.length === 0 ? (
          <p>No open market comps yet for this page.</p>
        ) : (
          <div className="carsClusterGrid">
            {data.items.map((item) => (
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
