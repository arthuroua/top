"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type Listing = {
  listing_id: string;
  title: string | null;
  make: string | null;
  model: string | null;
  year: number | null;
  price_usd: number | null;
  mileage_km: number | null;
  fuel_name: string | null;
  city: string | null;
  region: string | null;
  url: string | null;
  photo_url: string | null;
  image_urls_json: string[];
  is_active: boolean;
  removal_status: string | null;
  sold_detected_at: string | null;
};

type Bucket = {
  label: string;
  total_count: number;
  sold_count: number;
  removed_count: number;
  median_price_usd: number | null;
};

type Period = {
  days: number;
  total_count: number;
  sold_count: number;
  removed_count: number;
  avg_price_usd: number | null;
  median_price_usd: number | null;
  buckets: Bucket[];
};

type Watch = {
  id: string;
  slug: string;
  name: string;
  search_text: string;
  search_params: string;
  last_run_at: string | null;
  last_active_ids_seen: number;
  last_listings_upserted: number;
  last_sold_or_removed_detected: number;
};

type WatchDetail = {
  watch: Watch;
  stats: { periods: Period[] };
  active_items: Listing[];
  changed_items: Listing[];
};

type SnapshotResult = {
  active_ids_seen: number;
  listings_upserted: number;
  sold_or_removed_detected: number;
  skipped_details: number;
};

const API_BASE = "/api/backend";

function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function vehicleName(item: Listing): string {
  return [item.year?.toString(), item.make, item.model].filter(Boolean).join(" ") || item.title || `Auto.RIA #${item.listing_id}`;
}

function imageUrl(item: Listing): string | null {
  return item.photo_url || item.image_urls_json?.[0] || null;
}

function statusLabel(item: Listing): string {
  if (item.is_active) return "Активне";
  if (item.removal_status === "sold") return "Продано";
  if (item.removal_status === "removed") return "Видалено / знято";
  return "Зникло";
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  try {
    const json = (await response.json()) as { detail?: unknown };
    if (typeof json.detail === "string" && json.detail.trim()) return json.detail;
    if (json.detail) return JSON.stringify(json.detail);
  } catch {
    // keep fallback
  }
  return `${fallback} (HTTP ${response.status})`;
}

function ListingCard({ item }: { item: Listing }) {
  const src = imageUrl(item);
  return (
    <article className="marketWatchCar">
      <a href={item.url || "#"} target="_blank" rel="noreferrer" className="marketWatchImage">
        {src ? <img src={src} alt={vehicleName(item)} loading="lazy" /> : <span>Без фото</span>}
      </a>
      <div className="marketWatchCarBody">
        <p className="label">Auto.RIA #{item.listing_id}</p>
        <h3>{vehicleName(item)}</h3>
        <div className={`marketWatchPrice ${item.is_active ? "active" : item.removal_status || "removed"}`}>
          <span>{statusLabel(item)}</span>
          <strong>{money(item.price_usd)}</strong>
        </div>
        <div className="recentMeta">
          <span>{item.city || item.region || "Україна"}</span>
          <span>{item.mileage_km ? `${new Intl.NumberFormat("uk-UA").format(item.mileage_km)} км` : "Пробіг -"}</span>
          <span>{item.fuel_name || "Паливо -"}</span>
        </div>
      </div>
    </article>
  );
}

export default function MarketWatchPage() {
  const [adminToken, setAdminToken] = useState("");
  const [searchText, setSearchText] = useState("Ford Edge 2020");
  const [watches, setWatches] = useState<Watch[]>([]);
  const [selectedSlug, setSelectedSlug] = useState("");
  const [detail, setDetail] = useState<WatchDetail | null>(null);
  const [result, setResult] = useState<SnapshotResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    try {
      setAdminToken(window.localStorage.getItem("adminToken") || "");
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (adminToken.trim()) void loadWatches(adminToken);
  }, [adminToken]);

  useEffect(() => {
    if (selectedSlug && adminToken.trim()) void loadDetail(selectedSlug, adminToken);
  }, [selectedSlug, adminToken]);

  const period = useMemo(() => detail?.stats.periods.find((item) => item.days === 30) || detail?.stats.periods[0], [detail]);

  async function loadWatches(token = adminToken) {
    if (!token.trim()) return;
    const response = await fetch(`${API_BASE}/api/v1/autoria/watches`, {
      cache: "no-store",
      headers: { "X-Admin-Token": token.trim() }
    });
    if (!response.ok) return;
    const json = (await response.json()) as Watch[];
    setWatches(json);
    if (!selectedSlug && json[0]) setSelectedSlug(json[0].slug);
  }

  async function loadDetail(slug: string, token = adminToken) {
    if (!token.trim()) return;
    const response = await fetch(`${API_BASE}/api/v1/autoria/watches/${encodeURIComponent(slug)}`, {
      cache: "no-store",
      headers: { "X-Admin-Token": token.trim() }
    });
    if (!response.ok) return;
    const json = (await response.json()) as WatchDetail;
    setDetail(json);
  }

  async function createWatch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);
    try {
      window.localStorage.setItem("adminToken", adminToken);
      const response = await fetch(`${API_BASE}/api/v1/autoria/watches`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": adminToken.trim()
        },
        body: JSON.stringify({ search_text: searchText })
      });
      if (!response.ok) throw new Error(await readApiError(response, "Не вдалося створити watch"));
      const watch = (await response.json()) as Watch;
      await loadWatches(adminToken);
      setSelectedSlug(watch.slug);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  async function runSelectedWatch() {
    if (!selectedSlug) return;
    setError("");
    setResult(null);
    setLoading(true);
    try {
      window.localStorage.setItem("adminToken", adminToken);
      const response = await fetch(`${API_BASE}/api/v1/autoria/watches/${encodeURIComponent(selectedSlug)}/run?max_pages=1`, {
        method: "POST",
        headers: { "X-Admin-Token": adminToken.trim() }
      });
      if (!response.ok) throw new Error(await readApiError(response, "Не вдалося запустити watch"));
      const json = (await response.json()) as SnapshotResult;
      setResult(json);
      await loadDetail(selectedSlug, adminToken);
      await loadWatches(adminToken);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell marketWatchShell">
      <section className="marketWatchHero">
        <div>
          <p className="label">Personal Market Watch</p>
          <h1>Слідкуй за конкретним авто на Auto.RIA</h1>
          <p>
            Введи фільтр типу <strong>Ford Edge 2020</strong>. Сервіс збере знайдені авто, покаже середню ціну,
            збере фото і далі буде ловити, що продалось або зникло.
          </p>
        </div>
        <Link href="/local-market" className="ghostButton">
          Загальний ринок
        </Link>
      </section>

      <section className="panel marketWatchControl">
        <form onSubmit={createWatch} className="marketWatchForm">
          <label>
            ADMIN_TOKEN
            <input value={adminToken} onChange={(event) => setAdminToken(event.target.value)} placeholder="твій admin token" />
          </label>
          <label>
            За чим слідкувати
            <input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder="Ford Edge 2020" />
          </label>
          <button type="submit" disabled={loading || !adminToken.trim() || !searchText.trim()}>
            {loading ? "Працюю..." : "Зберегти watch"}
          </button>
        </form>

        <div className="marketWatchPicker">
          <label>
            Мої watch
            <select value={selectedSlug} onChange={(event) => setSelectedSlug(event.target.value)}>
              <option value="">Ще немає watch</option>
              {watches.map((watch) => (
                <option key={watch.id} value={watch.slug}>
                  {watch.name}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={runSelectedWatch} disabled={loading || !adminToken.trim() || !selectedSlug}>
            {loading ? "Сканую..." : "Запустити вибраний watch"}
          </button>
        </div>

        {error && <div className="errorPanel"><p>{error}</p></div>}
        {result && (
          <div className="reportSaved">
            <p className="label">Останній запуск</p>
            <p>Знайдено активних: {result.active_ids_seen}</p>
            <p>Збережено/оновлено: {result.listings_upserted}</p>
            <p>Продано або видалено: {result.sold_or_removed_detected}</p>
          </div>
        )}
      </section>

      {detail && period && (
        <>
          <section className="marketWatchStats">
            <article>
              <span>Активних зараз</span>
              <strong>{detail.active_items.length}</strong>
            </article>
            <article>
              <span>Зникло / продано за 30 днів</span>
              <strong>{period.total_count}</strong>
            </article>
            <article>
              <span>Середня ціна</span>
              <strong>{money(period.avg_price_usd)}</strong>
            </article>
            <article>
              <span>Медіана</span>
              <strong>{money(period.median_price_usd)}</strong>
            </article>
          </section>

          <section className="panel localMarketBuckets">
            <div className="simpleSectionHead">
              <div>
                <p className="label">{detail.watch.name}</p>
                <h2>Ціни по діапазонах</h2>
              </div>
            </div>
            <div className="localMarketBucketGrid">
              {period.buckets.map((bucket) => (
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

          <section className="recentVehiclesSection">
            <div className="simpleSectionHead">
              <div>
                <p className="label">Активні оголошення</p>
                <h2>Що є на Auto.RIA зараз</h2>
              </div>
            </div>
            {detail.active_items.length > 0 ? (
              <div className="marketWatchGrid">
                {detail.active_items.map((item) => <ListingCard key={item.listing_id} item={item} />)}
              </div>
            ) : (
              <div className="recentEmpty">
                <h3>Активних авто ще немає</h3>
                <p>Створи watch і запусти його. Після першого проходу тут будуть авто з фото та цінами.</p>
              </div>
            )}
          </section>

          <section className="recentVehiclesSection">
            <div className="simpleSectionHead">
              <div>
                <p className="label">Історія змін</p>
                <h2>Що продалось або зникло</h2>
              </div>
            </div>
            {detail.changed_items.length > 0 ? (
              <div className="marketWatchGrid">
                {detail.changed_items.map((item) => <ListingCard key={item.listing_id} item={item} />)}
              </div>
            ) : (
              <div className="recentEmpty">
                <h3>Поки нічого не зникло</h3>
                <p>Після другого/третього snapshot тут буде видно, що продалось або було видалено з Auto.RIA.</p>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
