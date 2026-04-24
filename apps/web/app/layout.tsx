import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { cookies } from "next/headers";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";

import { I18nProvider } from "../components/i18n-provider";
import { SiteHeader } from "../components/site-header";
import { DEFAULT_LOCALE, LOCALE_COOKIE, getDictionary, normalizeLocale } from "../lib/i18n";

const display = Space_Grotesk({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-display"
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono"
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
const defaultDict = getDictionary(DEFAULT_LOCALE);

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: `${defaultDict.siteName} - VIN search, auction photos, NHTSA specs`,
    template: `%s | ${defaultDict.siteName}`
  },
  description:
    "Vehicle import platform with VIN lookup, auction lot history, NHTSA configuration data, and decision tools for importers.",
  applicationName: defaultDict.siteName,
  openGraph: {
    type: "website",
    locale: "en_US",
    url: siteUrl,
    title: `${defaultDict.siteName} - VIN search, auction photos, NHTSA specs`,
    description:
      "VIN lookup, lot history, official NHTSA VIN decoder, and importer tools for U.S. auction vehicles."
  },
  twitter: {
    card: "summary_large_image",
    title: defaultDict.siteName,
    description: "VIN lookup, auction history, and NHTSA specs for vehicle importers."
  },
  robots: {
    index: true,
    follow: true
  },
  alternates: {
    canonical: "/"
  }
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const cookieStore = await cookies();
  const locale = normalizeLocale(cookieStore.get(LOCALE_COOKIE)?.value);

  return (
    <html lang={locale}>
      <body className={`${display.variable} ${mono.variable}`}>
        <I18nProvider initialLocale={locale}>
          <SiteHeader />
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
