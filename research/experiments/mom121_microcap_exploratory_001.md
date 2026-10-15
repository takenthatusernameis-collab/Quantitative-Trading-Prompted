# Exploratory Diagnostic: Microcap 12-1 Momentum (mom121) via SEC EDGAR XBRL + yfinance

**Date:** 2026-10-15
**Status:** EXPLORATORY DIAGNOSTIC ONLY — NOT CONFIRMATORY — NO TRADABLE EDGE CLAIMED
**Hypothesis reference:** `research/hypotheses/mom121_microcap_001.md`
**Data sources:** SEC EDGAR XBRL companyfacts API (shares outstanding), yfinance (close prices)

---

## IMPORTANT DISCLOSURES

- **This is an exploratory feasibility diagnostic.** No performance metrics (Sharpe,
  returns, drawdowns) are reported as evidence of an edge.
- **Market cap is APPROXIMATED** as `shares_outstanding * close_price`. SEC XBRL reports
  shares quarterly/annually with filing lag; this is NOT a point-in-time microcap universe.
- **Survivorship bias:** the ticker set is applied retrospectively (current tickers only).
  Delisted names are absent (SEC EDGAR has no delisting file).
- **Look-ahead / revision risk:** shares are forward-filled from filing dates; revisions
  and restatements are not tracked.
- **No cost model** is applied. Turnover and slippage are NOT netted out.
- **Not a confirmatory backtest.** Results characterize data quality and pipeline mechanics.

---

## Data Sources Used

| Source | What it provides | Point-in-time? | Free? |
|---|---|---|---|
| SEC EDGAR XBRL companyfacts API | CommonStockSharesOutstanding per filing (period-end + filed date) | As-of filing date (quarterly lag) | Yes |
| yfinance | Daily adjusted close prices | Yes (data up to requested end date) | Yes |

SEC XBRL coverage verified for 38 tickers spanning mega-cap to micro-cap (see survey
`research/reports/microcap_datasource_survey_001.md`).

---

## Universe Construction

1. Fetch SEC XBRL `CommonStockSharesOutstanding` for each ticker (CIK lookup validated
   against `company_tickers.json`).
2. Build point-in-time daily shares series: assign each period-end value to its filing
   date, forward-fill to the next filing.
3. Fetch daily close from yfinance (2024-01-01 to 2026-10-15).
4. Align shares to price dates (forward-fill).
5. `market_cap = close * shares`.

**Tickers requested (38):** AAPL, AMTX, AMZN, AVGO, AVLN, BAC, BB, CRM, CTS, EPAM, GOOGL, HD, HOOD, HTZ, IONQ, JNJ, JPM, KIM-PM, LLY, MA, MEDS, META, MSFT, NOK, NVDA, OSIS, PATH, PG, PLTR, RBLX, SMCI, SNAP, TSLA, U, UNH, V, WMT, XOM

**Tickers with SEC XBRL shares data (33):** AAPL, AMTX, AMZN, AVGO, AVLN, BAC, BB, CRM, CTS, EPAM, GOOGL, HD, HOOD, HTZ, IONQ, JNJ, JPM, KIM-PM, LLY, MEDS, MSFT, NVDA, OSIS, PG, PLTR, RBLX, SMCI, SNAP, TSLA, U, UNH, WMT, XOM

**Tickers with NO SEC XBRL shares data (5):** MA, META, NOK, PATH, V

The uncovered names either do not file under US-GAAP XBRL (e.g. NOK files under IFRS), use a non-standard shares concept, or have no `CommonStockSharesOutstanding`/`CommonStockSharesIssued` history. They are dropped from the market-cap frame.

---

## Summary Statistics (descriptive only)

- Price/mcap date range: 2024-01-02 -> 2026-10-14
- Trading days: 699
- Max universe size (tickers with mcap): 31
- Mean universe size: 28.8
- Avg active positions (top-half momentum): 9.32
- Avg daily turnover: 0.0362
- p95 daily turnover: 0.1333
- Non-NaN momentum entries: 12495

### Market-cap buckets (latest snapshot)

- Large: 6
- Mega: 17
- Micro: 2
- Mid: 3
- Small: 3

---

## Biases and Limitations

1. **Survivorship bias:** retrospective ticker list; delistings absent.
2. **Quarterly reporting lag:** shares are stale between filings (up to ~90 days).
3. **Approximate market cap:** shares x close; price errors propagate.
4. **No delisting treatment:** bankrupt/failed names are not removed.
5. **No cost model:** turnover and slippage are NOT netted.
6. **Look-ahead/revision risk:** forward-filling may incorporate revisions not known as-of date.
7. **Microcap liquidity:** no volume/turnover filter; illiquid names dominate the universe.

---

## Verdict

SEC EDGAR XBRL resolves the **data gate blocker** for point-in-time shares outstanding
across the cap spectrum, enabling an exploratory diagnostic. However, the approximated
universe is **NOT sufficient** for a confirmatory microcap 12-1 momentum test due to
quarterly lag, absent delistings, survivorship bias, and lack of a cost model.

**Recommendation:** archive the microcap mom121 hypothesis as **blocked by data/infrastructure**
pending access to a point-in-time microcap dataset with delisting treatment (e.g., CRSP/Compustat).

---

## Reproduction

bash
python3 research/run_microcap_exploratory.py
