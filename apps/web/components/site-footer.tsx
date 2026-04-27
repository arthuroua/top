"use client";

import Link from "next/link";

import { useI18n } from "./i18n-provider";

export function SiteFooter() {
  const { dict } = useI18n();
  const year = new Date().getFullYear();

  return (
    <footer className="siteFooter">
      <div className="siteFooterInner">
        <div className="footerBrand">
          <strong>{dict.siteName}</strong>
          <p>{dict.footer.tagline}</p>
        </div>
        <nav className="footerLinks" aria-label="Footer navigation">
          <Link href="/search">{dict.nav.search}</Link>
          <Link href="/cars">{dict.nav.catalog}</Link>
          <Link href="/watchlist">{dict.nav.watchlist}</Link>
          <Link href="/about">{dict.nav.about}</Link>
        </nav>
        <div className="footerLegal">
          <p>{dict.footer.disclaimer}</p>
          <p>{dict.footer.notice}</p>
          <small>© {year} {dict.siteName}. {dict.footer.rights}</small>
        </div>
      </div>
    </footer>
  );
}
