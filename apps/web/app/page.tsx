"use client";

import Link from "next/link";

import { useI18n } from "../components/i18n-provider";

export default function HomePage() {
  const { dict } = useI18n();

  return (
    <main className="shell">
      <section className="panel homeHero iaaiHero">
        <div className="heroFrame">
          <div className="heroCopy">
            <p className="chip">{dict.home.chip}</p>
            <h1>{dict.home.title}</h1>
            <p className="lead">{dict.home.lead}</p>
            <div className="actions">
              <Link href="/search" className="button">
                {dict.home.openSearch}
              </Link>
              <Link href="/cars" className="ghostButton">
                {dict.home.openCatalog}
              </Link>
              <Link href="/search#toolkit" className="ghostButton">
                {dict.home.openCalculator}
              </Link>
            </div>
          </div>

          <div className="heroSignal">
            <div className="auctionBoard">
              <p className="label">Auction Flow</p>
              <div className="auctionRow">
                <span>VIN</span>
                <strong>Decoded</strong>
              </div>
              <div className="auctionRow">
                <span>Photos</span>
                <strong>Stored</strong>
              </div>
              <div className="auctionRow">
                <span>NHTSA</span>
                <strong>Decoded</strong>
              </div>
              <div className="auctionRow">
                <span>Max Bid</span>
                <strong>Calculated</strong>
              </div>
              <div className="signalBanner">Built for brokers, importers, and auction operators.</div>
            </div>
          </div>
        </div>
      </section>

      <section className="featureGrid featureGridWide">
        {dict.home.features.map((feature, index) => (
          <article
            key={feature.title}
            className={`panel featureCard ${index % 2 === 0 ? "featureAccentBlue" : "featureAccentGold"}`}
          >
            <p className="label">0{index + 1}</p>
            <h3>{feature.title}</h3>
            <p>{feature.text}</p>
          </article>
        ))}
      </section>

      <section className="showcaseGrid">
        <article className="panel showcaseCard">
          <p className="chip">Workflow</p>
          <h2>{dict.home.flowTitle}</h2>
          <p>{dict.home.flowLead}</p>
          <div className="actions compactActions">
            <Link href="/cars" className="button">
              {dict.home.flowButton}
            </Link>
          </div>
        </article>

        <article className="panel showcaseCard darkShowcase">
          <p className="chip">Why It Wins</p>
          <h2>{dict.home.edgeTitle}</h2>
          <p>{dict.home.edgeLead}</p>
        </article>
      </section>
    </main>
  );
}
