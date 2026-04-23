export type WatchlistSnapshot = {
  vin: string;
  label: string;
  titleBrand: string | null;
  latestLotNumber: string | null;
  latestStatus: string | null;
  latestBidUsd: number | null;
  imageCount: number;
  savedAt: string;
};

const STORAGE_KEY = "auto_import_watchlist_v1";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function readWatchlist(): WatchlistSnapshot[] {
  if (!canUseStorage()) return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as WatchlistSnapshot[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function writeWatchlist(items: WatchlistSnapshot[]): void {
  if (!canUseStorage()) return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event("watchlist-updated"));
}

export function isInWatchlist(vin: string): boolean {
  return readWatchlist().some((item) => item.vin === vin);
}

export function toggleWatchlist(snapshot: WatchlistSnapshot): boolean {
  const items = readWatchlist();
  const exists = items.some((item) => item.vin === snapshot.vin);
  if (exists) {
    writeWatchlist(items.filter((item) => item.vin !== snapshot.vin));
    return false;
  }
  writeWatchlist([snapshot, ...items.filter((item) => item.vin !== snapshot.vin)]);
  return true;
}
