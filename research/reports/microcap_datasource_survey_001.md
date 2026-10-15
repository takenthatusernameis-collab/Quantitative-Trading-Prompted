# Free Data Source Survey for Point-in-Time Microcap Market Cap

**Date:** 2026-10-15
**Objective:** Survey freely accessible data sources to determine which can provide
point-in-time market capitalization (or shares outstanding) for individual US stocks —
the missing field that blocks the microcap data gate.

**Status:** EXPLORATORY DIAGNOSTIC ONLY. No tradable edge is claimed.

---

## Executive Summary

Of 8 free/accessible sources surveyed, **SEC EDGAR (XBRL companyfacts API)** is the only
source that provides point-in-time shares outstanding with filing dates for the full
public-company universe, including small caps. It is assessed **VIABLE** for an
exploratory diagnostic. yfinance is **PARTIALLY VIABLE** (historical shares outstanding
for liquid names only, ~1.5yr history, no delistings). All other surveyed sources
(alpha Vantage, IEX Cloud, Polygon.io, FRED, Twelve Data, EODHD, Nasdaq Data Link,
QuantConnect, Stooq, Tiingo, Kaggle) are **NOT VIABLE** for point-in-time microcap
universe construction within free tiers.

**Bottom line:** A point-in-time microcap universe can be approximated for an
exploratory diagnostic using SEC EDGAR XBRL shares outstanding + yfinance/close prices,
but it carries material limitations (quarterly reporting lag, no delisting events,
survivorship bias, approximate market cap). It is **NOT sufficient** for a confirmatory
microcap 12-1 momentum test.

---

## Source-by-Source Assessment

## 1. yfinance (installed: yes, v1.7.0)

- **Access:** Free, no API key. Python package `yfinance` (already in requirements.txt).
- **Coverage:** Historical OHLCV for most public US stocks/ETFs; historical shares
  outstanding via `Ticker.get_shares_full()` for liquid tickers.
- **Frequency/History:** Daily price history back decades. Shares outstanding history
  is irregular and typically ~1.5 years for liquid names (verified: AAPL shares_full
  spans 2025-04-16 to 2026-08-05, 58 rows).
- **Licensing/Terms:** Free for research; no warranty on accuracy.
- **Technical accessibility:** Python library, no auth.
- **Point-in-time market cap:** Approximate only — `shares × close`, requires
  forward-fill alignment of irregular shares series. Not directly provided.
- **Delisting events:** Not provided.
- **Point-in-time universe screening:** Not reliably possible — shares data sparse
  for microcap names; no delisting data → survivorship bias.
- **Assessment:** PARTIALLY VIABLE for exploratory diagnostic (liquid names only).
  Not viable for confirmatory microcap test.

## 2. SEC EDGAR / XBRL Companyfacts API (installed: no; accessed via HTTPS, no key)

- **Access:** Free, no API key. Requires a descriptive User-Agent header.
- **Coverage:** All US public companies that file (10-K/10-Q/A), including small caps
  and delisted entities (final filings retained). Verified: 10,451 entities in
  `company_tickers.json`; XBRL shares outstanding available for sampled small caps
  (AVLN: 4 records, EPAM: 116, CTS: 181, KIM-PM: 146).
- **Frequency/History:** Quarterly/annual fundamental observations tagged with `end`
  (period-end date) and `filed` (filing date). History extends as far back as filings
  exist (decades for mature names).
- **Licensing/Terms:** Public domain; fair-use rate limits (~10 req/s with good UA).
- **Technical accessibility:** REST JSON, no auth. `requests` (already installed).
- **Point-in-time market cap:** Not directly provided; approximated as
  `shares_outstanding × close_price` where close is merged from yfinance.
- **Delisting events:** Not directly provided; can be inferred from cessation of
  filings (imperfect, delayed).
- **Point-in-time universe screening:** Possible by aggregating shares per filing
  date, forward-filling to daily price dates, and filtering by approximate market
  cap. Universe membership is complete for filers.
- **Assessment:** VIABLE for exploratory diagnostic. Primary blocker resolved:
  point-in-time shares outstanding with filing dates is available for small caps.
  Remaining limitations: quarterly lag, no formal delisting file, approximate
  market cap, XBRL parsing complexity.

## 3. Alpha Vantage (installed: no; free tier with API key)

- **Access:** Free tier with API key (demo key available).
- **Coverage:** Current market cap via `OVERVIEW` endpoint (`MarketCapitalization`
  field). No historical market cap or shares outstanding time series.
- **Frequency/History:** Snapshot only.
- **Licensing/Terms:** Free tier; rate limits.
- **Technical accessibility:** REST API, key required.
- **Point-in-time market cap:** Not available.
- **Delisting events:** Not provided.
- **Assessment:** NOT VIABLE. Snapshot-only fundamental data.

## 4. IEX Cloud (installed: no; free tier with API key)

- **Access:** Free tier with API key.
- **Coverage:** Current market cap via `/stock/{symbol}/quote`. Historical
  fundamentals not in free tier.
- **Frequency/History:** Snapshot only in free tier.
- **Licensing/Terms:** Free tier; rate limits.
- **Technical accessibility:** REST API, key required.
- **Point-in-time market cap:** Not available in free tier.
- **Delisting events:** Not documented in free endpoints.
- **Assessment:** NOT VIABLE. Lacks historical point-in-time fundamentals.

## 5. Polygon.io (installed: no; free tier with API key)

- **Access:** Free tier with API key (verified: API returns "API Key was not
  provided" without key).
- **Coverage:** Fundamentals endpoint (`/vX/reference/financials`) may report market
  cap per filing; point-in-time semantics unverified at free tier.
- **Frequency/History:** Varies by plan.
- **Licensing/Terms:** Free tier; rate limits.
- **Technical accessibility:** REST API, key required.
- **Point-in-time market cap:** Possible in principle (per-filing fundamentals) but
  unverified for free tier coverage of microcaps.
- **Delisting events:** Possibly via corporate actions endpoints (unverified).
- **Assessment:** NOT VIABLE without credentials. Cannot be tested under task
  constraints (no paid accounts or credentials).

## 6. FRED (Federal Reserve Economic Data) (installed: no; API key for most endpoints)

- **Access:** Free, API key for most endpoints.
- **Coverage:** Macroeconomic/regional/international series only. No individual
  equity fundamental data.
- **Frequency/History:** Varies by series.
- **Licensing/Terms:** Free; attribution required.
- **Technical accessibility:** REST API, key required.
- **Point-in-time market cap:** Not provided.
- **Delisting events:** Not provided.
- **Assessment:** NOT VIABLE. No equity fundamental data.

## 7. Other Free Sources (surveyed from repository references)

| Source | Access | Historical Market Cap | Delistings | Assessment |
|---|---|---|---|---|
| Twelve Data | Free tier, API key | Limited | Limited | NOT VIABLE |
| EODHD | Free tier, API key | Limited | Limited | NOT VIABLE |
| Nasdaq Data Link | Free datasets, API key | Limited | No | NOT VIABLE |
| QuantConnect Lean Data | Free tier | Limited | No | NOT VIABLE |
| Stooq | CSV download, free | No fundamentals | No | NOT VIABLE |
| Tiingo | Free tier, API key | Limited | No | NOT VIABLE |
| Kaggle datasets | Manual download | Static snapshots only | No | NOT VIABLE (static, not point-in-time) |
| Kenneth French Data Library | Free, web/HTTPS | No (factor/returns only) | No | NOT VIABLE |
| WRDS | Academic access required | Yes (CRSP/Compustat) | Yes | NOT ACCESSIBLE (no academic subscription) |

None of these provide point-in-time historical market cap or shares outstanding
for a microcap universe within free tiers.

---

## Summary Scoring Table

| # | Source | (a) Data quality | (b) Structural mechanism | (c) Return after costs | (d) Robustness/ power | (e) Liquidity/ capacity | (f) Automation | (g) Diversification | Overall |
|---|---|---|---|---|---|---|---|---|---|
| 1 | yfinance | 4/10 | 3/10 | 3/10 | 3/10 | 4/10 | 9/10 | 4/10 | PARTIALLY VIABLE |
| 2 | SEC EDGAR XBRL | 8/10 | 6/10 | 3/10 | 5/10 | 6/10 | 7/10 | 6/10 | **VIABLE (exploratory)** |
| 3 | Alpha Vantage | 2/10 | 1/10 | 1/10 | 1/10 | 3/10 | 6/10 | 3/10 | NOT VIABLE |
| 4 | IEX Cloud | 2/10 | 1/10 | 1/10 | 1/10 | 3/10 | 6/10 | 3/10 | NOT VIABLE |
| 5 | Polygon.io | 3/10 | 3/10 | 2/10 | 2/10 | 4/10 | 6/10 | 4/10 | NOT ACCESSIBLE |
| 6 | FRED | 1/10 | 1/10 | 1/10 | 1/10 | 2/10 | 7/10 | 2/10 | NOT VIABLE |
| 7 | Others (12 Data, EODHD, Nasdaq, QuantConnect, Stooq, Tiingo, Kaggle, French, WRDS) | 1-3/10 | 1/10 | 1/10 | 1-2/10 | 2-4/10 | 4-7/10 | 2-4/10 | NOT VIABLE / NOT ACCESSIBLE |

Scoring rubric: 1-10 per criterion. (a) data quality/access, (b) plausible
structural explanation, (c) expected return after costs, (d) robustness and
statistical power, (e) liquidity/capacity, (f) automation/operating burden,
(g) diversification from existing research.

---

## Recommended Path for Exploratory Diagnostic

**Primary:** SEC EDGAR XBRL companyfacts API for point-in-time shares outstanding,
merged with yfinance close prices for market-cap approximation.

**Fallback:** yfinance `get_shares_full()` × close for liquid tickers only
(accept severe limitations).

**Definitive (not available):** CRSP/Compustat monthly stock file — the gold
standard for point-in-time microcap research with survivorship-bias corrections
and delisting files. Requires academic/subscription access not available here.
