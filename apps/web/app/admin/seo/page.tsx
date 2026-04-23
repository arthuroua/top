"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type SeoFaqItem = {
  question: string;
  answer: string;
};

type SeoLocaleContent = {
  title: string | null;
  teaser: string | null;
  body: string | null;
  faq: SeoFaqItem[];
};

type SeoPage = {
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
  localized: {
    en: SeoLocaleContent;
    uk: SeoLocaleContent;
    ru: SeoLocaleContent;
  };
  sort_order: number;
  is_active: boolean;
};

type SeoPageListResponse = {
  items: SeoPage[];
};

type LocaleFormState = {
  title: string;
  teaser: string;
  body: string;
};

type FormState = {
  page_type: "brand" | "cluster";
  slug_path: string;
  make: string;
  model: string;
  year: string;
  title: string;
  teaser: string;
  body: string;
  faq: SeoFaqItem[];
  localized: {
    en: LocaleFormState;
    uk: LocaleFormState;
    ru: LocaleFormState;
  };
  sort_order: string;
  is_active: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const LOCALES = ["en", "uk", "ru"] as const;

const emptyFaqItem = (): SeoFaqItem => ({ question: "", answer: "" });

const emptyForm: FormState = {
  page_type: "brand",
  slug_path: "",
  make: "",
  model: "",
  year: "",
  title: "",
  teaser: "",
  body: "",
  faq: [emptyFaqItem()],
  localized: {
    en: { title: "", teaser: "", body: "" },
    uk: { title: "", teaser: "", body: "" },
    ru: { title: "", teaser: "", body: "" }
  },
  sort_order: "0",
  is_active: true
};

function mapItemToForm(item: SeoPage): FormState {
  return {
    page_type: item.page_type,
    slug_path: item.slug_path,
    make: item.make || "",
    model: item.model || "",
    year: item.year ? String(item.year) : "",
    title: item.title,
    teaser: item.teaser,
    body: item.body || "",
    faq: item.faq.length > 0 ? item.faq : [emptyFaqItem()],
    localized: {
      en: {
        title: item.localized.en.title || "",
        teaser: item.localized.en.teaser || "",
        body: item.localized.en.body || ""
      },
      uk: {
        title: item.localized.uk.title || "",
        teaser: item.localized.uk.teaser || "",
        body: item.localized.uk.body || ""
      },
      ru: {
        title: item.localized.ru.title || "",
        teaser: item.localized.ru.teaser || "",
        body: item.localized.ru.body || ""
      }
    },
    sort_order: String(item.sort_order),
    is_active: item.is_active
  };
}

export default function AdminSeoPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<SeoPage[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState<FormState>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "brand" | "cluster">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");

  const filteredItems = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return items.filter((item) => {
      if (typeFilter !== "all" && item.page_type !== typeFilter) return false;
      if (statusFilter === "active" && !item.is_active) return false;
      if (statusFilter === "inactive" && item.is_active) return false;
      if (!q) return true;
      return [item.slug_path, item.title, item.teaser, item.make || "", item.model || ""].join(" ").toLowerCase().includes(q);
    });
  }, [items, searchTerm, statusFilter, typeFilter]);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/seo-pages`);
      if (!response.ok) throw new Error("Failed to load SEO pages.");
      const json = (await response.json()) as SeoPageListResponse;
      setItems(json.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchItems();
  }, [fetchItems]);

  function resetForm() {
    setForm(emptyForm);
    setEditingId(null);
  }

  function setLocalizedField(locale: (typeof LOCALES)[number], field: keyof LocaleFormState, value: string) {
    setForm((current) => ({
      ...current,
      localized: {
        ...current.localized,
        [locale]: {
          ...current.localized[locale],
          [field]: value
        }
      }
    }));
  }

  function updateFaq(index: number, patch: Partial<SeoFaqItem>) {
    setForm((current) => ({
      ...current,
      faq: current.faq.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item))
    }));
  }

  function addFaqItem() {
    setForm((current) => ({ ...current, faq: [...current.faq, emptyFaqItem()] }));
  }

  function removeFaqItem(index: number) {
    setForm((current) => {
      const nextFaq = current.faq.filter((_, itemIndex) => itemIndex !== index);
      return { ...current, faq: nextFaq.length > 0 ? nextFaq : [emptyFaqItem()] };
    });
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    const faq = form.faq
      .map((item) => ({ question: item.question.trim(), answer: item.answer.trim() }))
      .filter((item) => item.question && item.answer);

    const payload = {
      page_type: form.page_type,
      slug_path: form.slug_path.trim(),
      make: form.make.trim() || null,
      model: form.model.trim() || null,
      year: form.year.trim() ? Number(form.year) : null,
      title: form.title.trim(),
      teaser: form.teaser.trim(),
      body: form.body.trim() || null,
      faq,
      localized: {
        en: {
          title: form.localized.en.title.trim() || null,
          teaser: form.localized.en.teaser.trim() || null,
          body: form.localized.en.body.trim() || null,
          faq: []
        },
        uk: {
          title: form.localized.uk.title.trim() || null,
          teaser: form.localized.uk.teaser.trim() || null,
          body: form.localized.uk.body.trim() || null,
          faq
        },
        ru: {
          title: form.localized.ru.title.trim() || null,
          teaser: form.localized.ru.teaser.trim() || null,
          body: form.localized.ru.body.trim() || null,
          faq: []
        }
      },
      sort_order: Number(form.sort_order || "0"),
      is_active: form.is_active
    };

    try {
      const response = await fetch(editingId ? `${API_BASE}/api/v1/seo-pages/${editingId}` : `${API_BASE}/api/v1/seo-pages`, {
        method: editingId ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token
        },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail || "Failed to save SEO page.");
      }
      setMessage(editingId ? "SEO page updated." : "SEO page created.");
      resetForm();
      await fetchItems();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    }
  }

  async function onToggle(item: SeoPage) {
    try {
      const response = await fetch(`${API_BASE}/api/v1/seo-pages/${item.id}/active`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token
        },
        body: JSON.stringify({ is_active: !item.is_active })
      });
      if (!response.ok) throw new Error("Failed to update status.");
      setMessage(item.is_active ? "SEO page disabled." : "SEO page enabled.");
      await fetchItems();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Status update failed.");
    }
  }

  async function onDelete(item: SeoPage) {
    if (!confirm(`Delete SEO page "${item.title}"?`)) return;
    try {
      const response = await fetch(`${API_BASE}/api/v1/seo-pages/${item.id}`, {
        method: "DELETE",
        headers: { "X-Admin-Token": token }
      });
      if (!response.ok) throw new Error("Failed to delete SEO page.");
      setMessage("SEO page deleted.");
      if (editingId === item.id) resetForm();
      await fetchItems();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    }
  }

  return (
    <main className="shell carsHubShell">
      <section className="panel carsHubHero iaaiHero">
        <div className="heroFrame">
          <div className="heroCopy">
            <p className="chip">SEO Admin</p>
            <h1>Manage multilingual SEO pages</h1>
            <p className="lead">Create, edit, disable, and remove brand or cluster pages with localized SEO copy.</p>
          </div>
          <div className="heroSignal">
            <div className="auctionBoard">
              <p className="label">Admin Snapshot</p>
              <div className="auctionRow"><span>Total pages</span><strong>{items.length}</strong></div>
              <div className="auctionRow"><span>Visible</span><strong>{filteredItems.length}</strong></div>
              <div className="auctionRow"><span>Status</span><strong>{loading ? "Loading" : "Ready"}</strong></div>
              <div className="auctionRow"><span>Locales</span><strong>EN / UK / RU</strong></div>
            </div>
          </div>
        </div>
      </section>

      <section className="panel adminSeoPanel">
        <h2>Admin token</h2>
        <input className="input" type="password" placeholder="Enter ADMIN_TOKEN" value={token} onChange={(event) => setToken(event.target.value)} />
        {message ? <p className="statusOk">{message}</p> : null}
        {error ? <p className="statusError">{error}</p> : null}
      </section>

      <section className="panel adminSeoPanel">
        <div className="adminSeoHeaderRow">
          <h2>{editingId ? "Edit SEO page" : "Create SEO page"}</h2>
          {editingId ? <button className="ghostButton" type="button" onClick={resetForm}>Cancel editing</button> : null}
        </div>
        <form className="adminSeoForm" onSubmit={onSubmit}>
          <select className="input" value={form.page_type} onChange={(event) => setForm((current) => ({ ...current, page_type: event.target.value as "brand" | "cluster" }))}>
            <option value="brand">Brand</option>
            <option value="cluster">Cluster</option>
          </select>
          <input className="input" placeholder="slug_path: tesla or tesla/model-3/2022" value={form.slug_path} onChange={(event) => setForm((current) => ({ ...current, slug_path: event.target.value }))} />
          <input className="input" placeholder="make" value={form.make} onChange={(event) => setForm((current) => ({ ...current, make: event.target.value }))} />
          <input className="input" placeholder="model" value={form.model} onChange={(event) => setForm((current) => ({ ...current, model: event.target.value }))} />
          <input className="input" placeholder="year" value={form.year} onChange={(event) => setForm((current) => ({ ...current, year: event.target.value }))} />
          <input className="input" placeholder="default title" value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} />
          <textarea className="input adminTextarea" placeholder="default teaser" value={form.teaser} onChange={(event) => setForm((current) => ({ ...current, teaser: event.target.value }))} />
          <textarea className="input adminTextarea" placeholder="default body" value={form.body} onChange={(event) => setForm((current) => ({ ...current, body: event.target.value }))} />

          {LOCALES.map((locale) => (
            <div key={locale} className="adminSeoFaqCard">
              <h3>{`SEO ${locale.toUpperCase()}`}</h3>
              <input className="input" placeholder={`${locale.toUpperCase()} title`} value={form.localized[locale].title} onChange={(event) => setLocalizedField(locale, "title", event.target.value)} />
              <textarea className="input adminTextarea" placeholder={`${locale.toUpperCase()} teaser`} value={form.localized[locale].teaser} onChange={(event) => setLocalizedField(locale, "teaser", event.target.value)} />
              <textarea className="input adminTextarea" placeholder={`${locale.toUpperCase()} body`} value={form.localized[locale].body} onChange={(event) => setLocalizedField(locale, "body", event.target.value)} />
            </div>
          ))}

          <input className="input" placeholder="sort_order" value={form.sort_order} onChange={(event) => setForm((current) => ({ ...current, sort_order: event.target.value }))} />
          <label className="adminCheck">
            <input type="checkbox" checked={form.is_active} onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))} />
            Active page
          </label>

          <div className="adminSeoFaqSection">
            <div className="adminSeoHeaderRow">
              <h3>Default FAQ</h3>
              <button className="ghostButton" type="button" onClick={addFaqItem}>Add FAQ</button>
            </div>
            <div className="adminSeoFaqList">
              {form.faq.map((item, index) => (
                <article key={`faq-${index}`} className="adminSeoFaqCard">
                  <input className="input" placeholder={`Question #${index + 1}`} value={item.question} onChange={(event) => updateFaq(index, { question: event.target.value })} />
                  <textarea className="input adminTextarea" placeholder="Answer" value={item.answer} onChange={(event) => updateFaq(index, { answer: event.target.value })} />
                  <button className="ghostButton" type="button" onClick={() => removeFaqItem(index)}>Remove FAQ</button>
                </article>
              ))}
            </div>
          </div>

          <button className="button" type="submit">{editingId ? "Save changes" : "Create page"}</button>
        </form>
      </section>

      <section className="panel adminSeoPanel">
        <div className="adminSeoFilters">
          <input className="input" placeholder="Search slug, title, make, model" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} />
          <select className="input" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as "all" | "brand" | "cluster")}>
            <option value="all">All types</option>
            <option value="brand">Brand</option>
            <option value="cluster">Cluster</option>
          </select>
          <select className="input" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | "active" | "inactive")}>
            <option value="all">All statuses</option>
            <option value="active">Active only</option>
            <option value="inactive">Disabled only</option>
          </select>
        </div>
        <div className="adminSeoList">
          {filteredItems.map((item) => (
            <article key={item.id} className="adminSeoItem">
              <div>
                <p className="label">{item.page_type} · {item.slug_path} · {item.is_active ? "active" : "inactive"}</p>
                <h3>{item.title}</h3>
                <p>{item.teaser}</p>
              </div>
              <div className="adminSeoActions">
                <button className="ghostButton" type="button" onClick={() => { setEditingId(item.id); setForm(mapItemToForm(item)); setMessage(`Editing: ${item.title}`); setError(""); }}>Edit</button>
                <button className="ghostButton" type="button" onClick={() => void onToggle(item)}>{item.is_active ? "Disable" : "Enable"}</button>
                <button className="button dangerButton" type="button" onClick={() => void onDelete(item)}>Delete</button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
