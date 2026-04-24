"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useI18n } from "../../components/i18n-provider";
import { readWatchlist, writeWatchlist, type WatchlistSnapshot } from "../../lib/watchlist";

const API_BASE = "/api/backend";

type VehicleResponse = {
  vin: string;
  make: string | null;
  model: string | null;
  year: number | null;
  title_brand: string | null;
  lots: Array<{
    source: string;
    lot_number: string;
    sale_date: string | null;
    hammer_price_usd: number | null;
    status: string | null;
    location: string | null;
    images: Array<{ image_url: string }>;
  }>;
};

type MarketCompsResponse = {
  summary: {
    count: number;
    avg_hammer_price_usd: number | null;
    median_hammer_price_usd: number | null;
    p25_hammer_price_usd: number | null;
    p75_hammer_price_usd: number | null;
  };
};

type WatchlistCard = {
  saved: WatchlistSnapshot;
  vehicle: VehicleResponse | null;
  market: MarketCompsResponse | null;
};

function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function vehicleName(vehicle: VehicleResponse | null, fallback: string): string {
  if (!vehicle) return fallback;
  const parts = [vehicle.year?.toString(), vehicle.make, vehicle.model].filter(Boolean);
  return parts.length ? parts.join(" ") : fallback;
}

function detectChange(saved: WatchlistSnapshot, vehicle: VehicleResponse | null): boolean {
  const latestLot = vehicle?.lots?.[0];
  if (!latestLot) return false;
  const imageCount = latestLot.images?.length || 0;
  return (
    saved.latestLotNumber !== (latestLot.lot_number || null) ||
    saved.latestStatus !== (latestLot.status || null) ||
    saved.latestBidUsd !== (latestLot.hammer_price_usd || null) ||
    saved.imageCount !== imageCount
  );
}

export default function WatchlistPage() {
  const { dict } = useI18n();
  const [items, setItems] = useState<WatchlistSnapshot[]>([]);
  const [cards, setCards] = useState<WatchlistCard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const sync = () => setItems(readWatchlist());
    sync();
    window.addEventListener("watchlist-updated", sync);
    return () => window.removeEventListener("watchlist-updated", sync);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      const source = readWatchlist();
      if (source.length === 0) {
        if (!cancelled) {
          setCards([]);
          setLoading(false);
        }
        return;
      }

      const nextCards = await Promise.all(
        source.map(async (saved): Promise<WatchlistCard> => {
          const [vehicleRes, marketRes] = await Promise.all([
            fetch(`${API_BASE}/api/v1/vehicles/${saved.vin}`).catch(() => null),
            fetch(`${API_BASE}/api/v1/market/comps?vin=${saved.vin}&limit=8`).catch(() => null)
          ]);

          const vehicle = vehicleRes && vehicleRes.ok ? ((await vehicleRes.json()) as VehicleResponse) : null;
          const market = marketRes && marketRes.ok ? ((await marketRes.json()) as MarketCompsResponse) : null;
          return { saved, vehicle, market };
        })
      );

      if (!cancelled) {
        setCards(nextCards);
        setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [items]);

  const totalChanges = useMemo(
    () => cards.filter((card) => detectChange(card.saved, card.vehicle)).length,
    [cards]
  );

  function removeVin(vin: string) {
    const next = readWatchlist().filter((item) => item.vin !== vin);
    writeWatchlist(next);
  }

  return (
    <main className="shell watchlistShell">
      <section className="panel iaaiHero">
        <div className="heroFrame">
          <div className="heroCopy">
            <p className="chip">{dict.watchlist.chip}</p>
            <h1>{dict.watchlist.title}</h1>
            <p className="lead">{dict.watchlist.lead}</p>
            <div className="actions">
              <Link href="/search" className="button">
                {dict.watchlist.toSearch}
              </Link>
              <Link href="/cars" className="ghostButton">
                {dict.watchlist.toCatalog}
              </Link>
            </div>
          </div>
          <div className="heroSignal">
            <div className="auctionBoard">
              <p className="label">{dict.watchlist.snapshot}</p>
              <div className="auctionRow">
                <span>{dict.watchlist.savedCars}</span>
                <strong>{items.length}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.watchlist.changesDetected}</span>
                <strong>{totalChanges}</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      {loading ? (
        <section className="panel">
          <p>{dict.watchlist.loading}</p>
        </section>
      ) : cards.length === 0 ? (
        <section className="panel">
          <h2>{dict.watchlist.emptyTitle}</h2>
          <p className="lead">{dict.watchlist.emptyLead}</p>
        </section>
      ) : (
        <section className="watchlistGrid">
          {cards.map((card) => {
            const latestLot = card.vehicle?.lots?.[0];
            const changed = detectChange(card.saved, card.vehicle);
            return (
              <article key={card.saved.vin} className="panel watchlistCard">
                <div className="watchlistHeader">
                  <div>
                    <p className="label">VIN</p>
                    <h2>{vehicleName(card.vehicle, card.saved.label)}</h2>
                    <p className="lead">{card.saved.vin}</p>
                  </div>
                  <div className={`riskBadge ${changed ? "risk-medium" : "risk-low"}`}>
                    {changed ? dict.watchlist.changed : dict.watchlist.stable}
                  </div>
                </div>
                <div className="watchlistFacts">
                  <div>
                    <span>{dict.watchlist.latestLot}</span>
                    <strong>{latestLot?.lot_number || card.saved.latestLotNumber || "-"}</strong>
                  </div>
                  <div>
                    <span>{dict.watchlist.status}</span>
                    <strong>{latestLot?.status || card.saved.latestStatus || "-"}</strong>
                  </div>
                  <div>
                    <span>{dict.watchlist.currentBid}</span>
                    <strong>{money(latestLot?.hammer_price_usd ?? card.saved.latestBidUsd)}</strong>
                  </div>
                  <div>
                    <span>{dict.watchlist.lowerBound}</span>
                    <strong>{money(card.market?.summary.p25_hammer_price_usd)}</strong>
                  </div>
                </div>
                <div className="actions compactActions">
                  <Link href={`/auto/${card.saved.vin}`} className="button">
                    {dict.watchlist.openVin}
                  </Link>
                  <Link href={`/search?vin=${card.saved.vin}`} className="ghostButton">
                    {dict.watchlist.openAnalysis}
                  </Link>
                  <button type="button" className="ghostButton" onClick={() => removeVin(card.saved.vin)}>
                    {dict.watchlist.remove}
                  </button>
                </div>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}
