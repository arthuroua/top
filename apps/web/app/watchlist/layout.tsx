import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Watchlist",
  robots: {
    index: false,
    follow: true
  }
};

export default function WatchlistLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
