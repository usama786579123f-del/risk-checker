export type SdnEntry = {
  id: number;
  name: string;
  type: "entity" | "individual" | "vessel" | "aircraft";
  programs: string[];
  aliases: string[];
};
export type Signal = { date: string; form: string; code: string; label: string; category: string; url: string };
export type Company = { cik: number; name: string; ticker: string; industry: string | null; signals: Signal[] };

export type SourceInfo = {
  name: string;
  url: string;
  status: "ok" | "warning" | "stale" | "error";
  error: string | null;
  message: string | null;
  fetched_at: string;
  entries?: number;
  aliases?: number;
  companies_listed?: number;
  companies_checked?: number;
  failed?: number;
  signals?: number;
  with_signals?: number;
};
export type Status = { generated_at: string; mode: "live"; sanctions: SourceInfo; sec: SourceInfo };

// ---------- name matching (runs in the browser) ----------
const SUFFIXES = new Set([
  "inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation", "co", "company", "plc",
  "gmbh", "sa", "ag", "bv", "nv", "lp", "llp", "the", "pjsc", "ooo", "jsc", "sarl",
]);

export function tokens(s: string): string[] {
  const base = s
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
  return base.split(" ").filter((t) => t && !SUFFIXES.has(t));
}

export type IndexedSdn = { entry: SdnEntry; names: { label: string; set: Set<string>; key: string; compact: string }[] };

export function buildIndex(entries: SdnEntry[]): IndexedSdn[] {
  return entries.map((entry) => ({
    entry,
    names: [entry.name, ...entry.aliases].map((label) => {
      const t = tokens(label);
      return { label, set: new Set(t), key: [...t].sort().join(" "), compact: t.join("") };
    }),
  }));
}

export type SdnMatch = { entry: SdnEntry; matchedName: string; kind: "exact" | "similar"; score: number };

/**
 * Exact = same words in any order (so "DOE, John" equals "John Doe"), or the same letters when only
 * the spacing differs ("Aero Caribbean" equals "Aerocaribbean").
 * Similar = at least 2 shared words and Jaccard overlap >= 0.7. One-word queries only match exactly,
 * otherwise "bank" would hit hundreds of entries.
 */
export function matchSanctions(query: string, index: IndexedSdn[], limit = 8): SdnMatch[] {
  const q = tokens(query);
  if (q.length === 0) return [];
  const qSet = new Set(q);
  const qKey = [...qSet].sort().join(" ");
  const qCompact = q.join("");
  const out: SdnMatch[] = [];
  for (const { entry, names } of index) {
    let best: SdnMatch | null = null;
    for (const n of names) {
      let cand: SdnMatch | null = null;
      if (n.key === qKey || n.compact === qCompact) {
        cand = { entry, matchedName: n.label, kind: "exact", score: 1 };
      } else if (qSet.size >= 2 && n.set.size >= 2) {
        let inter = 0;
        for (const t of qSet) if (n.set.has(t)) inter++;
        const score = inter / (qSet.size + n.set.size - inter);
        if (inter >= 2 && score >= 0.7) cand = { entry, matchedName: n.label, kind: "similar", score };
      }
      if (cand && (!best || cand.score > best.score)) best = cand;
    }
    if (best) out.push(best);
  }
  return out.sort((a, b) => b.score - a.score).slice(0, limit);
}

export function findCompanies(query: string, companies: Company[], limit = 5): Company[] {
  const raw = query.trim().toLowerCase();
  if (!raw) return [];
  const q = tokens(query).join(" ");
  const scored: [number, Company][] = [];
  for (const c of companies) {
    const name = tokens(c.name).join(" ");
    let rank = 0;
    if (c.ticker.toLowerCase() === raw) rank = 4;
    else if (name === q) rank = 3;
    else if (q && name.startsWith(q)) rank = 2;
    else if (q && name.includes(q)) rank = 1;
    if (rank) scored.push([rank, c]);
  }
  return scored.sort((a, b) => b[0] - a[0] || a[1].name.length - b[1].name.length).slice(0, limit).map((s) => s[1]);
}

export const formatDate = (d: string) =>
  new Date(`${d.slice(0, 10)}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });

export const titleCase = (s: string) =>
  s === s.toUpperCase() ? s.toLowerCase().replace(/\b[a-z]/g, (c) => c.toUpperCase()) : s;

export const TYPE_LABEL: Record<SdnEntry["type"], string> = {
  entity: "Entity",
  individual: "Individual",
  vessel: "Vessel",
  aircraft: "Aircraft",
};

export function safeSecUrl(url: string): string | null {
  try {
    const u = new URL(url);
    return u.protocol === "https:" && (u.hostname === "www.sec.gov" || u.hostname === "sec.gov") ? u.href : null;
  } catch {
    return null;
  }
}
