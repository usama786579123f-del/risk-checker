"""Settings for the Risk Checker pipeline.

Both sources are public and need NO API key:
  * OFAC SDN list (US Treasury sanctions list), downloaded as CSV files
  * SEC EDGAR (public company filings). SEC asks every automated client to identify itself with a
    contact email in the User-Agent header and to stay under 10 requests/second.
    https://www.sec.gov/os/accessing-edgar-data
"""
from __future__ import annotations

# (SDN.CSV, ALT.CSV) pairs, tried in order. The first pair that downloads is used.
# The OFAC file-location has moved before, so run `python -m pipeline.discover` to check these.
OFAC_SOURCES = [
    (
        "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV",
        "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ALT.CSV",
    ),
    ("https://www.treasury.gov/ofac/downloads/sdn.csv", "https://www.treasury.gov/ofac/downloads/alt.csv"),
]
OFAC_PAGE = "https://ofac.treasury.gov/sanctions-list-service"
MIN_SDN_ENTRIES = 1000  # the real list has many thousands; far fewer means a broken download

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SEC_PAGE = "https://www.sec.gov/edgar/search/"
MAX_COMPANIES = 1500        # companies checked per run (file order = largest names first)
LOOKBACK_DAYS = 365         # filings newer than this are scanned for signals
REQUEST_DELAY = 0.25        # seconds between SEC requests (SEC limit is 10 per second)
MAX_FAIL_RATE = 0.20        # more failed companies than this is reported as "warning"
MAX_CONSECUTIVE_FAILS = 8   # this many failures in a row aborts the SEC part

# 8-K item numbers that are worth surfacing. These are facts a company itself filed,
# not opinions: the page shows them with a link to the original filing.
ITEM_SIGNALS = {
    "1.03": ("Bankruptcy or receivership", "Bankruptcy"),
    "3.01": ("Delisting or listing-standard notice", "Listing"),
    "4.01": ("Change of auditor", "Accounting"),
    "4.02": ("Past financial statements should no longer be relied on", "Accounting"),
    "1.05": ("Cybersecurity incident reported", "Security"),
    "2.04": ("Debt acceleration or similar trigger", "Debt"),
    "2.06": ("Material impairment", "Accounting"),
}
FORM_SIGNALS = {
    "NT 10-K": ("Late filing notice: annual report", "Reporting"),
    "NT 10-Q": ("Late filing notice: quarterly report", "Reporting"),
    "15-12G": ("Ended SEC registration (Form 15)", "Reporting"),
    "15-12B": ("Ended SEC registration (Form 15)", "Reporting"),
}
