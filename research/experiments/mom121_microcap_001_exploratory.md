# Exploratory Diagnostic: Microcap mom121 — Code Mechanics Verification

**Date:** 2026-10-14
**Status:** EXPLORATORY — NOT CONFIRMATORY — SURVIVORSHIP BIASED — CURRENT TICKERS APPLIED RETROSPECTIVELY
**Hypothesis reference:** `research/hypotheses/mom121_microcap_001.md`
**Code revision:** current (with defensive fix to `src/features/momentum.py` to handle all-NA rows)

---

## IMPORTANT DISCLOSURES

- **This is exploratory code verification ONLY.** No performance metrics (Sharpe, returns, drawdowns) are reported as evidence of an edge.
- **Current tickers applied retrospectively.** The test basket uses today's ETF tickers from `data/raw/` (SPY, QQQ, IWM, EFA, EEM). This introduces severe survivorship bias and look-ahead bias; it does NOT constitute a valid point-in-time microcap universe.
- **Not a confirmatory backtest.** Results below verify pipeline mechanics only.

---

## Data used (exploratory)

| Asset | Source | Columns | Date range | Notes |
|---|---|---|---|---|
| SPY, QQQ, IWM, EFA, EEM | `data/raw/*.parquet` (cached ETF OHLCV) | Close (daily) | Varies by symbol (all end 2026-10-14) | Current constituents applied retrospectively; ETFs, not microcap stocks |

---

## 1) Free data source survey (repeated from audit)

See `research/experiments/mom121_microcap_001.md` Section A for full details. Key findings:

- **yfinance 1.7.0:** No `get_market_cap_history()`; `info` gives current-only market cap/shares. `get_shares_full()` can provide historical shares outstanding for liquid tickers (sparse/irregular, requires alignment/ffill), enabling approximate historical market cap = shares × price for those names. Cannot easily screen for microcap universe or get delisting events for illiquid/delisted names.
- **Other free sources:** ccxt (crypto only), fredapi, sec-edgar-downloader, pandas-datareader, quandl, finnhub, alpha_vantage, polygon, sec_api, nasdaq — **not installed** in the environment.
- **Repository cache:** 19 parquet files, all ETFs/indices only; **zero individual stock data files**.

**Conclusion:** Point-in-time microcap universe construction (with historical market cap, shares outstanding, delisting coverage, and point-in-time membership) is **not feasible** with the free sources accessible in this environment. Approximate market cap reconstruction via shares×price is possible only for liquid surviving tickers and is insufficient for proper point-in-time microcap screening with delisting treatment.

---

## 2) Momentum conventions tested

### A. Daily convention (existing code in `src/features/momentum.py`)
- `compute_momentum(prices, lookback=252, skip=21)`: `shifted = prices.shift(skip)`, `past = shifted.shift(lookback)`, `momentum = (shifted/past)-1`
- Formula: `Price(t-21 trading days) / Price(t-273 trading days) - 1` (span of 273 trading days ≈ 13.5 months)
- Uses trading-day offsets, not calendar month-ends.

### B. Monthly convention (hypothesis primary spec)
- `MOM(t) = AdjClose(end of t-1 month) / AdjClose(end of t-12 months) - 1` (calendar month-end endpoints)
- Computed via `prices.resample('ME').last().shift(1) / prices.resample('ME').last().shift(12) - 1`

**Observed difference (SPY, last overlapping month-ends):**
- 2026-07-31: daily=0.2070, monthly=0.1814, diff=0.0256
- 2026-08-31: daily=0.1774, monthly=0.1581, diff=0.0193
- 2026-09-30: daily=0.1820, monthly=0.1514, diff=0.0306

The discrepancy is material in magnitude and is expected due to different lookback windows (273 trading days vs 12 calendar months) and endpoint alignment. This confirms the code's daily convention is **not** the monthly calendar-month convention specified in the hypothesis.

---

## 3) Pipeline mechanics verification

### Test 4: Weights pipeline (`build_weights`, 5-asset universe)
- `build_weights(prices, lookback=252, skip=21, top_fraction=0.5)`
- Periods with active weights: 5640
- Avg active positions: 3.00 (for top half of 5 assets)
- Max active: 3, weights sum to 1.0
- Point-in-time shift applied (`weights.shift(1).fillna(0.0)`)

### Test 5: Small universe behavior
- When `n_assets < 5`, `select_top_decile` picks the single best asset per period (to avoid degenerate equal-weight splits). Verified behavior holds (edge cases handled gracefully with all-NA guards added).

---

## 4) Code fixes (minimal, justified)

Added defensive handling in `src/features/momentum.py`:
- `select_top_decile`: Skip rows where all momentum values are NA (return False mask for those dates). For `n_assets < 5`, iterate with `iterrows()` and skip all-NA rows before calling `idxmax()`. For `n_assets >= 5`, same guard applied before thresholding.

This prevents `ValueError: Encountered all NA values` from pandas operations when momentum contains all-NA rows (common in early history before sufficient lookback/skip). No change to signal logic, just robustness.

---

## 5) Ranked shortlist of data sources that COULD resolve the blocker

| Source | Point-in-time market cap | Delisting events | Historical shares out | Point-in-time universe | Free? | Effort | Notes |
|---|---|---|---|---|---|---|---|
| **CRSP (Center for Research in Security Prices)** | Yes (monthly/daily with point-in-time) | Yes (delisting file) | Yes | Yes | No (subscription/academic) | High | Gold standard for point-in-time research; includes survivorship bias corrections. |
| **Compustat** | Yes (point-in-time, with standardization) | Yes | Yes | Yes | No | High | Often combined with CRSP; fundamental + market data. |
| **Polygon.io** | Partial (depends on plan; tickers + fundamentals vary) | Varies | Varies | Varies | Limited free tier | Medium-High | API-based; need to verify point-in-time semantics and coverage. |
| **IEX Cloud** | Limited (mostly current/snapshots) | Limited | Limited | No | Limited | Medium | Better for real-time than full historical point-in-time universes. |
| **SEC EDGAR APIs** | No convenient time series | Filings only | Reported periodically | No | Free | High | Need to parse 10-K/Q for shares; not straightforward for screening. |
| **OpenBB / others** | Varies | Varies | Varies | Varies | Mixed | Medium | Many require credentials or have rate limits; not installed. |

**Lowest-friction credible path (recommendation):** For a proper confirmatory microcap study, **CRSP monthly stock file** (or CRSP+Compustat merged) is the standard choice providing point-in-time market cap, delisting events, and universe membership with correct survivorship handling. Without subscription access, the only viable path within free resources is to (1) construct historical market cap from yfinance `get_shares_full()` × close for liquid names where shares history exists, and (2) accept severe limitations (survivorship bias, missing delistings, poor microcap coverage). The latter is **not sufficient** for a confirmatory test per the hypothesis requirements.

---

## 6) Verification

```bash
# Run exploratory diagnostic
cd /home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/research && \
  PYTHONPATH=/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted python3 run_mom121_microcap_exploratory.py
```

**Observed:** All 5 test sections complete without errors after defensive fix. Conventions differ materially (daily vs monthly). Pipeline mechanics verified (weights, small-universe behavior, point-in-time shift).

---

## 7) Next steps (bounded)

The microcap mom121 hypothesis remains **BLOCKED by data/infrastructure** for confirmatory testing. The exploratory diagnostic confirms code mechanics are intact (with minor robustness fix). No code defects requiring changes to signal logic were found. The key blocker is acquiring point-in-time microcap data with proper delisting coverage.

**Recommendation for next task:** If proceeding with microcap, focus on data acquisition (CRSP/Compustat or building a careful free-data approximation with full bias disclosure). Alternatively, pivot to a hypothesis that can be tested with existing ETF data while preserving the research discipline.
