"use client";

import { useMemo, useState } from "react";

type SearchResponse = {
  vin: string;
  lots_found: number;
  latest_status: string;
};

type VehicleResponse = {
  vin: string;
  make: string;
  model: string;
  year: number;
  title_brand: string;
  lots: Array<{
    source: string;
    lot_number: string;
    sale_date: string;
    hammer_price_usd: number;
    status: string;
    location: string;
  }>;
};

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

type AdvisorForm = {
  target_sell_price_usd: string;
  desired_margin_usd: string;
  fees_usd: string;
  logistics_usd: string;
  customs_usd: string;
  repair_usd: string;
  local_costs_usd: string;
  risk_buffer_usd: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const DEFAULT_ADVISOR_FORM: AdvisorForm = {
  target_sell_price_usd: "17000",
  desired_margin_usd: "1800",
  fees_usd: "1100",
  logistics_usd: "1650",
  customs_usd: "2900",
  repair_usd: "2700",
  local_costs_usd: "600",
  risk_buffer_usd: "900"
};

function toMoney(value: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(
    value
  );
}

function toPayload(form: AdvisorForm): AdvisorPayload {
  return {
    target_sell_price_usd: Number(form.target_sell_price_usd),
    desired_margin_usd: Number(form.desired_margin_usd),
    fees_usd: Number(form.fees_usd),
    logistics_usd: Number(form.logistics_usd),
    customs_usd: Number(form.customs_usd),
    repair_usd: Number(form.repair_usd),
    local_costs_usd: Number(form.local_costs_usd),
    risk_buffer_usd: Number(form.risk_buffer_usd)
  };
}

export default function SearchPage() {
  const [vin, setVin] = useState("1HGCM82633A004352");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState<SearchResponse | null>(null);
  const [vehicle, setVehicle] = useState<VehicleResponse | null>(null);

  const [advisorForm, setAdvisorForm] = useState<AdvisorForm>(DEFAULT_ADVISOR_FORM);
  const [advisorLoading, setAdvisorLoading] = useState(false);
  const [advisorError, setAdvisorError] = useState("");
  const [advisorResult, setAdvisorResult] = useState<AdvisorResponse | null>(null);
  const [reportSaving, setReportSaving] = useState(false);
  const [reportError, setReportError] = useState("");
  const [savedReport, setSavedReport] = useState<AdvisorReportResponse | null>(null);

  const advisorScenarioMap = useMemo(() => {
    if (!advisorResult) return new Map<string, number>();
    return new Map(advisorResult.scenarios.map((s) => [s.name, s.max_bid_usd]));
  }, [advisorResult]);

  async function onSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSearch(null);
    setVehicle(null);
    setSavedReport(null);
    setReportError("");

    try {
      const normalizedVin = vin.trim().toUpperCase();

      const sRes = await fetch(`${API_BASE}/api/v1/search?vin=${normalizedVin}`);
      if (!sRes.ok) throw new Error("VIN not found");
      const sJson = (await sRes.json()) as SearchResponse;
      setSearch(sJson);

      const vRes = await fetch(`${API_BASE}/api/v1/vehicles/${normalizedVin}`);
      if (!vRes.ok) throw new Error("Vehicle card not available");
      const vJson = (await vRes.json()) as VehicleResponse;
      setVehicle(vJson);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  function onAdvisorFieldChange(field: keyof AdvisorForm, value: string) {
    setAdvisorForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onAdvisorSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAdvisorLoading(true);
    setAdvisorError("");
    setAdvisorResult(null);
    setSavedReport(null);
    setReportError("");

    const payload = toPayload(advisorForm);
    if (!Number.isFinite(payload.target_sell_price_usd) || payload.target_sell_price_usd <= 0) {
      setAdvisorLoading(false);
      setAdvisorError("Target sell price must be greater than 0.");
      return;
    }

    const fields = Object.entries(payload) as Array<[keyof AdvisorPayload, number]>;
    const hasInvalid = fields.some(([, value]) => !Number.isFinite(value) || value < 0);
    if (hasInvalid) {
      setAdvisorLoading(false);
      setAdvisorError("All cost fields must be valid non-negative numbers.");
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/v1/advisor/calculate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error("Failed to calculate advisor result");
      }

      const json = (await response.json()) as AdvisorResponse;
      setAdvisorResult(json);
    } catch (err) {
      setAdvisorError(err instanceof Error ? err.message : "Advisor request failed");
    } finally {
      setAdvisorLoading(false);
    }
  }

  async function onSaveReport() {
    setReportSaving(true);
    setReportError("");
    setSavedReport(null);

    const normalizedVin = vin.trim().toUpperCase();
    if (normalizedVin.length !== 17) {
      setReportSaving(false);
      setReportError("VIN must contain 17 characters before saving report.");
      return;
    }

    if (!advisorResult) {
      setReportSaving(false);
      setReportError("Run advisor calculation first.");
      return;
    }

    try {
      const assumptions = toPayload(advisorForm);
      const response = await fetch(`${API_BASE}/api/v1/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vin: normalizedVin,
          assumptions,
          result: advisorResult
        })
      });

      if (!response.ok) {
        throw new Error("Failed to save report");
      }

      const json = (await response.json()) as AdvisorReportResponse;
      setSavedReport(json);
    } catch (err) {
      setReportError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setReportSaving(false);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <p className="chip">VIN Intelligence</p>
        <h1>VIN Search</h1>
        <p className="lead">Enter a 17-character VIN to load auction history and sold-price trail.</p>

        <form onSubmit={onSearchSubmit} className="searchForm">
          <label htmlFor="vin">VIN</label>
          <div className="searchRow">
            <input
              id="vin"
              value={vin}
              onChange={(e) => setVin(e.target.value)}
              placeholder="Enter 17-char VIN"
              minLength={17}
              maxLength={17}
              required
            />
            <button type="submit" disabled={loading}>
              {loading ? "Loading" : "Search"}
            </button>
          </div>
        </form>
      </section>

      {error && (
        <section className="panel errorPanel">
          <p>{error}</p>
        </section>
      )}

      {search && (
        <section className="stats">
          <article className="panel statCard">
            <p className="label">VIN</p>
            <h3>{search.vin}</h3>
          </article>
          <article className="panel statCard">
            <p className="label">Lots Found</p>
            <h3>{search.lots_found}</h3>
          </article>
          <article className="panel statCard">
            <p className="label">Latest Status</p>
            <h3>{search.latest_status}</h3>
          </article>
        </section>
      )}

      {vehicle && (
        <section className="panel">
          <p className="label">Vehicle Card</p>
          <h2>
            {vehicle.year} {vehicle.make} {vehicle.model}
          </h2>
          <p className="lead">Title brand: {vehicle.title_brand}</p>

          <div className="lotsGrid">
            {vehicle.lots.map((lot) => (
              <article key={`${lot.source}-${lot.lot_number}`} className="lotCard">
                <p className="label">{lot.source}</p>
                <h3>Lot #{lot.lot_number}</h3>
                <p>Date: {lot.sale_date}</p>
                <p>Price: {toMoney(lot.hammer_price_usd)}</p>
                <p>Status: {lot.status}</p>
                <p>Location: {lot.location}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="panel">
        <p className="chip">Bid Strategy</p>
        <h2>Max Bid Advisor</h2>
        <p className="lead">Fill your cost assumptions and get a safe bid ceiling before auction.</p>

        <form className="advisorForm" onSubmit={onAdvisorSubmit}>
          <label>
            Target sell price (USD)
            <input
              type="number"
              min={1}
              step="100"
              value={advisorForm.target_sell_price_usd}
              onChange={(e) => onAdvisorFieldChange("target_sell_price_usd", e.target.value)}
              required
            />
          </label>
          <label>
            Desired margin (USD)
            <input
              type="number"
              min={0}
              step="50"
              value={advisorForm.desired_margin_usd}
              onChange={(e) => onAdvisorFieldChange("desired_margin_usd", e.target.value)}
              required
            />
          </label>
          <label>
            Auction fees (USD)
            <input
              type="number"
              min={0}
              step="50"
              value={advisorForm.fees_usd}
              onChange={(e) => onAdvisorFieldChange("fees_usd", e.target.value)}
              required
            />
          </label>
          <label>
            Logistics (USD)
            <input
              type="number"
              min={0}
              step="50"
              value={advisorForm.logistics_usd}
              onChange={(e) => onAdvisorFieldChange("logistics_usd", e.target.value)}
              required
            />
          </label>
          <label>
            Customs (USD)
            <input
              type="number"
              min={0}
              step="50"
              value={advisorForm.customs_usd}
              onChange={(e) => onAdvisorFieldChange("customs_usd", e.target.value)}
              required
            />
          </label>
          <label>
            Repair (USD)
            <input
              type="number"
              min={0}
              step="50"
              value={advisorForm.repair_usd}
              onChange={(e) => onAdvisorFieldChange("repair_usd", e.target.value)}
              required
            />
          </label>
          <label>
            Local costs (USD)
            <input
              type="number"
              min={0}
              step="50"
              value={advisorForm.local_costs_usd}
              onChange={(e) => onAdvisorFieldChange("local_costs_usd", e.target.value)}
              required
            />
          </label>
          <label>
            Risk buffer (USD)
            <input
              type="number"
              min={0}
              step="50"
              value={advisorForm.risk_buffer_usd}
              onChange={(e) => onAdvisorFieldChange("risk_buffer_usd", e.target.value)}
              required
            />
          </label>

          <div className="advisorActions">
            <button type="submit" disabled={advisorLoading}>
              {advisorLoading ? "Calculating" : "Calculate Max Bid"}
            </button>
          </div>
        </form>

        {advisorError && (
          <div className="errorPanel inlineError">
            <p>{advisorError}</p>
          </div>
        )}

        {advisorResult && (
          <div className="advisorResult">
            <div className="stats">
              <article className="panel statCard">
                <p className="label">Total No Bid</p>
                <h3>{toMoney(advisorResult.total_no_bid_usd)}</h3>
              </article>
              <article className="panel statCard">
                <p className="label">Max Bid (Base)</p>
                <h3>{toMoney(advisorResult.max_bid_usd)}</h3>
              </article>
              <article className="panel statCard">
                <p className="label">Recommendation</p>
                <h3>{advisorResult.max_bid_usd > 0 ? "Bid <= Base" : "Skip Lot"}</h3>
              </article>
            </div>

            <div className="scenarioGrid">
              <article className="lotCard">
                <p className="label">Low Scenario</p>
                <h3>{toMoney(advisorScenarioMap.get("low") ?? 0)}</h3>
              </article>
              <article className="lotCard">
                <p className="label">Base Scenario</p>
                <h3>{toMoney(advisorScenarioMap.get("base") ?? 0)}</h3>
              </article>
              <article className="lotCard">
                <p className="label">High Scenario</p>
                <h3>{toMoney(advisorScenarioMap.get("high") ?? 0)}</h3>
              </article>
            </div>

            <div className="advisorActions">
              <button type="button" disabled={reportSaving} onClick={onSaveReport}>
                {reportSaving ? "Saving" : "Save Report"}
              </button>
            </div>

            {reportError && (
              <div className="errorPanel inlineError">
                <p>{reportError}</p>
              </div>
            )}

            {savedReport && (
              <div className="panel reportSaved">
                <p className="label">Saved Report</p>
                <h3>Report ID: {savedReport.id}</h3>
                <p>VIN: {savedReport.vin}</p>
                <p>Created: {new Date(savedReport.created_at).toLocaleString()}</p>
                <div className="advisorActions">
                  <a
                    className="button"
                    href={`${API_BASE}/api/v1/reports/${savedReport.id}/pdf`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download PDF
                  </a>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
