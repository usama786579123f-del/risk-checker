"""OFAC SDN list -> compact JSON the browser can search.

SDN.CSV has no header row. Columns (OFAC data spec): 0 ent_num, 1 SDN_Name, 2 SDN_Type,
3 Program, 4 Title, ... ALT.CSV: 0 ent_num, 1 alt_num, 2 alt_type, 3 alt_name, 4 alt_remarks.
OFAC writes "-0- " for an empty value. Remarks and addresses are not published here.
"""
from __future__ import annotations

import csv
import io
import re

from . import config
from .http import ApiError

_NULL = {"", "-0-"}
_TYPES = {"individual": "individual", "vessel": "vessel", "aircraft": "aircraft"}


def _clean(v: str) -> str:
    v = (v or "").strip()
    return "" if v in _NULL else v


def parse_sdn(sdn_text: str, alt_text: str) -> list[dict]:
    entries: dict[int, dict] = {}
    for row in csv.reader(io.StringIO(sdn_text)):
        if len(row) < 4 or not row[0].strip().isdigit():
            continue
        name = _clean(row[1])
        if not name:
            continue
        ent = int(row[0])
        kind = _TYPES.get(_clean(row[2]).lower(), "entity")
        programs = [p.strip() for p in re.split(r"\]\s*\[|;", _clean(row[3])) if p.strip()]
        entries[ent] = {"id": ent, "name": name, "type": kind, "programs": programs, "aliases": []}
    for row in csv.reader(io.StringIO(alt_text)):
        if len(row) < 4 or not row[0].strip().isdigit():
            continue
        ent = int(row[0])
        alias = _clean(row[3])
        if ent in entries and alias and "weak" not in row[2].lower():  # weak aliases cause false hits
            if alias not in entries[ent]["aliases"]:
                entries[ent]["aliases"].append(alias)
    return sorted(entries.values(), key=lambda e: e["id"])


def fetch(client, sources=None) -> tuple[list[dict], dict]:
    errors = []
    for sdn_url, alt_url in sources or config.OFAC_SOURCES:
        try:
            entries = parse_sdn(client.get_text(sdn_url), client.get_text(alt_url))
        except ApiError as exc:
            errors.append(str(exc))
            continue
        if len(entries) < config.MIN_SDN_ENTRIES:
            errors.append(f"{sdn_url}: only {len(entries)} entries parsed (expected thousands)")
            continue
        return entries, {"url": sdn_url, "entries": len(entries),
                         "aliases": sum(len(e["aliases"]) for e in entries)}
    raise ApiError("OFAC list could not be downloaded: " + " | ".join(errors))
