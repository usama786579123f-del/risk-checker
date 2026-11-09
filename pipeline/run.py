"""Daily pipeline: fetch OFAC list + SEC filing signals -> publish JSON.

    SEC_CONTACT_EMAIL=you@example.com  python -m pipeline.run

No API key is needed. SEC asks automated clients to put a contact email in the User-Agent, so
that is the only setting. Each source is handled on its own:
  * on failure the previous published file is kept and marked "stale" (exit code 1, job turns red)
  * a broken or empty download never replaces good data
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from . import config, ofac, sec
from .http import ApiError, Client

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "public" / "data"
FILES = {"sanctions": "sanctions.json", "sec": "companies.json"}
STATUS_FILE = "status.json"


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)  # atomic: readers never see a half-written file


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run(client, out_dir: Path, today: date, *, max_companies: int = config.MAX_COMPANIES,
        ofac_sources=None) -> int:
    out_dir = Path(out_dir)
    prev = _load(out_dir / STATUS_FILE) or {}
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    sources, bad = {}, False

    jobs = {
        "sanctions": ("OFAC Specially Designated Nationals list", config.OFAC_PAGE,
                      lambda: ofac.fetch(client, ofac_sources)),
        "sec": ("SEC EDGAR filings", config.SEC_PAGE,
                lambda: sec.fetch(client, today, max_companies)),
    }
    for key, (name, url, job) in jobs.items():
        info = {"name": name, "url": url, "status": "ok", "error": None, "message": None, "fetched_at": now}
        try:
            data, meta = job()
            info.update(meta)
            if key == "sec" and meta["failed"] > config.MAX_FAIL_RATE * meta["companies_listed"]:
                info["status"] = "warning"
                info["message"] = f"{meta['failed']} of {meta['companies_listed']} companies could not be read."
            _write_json(out_dir / FILES[key], data)
        except ApiError as exc:
            bad = True
            old = prev.get(key)
            if old and (out_dir / FILES[key]).exists():
                info = {**old, "status": "stale", "error": str(exc)}
            else:
                info.update(status="error", error=str(exc))
        sources[key] = info

    if not any((out_dir / f).exists() for f in FILES.values()):
        print("No data could be fetched and nothing was published before.", file=sys.stderr)
        for s in sources.values():
            print(f"  {s['name']}: {s['error']}", file=sys.stderr)
        return 1

    _write_json(out_dir / STATUS_FILE, {"generated_at": now, "mode": "live", **sources})
    for s in sources.values():
        print(f"{s['name']}: {s['status']}" + (f" ({s['error']})" if s["error"] else ""))
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Refresh Risk Checker data")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--max-companies", type=int, default=config.MAX_COMPANIES)
    args = ap.parse_args(argv)
    email = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
    if "@" not in email:
        print("Set SEC_CONTACT_EMAIL to your email address. SEC asks automated clients to identify "
              "themselves; no API key is needed.", file=sys.stderr)
        return 2
    client = Client(f"RiskChecker/1.0 ({email})", delay=config.REQUEST_DELAY)
    return run(client, Path(args.out), date.today(), max_companies=args.max_companies)


if __name__ == "__main__":
    sys.exit(main())
