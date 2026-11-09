"""Offline tests: no network is used; OFAC and SEC are replaced by a fake client."""
import json
from datetime import date

import pytest

from pipeline import config, ofac, sec
from pipeline import run as runmod
from pipeline.http import ApiError, BlockedError

TODAY = date(2026, 11, 8)

SDN_CSV = (
    '36,"AEROCARIBBEAN AIRLINES","-0- ","CUBA",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,"Remarks that are not published"\n'
    '100,"DOE, John","individual","SDGT] [IFSR",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- \n'
    '200,"SEA STAR","vessel","IRAN",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- \n'
    'garbage line\n'
)
ALT_CSV = (
    '36,1,"a.k.a.","AERO CARIBBEAN",-0- \n'
    '36,2,"weak a.k.a.","ACA",-0- \n'
    '999,3,"a.k.a.","ORPHAN ALIAS",-0- \n'
)


def many_entries(n=1200):
    return "\n".join(f'{i},"COMPANY {i}","-0- ","SDGT",-0- ' for i in range(1000, 1000 + n)) + "\n"


class FakeClient:
    def __init__(self, texts=None, jsons=None):
        self.texts, self.jsons, self.calls = texts or {}, jsons or {}, []

    def _lookup(self, table, url):
        self.calls.append(url)
        v = table.get(url)
        if isinstance(v, Exception):
            raise v
        if v is None:
            raise ApiError(f"HTTP 404 from {url}")
        return v

    def get_text(self, url):
        return self._lookup(self.texts, url)

    def get_json(self, url):
        return self._lookup(self.jsons, url)


# ---------- OFAC ----------
def test_parse_sdn_types_programs_aliases():
    e = {x["id"]: x for x in ofac.parse_sdn(SDN_CSV, ALT_CSV)}
    assert set(e) == {36, 100, 200}
    assert e[36]["type"] == "entity" and e[36]["programs"] == ["CUBA"]
    assert e[100]["type"] == "individual" and e[100]["programs"] == ["SDGT", "IFSR"]
    assert e[200]["type"] == "vessel"
    assert e[36]["aliases"] == ["AERO CARIBBEAN"]  # weak alias skipped, orphan alias ignored


def test_remarks_are_not_published():
    assert "Remarks" not in json.dumps(ofac.parse_sdn(SDN_CSV, ALT_CSV))


def test_ofac_fetch_falls_back_to_second_location_and_rejects_tiny_lists():
    sources = [("https://a/sdn", "https://a/alt"), ("https://b/sdn", "https://b/alt")]
    client = FakeClient(texts={"https://a/sdn": ApiError("HTTP 404"),
                               "https://b/sdn": many_entries(), "https://b/alt": ""})
    entries, meta = ofac.fetch(client, sources)
    assert len(entries) == 1200 and meta["url"] == "https://b/sdn"
    tiny = FakeClient(texts={"https://a/sdn": SDN_CSV, "https://a/alt": ALT_CSV})
    with pytest.raises(ApiError):
        ofac.fetch(tiny, sources[:1])


# ---------- SEC ----------
def sub(forms, items=None, dates=None):
    n = len(forms)
    return {"sicDescription": "Services", "filings": {"recent": {
        "accessionNumber": [f"0000000001-26-00000{i}" for i in range(n)],
        "filingDate": dates or ["2026-10-01"] * n, "form": forms,
        "items": items or [""] * n, "primaryDocument": [f"d{i}.htm" for i in range(n)]}}}


def test_extract_signals_items_forms_and_lookback():
    s = sub(["8-K", "8-K", "NT 10-K", "10-K", "8-K"],
            items=["1.03,9.01", "5.02", "", "", "4.02"],
            dates=["2026-10-01", "2026-10-02", "2026-09-01", "2026-08-01", "2024-01-01"])
    got = sec.extract_signals(s, 123, date(2025, 11, 8))
    assert sorted((g["code"], g["category"]) for g in got) == [("Item 1.03", "Bankruptcy"), ("NT 10-K", "Reporting")]
    assert {g["code"] for g in got} == {"Item 1.03", "NT 10-K"}  # 5.02 not a signal, 4.02 is too old
    assert got[0]["date"] >= got[-1]["date"]
    assert got[0]["url"].startswith("https://www.sec.gov/Archives/edgar/data/123/000000000126000000/")


def test_extract_signals_handles_missing_fields():
    assert sec.extract_signals({}, 1, date(2025, 1, 1)) == []
    assert sec.extract_signals({"filings": {"recent": {"filingDate": ["2026-10-01"]}}}, 1, date(2025, 1, 1)) == []


def tickers(n):
    return {str(i): {"cik_str": 1000 + i, "ticker": f"T{i}", "title": f"Co {i}"} for i in range(n)}


def test_load_companies_dedupes_by_cik_and_limits():
    raw = {"0": {"cik_str": 1, "ticker": "A", "title": "Alpha"}, "1": {"cik_str": 1, "ticker": "AA", "title": "Alpha"},
           "2": {"cik_str": "bad", "ticker": "X", "title": "X"}, "3": {"cik_str": 2, "ticker": "B", "title": "Beta"}}
    got = sec.load_companies(FakeClient(jsons={config.TICKERS_URL: raw}), 10)
    assert [c["ticker"] for c in got] == ["A", "B"]
    assert len(sec.load_companies(FakeClient(jsons={config.TICKERS_URL: tickers(50)}), 5)) == 5


def sec_client(n=10, bad=(), blocked_at=None):
    jsons = {config.TICKERS_URL: tickers(n)}
    for i in range(n):
        url = config.SUBMISSIONS_URL.format(cik=1000 + i)
        jsons[url] = sub(["8-K"], items=["1.03"]) if i % 2 == 0 else sub(["10-Q"])
        if i in bad:
            jsons[url] = ApiError("HTTP 404")
        if i == blocked_at:
            jsons[url] = BlockedError("HTTP 429")
    return FakeClient(jsons=jsons)


def test_sec_fetch_counts():
    rows, meta = sec.fetch(sec_client(10, bad=(3,)), TODAY)
    assert meta["companies_checked"] == 9 and meta["failed"] == 1 and meta["with_signals"] == 5


def test_sec_blocked_stops_immediately():
    client = sec_client(10, blocked_at=2)
    with pytest.raises(BlockedError):
        sec.fetch(client, TODAY)
    assert len(client.calls) == 1 + 3  # tickers + 3 submissions, nothing after the refusal


def test_sec_gives_up_after_consecutive_failures():
    with pytest.raises(ApiError):
        sec.fetch(sec_client(20, bad=range(20)), TODAY)


# ---------- end to end ----------
def both(n=10, **kw):
    c = sec_client(n, **kw)
    c.texts = {"https://a/sdn": many_entries(), "https://a/alt": ""}
    return c


SRC = [("https://a/sdn", "https://a/alt")]


def test_run_publishes_both_sources(tmp_path):
    assert runmod.run(both(), tmp_path, TODAY, ofac_sources=SRC) == 0
    status = json.loads((tmp_path / "status.json").read_text())
    assert status["mode"] == "live" and status["sanctions"]["status"] == "ok"
    assert status["sec"]["companies_checked"] == 10 and status["sec"]["signals"] == 5
    assert len(json.loads((tmp_path / "sanctions.json").read_text())) == 1200
    assert len(json.loads((tmp_path / "companies.json").read_text())) == 10


def test_one_source_failing_keeps_old_file_and_goes_stale(tmp_path):
    runmod.run(both(), tmp_path, TODAY, ofac_sources=SRC)
    before = (tmp_path / "sanctions.json").read_text()
    c = both()
    c.texts["https://a/sdn"] = ApiError("HTTP 500")
    assert runmod.run(c, tmp_path, TODAY, ofac_sources=SRC) == 1  # red in GitHub Actions
    status = json.loads((tmp_path / "status.json").read_text())
    assert status["sanctions"]["status"] == "stale" and status["sanctions"]["entries"] == 1200
    assert status["sec"]["status"] == "ok"
    assert (tmp_path / "sanctions.json").read_text() == before


def test_nothing_fetched_and_nothing_before_publishes_nothing(tmp_path):
    empty = FakeClient()
    assert runmod.run(empty, tmp_path, TODAY, ofac_sources=SRC) == 1
    assert not list(tmp_path.glob("*.json"))


def test_first_run_with_one_source_down_is_error_not_stale(tmp_path):
    c = both()
    c.texts["https://a/sdn"] = ApiError("down")
    assert runmod.run(c, tmp_path, TODAY, ofac_sources=SRC) == 1
    status = json.loads((tmp_path / "status.json").read_text())
    assert status["sanctions"]["status"] == "error" and status["sec"]["status"] == "ok"
    assert not (tmp_path / "sanctions.json").exists()


def test_many_failed_companies_is_a_warning(tmp_path):
    assert runmod.run(both(10, bad=(1, 3, 5)), tmp_path, TODAY, ofac_sources=SRC) == 0
    assert json.loads((tmp_path / "status.json").read_text())["sec"]["status"] == "warning"


def test_main_without_email_exits_2(monkeypatch, tmp_path):
    monkeypatch.delenv("SEC_CONTACT_EMAIL", raising=False)
    assert runmod.main(["--out", str(tmp_path)]) == 2
    monkeypatch.setenv("SEC_CONTACT_EMAIL", "not-an-email")
    assert runmod.main(["--out", str(tmp_path)]) == 2
