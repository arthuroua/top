"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

type AdvisorPayload = {
  target_sell_price_usd: number;
  desired_margin_usd: number;
  fees_usd: number;
  logistics_usd: number;
  customs_usd: number;
  repair_usd: number;
  local_costs_usd: number;
  risk_buffer_usd: number;
};

type AdvisorScenario = {
  name: string;
  max_bid_usd: number;
};

type AdvisorResponse = {
  total_no_bid_usd: number;
  max_bid_usd: number;
  scenarios: AdvisorScenario[];
};

type AdvisorReportResponse = {
  id: string;
  vin: string;
  assumptions: AdvisorPayload;
  result: AdvisorResponse;
  created_at: string;
};

type ReportShareResponse = {
  id: string;
  report_id: string;
  token: string;
  created_at: string;
  expires_at: string | null;
  revoked_at: string | null;
};

type SharedReportResponse = {
  share: ReportShareResponse;
  report: AdvisorReportResponse;
};

const API_BASE = "/api/backend";

function toMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("uk-UA", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(
    value
  );
}

export default function SharedReportPage() {
  const params = useParams<{ token: string }>();
  const token = typeof params.token === "string" ? params.token : "";

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState<SharedReportResponse | null>(null);

  useEffect(() => {
    async function loadSharedReport() {
      if (!token) return;
      setLoading(true);
      setError("");
      setData(null);

      try {
        const res = await fetch(`${API_BASE}/api/v1/reports/shared/${token}`);
        if (!res.ok) throw new Error("Публічний звіт не знайдено або термін дії завершився");
        const json = (await res.json()) as SharedReportResponse;
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Помилка запиту");
      } finally {
        setLoading(false);
      }
    }

    void loadSharedReport();
  }, [token]);

  const scenarios = useMemo(() => {
    if (!data) return [] as AdvisorScenario[];
    return [...data.report.result.scenarios].sort((a, b) => a.name.localeCompare(b.name));
  }, [data]);

  return (
    <main className="shell">
      <section className="panel">
        <p className="chip">Публічний Звіт</p>
        <h1>Сторінка Для Клієнта</h1>
        <p className="lead">Безпечний доступ за одним посиланням до збереженого розрахунку MaxBid.</p>
        <div className="actions">
          <Link href="/" className="button">
            Головна
          </Link>
        </div>
      </section>

      {loading && (
        <section className="panel">
          <p>Завантаження публічного звіту...</p>
        </section>
      )}

      {error && (
        <section className="panel errorPanel">
          <p>{error}</p>
        </section>
      )}

      {data && (
        <>
          <section className="panel">
            <p className="label">VIN</p>
            <h2>{data.report.vin}</h2>
            <p className="lead">Створено: {new Date(data.report.created_at).toLocaleString()}</p>
            <p className="lead">
              Посилання діє до: {data.share.expires_at ? new Date(data.share.expires_at).toLocaleString() : "Без обмеження"}
            </p>

            <div className="actions compactActions">
              <a
                className="button"
                href={`${API_BASE}/api/v1/reports/${data.report.id}/pdf`}
                target="_blank"
                rel="noreferrer"
              >
                Завантажити PDF
              </a>
            </div>
          </section>

          <section className="stats">
            <article className="panel statCard">
              <p className="label">Max Bid</p>
              <h3>{toMoney(data.report.result.max_bid_usd)}</h3>
            </article>
            <article className="panel statCard">
              <p className="label">Сума Без Ставки</p>
              <h3>{toMoney(data.report.result.total_no_bid_usd)}</h3>
            </article>
            <article className="panel statCard">
              <p className="label">Цільова Ціна Продажу</p>
              <h3>{toMoney(data.report.assumptions.target_sell_price_usd)}</h3>
            </article>
          </section>

          <section className="panel">
            <h2>Сценарії</h2>
            <div className="scenarioGrid">
              {scenarios.map((scenario) => (
                <article key={scenario.name} className="lotCard">
                  <p className="label">{scenario.name}</p>
                  <h3>{toMoney(scenario.max_bid_usd)}</h3>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
