"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

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

type ReportPipelineStage = "lead" | "bid" | "won" | "in_transit" | "customs" | "delivered";

type ReportPipelineResponse = {
  report_id: string;
  stage: ReportPipelineStage;
  note: string | null;
  updated_at: string;
};

type AdvisorReportResponse = {
  id: string;
  vin: string;
  assumptions: AdvisorPayload;
  result: AdvisorResponse;
  created_at: string;
  pipeline: ReportPipelineResponse | null;
};

type ReportShareResponse = {
  id: string;
  report_id: string;
  token: string;
  created_at: string;
  expires_at: string | null;
  revoked_at: string | null;
};

const API_BASE = "/api/backend";
const PIPELINE_STAGES: ReportPipelineStage[] = ["lead", "bid", "won", "in_transit", "customs", "delivered"];

function toMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("uk-UA", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(
    value
  );
}

function formatStage(stage: ReportPipelineStage): string {
  const map: Record<ReportPipelineStage, string> = {
    lead: "Лід",
    bid: "План ставки",
    won: "Виграно",
    in_transit: "У дорозі",
    customs: "Митниця",
    delivered: "Доставлено"
  };
  return map[stage];
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  try {
    const json = (await response.json()) as { detail?: unknown };
    if (typeof json.detail === "string" && json.detail.trim()) {
      return json.detail;
    }
  } catch {
    // ignore parse errors
  }
  return fallback;
}

export default function ReportsPage() {
  const [vinFilter, setVinFilter] = useState("");
  const [reports, setReports] = useState<AdvisorReportResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [creatingShareId, setCreatingShareId] = useState<string | null>(null);
  const [pipelineSavingId, setPipelineSavingId] = useState<string | null>(null);
  const [shareByReportId, setShareByReportId] = useState<Record<string, ReportShareResponse>>({});
  const [pipelineDraftByReportId, setPipelineDraftByReportId] = useState<Record<string, ReportPipelineStage>>({});
  const [shareMessage, setShareMessage] = useState("");
  const [pipelineMessage, setPipelineMessage] = useState("");

  const fetchReports = useCallback(async (vin?: string) => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams();
      params.set("limit", "50");
      if (vin && vin.trim().length > 0) {
        params.set("vin", vin.trim().toUpperCase());
      }

      const res = await fetch(`${API_BASE}/api/v1/reports?${params.toString()}`);
      if (!res.ok) throw new Error(await readApiError(res, "Не вдалося завантажити звіти"));

      const json = (await res.json()) as AdvisorReportResponse[];
      setReports(json);
      setShareByReportId({});
      setPipelineDraftByReportId(
        json.reduce<Record<string, ReportPipelineStage>>((acc, report) => {
          acc[report.id] = report.pipeline?.stage || "lead";
          return acc;
        }, {})
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Помилка запиту");
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const vin = params.get("vin");
    if (!vin) {
      void fetchReports();
      return;
    }

    const normalized = vin.toUpperCase();
    setVinFilter(normalized);
    void fetchReports(normalized);
  }, [fetchReports]);

  const reportCountLabel = useMemo(() => {
    if (loading) return "Завантаження звітів...";
    return `${reports.length} звіт${reports.length === 1 ? "" : "ів"}`;
  }, [loading, reports.length]);

  async function onFilterSubmit(e: React.FormEvent) {
    e.preventDefault();
    const normalized = vinFilter.trim().toUpperCase();

    if (normalized.length > 0 && normalized.length !== 17) {
      setError("Фільтр VIN має містити 17 символів.");
      return;
    }

    await fetchReports(normalized);
  }

  async function onClearFilter() {
    setVinFilter("");
    await fetchReports();
  }

  function setPipelineDraft(reportId: string, stage: ReportPipelineStage) {
    setPipelineDraftByReportId((prev) => ({
      ...prev,
      [reportId]: stage
    }));
  }

  async function savePipeline(reportId: string) {
    const stage = pipelineDraftByReportId[reportId] || "lead";
    setPipelineSavingId(reportId);
    setError("");
    setPipelineMessage("");

    try {
      const res = await fetch(`${API_BASE}/api/v1/reports/${reportId}/pipeline`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage })
      });

      if (!res.ok) throw new Error(await readApiError(res, "Не вдалося оновити етап воронки"));
      const pipeline = (await res.json()) as ReportPipelineResponse;

      setReports((prev) =>
        prev.map((item) => {
          if (item.id !== reportId) return item;
          return { ...item, pipeline };
        })
      );
      setPipelineMessage(`Етап збережено: ${formatStage(stage)}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Помилка збереження етапу");
    } finally {
      setPipelineSavingId(null);
    }
  }

  async function createShare(reportId: string) {
    setCreatingShareId(reportId);
    setError("");
    setShareMessage("");

    try {
      const res = await fetch(`${API_BASE}/api/v1/reports/${reportId}/share`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expires_in_days: 30 })
      });

      if (!res.ok) throw new Error(await readApiError(res, "Не вдалося створити публічне посилання"));
      const json = (await res.json()) as ReportShareResponse;
      setShareByReportId((prev) => ({ ...prev, [reportId]: json }));
      setShareMessage("Публічне посилання створено. Можна копіювати.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Помилка створення посилання");
    } finally {
      setCreatingShareId(null);
    }
  }

  async function copyShareLink(shareToken: string) {
      const url = `${window.location.origin}/shared/${shareToken}`;
    try {
      await navigator.clipboard.writeText(url);
      setShareMessage("Посилання скопійовано.");
    } catch {
      setShareMessage(`Скопіюйте вручну: ${url}`);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <p className="chip">Робочий Простір Брокера</p>
        <h1>Звіти</h1>
        <p className="lead">Історія збережених MaxBid-звітів з PDF, етапами воронки та публічними посиланнями.</p>

        <div className="actions">
          <Link href="/search" className="button">
            Відкрити Пошук VIN
          </Link>
          <Link href="/" className="button">
            Головна
          </Link>
        </div>
      </section>

      <section className="panel">
        <form className="filterForm" onSubmit={onFilterSubmit}>
          <label htmlFor="vinFilter">Фільтр по VIN</label>
          <div className="searchRow">
            <input
              id="vinFilter"
              value={vinFilter}
              onChange={(e) => setVinFilter(e.target.value)}
              placeholder="Опційно: 17-символьний VIN"
              minLength={0}
              maxLength={17}
            />
            <button type="submit" disabled={loading}>
              {loading ? "Завантаження" : "Застосувати"}
            </button>
          </div>
        </form>

        <div className="actions compactActions">
          <button type="button" onClick={onClearFilter} disabled={loading}>
            Очистити Фільтр
          </button>
          <button type="button" onClick={() => void fetchReports(vinFilter)} disabled={loading}>
            Оновити
          </button>
        </div>

        <p className="lead muted">{reportCountLabel}</p>

        {error && (
          <div className="errorPanel inlineError">
            <p>{error}</p>
          </div>
        )}

        {pipelineMessage && (
          <div className="panel reportSaved">
            <p>{pipelineMessage}</p>
          </div>
        )}

        {shareMessage && (
          <div className="panel reportSaved">
            <p>{shareMessage}</p>
          </div>
        )}
      </section>

      <section className="reportList">
        {reports.map((report) => {
          const share = shareByReportId[report.id];
          const shareUrl = share ? `${typeof window !== "undefined" ? window.location.origin : ""}/shared/${share.token}` : "";
          const stage = pipelineDraftByReportId[report.id] || report.pipeline?.stage || "lead";

          return (
            <article className="panel" key={report.id}>
              <div className="reportHeader">
                <div>
                  <p className="label">VIN</p>
                  <h2>{report.vin}</h2>
                </div>
                <div>
                  <p className="label">Створено</p>
                  <p>{new Date(report.created_at).toLocaleString()}</p>
                </div>
              </div>

              <div className="stats">
                <article className="panel statCard">
                  <p className="label">Max Bid</p>
                  <h3>{toMoney(report.result.max_bid_usd)}</h3>
                </article>
                <article className="panel statCard">
                  <p className="label">Сума Без Ставки</p>
                  <h3>{toMoney(report.result.total_no_bid_usd)}</h3>
                </article>
                <article className="panel statCard">
                  <p className="label">Бажана Маржа</p>
                  <h3>{toMoney(report.assumptions.desired_margin_usd)}</h3>
                </article>
              </div>

              <div className="actions compactActions">
                <label className="inlineControl">
                  Воронка
                  <select value={stage} onChange={(e) => setPipelineDraft(report.id, e.target.value as ReportPipelineStage)}>
                    {PIPELINE_STAGES.map((value) => (
                      <option value={value} key={value}>
                        {formatStage(value)}
                      </option>
                    ))}
                  </select>
                </label>
                <button type="button" onClick={() => void savePipeline(report.id)} disabled={pipelineSavingId === report.id}>
                  {pipelineSavingId === report.id ? "Збереження етапу..." : "Зберегти Етап"}
                </button>
                <a className="button" href={`${API_BASE}/api/v1/reports/${report.id}/pdf`} target="_blank" rel="noreferrer">
                  Завантажити PDF
                </a>
                <button
                  type="button"
                  onClick={() => void createShare(report.id)}
                  disabled={creatingShareId === report.id}
                >
                  {creatingShareId === report.id ? "Створення..." : "Створити Посилання"}
                </button>
              </div>

              <p className="lead muted">
                Етап: {formatStage(stage)}
                {report.pipeline?.updated_at ? ` (оновлено ${new Date(report.pipeline.updated_at).toLocaleString()})` : ""}
              </p>

              {share && (
                <div className="shareBox">
                  <p className="label">Публічний URL (30 днів)</p>
                  <input className="shareInput" value={shareUrl} readOnly />
                  <div className="actions compactActions">
                    <button type="button" onClick={() => void copyShareLink(share.token)}>
                      Копіювати
                    </button>
                    <a className="button" href={shareUrl} target="_blank" rel="noreferrer">
                      Відкрити Публічну Сторінку
                    </a>
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </section>
    </main>
  );
}
