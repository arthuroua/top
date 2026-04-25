"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

type IngestionForm = {
  source: string;
  vin: string;
  lot_number: string;
  sale_date: string;
  hammer_price_usd: string;
  status: string;
  location: string;
  images_csv: string;
  event_type: string;
  old_value: string;
  new_value: string;
  event_time: string;
};

type IngestionEnqueueResponse = {
  accepted: boolean;
  queue_depth: number;
};

type IngestionQueueDepth = {
  queue_depth: number;
};

type IngestionProcessResult = {
  processed: boolean;
  message: string;
  lot_id?: string | null;
  vin?: string | null;
  source?: string | null;
  lot_number?: string | null;
  images_upserted: number;
  price_events_added: number;
};

type CopartCsvRunResult = {
  source: string;
  downloaded_rows: number;
  valid_rows: number;
  enqueued_rows: number;
  deduped_rows: number;
  skipped_rows: number;
  processed_rows: number;
  queue_depth: number;
  processing_errors: string[];
  started_at: string;
  finished_at: string;
};

type EnrichmentQueueDepth = {
  queue_depth: number;
};

type EnrichmentEnqueueResult = {
  enqueued: number;
  queue_depth: number;
};

type EnrichmentProcessResult = {
  processed: boolean;
  message: string;
  vin?: string | null;
  source?: string | null;
  lot_number?: string | null;
  images_added: number;
};

type AutoRiaSnapshotResult = {
  provider: string;
  query_label: string;
  active_ids_seen: number;
  listings_upserted: number;
  sold_or_removed_detected: number;
  skipped_details: number;
};

type AutoRiaSoldTodayResult = {
  total_count: number;
  items: Array<{
    listing_id: string;
    title: string | null;
    make: string | null;
    model: string | null;
    year: number | null;
    price_usd: number | null;
    mileage_km: number | null;
    city: string | null;
    region: string | null;
    url: string | null;
    sold_detected_at: string | null;
  }>;
};

type ConnectorStatus = {
  provider: "copart" | "iaai";
  mode: string;
  ready: boolean;
  note: string;
};

type ConnectorFetchForm = {
  provider: "copart" | "iaai";
  vin: string;
  lot_number: string;
};

type ConnectorFetchResponse = {
  provider: "copart" | "iaai";
  mode: string;
  source_record_id: string;
  enqueued: boolean;
  queue_depth: number | null;
  run_id: string | null;
  job: {
    source: string;
    vin: string;
    lot_number: string;
    sale_date: string | null;
    hammer_price_usd: number | null;
    status: string | null;
    location: string | null;
    images: string[];
    price_events: Array<{
      event_type: string;
      old_value: string | null;
      new_value: string;
      event_time: string;
    }>;
  };
};

type IngestionRun = {
  id: string;
  provider: "copart" | "iaai";
  mode: string;
  selector: {
    provider: string;
    vin: string | null;
    lot_number: string | null;
    enqueue: boolean;
  };
  request_hash: string;
  source_record_id: string | null;
  response_hash: string | null;
  success: boolean;
  error_message: string | null;
  latency_ms: number;
  enqueued: boolean;
  queue_depth: number | null;
  created_at: string;
  job: {
    source: string;
    vin: string;
    lot_number: string;
  } | null;
};

type AuditFilters = {
  provider: "all" | "copart" | "iaai";
  result: "all" | "failed";
  q: string;
  sort_by: "created_at" | "latency_ms";
  sort_order: "desc" | "asc";
  page_size: 10 | 20 | 50;
};

type IngestionRunsPageResponse = {
  items: IngestionRun[];
  total_count: number;
  page: number;
  page_size: number;
  has_next: boolean;
};

type RunsRefreshSource = "manual" | "auto";

const API_BASE = "/api/backend";
const STORAGE_KEYS = {
  autoRefreshEnabled: "ingestion.auto_refresh_enabled",
  autoRefreshSeconds: "ingestion.auto_refresh_seconds",
  audioSignalEnabled: "ingestion.audio_signal_enabled",
  browserNotificationsEnabled: "ingestion.browser_notifications_enabled",
  adminToken: "ingestion.admin_token"
} as const;

const DEFAULT_FORM: IngestionForm = {
  source: "Copart",
  vin: "2HGFC2F59JH000001",
  lot_number: "A1002003",
  sale_date: "2026-04-13",
  hammer_price_usd: "7400",
  status: "Sold",
  location: "FL - Miami",
  images_csv: "https://img.example/a.jpg, https://img.example/b.jpg",
  event_type: "sold_price",
  old_value: "7000",
  new_value: "7400",
  event_time: "2026-04-13T09:00:00Z"
};

const DEFAULT_AUDIT_FILTERS: AuditFilters = {
  provider: "all",
  result: "all",
  q: "",
  sort_by: "created_at",
  sort_order: "desc",
  page_size: 20
};

function parseCsv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function buildAuditQueryParams(filters: AuditFilters, page?: number): URLSearchParams {
  const params = new URLSearchParams();
  params.set("sort_by", filters.sort_by);
  params.set("sort_order", filters.sort_order);
  if (page !== undefined) {
    params.set("page", String(page));
    params.set("page_size", String(filters.page_size));
  }
  if (filters.provider !== "all") {
    params.set("provider", filters.provider);
  }
  if (filters.result === "failed") {
    params.set("failed_only", "true");
  }
  const query = filters.q.trim();
  if (query) {
    params.set("q", query);
  }
  return params;
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  try {
    const json = (await response.json()) as { detail?: unknown };
    if (typeof json.detail === "string" && json.detail.trim()) {
      return json.detail;
    }
    if (Array.isArray(json.detail)) {
      return json.detail.map((item) => JSON.stringify(item)).join(" | ");
    }
    if (json.detail && typeof json.detail === "object") {
      return JSON.stringify(json.detail);
    }
  } catch {
    // ignore parse errors and return fallback
  }
  return `${fallback} (HTTP ${response.status})`;
}

function readStoredBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === "1" || raw === "true") return true;
    if (raw === "0" || raw === "false") return false;
  } catch {
    // ignore localStorage access errors
  }
  return fallback;
}

function readStoredInterval(key: string, fallback: 15 | 30 | 60): 15 | 30 | 60 {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === "15" || raw === "30" || raw === "60") {
      return Number(raw) as 15 | 30 | 60;
    }
  } catch {
    // ignore localStorage access errors
  }
  return fallback;
}

function writeStoredValue(key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // ignore localStorage access errors
  }
}

function readNotificationPermission(): NotificationPermission | "unsupported" {
  if (typeof window === "undefined") return "unsupported";
  if (!("Notification" in window)) return "unsupported";
  return window.Notification.permission;
}

export default function IngestionPage() {
  const [form, setForm] = useState<IngestionForm>(DEFAULT_FORM);
  const [loadingEnqueue, setLoadingEnqueue] = useState(false);
  const [loadingDepth, setLoadingDepth] = useState(false);
  const [loadingProcess, setLoadingProcess] = useState(false);
  const [loadingCopartCsvRun, setLoadingCopartCsvRun] = useState(false);
  const [loadingEnrichmentDepth, setLoadingEnrichmentDepth] = useState(false);
  const [loadingEnrichmentEnqueue, setLoadingEnrichmentEnqueue] = useState(false);
  const [loadingEnrichmentProcess, setLoadingEnrichmentProcess] = useState(false);
  const [loadingAutoRiaSnapshot, setLoadingAutoRiaSnapshot] = useState(false);
  const [loadingAutoRiaSoldToday, setLoadingAutoRiaSoldToday] = useState(false);

  const [error, setError] = useState("");
  const [enqueueResult, setEnqueueResult] = useState<IngestionEnqueueResponse | null>(null);
  const [depthResult, setDepthResult] = useState<IngestionQueueDepth | null>(null);
  const [processResult, setProcessResult] = useState<IngestionProcessResult | null>(null);
  const [copartCsvResult, setCopartCsvResult] = useState<CopartCsvRunResult | null>(null);
  const [enrichmentDepthResult, setEnrichmentDepthResult] = useState<EnrichmentQueueDepth | null>(null);
  const [enrichmentEnqueueResult, setEnrichmentEnqueueResult] = useState<EnrichmentEnqueueResult | null>(null);
  const [enrichmentProcessResult, setEnrichmentProcessResult] = useState<EnrichmentProcessResult | null>(null);
  const [autoRiaSnapshotResult, setAutoRiaSnapshotResult] = useState<AutoRiaSnapshotResult | null>(null);
  const [autoRiaSoldTodayResult, setAutoRiaSoldTodayResult] = useState<AutoRiaSoldTodayResult | null>(null);
  const [adminToken, setAdminToken] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    try {
      return window.localStorage.getItem(STORAGE_KEYS.adminToken) || "";
    } catch {
      return "";
    }
  });
  const [connectorStatuses, setConnectorStatuses] = useState<ConnectorStatus[]>([]);
  const [loadingConnectorStatus, setLoadingConnectorStatus] = useState(false);
  const [loadingConnectorFetch, setLoadingConnectorFetch] = useState(false);
  const [connectorResult, setConnectorResult] = useState<ConnectorFetchResponse | null>(null);
  const [connectorRuns, setConnectorRuns] = useState<IngestionRun[]>([]);
  const [loadingConnectorRuns, setLoadingConnectorRuns] = useState(false);
  const [connectorForm, setConnectorForm] = useState<ConnectorFetchForm>({
    provider: "copart",
    vin: "1HGCM82633A004352",
    lot_number: ""
  });
  const [auditFilters, setAuditFilters] = useState<AuditFilters>(DEFAULT_AUDIT_FILTERS);
  const [auditPage, setAuditPage] = useState(1);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditHasNext, setAuditHasNext] = useState(false);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState<boolean>(() =>
    readStoredBoolean(STORAGE_KEYS.autoRefreshEnabled, false)
  );
  const [autoRefreshSeconds, setAutoRefreshSeconds] = useState<15 | 30 | 60>(() =>
    readStoredInterval(STORAGE_KEYS.autoRefreshSeconds, 30)
  );
  const [audioSignalEnabled, setAudioSignalEnabled] = useState<boolean>(() =>
    readStoredBoolean(STORAGE_KEYS.audioSignalEnabled, true)
  );
  const [browserNotificationsEnabled, setBrowserNotificationsEnabled] = useState<boolean>(() =>
    readStoredBoolean(STORAGE_KEYS.browserNotificationsEnabled, false)
  );
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission | "unsupported">(
    () => readNotificationPermission()
  );
  const [lastRunsRefreshAt, setLastRunsRefreshAt] = useState<string | null>(null);
  const [refreshNotice, setRefreshNotice] = useState<string>("");
  const [newRunsSignalCount, setNewRunsSignalCount] = useState(0);
  const [signalPulseActive, setSignalPulseActive] = useState(false);
  const latestRunIdsRef = useRef<string[]>([]);
  const audioSignalEnabledRef = useRef(audioSignalEnabled);
  const browserNotificationsEnabledRef = useRef(browserNotificationsEnabled);
  const pulseTimeoutRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  const resetRunsSignal = useCallback(() => {
    setNewRunsSignalCount(0);
    setSignalPulseActive(false);
    if (pulseTimeoutRef.current !== null) {
      window.clearTimeout(pulseTimeoutRef.current);
      pulseTimeoutRef.current = null;
    }
  }, []);

  const triggerRunsSignal = useCallback((count: number) => {
    setNewRunsSignalCount(count);
    setSignalPulseActive(true);
    if (pulseTimeoutRef.current !== null) {
      window.clearTimeout(pulseTimeoutRef.current);
    }
    pulseTimeoutRef.current = window.setTimeout(() => {
      setSignalPulseActive(false);
      pulseTimeoutRef.current = null;
    }, 1400);
  }, []);

  const playSignalBeep = useCallback(async () => {
    if (!audioSignalEnabledRef.current) return;
    if (typeof window === "undefined") return;
    if (typeof window.AudioContext === "undefined") return;
    try {
      if (!audioContextRef.current || audioContextRef.current.state === "closed") {
        audioContextRef.current = new window.AudioContext();
      }
      const audioContext = audioContextRef.current;
      if (!audioContext) return;
      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }

      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      oscillator.type = "triangle";
      oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
      gainNode.gain.setValueAtTime(0.0001, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.08, audioContext.currentTime + 0.01);
      gainNode.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + 0.22);
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.24);
    } catch {
      // Browser autoplay rules may block audio; ignore silently.
    }
  }, []);

  const sendBrowserNotification = useCallback((count: number) => {
    if (typeof window === "undefined") return;
    if (!browserNotificationsEnabledRef.current) return;
    if (!("Notification" in window)) {
      setNotificationPermission("unsupported");
      return;
    }

    const permission = window.Notification.permission;
    setNotificationPermission(permission);
    if (permission !== "granted") {
      setBrowserNotificationsEnabled(false);
      return;
    }

    try {
      const note = new window.Notification("Car Import MVP", {
        body: `Connector audit: +${count} new run${count === 1 ? "" : "s"}.`,
        tag: "connector-runs"
      });
      window.setTimeout(() => note.close(), 7000);
    } catch {
      // Ignore notification failures (browser policy / OS settings).
    }
  }, []);

  useEffect(() => {
    audioSignalEnabledRef.current = audioSignalEnabled;
  }, [audioSignalEnabled]);

  useEffect(() => {
    browserNotificationsEnabledRef.current = browserNotificationsEnabled;
  }, [browserNotificationsEnabled]);

  useEffect(() => {
    setNotificationPermission(readNotificationPermission());
  }, []);

  useEffect(() => {
    writeStoredValue(STORAGE_KEYS.autoRefreshEnabled, autoRefreshEnabled ? "1" : "0");
  }, [autoRefreshEnabled]);

  useEffect(() => {
    writeStoredValue(STORAGE_KEYS.autoRefreshSeconds, String(autoRefreshSeconds));
  }, [autoRefreshSeconds]);

  useEffect(() => {
    writeStoredValue(STORAGE_KEYS.audioSignalEnabled, audioSignalEnabled ? "1" : "0");
  }, [audioSignalEnabled]);

  useEffect(() => {
    writeStoredValue(STORAGE_KEYS.browserNotificationsEnabled, browserNotificationsEnabled ? "1" : "0");
  }, [browserNotificationsEnabled]);

  useEffect(() => {
    writeStoredValue(STORAGE_KEYS.adminToken, adminToken);
  }, [adminToken]);

  useEffect(() => {
    if (notificationPermission === "granted" || notificationPermission === "unsupported") return;
    if (browserNotificationsEnabled) {
      setBrowserNotificationsEnabled(false);
    }
  }, [notificationPermission, browserNotificationsEnabled]);

  useEffect(() => {
    if (autoRefreshEnabled) return;
    setRefreshNotice("");
    resetRunsSignal();
  }, [autoRefreshEnabled, resetRunsSignal]);

  useEffect(() => {
    return () => {
      if (pulseTimeoutRef.current !== null) {
        window.clearTimeout(pulseTimeoutRef.current);
        pulseTimeoutRef.current = null;
      }
      if (audioContextRef.current) {
        void audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    void loadConnectorStatuses();
    void loadConnectorRuns(DEFAULT_AUDIT_FILTERS, 1);
  }, []);

  function setField<K extends keyof IngestionForm>(key: K, value: IngestionForm[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function enqueueJob(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setEnqueueResult(null);

    const payload: Record<string, unknown> = {
      source: form.source.trim(),
      vin: form.vin.trim().toUpperCase(),
      lot_number: form.lot_number.trim(),
      sale_date: form.sale_date || null,
      hammer_price_usd: form.hammer_price_usd ? Number(form.hammer_price_usd) : null,
      status: form.status || null,
      location: form.location || null,
      images: parseCsv(form.images_csv),
      price_events: []
    };

    if (form.event_type.trim() && form.new_value.trim() && form.event_time.trim()) {
      payload.price_events = [
        {
          event_type: form.event_type.trim(),
          old_value: form.old_value.trim() || null,
          new_value: form.new_value.trim(),
          event_time: form.event_time.trim()
        }
      ];
    }

    setLoadingEnqueue(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/ingestion/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(await readApiError(res, "Failed to enqueue job"));
      const json = (await res.json()) as IngestionEnqueueResponse;
      setEnqueueResult(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingEnqueue(false);
    }
  }

  async function checkQueueDepth() {
    setError("");
    setDepthResult(null);
    setLoadingDepth(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/ingestion/queue-depth`);
      if (!res.ok) throw new Error(await readApiError(res, "Failed to fetch queue depth"));
      const json = (await res.json()) as IngestionQueueDepth;
      setDepthResult(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingDepth(false);
    }
  }

  async function processOne() {
    setError("");
    setProcessResult(null);
    setLoadingProcess(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/ingestion/process-one`, {
        method: "POST",
        headers: { "X-Admin-Token": adminToken.trim() }
      });
      if (!res.ok) throw new Error(await readApiError(res, "Failed to process queue"));
      const json = (await res.json()) as IngestionProcessResult;
      setProcessResult(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingProcess(false);
    }
  }

  async function runCopartCsvNow() {
    setError("");
    setCopartCsvResult(null);
    setLoadingCopartCsvRun(true);
    try {
      const params = new URLSearchParams({
        process_immediately: "true",
        max_process: "100"
      });
      const res = await fetch(`${API_BASE}/api/v1/ingestion/copart-csv/run-once?${params.toString()}`, {
        method: "POST",
        headers: { "X-Admin-Token": adminToken.trim() }
      });
      if (!res.ok) throw new Error(await readApiError(res, "Failed to run Copart CSV import"));
      const json = (await res.json()) as CopartCsvRunResult;
      setCopartCsvResult(json);
      await checkQueueDepth();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingCopartCsvRun(false);
    }
  }

  async function runAutoRiaSnapshot() {
    setError("");
    setAutoRiaSnapshotResult(null);
    setLoadingAutoRiaSnapshot(true);
    try {
      const params = new URLSearchParams({ query_label: "ukraine-market", max_pages: "1" });
      const res = await fetch(`${API_BASE}/api/v1/autoria/snapshot?${params.toString()}`, {
        method: "POST",
        headers: { "X-Admin-Token": adminToken.trim() }
      });
      if (!res.ok) throw new Error(await readApiError(res, "Failed to run Auto.RIA snapshot"));
      const json = (await res.json()) as AutoRiaSnapshotResult;
      setAutoRiaSnapshotResult(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingAutoRiaSnapshot(false);
    }
  }

  async function loadAutoRiaSoldToday() {
    setError("");
    setAutoRiaSoldTodayResult(null);
    setLoadingAutoRiaSoldToday(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/autoria/sold-today?hours=24&limit=100`, {
        headers: { "X-Admin-Token": adminToken.trim() }
      });
      if (!res.ok) throw new Error(await readApiError(res, "Failed to load Auto.RIA sold today"));
      const json = (await res.json()) as AutoRiaSoldTodayResult;
      setAutoRiaSoldTodayResult(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingAutoRiaSoldToday(false);
    }
  }

  async function checkEnrichmentQueueDepth() {
    setError("");
    setEnrichmentDepthResult(null);
    setLoadingEnrichmentDepth(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/ingestion/enrichment/queue-depth`);
      if (!res.ok) throw new Error(await readApiError(res, "Failed to fetch enrichment queue depth"));
      const json = (await res.json()) as EnrichmentQueueDepth;
      setEnrichmentDepthResult(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingEnrichmentDepth(false);
    }
  }

  async function enqueueRecentEnrichment() {
    setError("");
    setEnrichmentEnqueueResult(null);
    setLoadingEnrichmentEnqueue(true);
    try {
      const params = new URLSearchParams({ limit: "1000", only_single_image: "true" });
      const res = await fetch(`${API_BASE}/api/v1/ingestion/enrichment/enqueue-recent?${params.toString()}`, {
        method: "POST",
        headers: { "X-Admin-Token": adminToken.trim() }
      });
      if (!res.ok) throw new Error(await readApiError(res, "Failed to enqueue enrichment jobs"));
      const json = (await res.json()) as EnrichmentEnqueueResult;
      setEnrichmentEnqueueResult(json);
      await checkEnrichmentQueueDepth();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingEnrichmentEnqueue(false);
    }
  }

  async function processOneEnrichment() {
    setError("");
    setEnrichmentProcessResult(null);
    setLoadingEnrichmentProcess(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/ingestion/enrichment/process-one`, {
        method: "POST",
        headers: { "X-Admin-Token": adminToken.trim() }
      });
      if (!res.ok) throw new Error(await readApiError(res, "Failed to process enrichment queue"));
      const json = (await res.json()) as EnrichmentProcessResult;
      setEnrichmentProcessResult(json);
      await checkEnrichmentQueueDepth();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingEnrichmentProcess(false);
    }
  }

  function setConnectorField<K extends keyof ConnectorFetchForm>(key: K, value: ConnectorFetchForm[K]) {
    setConnectorForm((prev) => ({ ...prev, [key]: value }));
  }

  function setAuditFilter<K extends keyof AuditFilters>(key: K, value: AuditFilters[K]) {
    setAuditFilters((prev) => ({ ...prev, [key]: value }));
  }

  async function loadConnectorStatuses() {
    setLoadingConnectorStatus(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/ingestion/connectors`);
      if (!res.ok) throw new Error(await readApiError(res, "Failed to load connector statuses"));
      const json = (await res.json()) as ConnectorStatus[];
      setConnectorStatuses(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingConnectorStatus(false);
    }
  }

  const loadConnectorRuns = useCallback(
    async (filters: AuditFilters, page: number, source: RunsRefreshSource = "manual") => {
      const isAuto = source === "auto";
      if (!isAuto) {
        setLoadingConnectorRuns(true);
        setError("");
        setRefreshNotice("");
        resetRunsSignal();
      }

      try {
        const params = buildAuditQueryParams(filters, page);

        const res = await fetch(`${API_BASE}/api/v1/ingestion/runs?${params.toString()}`);
        if (!res.ok) throw new Error(await readApiError(res, "Failed to load connector runs"));
        const json = (await res.json()) as IngestionRunsPageResponse;

        if (isAuto) {
          const previousIds = new Set(latestRunIdsRef.current);
          const newCount = json.items.filter((item) => !previousIds.has(item.id)).length;
          if (newCount > 0) {
            setRefreshNotice(`Auto-refresh: +${newCount} new run${newCount === 1 ? "" : "s"}`);
            triggerRunsSignal(newCount);
            void playSignalBeep();
            sendBrowserNotification(newCount);
          } else {
            setRefreshNotice("Auto-refresh: no new runs");
            resetRunsSignal();
          }
        }

        latestRunIdsRef.current = json.items.map((item) => item.id);
        setConnectorRuns(json.items);
        setAuditPage(json.page);
        setAuditTotal(json.total_count);
        setAuditHasNext(json.has_next);
        setLastRunsRefreshAt(new Date().toISOString());
      } catch (err) {
        const message = err instanceof Error ? err.message : "Request failed";
        if (isAuto) {
          setRefreshNotice(`Auto-refresh error: ${message}`);
          resetRunsSignal();
        } else {
          setError(message);
        }
      } finally {
        if (!isAuto) {
          setLoadingConnectorRuns(false);
        }
      }
    },
    [playSignalBeep, resetRunsSignal, sendBrowserNotification, triggerRunsSignal]
  );

  useEffect(() => {
    if (!autoRefreshEnabled) return;
    const timerId = window.setInterval(() => {
      void loadConnectorRuns(auditFilters, auditPage, "auto");
    }, autoRefreshSeconds * 1000);
    return () => window.clearInterval(timerId);
  }, [autoRefreshEnabled, autoRefreshSeconds, auditFilters, auditPage, loadConnectorRuns]);

  async function applyAuditFilters(e: React.FormEvent) {
    e.preventDefault();
    await loadConnectorRuns(auditFilters, 1);
  }

  async function clearAuditFilters() {
    setAuditFilters(DEFAULT_AUDIT_FILTERS);
    await loadConnectorRuns(DEFAULT_AUDIT_FILTERS, 1);
  }

  async function goToPreviousAuditPage() {
    if (auditPage <= 1) return;
    await loadConnectorRuns(auditFilters, auditPage - 1);
  }

  async function goToNextAuditPage() {
    if (!auditHasNext) return;
    await loadConnectorRuns(auditFilters, auditPage + 1);
  }

  function exportAuditCsv() {
    const params = buildAuditQueryParams(auditFilters);
    params.set("max_rows", "5000");
    const url = `${API_BASE}/api/v1/ingestion/runs/export.csv?${params.toString()}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function fetchFromConnector(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setConnectorResult(null);

    const vin = connectorForm.vin.trim().toUpperCase();
    const lotNumber = connectorForm.lot_number.trim().toUpperCase();

    if (!vin && !lotNumber) {
      setError("Provide VIN or Lot Number for connector fetch.");
      return;
    }

    if (vin && vin.length !== 17) {
      setError("VIN must contain 17 characters.");
      return;
    }

    setLoadingConnectorFetch(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/ingestion/fetch-and-enqueue`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Token": adminToken.trim() },
        body: JSON.stringify({
          provider: connectorForm.provider,
          vin: vin || null,
          lot_number: lotNumber || null,
          enqueue: true
        })
      });
      if (!res.ok) throw new Error(await readApiError(res, "Failed to fetch from connector"));
      const json = (await res.json()) as ConnectorFetchResponse;
      setConnectorResult(json);
      await loadConnectorRuns(auditFilters, 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoadingConnectorFetch(false);
    }
  }

  async function toggleBrowserNotifications() {
    if (typeof window === "undefined" || !("Notification" in window)) {
      setNotificationPermission("unsupported");
      setRefreshNotice("Browser notifications are not supported in this environment.");
      return;
    }

    if (browserNotificationsEnabled) {
      setBrowserNotificationsEnabled(false);
      setRefreshNotice("Browser notifications disabled.");
      return;
    }

    const permissionNow = window.Notification.permission;
    setNotificationPermission(permissionNow);
    if (permissionNow === "granted") {
      setBrowserNotificationsEnabled(true);
      setRefreshNotice("Browser notifications enabled.");
      return;
    }

    if (permissionNow === "denied") {
      setRefreshNotice("Browser notifications are blocked in browser settings.");
      return;
    }

    try {
      const requested = await window.Notification.requestPermission();
      setNotificationPermission(requested);
      if (requested === "granted") {
        setBrowserNotificationsEnabled(true);
        setRefreshNotice("Browser notifications enabled.");
      } else {
        setBrowserNotificationsEnabled(false);
        setRefreshNotice("Notification permission was not granted.");
      }
    } catch {
      setRefreshNotice("Could not request notification permission.");
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <p className="chip">Ingestion Admin</p>
        <h1>Queue Control</h1>
        <p className="lead">Enqueue lot updates, inspect queue depth, and process ingestion jobs manually.</p>
        <label className="adminTokenField">
          Admin token
          <input
            value={adminToken}
            onChange={(event) => setAdminToken(event.target.value)}
            placeholder="Paste ADMIN_TOKEN from Railway variables"
            type="password"
          />
        </label>
        <div className="actions">
          <Link href="/search" className="button">
            Back to VIN Search
          </Link>
        </div>
      </section>

      <section className="panel">
        <h2>Connector Fetch (Copart / IAAI)</h2>
        <p className="lead">Pull a lot snapshot from connector adapter and push it to queue in one click.</p>

        <form className="ingestionForm" onSubmit={fetchFromConnector}>
          <label>
            Provider
            <select
              value={connectorForm.provider}
              onChange={(e) => setConnectorField("provider", e.target.value as "copart" | "iaai")}
            >
              <option value="copart">Copart</option>
              <option value="iaai">IAAI</option>
            </select>
          </label>
          <label>
            VIN (optional)
            <input
              value={connectorForm.vin}
              onChange={(e) => setConnectorField("vin", e.target.value)}
              placeholder="17-char VIN"
              minLength={0}
              maxLength={17}
            />
          </label>
          <label>
            Lot Number (optional)
            <input
              value={connectorForm.lot_number}
              onChange={(e) => setConnectorField("lot_number", e.target.value)}
              placeholder="A1234567"
            />
          </label>

          <div className="advisorActions">
            <button type="submit" disabled={loadingConnectorFetch}>
              {loadingConnectorFetch ? "Fetching" : "Fetch + Enqueue"}
            </button>
          </div>
        </form>

        <div className="actions compactActions">
          <button type="button" onClick={loadConnectorStatuses} disabled={loadingConnectorStatus}>
            {loadingConnectorStatus ? "Loading statuses" : "Refresh Connector Status"}
          </button>
        </div>

        {connectorStatuses.length > 0 && (
          <div className="panel reportSaved">
            <p className="label">Connector Status</p>
            {connectorStatuses.map((item) => (
              <p key={item.provider}>
                {item.provider.toUpperCase()}: mode={item.mode}, ready={String(item.ready)} ({item.note})
              </p>
            ))}
          </div>
        )}

        {connectorResult && (
          <div className="panel reportSaved">
            <p className="label">Connector Result</p>
            <p>Run ID: {connectorResult.run_id || "-"}</p>
            <p>Provider: {connectorResult.provider.toUpperCase()}</p>
            <p>Mode: {connectorResult.mode}</p>
            <p>Record ID: {connectorResult.source_record_id}</p>
            <p>Enqueued: {String(connectorResult.enqueued)}</p>
            <p>Queue depth: {connectorResult.queue_depth ?? "-"}</p>
            <p>VIN: {connectorResult.job.vin}</p>
            <p>
              Lot: {connectorResult.job.source} #{connectorResult.job.lot_number}
            </p>
            <div className="actions compactActions">
              <Link className="button" href={`/search?vin=${connectorResult.job.vin}`}>
                Open VIN in Search
              </Link>
            </div>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Connector Audit Trail</h2>
        <p className="lead">Latest connector runs with status, latency, and error details.</p>
        <form className="ingestionForm" onSubmit={applyAuditFilters}>
          <label>
            Provider
            <select
              value={auditFilters.provider}
              onChange={(e) => setAuditFilter("provider", e.target.value as "all" | "copart" | "iaai")}
            >
              <option value="all">All</option>
              <option value="copart">Copart</option>
              <option value="iaai">IAAI</option>
            </select>
          </label>
          <label>
            Result
            <select
              value={auditFilters.result}
              onChange={(e) => setAuditFilter("result", e.target.value as "all" | "failed")}
            >
              <option value="all">All</option>
              <option value="failed">Failed only</option>
            </select>
          </label>
          <label>
            Sort By
            <select
              value={auditFilters.sort_by}
              onChange={(e) => setAuditFilter("sort_by", e.target.value as "created_at" | "latency_ms")}
            >
              <option value="created_at">Created At</option>
              <option value="latency_ms">Latency</option>
            </select>
          </label>
          <label>
            Order
            <select
              value={auditFilters.sort_order}
              onChange={(e) => setAuditFilter("sort_order", e.target.value as "desc" | "asc")}
            >
              <option value="desc">Newest / Highest</option>
              <option value="asc">Oldest / Lowest</option>
            </select>
          </label>
          <label>
            Page Size
            <select
              value={auditFilters.page_size}
              onChange={(e) => setAuditFilter("page_size", Number(e.target.value) as 10 | 20 | 50)}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </label>
          <label className="fieldWide">
            Search VIN / Lot / Error
            <input
              value={auditFilters.q}
              onChange={(e) => setAuditFilter("q", e.target.value)}
              placeholder="e.g. 1HGCM..., A1234567, timeout"
            />
          </label>
          <div className="advisorActions">
            <button type="submit" disabled={loadingConnectorRuns}>
              {loadingConnectorRuns ? "Applying" : "Apply Filters"}
            </button>
          </div>
        </form>

        <div className="actions compactActions">
          <button type="button" onClick={clearAuditFilters} disabled={loadingConnectorRuns}>
            Clear Filters
          </button>
          <button type="button" onClick={() => void loadConnectorRuns(auditFilters, auditPage)} disabled={loadingConnectorRuns}>
            {loadingConnectorRuns ? "Loading runs" : "Refresh Runs"}
          </button>
          <button type="button" onClick={exportAuditCsv}>
            Export CSV
          </button>
          <button type="button" onClick={goToPreviousAuditPage} disabled={loadingConnectorRuns || auditPage <= 1}>
            Prev
          </button>
          <button type="button" onClick={goToNextAuditPage} disabled={loadingConnectorRuns || !auditHasNext}>
            Next
          </button>
        </div>

        <p className="lead muted">
          Page {auditPage} - Total runs: {auditTotal}
        </p>
        <div className="actions compactActions">
          <button type="button" onClick={() => setAutoRefreshEnabled((prev) => !prev)}>
            Auto Refresh: {autoRefreshEnabled ? "On" : "Off"}
          </button>
          <button type="button" onClick={() => setAudioSignalEnabled((prev) => !prev)}>
            Beep: {audioSignalEnabled ? "On" : "Off"}
          </button>
          <button type="button" onClick={() => void toggleBrowserNotifications()} disabled={notificationPermission === "unsupported"}>
            Browser Notify:{" "}
            {notificationPermission === "unsupported"
              ? "N/A"
              : browserNotificationsEnabled
                ? "On"
                : notificationPermission === "denied"
                  ? "Blocked"
                  : "Off"}
          </button>
          <label className="inlineControl">
            Interval
            <select
              value={autoRefreshSeconds}
              onChange={(e) => setAutoRefreshSeconds(Number(e.target.value) as 15 | 30 | 60)}
              disabled={!autoRefreshEnabled}
            >
              <option value={15}>15 sec</option>
              <option value={30}>30 sec</option>
              <option value={60}>60 sec</option>
            </select>
          </label>
        </div>
        <p className="lead muted">
          Last refresh: {lastRunsRefreshAt ? new Date(lastRunsRefreshAt).toLocaleTimeString() : "-"}
        </p>
        {refreshNotice && <p className="lead muted">{refreshNotice}</p>}
        {newRunsSignalCount > 0 && (
          <div className={`signalBanner ${signalPulseActive ? "signalPulse" : ""}`}>
            New connector runs detected: +{newRunsSignalCount}
          </div>
        )}

        {connectorRuns.length === 0 && <p className="lead muted">No connector runs yet.</p>}

        {connectorRuns.length > 0 && (
          <div className="auditList">
            {connectorRuns.map((run) => (
              <article key={run.id} className={`lotCard ${run.success ? "auditSuccess" : "auditError"}`}>
                <p className="label">
                  {run.provider.toUpperCase()} | {run.mode}
                </p>
                <h3>{run.success ? "Success" : "Failed"}</h3>
                <p>Run ID: {run.id}</p>
                <p>Created: {new Date(run.created_at).toLocaleString()}</p>
                <p>Latency: {run.latency_ms} ms</p>
                <p>VIN: {run.job?.vin || run.selector.vin || "-"}</p>
                <p>Lot: {run.job?.lot_number || run.selector.lot_number || "-"}</p>
                <p>Enqueued: {String(run.enqueued)}</p>
                <p>Queue depth: {run.queue_depth ?? "-"}</p>
                <p>Source record: {run.source_record_id || "-"}</p>
                {!run.success && <p>Error: {run.error_message || "-"}</p>}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Enqueue Job</h2>
        <form className="ingestionForm" onSubmit={enqueueJob}>
          <label>
            Source
            <input value={form.source} onChange={(e) => setField("source", e.target.value)} required />
          </label>
          <label>
            VIN
            <input
              value={form.vin}
              onChange={(e) => setField("vin", e.target.value)}
              minLength={17}
              maxLength={17}
              required
            />
          </label>
          <label>
            Lot Number
            <input value={form.lot_number} onChange={(e) => setField("lot_number", e.target.value)} required />
          </label>
          <label>
            Sale Date
            <input type="date" value={form.sale_date} onChange={(e) => setField("sale_date", e.target.value)} />
          </label>
          <label>
            Hammer Price USD
            <input
              type="number"
              min={0}
              value={form.hammer_price_usd}
              onChange={(e) => setField("hammer_price_usd", e.target.value)}
            />
          </label>
          <label>
            Status
            <input value={form.status} onChange={(e) => setField("status", e.target.value)} />
          </label>
          <label className="fieldWide">
            Location
            <input value={form.location} onChange={(e) => setField("location", e.target.value)} />
          </label>
          <label className="fieldWide">
            Images CSV
            <input
              value={form.images_csv}
              onChange={(e) => setField("images_csv", e.target.value)}
              placeholder="https://img/a.jpg, https://img/b.jpg"
            />
          </label>

          <label>
            Event Type
            <input value={form.event_type} onChange={(e) => setField("event_type", e.target.value)} />
          </label>
          <label>
            Old Value
            <input value={form.old_value} onChange={(e) => setField("old_value", e.target.value)} />
          </label>
          <label>
            New Value
            <input value={form.new_value} onChange={(e) => setField("new_value", e.target.value)} />
          </label>
          <label>
            Event Time (ISO)
            <input
              value={form.event_time}
              onChange={(e) => setField("event_time", e.target.value)}
              placeholder="2026-04-13T09:00:00Z"
            />
          </label>

          <div className="advisorActions">
            <button type="submit" disabled={loadingEnqueue}>
              {loadingEnqueue ? "Enqueueing" : "Enqueue Job"}
            </button>
          </div>
        </form>

        {enqueueResult && (
          <div className="panel reportSaved">
            <p className="label">Enqueue Result</p>
            <p>Accepted: {String(enqueueResult.accepted)}</p>
            <p>Queue depth: {enqueueResult.queue_depth}</p>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Queue Tools</h2>
        <div className="actions">
          <button type="button" onClick={runCopartCsvNow} disabled={loadingCopartCsvRun || !adminToken.trim()}>
            {loadingCopartCsvRun ? "Importing Copart CSV" : "Run Copart CSV Now"}
          </button>
          <button type="button" onClick={checkQueueDepth} disabled={loadingDepth}>
            {loadingDepth ? "Checking" : "Check Queue Depth"}
          </button>
          <button type="button" onClick={processOne} disabled={loadingProcess}>
            {loadingProcess ? "Processing" : "Process One"}
          </button>
          <button type="button" onClick={enqueueRecentEnrichment} disabled={loadingEnrichmentEnqueue || !adminToken.trim()}>
            {loadingEnrichmentEnqueue ? "Enqueueing Enrichment" : "Enqueue Photo Enrichment"}
          </button>
          <button type="button" onClick={checkEnrichmentQueueDepth} disabled={loadingEnrichmentDepth}>
            {loadingEnrichmentDepth ? "Checking Enrichment" : "Check Enrichment Depth"}
          </button>
          <button type="button" onClick={processOneEnrichment} disabled={loadingEnrichmentProcess || !adminToken.trim()}>
            {loadingEnrichmentProcess ? "Enriching One" : "Process One Enrichment"}
          </button>
          <button type="button" onClick={runAutoRiaSnapshot} disabled={loadingAutoRiaSnapshot || !adminToken.trim()}>
            {loadingAutoRiaSnapshot ? "Scanning Auto.RIA" : "Run Auto.RIA Snapshot"}
          </button>
          <button type="button" onClick={loadAutoRiaSoldToday} disabled={loadingAutoRiaSoldToday || !adminToken.trim()}>
            {loadingAutoRiaSoldToday ? "Loading Auto.RIA" : "Auto.RIA Sold Today"}
          </button>
        </div>

        {depthResult && (
          <div className="panel reportSaved">
            <p className="label">Queue Depth</p>
            <h3>{depthResult.queue_depth}</h3>
          </div>
        )}

        {copartCsvResult && (
          <div className="panel reportSaved">
            <p className="label">Copart CSV Import</p>
            <p>Downloaded rows: {copartCsvResult.downloaded_rows}</p>
            <p>Valid rows: {copartCsvResult.valid_rows}</p>
            <p>Enqueued rows: {copartCsvResult.enqueued_rows}</p>
            <p>Processed rows: {copartCsvResult.processed_rows}</p>
            <p>Deduped rows: {copartCsvResult.deduped_rows}</p>
            <p>Skipped rows: {copartCsvResult.skipped_rows}</p>
            <p>Queue depth: {copartCsvResult.queue_depth}</p>
            {copartCsvResult.processing_errors.length > 0 && (
              <p>Errors: {copartCsvResult.processing_errors.join(" | ")}</p>
            )}
          </div>
        )}

        {enrichmentDepthResult && (
          <div className="panel reportSaved">
            <p className="label">Enrichment Queue Depth</p>
            <h3>{enrichmentDepthResult.queue_depth}</h3>
          </div>
        )}

        {enrichmentEnqueueResult && (
          <div className="panel reportSaved">
            <p className="label">Photo Enrichment Enqueue</p>
            <p>Enqueued: {enrichmentEnqueueResult.enqueued}</p>
            <p>Queue depth: {enrichmentEnqueueResult.queue_depth}</p>
          </div>
        )}

        {enrichmentProcessResult && (
          <div className="panel reportSaved">
            <p className="label">Photo Enrichment Result</p>
            <p>Processed: {String(enrichmentProcessResult.processed)}</p>
            <p>Message: {enrichmentProcessResult.message}</p>
            <p>VIN: {enrichmentProcessResult.vin || "-"}</p>
            <p>
              Lot:{" "}
              {enrichmentProcessResult.source && enrichmentProcessResult.lot_number
                ? `${enrichmentProcessResult.source} #${enrichmentProcessResult.lot_number}`
                : "-"}
            </p>
            <p>Images added: {enrichmentProcessResult.images_added}</p>
          </div>
        )}

        {autoRiaSnapshotResult && (
          <div className="panel reportSaved">
            <p className="label">Auto.RIA Snapshot</p>
            <p>Query: {autoRiaSnapshotResult.query_label}</p>
            <p>Active IDs seen: {autoRiaSnapshotResult.active_ids_seen}</p>
            <p>Listings saved/updated: {autoRiaSnapshotResult.listings_upserted}</p>
            <p>Sold or removed detected: {autoRiaSnapshotResult.sold_or_removed_detected}</p>
            <p>Skipped details: {autoRiaSnapshotResult.skipped_details}</p>
          </div>
        )}

        {autoRiaSoldTodayResult && (
          <div className="panel reportSaved">
            <p className="label">Auto.RIA Sold / Removed Last 24h</p>
            <h3>{autoRiaSoldTodayResult.total_count}</h3>
            {autoRiaSoldTodayResult.items.length === 0 && (
              <p>No disappeared listings detected yet. Run at least two snapshots with some time between them.</p>
            )}
            {autoRiaSoldTodayResult.items.slice(0, 12).map((item) => (
              <p key={item.listing_id}>
                {item.year || "-"} {item.make || ""} {item.model || ""} · ${item.price_usd ?? "-"} ·{" "}
                {item.city || item.region || "-"} · {item.url ? <a href={item.url}>open</a> : item.listing_id}
              </p>
            ))}
          </div>
        )}

        {processResult && (
          <div className="panel reportSaved">
            <p className="label">Process Result</p>
            <p>Processed: {String(processResult.processed)}</p>
            <p>Message: {processResult.message}</p>
            <p>VIN: {processResult.vin || "-"}</p>
            <p>Lot: {processResult.source && processResult.lot_number ? `${processResult.source} #${processResult.lot_number}` : "-"}</p>
            <p>Images upserted: {processResult.images_upserted}</p>
            <p>Price events added: {processResult.price_events_added}</p>
          </div>
        )}

        {error && (
          <div className="errorPanel inlineError">
            <p>{error}</p>
          </div>
        )}
      </section>
    </main>
  );
}
