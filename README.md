# Risk Checker

Type a company name or ticker. The page compares the name with the **US Treasury OFAC sanctions list**
and shows recent **risk-related SEC filings** the company itself made (bankruptcy notice, delisting
notice, change of auditor, late-filing notice and similar), each with a link to the original filing.

**No API key is needed.** Both sources are public. The only setting is your own email address, because
the SEC asks automated clients to identify themselves in the User-Agent header.

```
GitHub Actions (daily)         public/data/*.json                    Vercel
python -m pipeline.run  -->  sanctions.json, companies.json,  -->  the site
                             status.json                           (name matching runs in the browser)
```

There is **no demo or sample data**. Until the pipeline has run once, the site says "No live data yet".

## Run it locally
```powershell
# Windows PowerShell (use your own email)
$env:SEC_CONTACT_EMAIL = "you@example.com"
```
```bash
# Mac / Linux
export SEC_CONTACT_EMAIL="you@example.com"
```
```bash
pip install -r pipeline/requirements.txt pytest
python -m pytest -q                 # offline tests, no network
python -m pipeline.discover         # a few requests: checks both sources and prints what came back
python -m pipeline.run              # about 5-8 minutes (SEC allows max 10 requests/second, we use ~4)
npm install
npm run dev                         # http://localhost:3000
```
For a quick first run: `python -m pipeline.run --max-companies 100`.

## Deploy for free
1. Push to a **public** GitHub repo.
2. Settings > Secrets and variables > Actions > New repository secret: `SEC_CONTACT_EMAIL` = your email.
3. Actions tab > **Refresh risk data** > Run workflow (do this before the first Vercel deploy).
   It then runs daily, commits the new data, and Vercel redeploys.
4. Import the repo on vercel.com.
5. If a run fails, GitHub emails you and the site keeps the old data marked **stale**.

Optional: `NEXT_PUBLIC_PORTFOLIO_URL` shows a "Portfolio" back link.

## What it does and does not do
- Name matching is **not** a sanctions determination. "Same name" means the words are the same (any
  order, spacing ignored); "Similar name" means strong word overlap. One-word queries only match exactly,
  to avoid hundreds of false hits. Weak aliases on the OFAC list are skipped. Always confirm in OFAC's
  official search tool.
- SEC signals are facts from a company's own filings (8-K items 1.03, 3.01, 4.01, 4.02, 1.05, 2.04, 2.06,
  forms NT 10-K, NT 10-Q, Form 15). No risk score is calculated and none is implied.
- Coverage: the largest `MAX_COMPANIES` (1500) US-listed companies, last 12 months. Private companies are
  not covered.
- OFAC file locations have changed in the past. `pipeline/config.py` lists two; run `discover` to confirm
  that one works. SEC is asked politely: 0.25 s between requests, and the run stops at once on HTTP 403/429.
- Only company names, tickers, industry and filing facts are published. OFAC remarks and addresses are not.

Not affiliated with OFAC, the US Treasury or the SEC. Not legal advice.
