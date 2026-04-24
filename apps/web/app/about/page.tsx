import Link from "next/link";

import { getServerDictionary } from "../../lib/server-locale";

export const metadata = {
  title: "About the service",
  alternates: {
    canonical: "/about"
  }
};

export default async function AboutPage() {
  const { dict } = await getServerDictionary();

  return (
    <main className="shell">
      <section className="panel marketHero iaaiHero">
        <div className="heroFrame">
          <div className="heroCopy">
            <p className="chip">{dict.about.chip}</p>
            <h1>{dict.about.title}</h1>
            <p className="lead">{dict.about.lead}</p>
            <div className="actions">
              <Link href="/search" className="button">
                {dict.about.openSearch}
              </Link>
              <Link href="/cars" className="ghostButton">
                {dict.about.openCars}
              </Link>
            </div>
          </div>

          <div className="heroSignal">
            <div className="auctionBoard">
              <p className="label">{dict.about.boardTitle}</p>
              <div className="auctionRow">
                <span>{dict.about.boardSearch}</span>
                <strong>VIN / Lot / URL</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.about.boardHistory}</span>
                <strong>{dict.about.boardHistoryValue}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.about.boardDecision}</span>
                <strong>{dict.about.boardDecisionValue}</strong>
              </div>
              <div className="auctionRow">
                <span>{dict.about.boardAudience}</span>
                <strong>{dict.about.boardAudienceValue}</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="featureGrid">
        {dict.about.blocks.map((block) => (
          <article key={block.title} className="panel featureCard featureAccentBlue">
            <p className="label">{dict.about.blockLabel}</p>
            <h3>{block.title}</h3>
            <p>{block.text}</p>
          </article>
        ))}
      </section>

      <section className="panel">
        <div className="sectionHead">
          <div>
            <p className="chip">{dict.about.contactsChip}</p>
            <h2>{dict.about.contactsTitle}</h2>
          </div>
        </div>
        <div className="contactGrid">
          <article className="contactCard">
            <span>{dict.about.contactEmail}</span>
            <a href="mailto:arthuroua@gmail.com">arthuroua@gmail.com</a>
          </article>
          <article className="contactCard">
            <span>{dict.about.contactFacebook}</span>
            <a href="https://www.facebook.com/profile.php?id=61584851876118" target="_blank" rel="noreferrer">
              Filiia Liube Auto
            </a>
          </article>
          <article className="contactCard">
            <span>{dict.about.contactCountry}</span>
            <strong>Ukraine</strong>
          </article>
        </div>
      </section>
    </main>
  );
}
