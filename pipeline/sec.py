"""SEC EDGAR -> public filing signals per company (no API key; polite User-Agent required)."""
from __future__ import annotations

from datetime import date, timedelta

from . import config
from .http import ApiError, BlockedError


def load_companies(client, limit: int) -> list[dict]:
    raw = client.get_json(config.TICKERS_URL)
    rows = raw.values() if isinstance(raw, dict) else raw
    seen, out = set(), []
    for r in rows:
        try:
            cik, name, ticker = int(r["cik_str"]), str(r["title"]).strip(), str(r["ticker"]).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if cik in seen or not name:
            continue
        seen.add(cik)
        out.append({"cik": cik, "name": name, "ticker": ticker})
        if len(out) >= limit:
            break
    if not out:
        raise ApiError("SEC company list was empty or in an unexpected format")
    return out


def extract_signals(sub: dict, cik: int, since: date) -> list[dict]:
    recent = (sub.get("filings") or {}).get("recent") or {}
    dates, forms = recent.get("filingDate") or [], recent.get("form") or []
    accs, items = recent.get("accessionNumber") or [], recent.get("items") or []
    docs = recent.get("primaryDocument") or []
    signals = []
    for i, d in enumerate(dates):
        if i >= len(forms) or i >= len(accs) or d < since.isoformat():
            continue
        form = forms[i]
        found = []
        if form in config.FORM_SIGNALS:
            found.append((form, *config.FORM_SIGNALS[form]))
        if form.startswith("8-K"):
            for code in (items[i] if i < len(items) else "").split(","):
                if code.strip() in config.ITEM_SIGNALS:
                    found.append((f"Item {code.strip()}", *config.ITEM_SIGNALS[code.strip()]))
        acc = accs[i].replace("-", "")
        doc = docs[i] if i < len(docs) else ""
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}" if doc else \
              f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}"
        for code, label, category in found:
            signals.append({"date": d, "form": form, "code": code, "label": label,
                            "category": category, "url": url})
    return sorted(signals, key=lambda s: s["date"], reverse=True)


def fetch(client, today: date, max_companies: int = config.MAX_COMPANIES) -> tuple[list[dict], dict]:
    companies = load_companies(client, max_companies)
    since = today - timedelta(days=config.LOOKBACK_DAYS)
    out, failed, streak = [], 0, 0
    for c in companies:
        try:
            sub = client.get_json(config.SUBMISSIONS_URL.format(cik=c["cik"]))
            if not isinstance(sub, dict):
                raise ApiError("unexpected response")
        except BlockedError:
            raise  # being refused: stop immediately instead of hammering the server
        except ApiError:
            failed += 1
            streak += 1
            if streak >= config.MAX_CONSECUTIVE_FAILS:
                raise ApiError(f"{streak} SEC requests failed in a row; giving up") from None
            continue
        streak = 0
        out.append({
            "cik": c["cik"], "name": c["name"], "ticker": c["ticker"],
            "industry": sub.get("sicDescription") or None,
            "signals": extract_signals(sub, c["cik"], since),
        })
    if not out:
        raise ApiError("no company filings could be read")
    return out, {"companies_listed": len(companies), "companies_checked": len(out), "failed": failed,
                 "signals": sum(len(c["signals"]) for c in out),
                 "with_signals": sum(1 for c in out if c["signals"])}
