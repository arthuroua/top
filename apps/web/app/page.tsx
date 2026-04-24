"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useI18n } from "../components/i18n-provider";

type RecentVehicle = {
  vin: string;
  make: string | null;
  model: string | null;
  year: number | null;
  title_brand: string | null;
  lot_number: string;
  sale_date: string | null;
  hammer_price_usd: number | null;
  status: string | null;
  location: string | null;
  image_url: string | null;
  updated_at: string;
};

type RecentVehiclesResponse = {
  items: RecentVehicle[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function toMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value);
}

function toVehicleName(item: RecentVehicle): string {
  const parts = [item.year?.toString(), item.make, item.model].filter(Boolean);
  return parts.length > 0 ? parts.join(" ") : item.vin;
}

function toDisplayImageUrl(value: string | null): string | null {
  if (!value) return null;
  if (value.startsWith("/api/")) return `${API_BASE}${value}`;
  if (value.startsWith("http://")) return value.replace("http://", "https://");
  return value;
}

export default function HomePage() {
  const { dict } = useI18n();
  const [query, setQuery] = useState("");
  const [vehicles, setVehicles] = useState<RecentVehicle[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    async function loadRecent() {
      try {
        const response = await fetch(`${API_BASE}/api/v1/vehicles/recent?limit=8`);
        if (!response.ok) return;
        const data = (await response.json()) as RecentVehiclesResponse;
        if (alive) setVehicles(data.items || []);
      } finally {
        if (alive) setLoading(false);
      }
    }
    void loadRecent();
    return () => {
      alive = false;
    };
  }, []);

  const searchHref = useMemo(() => {
    const clean = query.trim();
    return clean ? `/search?query=${encodeURIComponent(clean)}` : "/search";
  }, [query]);

  return (
    <main className="shell homeSimpleShell">
      <section className="homeSearchBand homeSearchMinimal">
        <h1>{dict.home.simpleTitle}</h1>
        <form className="homeSearchForm" action={searchHref}>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={dict.search.placeholder}
            aria-label={dict.search.label}
          />
          <Link href={searchHref} className="button">
            {dict.search.submit}
          </Link>
        </form>
        <div className="homeQuickLinks" aria-label="Quick navigation">
          <Link href="/cars">{dict.nav.catalog}</Link>
          <Link href="/watchlist">{dict.nav.watchlist}</Link>
          <Link href="/reports">{dict.nav.reports}</Link>
        </div>
      </section>

      <section className="recentVehiclesSection">
        <div className="simpleSectionHead">
          <h2>{dict.home.recentTitle}</h2>
          <Link href="/cars" className="ghostButton">
            {dict.nav.catalog}
          </Link>
        </div>

        {loading ? (
          <div className="recentVehiclesGrid">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="recentVehicleCard recentVehicleSkeleton" />
            ))}
          </div>
        ) : vehicles.length > 0 ? (
          <div className="recentVehiclesGrid">
            {vehicles.map((item) => {
              const imageUrl = toDisplayImageUrl(item.image_url);
              return (
                <Link key={`${item.vin}-${item.lot_number}`} href={`/auto/${item.vin}`} className="recentVehicleCard">
                  <div className="recentVehicleImage">
                    {imageUrl ? <img src={imageUrl} alt={toVehicleName(item)} loading="lazy" /> : <span>No photo</span>}
                  </div>
                  <div className="recentVehicleBody">
                    <p className="label">VIN {item.vin}</p>
                    <h3>{toVehicleName(item)}</h3>
                    <div className="recentPrice">
                      <span>{dict.search.boughtFor}</span>
                      <strong>{toMoney(item.hammer_price_usd)}</strong>
                    </div>
                    <div className="recentMeta">
                      <span>#{item.lot_number}</span>
                      <span>{item.status || "-"}</span>
                      <span>{item.location || "-"}</span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="recentEmpty">
            <h3>{dict.home.recentEmptyTitle}</h3>
            <p>{dict.home.recentEmptyLead}</p>
            <Link href="/search" className="button">
              {dict.home.openSearch}
            </Link>
          </div>
        )}
      </section>
    </main>
  );
}
