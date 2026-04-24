import Link from "next/link";

import { fetchBrandModelMenu, fetchSeoPages, modelPageHref, resolveSeoCopy } from "../../lib/seoApi";
import { getServerDictionary } from "../../lib/server-locale";

export const dynamic = "force-dynamic";

export default async function CarsHubPage() {
  const brands = await fetchSeoPages("brand");
  const clusters = await fetchSeoPages("cluster");
  const { dict, locale } = await getServerDictionary();

  return (
    <main className="shell carsHubShell">
      <section className="panel carsHubHero iaaiHero">
        <div className="heroFrame">
          <div className="heroCopy">
            <p className="chip">{dict.cars.hubChip}</p>
            <h1>{dict.cars.hubTitle}</h1>
            <p className="lead">{dict.cars.hubLead}</p>
            <div className="actions">
              <Link href="/search" className="button">
                {dict.cars.openSearch}
              </Link>
              <Link href="/about" className="ghostButton">
                {dict.nav.about}
              </Link>
            </div>
          </div>

          <div className="heroSignal">
            <div className="auctionBoard">
              <p className="label">Catalog Snapshot</p>
              <div className="auctionRow">
                <span>Brands</span>
                <strong>{brands.length}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.cars.modelPages}</span>
                <strong>{clusters.length}</strong>
              </div>
              <div className="auctionRow">
                <span>Source</span>
                <strong>Database</strong>
              </div>
              <div className="auctionRow">
                <span>SEO Layer</span>
                <strong>Managed</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="carsHubGrid">
        {brands.map((brand) => {
          const copy = resolveSeoCopy(brand, locale);
          const models = brand.make ? fetchBrandModelMenu(brand.make).slice(0, 8) : [];
          return (
            <article key={brand.id} className="panel carsHubCard">
              <p className="label">{brand.make}</p>
              <h2>{brand.make}</h2>
              <p>{copy.teaser}</p>
              {models.length > 0 && (
                <div className="modelPillGrid">
                  {models.map((model) => (
                    <Link key={`${brand.make}-${model}`} href={modelPageHref(brand.make || "", model)}>
                      {model}
                    </Link>
                  ))}
                </div>
              )}
              <div className="actions compactActions">
                <Link href={`/cars/${brand.slug_path}`} className="button">
                  {dict.cars.goBrand}
                </Link>
              </div>
            </article>
          );
        })}
      </section>

      <section className="carsHubSection">
        <div className="sectionHead">
          <div>
            <h2>{dict.cars.popularPages}</h2>
            <p className="muted">{dict.cars.popularPagesLead}</p>
          </div>
        </div>
        <div className="carsHubGrid">
        {clusters.map((cluster) => {
          const copy = resolveSeoCopy(cluster, locale);
          return (
            <article key={cluster.id} className="panel carsHubCard">
              <p className="label">
                {cluster.make} {cluster.model} {cluster.year}
              </p>
              <h2>{copy.title}</h2>
              <p>{copy.teaser}</p>
              <div className="actions compactActions">
                <Link href={`/cars/${cluster.slug_path}`} className="button">
                  {dict.cars.openPage}
                </Link>
              </div>
            </article>
          );
        })}
        </div>
      </section>
    </main>
  );
}
