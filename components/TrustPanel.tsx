import { ExternalLink } from "lucide-react";
import { formatDate, type SourceInfo, type Status } from "@/lib/risk";

const STATUS_BADGE: Record<SourceInfo["status"], string> = {
  ok: "bg-emerald-50 text-emerald-700",
  warning: "bg-amber-50 text-amber-700",
  stale: "bg-amber-50 text-amber-700",
  error: "bg-rose-50 text-rose-700",
};

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-t border-brand/10 py-2 text-sm first:border-t-0">
      <dt className="text-ink-muted">{label}</dt>
      <dd className="text-right font-medium text-ink">{value}</dd>
    </div>
  );
}

function Source({ s, rows }: { s: SourceInfo; rows: [string, React.ReactNode][] }) {
  return (
    <div>
      <h3 className="flex flex-wrap items-center gap-2 text-sm font-bold text-ink">
        <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:text-brand">
          {s.name} <ExternalLink size={12} />
        </a>
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_BADGE[s.status]}`}>{s.status}</span>
      </h3>
      <dl className="mt-3">
        <Row label="Last successful fetch" value={formatDate(s.fetched_at)} />
        {rows.map(([k, v]) => (
          <Row key={k} label={k} value={v} />
        ))}
      </dl>
      {s.error && <p className="mt-3 rounded-lg bg-rose-50 p-3 text-xs text-rose-800">Last refresh failed: {s.error}</p>}
      {s.message && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-900">{s.message}</p>}
    </div>
  );
}

export default function TrustPanel({ status }: { status: Status | null }) {
  return (
    <section className="card p-5 sm:p-6" aria-labelledby="trust-title">
      <h2 id="trust-title" className="text-lg font-bold text-ink">
        Where this comes from and what it can’t tell you
      </h2>
      {status && (
        <div className="mt-5 grid gap-8 lg:grid-cols-2">
          <Source
            s={status.sanctions}
            rows={[
              ["Entries on the list", status.sanctions.entries?.toLocaleString("en-US") ?? "—"],
              ["Alternate names (aliases)", status.sanctions.aliases?.toLocaleString("en-US") ?? "—"],
            ]}
          />
          <Source
            s={status.sec}
            rows={[
              ["Companies checked", status.sec.companies_checked?.toLocaleString("en-US") ?? "—"],
              ["Companies with a signal", status.sec.with_signals ?? "—"],
              ["Signals found (last 12 months)", status.sec.signals ?? "—"],
              ["Companies that could not be read", status.sec.failed ?? 0],
            ]}
          />
        </div>
      )}
      <ul className="mt-6 space-y-2 text-xs leading-relaxed text-ink-muted">
        <li>
          <strong className="text-ink">A name match is not a determination.</strong> Many companies and people share
          names. Use OFAC’s official Sanctions List Search and your own counsel before any compliance decision.
        </li>
        <li>
          <strong className="text-ink">Only a company’s own public filings are shown.</strong> Signals such as a late
          filing notice or a change of auditor are facts, not a verdict that a company is risky. Each one links to the
          original filing.
        </li>
        <li>
          <strong className="text-ink">Coverage is limited.</strong> The SEC part covers the largest listed US
          companies, not private companies or every filer. No score is calculated.
        </li>
        <li>This site is not affiliated with OFAC, the US Treasury or the SEC, and is not legal advice.</li>
      </ul>
    </section>
  );
}
