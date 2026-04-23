import { cookies } from "next/headers";

import { LOCALE_COOKIE, getDictionary, normalizeLocale } from "./i18n";

export async function getServerLocale() {
  const cookieStore = await cookies();
  return normalizeLocale(cookieStore.get(LOCALE_COOKIE)?.value);
}

export async function getServerDictionary() {
  const locale = await getServerLocale();
  return { locale, dict: getDictionary(locale) };
}
