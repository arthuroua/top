"use client";

import { useEffect, useState } from "react";

import { useI18n } from "./i18n-provider";
import { isInWatchlist, toggleWatchlist, type WatchlistSnapshot } from "../lib/watchlist";

export function WatchlistToggle({ snapshot }: { snapshot: WatchlistSnapshot }) {
  const { dict } = useI18n();
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSaved(isInWatchlist(snapshot.vin));
  }, [snapshot.vin]);

  useEffect(() => {
    const sync = () => setSaved(isInWatchlist(snapshot.vin));
    window.addEventListener("watchlist-updated", sync);
    return () => window.removeEventListener("watchlist-updated", sync);
  }, [snapshot.vin]);

  return (
    <button
      type="button"
      className={`ghostButton watchlistButton ${saved ? "watchlistButtonActive dangerButton" : ""}`}
      onClick={() => setSaved(toggleWatchlist(snapshot))}
    >
      {saved ? dict.watchlist.remove : dict.watchlist.add}
    </button>
  );
}
