import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { fetchBrandClusters, fetchSeoPageBySlug, readableMakeFromSlug, resolveSeoCopy } from "../../../lib/seoApi";
import { getServerDictionary } from "../../../lib/server-locale";

type PageProps = {
  params: Promise<{
    make: string;
  }>;
};

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

function buildFaq(make: string) {
  return [
    {
      question: `Is importing ${make} from the U.S. profitable?`,
      answer:
        "It depends on the model, year, damage type, and full landed cost. The right decision comes after comparing auction price with logistics, customs, and repair costs."
    },
    {
      question: `What should you check first for ${make}?`,
      answer:
        "Look at entry price, damage type, repeated auction appearances, title status, and local market liquidity before placing a bid."
    },
    {
      question: "Why move from brand pages to model and year pages?",
      answer:
        "Model and year pages give a much tighter market slice, with more relevant comps and better decision support for a specific purchase."
    }
  ];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { make: makeSlug } = await params;
  const page = await fetchSeoPageBySlug(makeSlug);
  const make = page?.make || readableMakeFromSlug(makeSlug);
  const canonical = `/cars/${makeSlug}`;

  return {
    title: `${make} from the U.S. - models and import guide`,
    description: `${make} from the U.S.: model overview, auction guidance, and links to deeper model-year pages and VIN analysis.`,
    alternates: { canonical },
    openGraph: {
      type: "website",
      locale: "en_US",
      url: `${siteUrl}${canonical}`,
      title: `${make} from the U.S. - models and import guide`,
      description: `${make} pages with model navigation, market context, and links to VIN pages.`
    }
  };
}

export default async function BrandPage({ params }: PageProps) {
  const { make: makeSlug } = await params;
  const page = await fetchSeoPageBySlug(makeSlug);
  if (!page || page.page_type !== "brand") {
    notFound();
  }

  const { dict, locale } = await getServerDictionary();
  const make = page.make || readableMakeFromSlug(makeSlug);
  const clusters = await fetchBrandClusters(make);
  const copy = resolveSeoCopy(page, locale);
  const faqItems = copy.faq.length > 0 ? copy.faq : buildFaq(make);

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "CollectionPage",
        "@id": `${siteUrl}/cars/${makeSlug}#collection`,
        url: `${siteUrl}/cars/${makeSlug}`,
        name: `${make} from the U.S.`,
        inLanguage: locale
      },
      {
        "@type": "FAQPage",
        "@id": `${siteUrl}/cars/${makeSlug}#faq`,
        mainEntity: faqItems.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: item.answer
          }
        }))
      }
    ]
  };

  return (
    <main className="shell carsClusterShell">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <section className="panel carsClusterHero iaaiHero">
        <div className="heroFrame">
          <div className="heroCopy">
            <p className="chip">{dict.cars.brandChip}</p>
            <h1>{copy.title}</h1>
            <p className="lead">{copy.body || copy.teaser}</p>
            <div className="actions">
              <Link href="/cars" className="button">
                {dict.cars.brandAll}
              </Link>
              <Link href="/search" className="ghostButton">
                {dict.cars.brandSearch}
              </Link>
            </div>
          </div>

          <div className="heroSignal">
            <div className="auctionBoard">
              <p className="label">{dict.cars.brandSnapshot}</p>
              <div className="auctionRow">
                <span>Brand</span>
                <strong>{make}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.cars.modelPages}</span>
                <strong>{clusters.length}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.cars.status}</span>
                <strong>{page.is_active ? dict.cars.active : dict.cars.paused}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.cars.decisionFlow}</span>
                <strong>Brand to Model to VIN</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="panel carsClusterSection">
        <h2>{make}</h2>
        <p>{copy.teaser}</p>
      </section>

      <section className="panel carsClusterSection">
        <h2>{dict.cars.modelPages}</h2>
        {clusters.length > 0 ? (
          <div className="carsClusterGrid">
            {clusters.map((cluster) => (
              <article key={cluster.id} className="carsClusterCard">
                <p className="label">
                  {cluster.make} {cluster.model} {cluster.year}
                </p>
                <h3>{cluster.title}</h3>
                <p>{cluster.teaser}</p>
                <div className="actions compactActions">
                  <Link href={`/cars/${cluster.slug_path}`} className="button">
                    {dict.cars.openPage}
                  </Link>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p>No prepared model pages yet.</p>
        )}
      </section>

      <section className="panel carsClusterSection">
        <h2>FAQ</h2>
        <div className="faqList">
          {faqItems.map((item) => (
            <article key={item.question} className="faqItem">
              <h3>{item.question}</h3>
              <p>{item.answer}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
