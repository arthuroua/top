"use client";

import Link from "next/link";

import { LANGUAGE_LABELS, SUPPORTED_LOCALES, type Locale } from "../lib/i18n";
import { useI18n } from "./i18n-provider";

export function SiteHeader() {
  const { locale, setLocale, dict } = useI18n();

  return (
    <header className="siteHeader">
      <div className="siteHeaderInner">
        <Link href="/" className="siteBrand">
          <span>{dict.siteName}</span>
          <small>{dict.siteSubtitle}</small>
        </Link>
        <nav className="siteNav">
          <Link href="/search">{dict.nav.search}</Link>
          <Link href="/cars">{dict.nav.catalog}</Link>
          <Link href="/watchlist">{dict.nav.watchlist}</Link>
          <Link href="/reports">{dict.nav.reports}</Link>
          <Link href="/search#toolkit">{dict.nav.calculator}</Link>
        </nav>
        <div className="localeSwitch" aria-label="Language switcher">
          {SUPPORTED_LOCALES.map((item) => (
            <button
              key={item}
              type="button"
              className={`localePill ${locale === item ? "active" : ""}`}
              onClick={() => setLocale(item as Locale)}
            >
              {LANGUAGE_LABELS[item]}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
