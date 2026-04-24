import {
  SEO_BRANDS,
  SEO_CLUSTERS,
  brandHref,
  clusterHref,
  findBrandBySlug,
  findClusterBySlugs,
  findModelBySlugs,
  findModelsForMake,
  getBrandClusters,
  modelHref,
  readableFromSlug,
} from "./seoCatalog";

export type SeoFaqItem = {
  question: string;
  answer: string;
};

export type SeoLocaleContent = {
  title: string | null;
  teaser: string | null;
  body: string | null;
  faq: SeoFaqItem[];
};

export type SeoLocalizedContent = {
  en: SeoLocaleContent;
  uk: SeoLocaleContent;
  ru: SeoLocaleContent;
};

export type SeoPage = {
  id: string;
  page_type: "brand" | "cluster";
  slug_path: string;
  make: string | null;
  model: string | null;
  year: number | null;
  title: string;
  teaser: string;
  body: string | null;
  faq: SeoFaqItem[];
  localized: SeoLocalizedContent;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type SeoPageListResponse = {
  items: SeoPage[];
};

const apiInternalBase =
  process.env.API_INTERNAL_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const seoApiEnabled = process.env.SEO_API_ENABLED === "true";

async function safeJsonFetch<T>(url: string, revalidate: number): Promise<T | null> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 4000);
  try {
    const response = await fetch(url, { next: { revalidate }, signal: controller.signal });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  } finally {
    clearTimeout(timeoutId);
  }
}

function fallbackBrandPages(): SeoPage[] {
  return SEO_BRANDS.map((item, index) => ({
    id: `fallback-brand-${index}`,
    page_type: "brand",
    slug_path: brandHref(item.make).replace(/^\/cars\//, ""),
    make: item.make,
    model: null,
    year: null,
    title: item.title,
    teaser: item.teaser,
    body: null,
    faq: [],
    localized: {
      en: { title: null, teaser: null, body: null, faq: [] },
      uk: { title: item.title, teaser: item.teaser, body: null, faq: [] },
      ru: { title: null, teaser: null, body: null, faq: [] },
    },
    sort_order: index,
    is_active: true,
    created_at: "",
    updated_at: "",
  }));
}

function fallbackClusterPages(): SeoPage[] {
  return SEO_CLUSTERS.map((item, index) => ({
    id: `fallback-cluster-${index}`,
    page_type: "cluster",
    slug_path: clusterHref(item).replace(/^\/cars\//, ""),
    make: item.make,
    model: item.model,
    year: item.year,
    title: item.title,
    teaser: item.teaser,
    body: null,
    faq: [],
    localized: {
      en: { title: null, teaser: null, body: null, faq: [] },
      uk: { title: item.title, teaser: item.teaser, body: null, faq: [] },
      ru: { title: null, teaser: null, body: null, faq: [] },
    },
    sort_order: index,
    is_active: true,
    created_at: "",
    updated_at: "",
  }));
}

export async function fetchSeoPages(pageType?: "brand" | "cluster"): Promise<SeoPage[]> {
  if (!seoApiEnabled) {
    return pageType === "cluster"
      ? fallbackClusterPages()
      : pageType === "brand"
        ? fallbackBrandPages()
        : [...fallbackBrandPages(), ...fallbackClusterPages()];
  }
  const params = new URLSearchParams({ active_only: "true" });
  if (pageType) params.set("page_type", pageType);
  const data = await safeJsonFetch<SeoPageListResponse>(`${apiInternalBase}/api/v1/seo-pages?${params.toString()}`, 300);
  if (data?.items?.length) return data.items;
  return pageType === "cluster"
    ? fallbackClusterPages()
    : pageType === "brand"
      ? fallbackBrandPages()
      : [...fallbackBrandPages(), ...fallbackClusterPages()];
}

export async function fetchSeoPageBySlug(slugPath: string): Promise<SeoPage | null> {
  if (seoApiEnabled) {
    const data = await safeJsonFetch<SeoPage>(
      `${apiInternalBase}/api/v1/seo-pages/${encodeURI(slugPath)}?active_only=true`,
      300
    );
    if (data) return data;
  }

  const fallbackBrand = findBrandBySlug(slugPath);
  if (fallbackBrand) {
    return fallbackBrandPages().find((item) => item.slug_path === slugPath) || null;
  }

  const parts = slugPath.split("/");
  if (parts.length === 3) {
    const year = Number(parts[2]);
    const fallbackCluster = findClusterBySlugs(parts[0], parts[1], year);
    if (fallbackCluster) {
      return (
        fallbackClusterPages().find(
          (item) => item.slug_path === `${parts[0]}/${parts[1]}/${year}` && item.year === year
        ) || null
      );
    }
  }

  return null;
}

export async function fetchBrandClusters(make: string): Promise<SeoPage[]> {
  const items = await fetchSeoPages("cluster");
  const normalized = make.toLowerCase();
  const filtered = items.filter((item) => item.make?.toLowerCase() === normalized);
  if (filtered.length > 0) return filtered;
  return getBrandClusters(make).map((item, index) => ({
    id: `fallback-brand-cluster-${index}`,
    page_type: "cluster",
    slug_path: clusterHref(item).replace(/^\/cars\//, ""),
    make: item.make,
    model: item.model,
    year: item.year,
    title: item.title,
    teaser: item.teaser,
    body: null,
    faq: [],
    localized: {
      en: { title: null, teaser: null, body: null, faq: [] },
      uk: { title: item.title, teaser: item.teaser, body: null, faq: [] },
      ru: { title: null, teaser: null, body: null, faq: [] },
    },
    sort_order: index,
    is_active: true,
    created_at: "",
    updated_at: "",
  }));
}

export function readableMakeFromSlug(slug: string): string {
  return findBrandBySlug(slug)?.make || readableFromSlug(slug);
}

export function readableModelFromSlugs(makeSlug: string, modelSlug: string): string {
  return findModelBySlugs(makeSlug, modelSlug)?.model || readableFromSlug(modelSlug);
}

export function fetchBrandModelMenu(make: string): string[] {
  const direct = findModelsForMake(make);
  const fromClusters = SEO_CLUSTERS.filter((item) => item.make.toLowerCase() === make.toLowerCase()).map(
    (item) => item.model
  );
  return Array.from(new Set([...direct, ...fromClusters]));
}

export function modelPageHref(make: string, model: string): string {
  return modelHref(make, model);
}

export function resolveSeoCopy(page: SeoPage, locale: "en" | "uk" | "ru") {
  const localized = page.localized?.[locale];
  return {
    title: localized?.title || page.title,
    teaser: localized?.teaser || page.teaser,
    body: localized?.body || page.body,
    faq: localized?.faq?.length ? localized.faq : page.faq,
  };
}
