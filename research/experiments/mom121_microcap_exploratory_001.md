# Exploratory Diagnostic: Microcap mom121 — Pipeline Mechanics Verification

**Date:** 2026-10-15
**Status:** EXPLORATORY DIAGNOSTIC ONLY — NOT CONFIRMATORY — SURVIVORSHIP BIASED — CURRENT TICKERS APPLIED RETROSPECTIVELY
**Hypothesis reference:** `research/hypotheses/mom121_microcap_001.md`
**Data source survey:** `research/reports/microcap_datasource_survey_001.md`

---

## IMPORTANT DISCLOSURES

- **This is an exploratory diagnostic only.** No performance metrics (Sharpe, returns, drawdowns) are reported as evidence of a tradable edge.
- **No point-in-time microcap universe was constructed.** The test basket uses current ETF tickers from `data/raw/` (SPY, QQQ, IWM, EFA, EEM) as a code-mechanics test. This introduces severe survivorship bias and look-ahead bias.
- **No free data source surveyed provides all required elements** (point-in-time market cap, delisting events, point-in-time universe membership) at low friction.
- **The microcap mom121 hypothesis remains BLOCKED by data/infrastructure** for confirmatory testing.

---

## 1. Data Source Survey Summary

A survey of 7 free/accessible data sources was conducted. Full details: `research/reports/microcap_datasource_survey_001.md`.

| Source | Point-in-time Market Cap | Delisting Events | Historical Shares | Free? | Viable for Microcap Universe? |
|--------|--------------------------|------------------|------------------|-------|-------------------------------|
| yfinance | Approximate (shares × price) | No | Yes (sparse) | Yes | Partially viable (exploratory only) |
| Polygon.io | Partial (per filing) | Possibly | Likely | Limited free tier | Partially viable (with API key) |
| Alpha Vantage | No (snapshot only) | No | No | Limited free tier | Not viable |
| IEX Cloud | No (snapshot only) | No | No | Limited free tier | Not viable |
| SEC EDGAR | Approximate (shares × price) | Inferred | Yes (quarterly XBRL) | Yes | Partially viable (high effort) |
| FRED | No | No | No | Free with key | Not viable |
| Other sources | No | No | No | Varies | Not viable |

**Conclusion:** No free source is fully viable for a confirmatory microcap study. yfinance offers the lowest-friction exploratory path with full bias disclosure.

---

## 2. Exploratory Diagnostic Results

Script: `research/run_microcap_exploratory.py`

### Test Universe
- **Assets:** SPY, QQQ, IWM, EFA, EEM (current ETF tickers, NOT microcap stocks)
- **Date range:** 2003-04-14 to 2026-10-14
- **Observations:** 5,914 trading days

### Test 1: Daily Momentum Convention (existing code)
- `compute_momentum(prices, lookback=252, skip=21)` → `Price(t-21)/Price(t-273) - 1`
- Shape: (5641, 5) after dropna
- Non-NaN values: 28,205
- Pipeline mechanics: working correctly

### Test 2: Monthly Momentum Convention (hypothesis spec)
- `MOM(t) = Price(end of t-1 month) / Price(end of t-12 months) - 1`
- Shape: (271, 5)
- Non-NaN values: 1,355
- Pipeline mechanics: working correctly

### Test 3: Convention Comparison
Material discrepancy between daily and monthly conventions (e.g., SPY 2026-09-30: daily=0.1820, monthly=0.1514, diff=0.0306). Confirms the code's daily convention is NOT the monthly calendar-month convention specified in the hypothesis.

### Test 4: Weights Pipeline
- Periods with active weights: 5,640
- Avg active positions: 3.00 (top half of 5 assets)
- Weights sum to 1.0
- Point-in-time shift applied correctly

### Test 5: Small Universe Behavior
- When n_assets < 5, code picks single best asset per period
- Edge cases handled gracefully

---

## 3. Bias Disclosures

1. **Survivorship bias:** Only current ETF tickers tested; microcap and delisted stocks absent.
2. **Look-ahead bias:** Current tickers applied retrospectively; not a point-in-time universe.
3. **No cost model:** No transaction costs, slippage, or market impact applied.
4. **Not microcap:** Test basket consists of broad equity ETFs, not microcap stocks.
5. **Signal definition discrepancy:** Existing code uses daily 273-trading-day lookback, not the monthly 12-1 convention specified in the hypothesis.

---

## 4. Verdict

**BLOCKED by data/infrastructure.** No free data source surveyed can construct a point-in-time microcap universe with historical market cap, delisting coverage, and point-in-time membership. The exploratory diagnostic confirms code mechanics are intact but cannot test the economic hypothesis. For a confirmatory study, CRSP/Compustat (paid/academic) remains the standard choice.

---

## 5. Verification

```bash
# Survey document structure
python3 -c "
import os
path = 'research/reports/microcap_datasource_survey_001.md'
assert os.path.exists(path)
with open(path) as f:
    content = f.read()
required = ['Source', 'Coverage', 'Frequency', 'History', 'Licensing', 'Accessibility', 'Assessment']
for r in required:
    assert r.lower() in content.lower(), f'Missing: {r}'
print('Survey document structure OK')
"

# Exploratory script
PYTHONPATH=. .venv/bin/python3 research/run_microcap_exploratory.py

# Existing test suite
.venv/bin/python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

**Observed:** Survey structure assertion passed. Exploratory script ran successfully (5 tests, all passed). Existing test suite: 10/10 passed.