import type { Metadata } from "next";
import Link from "next/link";

type LocalMarketListing = {
  provider: string;
  listing_id: string;
  title: string | null;
  make: string | null;
  model: string | null;
  year: number | null;
  price_usd: number | null;
  price_uah: number | null;
  mileage_km: number | null;
  fuel_name: string | null;
  gearbox_name: string | null;
  city: string | null;
  region: string | null;
  url: string | null;
  photo_url: string | null;
  image_urls_json: string[];
  is_active: boolean;
  is_sold: boolean | null;
  removal_status: string | null;
  sold_detected_at: string | null;
};

type LocalMarketBucket = {
  label: string;
  min_usd: number | null;
  max_usd: number | null;
  total_count: number;
  sold_count: number;
  removed_count: number;
  avg_price_usd: number | null;
  median_price_usd: number | null;
};

type LocalMarketPeriodStats = {
  days: number;
  total_count: number;
  sold_count: number;
  removed_count: number;
  avg_price_usd: number | null;
  median_price_usd: number | null;
  buckets: LocalMarketBucket[];
};

type LocalMarketStatsResponse = {
  provider: string;
  periods: LocalMarketPeriodStats[];
};

type LocalMarketItemsResponse = {
  items: LocalMarketListing[];
  total_count: number;
};

const API_BASE =
  process.env.API_INTERNAL_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export const metadata: Metadata = {
  title: "Ринок Auto.RIA: що продалось або зникло сьогодні",
  description:
    "Статистика Auto.RIA для імпортерів авто: що зникло з продажу за сьогодні, 7 і 30 днів, фото, ціни та бюджетні діапазони.",
  alternates: {
    canonical: "/local-market"
  },
  openGraph: {
    title: "Ринок Auto.RIA для пригонщиків авто",
    description: "Що продалось або зникло з Auto.RIA, фото авто, ціни та статистика по бюджетах.",
    url: `${SITE_URL}/local-market`
  }
};

function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value);
}

function compactNumber(value: number): string {
  return new Intl.NumberFormat("uk-UA").format(value);
}

function vehicleName(item: LocalMarketListing): string {
  const parts = [item.year?.toString(), item.make, item.model].filter(Boolean);
  return parts.length ? parts.join(" ") : item.title || `Auto.RIA #${item.listing_id}`;
}

function statusLabel(status: string | null): string {
  if (status === "sold") return "Продано";
  if (status === "removed") return "Видалено / знято";
  return "Зникло з ринку";
}

function imageUrl(item: LocalMarketListing): string | null {
  return item.photo_url || item.image_urls_json?.[0] || null;
}

async function loadJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE.replace(/\/$/, "")}${path}`, {
      next: { revalidate: 300 }
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export default async function LocalMarketPage({
  searchParams
}: {
  searchParams: Promise<{ days?: string; status?: string }>;
}) {
  const params = await searchParams;
  const days = [1, 7, 30].includes(Number(params.days)) ? Number(params.days) : 1;
  const status = ["all", "sold", "removed"].includes(params.status || "") ? params.status || "all" : "all";
  const hours = days * 24;

  const [stats, market] = await Promise.all([
    loadJson<LocalMarketStatsResponse>("/api/v1/autoria/stats"),
    loadJson<LocalMarketItemsResponse>(`/api/v1/autoria/market?hours=${hours}&status=${status}&limit=80`)
  ]);

  const selectedStats = stats?.periods.find((item) => item.days === days) || stats?.periods[0] || null;
  const items = market?.items || [];

  return (
    <main className="shell localMarketShell">
      <section className="localMarketHero">
        <div>
          <p className="label">Auto.RIA Market Radar</p>
          <h1>Що продалось або зникло з Auto.RIA</h1>
          <p>
            Сервіс зберігає snapshot активних оголошень і показує, які авто пропали з ринку. Це допомагає бачити
            реальний попит, нижню межу цін і моделі, які швидко забирають покупці.
          </p>
        </div>
        <div className="localMarketHeroCard">
          <span>Період</span>
          <strong>{days === 1 ? "Сьогодні" : `${days} днів`}</strong>
          <small>{statusLabel(status)}</small>
        </div>
      </section>

      <section className="localMarketFilters" aria-label="Market filters">
        <div>
          {[1, 7, 30].map((item) => (
            <Link key={item} href={`/local-market?days=${item}&status=${status}`} className={days === item ? "active" : ""}>
              {item === 1 ? "Сьогодні" : `${item} днів`}
            </Link>
          ))}
        </div>
        <div>
          {[
            ["all", "Всі"],
            ["sold", "Продано"],
            ["removed", "Видалено"]
          ].map(([value, label]) => (
            <Link key={value} href={`/local-market?days=${days}&status=${value}`} className={status === value ? "active" : ""}>
              {label}
            </Link>
          ))}
        </div>
      </section>

      {selectedStats ? (
        <>
          <section className="localMarketStats">
            <article>
              <span>Всього сигналів</span>
              <strong>{compactNumber(selectedStats.total_count)}</strong>
            </article>
            <article>
              <span>Продано</span>
              <strong>{compactNumber(selectedStats.sold_count)}</strong>
            </article>
            <article>
              <span>Видалено / знято</span>
              <strong>{compactNumber(selectedStats.removed_count)}</strong>
            </article>
            <article>
              <span>Медіана ціни</span>
              <strong>{money(selectedStats.median_price_usd)}</strong>
            </article>
          </section>

          <section className="panel localMarketBuckets">
            <div className="simpleSectionHead">
              <div>
                <p className="label">Цінові діапазони</p>
                <h2>Де найбільше руху по бюджету</h2>
              </div>
            </div>
            <div className="localMarketBucketGrid">
              {selectedStats.buckets.map((bucket) => (
                <article key={bucket.label} className={bucket.total_count > 0 ? "hasData" : ""}>
                  <span>{bucket.label}</span>
                  <strong>{bucket.total_count}</strong>
                  <small>
                    {bucket.sold_count} продано · {bucket.removed_count} видалено
                  </small>
                  <em>Медіана {money(bucket.median_price_usd)}</em>
                </article>
              ))}
            </div>
          </section>
        </>
      ) : (
        <section className="panel">
          <h2>Статистика ще не готова</h2>
          <p>Потрібно запустити Auto.RIA snapshot хоча б два рази, щоб побачити, які оголошення зникли.</p>
        </section>
      )}

      <section className="recentVehiclesSection">
        <div className="simpleSectionHead">
          <div>
            <p className="label">Останні сигнали</p>
            <h2>{days === 1 ? "За сьогодні" : `За ${days} днів`}</h2>
          </div>
          <Link href="/ingestion" className="ghostButton">
            Відкрити імпорт
          </Link>
        </div>

        {items.length > 0 ? (
          <div className="localMarketGrid">
            {items.map((item) => {
              const src = imageUrl(item);
              return (
                <article key={`${item.provider}-${item.listing_id}`} className="localMarketCard">
                  <a href={item.url || "#"} target="_blank" rel="noreferrer" className="localMarketImage">
                    {src ? <img src={src} alt={vehicleName(item)} loading="lazy" /> : <span>Без фото</span>}
                  </a>
                  <div className="localMarketCardBody">
                    <p className="label">Auto.RIA #{item.listing_id}</p>
                    <h3>{vehicleName(item)}</h3>
                    <div className={`localMarketStatus ${item.removal_status === "sold" ? "sold" : "removed"}`}>
                      <span>{statusLabel(item.removal_status)}</span>
                      <strong>{money(item.price_usd)}</strong>
                    </div>
                    <div className="recentMeta">
                      <span>{item.city || item.region || "Україна"}</span>
                      <span>{item.mileage_km ? `${compactNumber(item.mileage_km)} км` : "Пробіг -"}</span>
                      <span>{item.fuel_name || "Паливо -"}</span>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="recentEmpty">
            <h3>Поки немає зниклих оголошень</h3>
            <p>Запусти Auto.RIA snapshot зараз і повтори пізніше. Після другого проходу тут з’явиться ринкова динаміка.</p>
            <Link href="/ingestion" className="button">
              Запустити імпорт
            </Link>
          </div>
        )}
      </section>
    </main>
  );
}
