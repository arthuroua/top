import type { MetadataRoute } from "next";
import { fetchSeoPages } from "../lib/seoApi";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const brands = await fetchSeoPages("brand");
  const clusters = await fetchSeoPages("cluster");

  const baseItems: MetadataRoute.Sitemap = [
    {
      url: `${siteUrl}/`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 1
    },
    {
      url: `${siteUrl}/cars`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.85
    }
  ];

  const seoItems: MetadataRoute.Sitemap = [...brands, ...clusters].map((item) => ({
    url: `${siteUrl}/cars/${item.slug_path}`,
    lastModified: item.updated_at ? new Date(item.updated_at) : now,
    changeFrequency: "daily",
    priority: item.page_type === "brand" ? 0.82 : 0.8
  }));

  const uniqueItems = [...baseItems, ...seoItems].filter(
    (item, index, array) => array.findIndex((candidate) => candidate.url === item.url) === index
  );

  return uniqueItems;
}
