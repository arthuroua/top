"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { CarsQuickPicker } from "../components/cars-quick-picker";
import { useI18n } from "../components/i18n-provider";
import { SEO_MODEL_MENU, brandHref } from "../lib/seoCatalog";

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

const API_BASE = "/api/backend";

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
  if (value.startsWith(`${API_BASE}/`)) return value;
  if (value.startsWith("/api/")) return `${API_BASE}${value}`;
  if (value.startsWith("http://")) return value.replace("http://", "https://");
  return value;
}

function isSoldStatus(status: string | null | undefined): boolean {
  const normalized = (status || "").toLowerCase();
  if (
    normalized.includes("on approval") ||
    normalized.includes("on minimum bid") ||
    normalized.includes("minimum bid") ||
    normalized.includes("pure sale")
  ) {
    return false;
  }
  return (
    normalized.includes("sold") ||
    normalized.includes("closed") ||
    normalized.includes("paid") ||
    normalized.includes("won / to be paid") ||
    normalized === "won" ||
    normalized.startsWith("won ")
  );
}

function getPriceLabel(item: RecentVehicle, dict: ReturnType<typeof useI18n>["dict"]): string {
  if (item.hammer_price_usd && isSoldStatus(item.status)) return dict.search.boughtFor;
  if (item.hammer_price_usd) return dict.search.stats.currentBid;
  return dict.search.kpiStatus;
}

function getPriceValue(item: RecentVehicle): string {
  if (item.hammer_price_usd) return toMoney(item.hammer_price_usd);
  return item.status || "-";
}

export default function HomePage() {
  const { dict } = useI18n();
  const [query, setQuery] = useState("");
  const [vehicles, setVehicles] = useState<RecentVehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const quickPickerBrands = useMemo(
    () =>
      SEO_MODEL_MENU.map((item) => ({
        make: item.make,
        slugPath: brandHref(item.make).replace(/^\/cars\//, ""),
        models: item.models
      })),
    []
  );

  useEffect(() => {
    let alive = true;
    async function loadRecent() {
      try {
        const primaryResponse = await fetch(`${API_BASE}/api/v1/vehicles/recent?limit=24`);
        if (!primaryResponse.ok) return;
        const primaryData = (await primaryResponse.json()) as RecentVehiclesResponse;
        const primaryItems = primaryData.items || [];
        const primaryWithPhotos = primaryItems.filter((item) => Boolean(item.image_url));
        if (alive) {
          setVehicles((primaryWithPhotos.length > 0 ? primaryWithPhotos : primaryItems).slice(0, 8));
        }
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

  const toMonogram = (item: RecentVehicle) => {
    const source = [item.make, item.model].filter(Boolean).join(" ").trim() || item.vin;
    return source
      .split(/[\s-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || "")
      .join("");
  };

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

      <CarsQuickPicker
        brands={quickPickerBrands}
        labels={{
          chip: dict.cars.quickChip,
          title: dict.cars.quickTitle,
          lead: dict.cars.quickLead,
          make: dict.cars.quickMake,
          model: dict.cars.quickModel,
          chooseMake: dict.cars.quickChooseMake,
          chooseModel: dict.cars.quickChooseModel,
          openBrand: dict.cars.goBrand,
          openModel: dict.cars.quickOpenModel
        }}
      />

      <section className="recentVehiclesSection">
        <div className="simpleSectionHead">
          <div>
            <h2>{dict.home.recentTitle}</h2>
          </div>
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
                  <div className={`recentVehicleImage ${imageUrl ? "" : "recentVehicleImagePlaceholder"}`}>
                    {imageUrl ? (
                      <img src={imageUrl} alt={toVehicleName(item)} loading="lazy" />
                    ) : (
                      <div className="recentVehicleImageFallback" aria-hidden="true">
                        <strong>{toMonogram(item)}</strong>
                        <span>Photo pending</span>
                      </div>
                    )}
                  </div>
                  <div className="recentVehicleBody">
                    <p className="label">VIN {item.vin}</p>
                    <h3>{toVehicleName(item)}</h3>
                    <div className="recentPrice">
                      <span>{getPriceLabel(item, dict)}</span>
                      <strong>{getPriceValue(item)}</strong>
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

