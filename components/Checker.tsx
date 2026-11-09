"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, ExternalLink, FileText, Search, ShieldAlert, X } from "lucide-react";
import TrustPanel from "@/components/TrustPanel";
import {
  buildIndex,
  findCompanies,
  formatDate,
  matchSanctions,
  safeSecUrl,
  titleCase,
  TYPE_LABEL,
  type Company,
  type IndexedSdn,
  type SdnEntry,
  type Signal,
  type Status,
} from "@/lib/risk";

const PORTFOLIO_URL = process.env.NEXT_PUBLIC_PORTFOLIO_URL || "";
const OFAC_SEARCH = "https://sanctionssearch.ofac.treas.gov/";
const ROWS = 40;

type SanctionsState = { phase: "loading" } | { phase: "missing" } | { phase: "ready"; index: IndexedSdn[] };

function SignalItem({ s }: { s: Signal }) {
  const link = safeSecUrl(s.url);
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 border-t border-brand/10 py-2.5 text-sm first:border-t-0">
      <div>
        <span className="mr-2 rounded-full bg-brand-soft px-2 py-0.5 text-xs font-semibold text-brand">{s.category}</span>
        <span className="font-medium text-ink">{s.label}</span>
        <span className="ml-2 text-xs text-ink-muted">
          {s.form} · {s.code} · {formatDate(s.date)}
        </span>
      </div>
      {link && (
        <a href={link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-brand hover:underline">
          Original filing <ExternalLink size={12} />
        </a>
      )}
    </li>
  );
}

function SanctionsCard({ query, state, status }: { query: string; state: SanctionsState; status: Status | null }) {
  const matches = useMemo(
    () => (state.phase === "ready" ? matchSanctions(query, state.index) : []),
    [query, state],
  );
  const asOf = status ? formatDate(status.sanctions.fetched_at) : null;
  return (
    <section className="card p-5 sm:p-6" aria-labelledby="sanc-title">
      <h2 id="sanc-title" className="flex items-center gap-2 text-lg font-bold text-ink">
        <ShieldAlert size={20} className="text-brand" /> OFAC sanctions list
      </h2>
      {state.phase === "loading" && <p className="mt-3 text-sm text-ink-muted">Loading the list…</p>}
      {state.phase === "missing" && (
        <p className="mt-3 text-sm text-ink-muted">The sanctions list is not available yet. Run the data refresh first.</p>
      )}
      {state.phase === "ready" && matches.length === 0 && (
        <div className="mt-3 flex gap-3 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-900">
          <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
          <p>
            No name match in the list{asOf ? ` as fetched on ${asOf}` : ""}. This is a name check only. It does not
            clear anyone. Confirm in OFAC’s{" "}
            <a href={OFAC_SEARCH} target="_blank" rel="noopener noreferrer" className="font-semibold underline">
              official search tool
            </a>
            .
          </p>
        </div>
      )}
      {matches.length > 0 && (
        <>
          <p className="mt-3 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">
            {matches.length} possible {matches.length === 1 ? "match" : "matches"}. Names are shared by unrelated
            parties, so verify each one at the source before drawing any conclusion.
          </p>
          <ul className="mt-3">
            {matches.map((m) => (
              <li key={m.entry.id} className="border-t border-brand/10 py-3 text-sm first:border-t-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-ink">{titleCase(m.entry.name)}</span>
                  <span className="rounded-full bg-brand-soft px-2 py-0.5 text-xs font-semibold text-brand">{TYPE_LABEL[m.entry.type]}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${m.kind === "exact" ? "bg-rose-50 text-rose-700" : "bg-amber-50 text-amber-700"}`}>
                    {m.kind === "exact" ? "Same name" : "Similar name"}
                  </span>
                </div>
                <p className="mt-1 text-xs text-ink-muted">
                  {m.matchedName !== m.entry.name && <>Matched on “{titleCase(m.matchedName)}”. </>}
                  {m.entry.programs.length > 0 && <>Programs: {m.entry.programs.join(", ")}. </>}
                  OFAC entry #{m.entry.id}.
                </p>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function SecCard({ query, companies, onPick }: { query: string; companies: Company[]; onPick: (q: string) => void }) {
  const found = useMemo(() => findCompanies(query, companies), [query, companies]);
  return (
    <section className="card p-5 sm:p-6" aria-labelledby="sec-title">
      <h2 id="sec-title" className="flex items-center gap-2 text-lg font-bold text-ink">
        <FileText size={20} className="text-brand" /> SEC filing signals (last 12 months)
      </h2>
      {companies.length === 0 && <p className="mt-3 text-sm text-ink-muted">SEC data is not available yet.</p>}
      {companies.length > 0 && found.length === 0 && (
        <p className="mt-3 text-sm text-ink-muted">
          No listed company with that name or ticker among the {companies.length.toLocaleString("en-US")} checked. It
          may be private, or outside this list.
        </p>
      )}
      {found.map((c) => (
        <div key={c.cik} className="mt-4 first:mt-3">
          <div className="flex flex-wrap items-baseline gap-2">
            <button type="button" onClick={() => onPick(c.name)} className="text-left font-semibold text-ink hover:text-brand">
              {titleCase(c.name)}
            </button>
            <span className="text-xs font-semibold text-brand">{c.ticker}</span>
            {c.industry && <span className="text-xs text-ink-muted">{c.industry}</span>}
          </div>
          {c.signals.length === 0 ? (
            <p className="mt-1 text-sm text-ink-muted">None of the tracked signals were filed in the last 12 months.</p>
          ) : (
            <ul className="mt-1">{c.signals.map((s, i) => <SignalItem key={i} s={s} />)}</ul>
          )}
        </div>
      ))}
    </section>
  );
}

export default function Checker({ companies, status }: { companies: Company[]; status: Status | null }) {
  const [query, setQuery] = useState("");
  const deferred = useDeferredValue(query.trim());
  const [state, setState] = useState<SanctionsState>({ phase: "loading" });
  const [category, setCategory] = useState("all");
  const [shown, setShown] = useState(ROWS);

  useEffect(() => {
    let cancelled = false;
    fetch("/data/sanctions.json")
      .then((r) => (r.ok ? (r.json() as Promise<SdnEntry[]>) : Promise.reject(new Error("missing"))))
      .then((d) => !cancelled && setState({ phase: "ready", index: buildIndex(d) }))
      .catch(() => !cancelled && setState({ phase: "missing" }));
    return () => {
      cancelled = true;
    };
  }, []);

  const all = useMemo(
    () =>
      companies
        .flatMap((c) => c.signals.map((s) => ({ c, s })))
        .sort((a, b) => b.s.date.localeCompare(a.s.date)),
    [companies],
  );
  const categories = useMemo(() => Array.from(new Set(all.map((x) => x.s.category))).sort(), [all]);
  const feed = all.filter((x) => category === "all" || x.s.category === category);
  const hasData = status !== null || companies.length > 0;

  return (
    <div className="min-h-screen bg-brand-mist">
      <header className="border-b border-brand/10 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            {PORTFOLIO_URL && (
              <a href={PORTFOLIO_URL} className="inline-flex items-center gap-1 text-sm font-semibold text-brand hover:underline">
                <ArrowLeft size={14} /> Portfolio
              </a>
            )}
            <span className="text-lg font-extrabold text-ink">Risk Checker</span>
          </div>
          {status && (
            <span className="hidden rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 sm:inline-block">
              Live public data · updated {formatDate(status.generated_at)}
            </span>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
        <section className="card p-6 sm:p-8">
          <p className="section-label">Public-data company check</p>
          <h1 className="mt-3 text-2xl font-extrabold text-ink sm:text-3xl">Check a company before you work with it</h1>
          <p className="mt-2 max-w-2xl text-sm text-ink-muted">
            Type a company name or stock ticker. We compare the name with the US Treasury sanctions list and show
            recent risk-related filings the company itself made with the SEC.
          </p>
          <div className="relative mt-5">
            <label htmlFor="q" className="sr-only">Company name or ticker</label>
            <Search size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-ink-muted" />
            <input
              id="q"
              type="search"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
              }}
              placeholder="Company name or ticker, e.g. Boeing or BA"
              autoComplete="off"
              className="w-full rounded-xl border border-brand/20 bg-white py-3 pl-11 pr-10 text-sm text-ink outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
            />
            {query && (
              <button type="button" aria-label="Clear" onClick={() => setQuery("")} className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 text-ink-muted hover:text-brand">
                <X size={16} />
              </button>
            )}
          </div>
        </section>

        {!hasData && (
          <div className="card p-8 text-center text-ink-muted">
            <p className="font-semibold text-ink">No live data yet.</p>
            <p className="mt-2 text-sm">
              Data appears after the first successful run of the pipeline (
              <code className="rounded bg-brand-soft px-1.5 py-0.5 text-brand">python -m pipeline.run</code>, or the
              “Refresh risk data” workflow on GitHub).
            </p>
          </div>
        )}

        {hasData && deferred && (
          <div className="grid gap-6 lg:grid-cols-2">
            <SanctionsCard query={deferred} state={state} status={status} />
            <SecCard query={deferred} companies={companies} onPick={setQuery} />
          </div>
        )}

        {hasData && !deferred && companies.length > 0 && (
          <section className="card p-5 sm:p-6" aria-labelledby="feed-title">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 id="feed-title" className="text-lg font-bold text-ink">Recent filing signals</h2>
              <label className="flex items-center gap-2 text-sm text-ink-muted">
                Type
                <select
                  value={category}
                  onChange={(e) => {
                    setCategory(e.target.value);
                    setShown(ROWS);
                  }}
                  className="rounded-lg border border-brand/20 bg-white px-2 py-1.5 text-sm text-ink"
                >
                  <option value="all">All</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </label>
            </div>
            {feed.length === 0 ? (
              <p className="mt-4 text-sm text-ink-muted">No signals found in the data.</p>
            ) : (
              <ul className="mt-3">
                {feed.slice(0, shown).map(({ c, s }, i) => (
                  <li key={`${c.cik}-${i}`} className="flex flex-wrap items-center justify-between gap-2 border-t border-brand/10 py-2.5 text-sm first:border-t-0">
                    <div>
                      <button type="button" onClick={() => setQuery(c.name)} className="mr-2 font-semibold text-ink hover:text-brand">
                        {titleCase(c.name)}
                      </button>
                      <span className="mr-2 rounded-full bg-brand-soft px-2 py-0.5 text-xs font-semibold text-brand">{s.category}</span>
                      <span className="text-ink">{s.label}</span>
                      <span className="ml-2 text-xs text-ink-muted">{formatDate(s.date)}</span>
                    </div>
                    {safeSecUrl(s.url) && (
                      <a href={safeSecUrl(s.url)!} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-brand hover:underline">
                        Original filing <ExternalLink size={12} />
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {feed.length > shown && (
              <button type="button" onClick={() => setShown((n) => n + ROWS)} className="btn-outline mt-4">
                Show more ({feed.length - shown} left)
              </button>
            )}
          </section>
        )}

        <TrustPanel status={status} />
      </main>

      <footer className="mx-auto max-w-5xl px-4 pb-10 text-xs text-ink-muted sm:px-6">
        Built from public data. Not legal or compliance advice.
      </footer>
    </div>
  );
}
