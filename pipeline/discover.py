"""Checks both sources with a handful of requests and prints what came back.

    SEC_CONTACT_EMAIL=you@example.com  python -m pipeline.discover
"""
from __future__ import annotations

import os
import sys

from . import config, ofac
from .http import ApiError, Client


def main() -> int:
    email = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
    if "@" not in email:
        print("Set SEC_CONTACT_EMAIL first (your own email; no API key needed).", file=sys.stderr)
        return 2
    client = Client(f"RiskChecker/1.0 ({email})", delay=config.REQUEST_DELAY)
    ok = True
    print("== OFAC SDN list ==")
    for sdn_url, alt_url in config.OFAC_SOURCES:
        try:
            text = client.get_text(sdn_url)
            alt = client.get_text(alt_url)
        except ApiError as exc:
            print(f"FAILED  {sdn_url}\n        {exc}")
            continue
        entries = ofac.parse_sdn(text, alt)
        print(f"OK      {sdn_url}\n        {len(entries)} entries parsed; first lines of the file:")
        for line in text.splitlines()[:3]:
            print("        " + line[:150])
        break
    else:
        ok = False
    print("== SEC EDGAR ==")
    try:
        first = client.get_json(config.TICKERS_URL)
        rows = list(first.values())[:2] if isinstance(first, dict) else first[:2]
        print("tickers file OK, first rows:", rows)
        cik = int(rows[0]["cik_str"])
        sub = client.get_json(config.SUBMISSIONS_URL.format(cik=cik))
        recent = sub.get("filings", {}).get("recent", {})
        print("submissions OK; keys:", sorted(recent.keys())[:12], "| filings listed:", len(recent.get("form", [])))
    except (ApiError, KeyError, ValueError, TypeError) as exc:
        ok = False
        print("FAILED:", exc)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
