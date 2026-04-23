import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "SEO Admin",
  robots: { index: false, follow: false }
};

export default function AdminSeoLayout({ children }: { children: ReactNode }) {
  return children;
}
