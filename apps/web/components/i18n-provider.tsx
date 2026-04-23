"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { DEFAULT_LOCALE, getDictionary, LOCALE_COOKIE, type Locale, normalizeLocale } from "../lib/i18n";

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  dict: ReturnType<typeof getDictionary>;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children, initialLocale }: { children: React.ReactNode; initialLocale: Locale }) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=31536000; samesite=lax`;
  }, [locale]);

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale: (nextLocale) => setLocaleState(normalizeLocale(nextLocale)),
      dict: getDictionary(locale)
    }),
    [locale]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    return {
      locale: DEFAULT_LOCALE,
      setLocale: () => undefined,
      dict: getDictionary(DEFAULT_LOCALE)
    };
  }
  return context;
}
