# Next Agent Task: Microcap Data Source Survey & Exploratory Diagnostic

## Context
The overnight drift exploratory diagnostic (overnight_drift_001) is complete. Results show:
- US broad equity ETFs (SPY, QQQ, IWM): Overnight returns positive and statistically significant (p < 0.05), intraday returns near zero/negative
- Sector ETFs: Similar pattern — overnight positive, intraday slightly negative
- International (EFA, EEM): Mixed — EFA shows intraday dominance, EEM shows overnight dominance
- Bonds (TLT): Intraday positive, overnight negative
- Commodities (GLD, DBC): Overnight positive (GLD strongly), intraday near zero
- REITs (VNQ): Overnight strongly positive, intraday negative
- ^VIX: Extreme overnight positive, intraday negative (non-tradeable index)

Sub-period analysis reveals instability: the overnight effect was strong pre-2008, weakened 2008-2020, and shows mixed signs post-2020. Per the pre-committed decision discipline, this is labeled **"exploratory signal"** — statistically significant in some segments but not stable, with material limitations (no bid-ask spreads, daily data only, survivorship bias, no cost model).

The microcap mom121 hypothesis remains **blocked by data** (no point-in-time market cap, shares outstanding, or delisting data from yfinance). All other tested hypotheses (C3, C4, C5, C6) have been rejected via pre-registered walk-forward tests. Paper trading monitoring continues but no new data has arrived recently.

## Objective
Conduct a survey of **free/accessible data sources** that could enable the microcap 12–1 momentum study, and run a **clearly-labelled exploratory diagnostic** on any viable source to assess feasibility. Do not claim a tradable edge.

## Acceptance Criteria
1. **Data source survey document created**: `research/reports/microcap_datasource_survey_001.md` documenting at least 5 free/accessible sources with:
   - Source name and access method (API, CSV download, etc.)
   - Data coverage: historical market cap, shares outstanding, delisting events, price data
   - Frequency and history depth
   - Licensing/terms of use
   - Technical accessibility (Python library, REST API, manual download)
   - Assessment: viable / partially viable / not viable for point-in-time microcap universe construction

2. **If any source is viable/partially viable**: Create an exploratory diagnostic script `research/run_microcap_exploratory.py` that:
   - Loads data from the source (or documents how to access it)
   - Constructs a point-in-time microcap universe (or documents blockers)
   - Computes 12-month momentum with 1-month skip (mom121) on available data
   - Produces summary statistics: universe size over time, turnover, return distribution
   - Outputs to `research/experiments/mom121_microcap_exploratory_001.md`

3. **Report must explicitly label results as "exploratory diagnostic only"** and disclose all biases (survivorship, lookahead, data quality, no costs).

4. **If NO source is viable**: Document the definitive blockers and recommend the microcap hypothesis be archived as "blocked by data/infrastructure" pending paid data access.

## Validation Commands
```bash
# 1. Verify survey document exists and has required content
python3 -c "
import os
path = 'research/reports/microcap_datasource_survey_001.md'
assert os.path.exists(path), 'Survey document missing'
with open(path) as f:
    content = f.read()
required = ['Source', 'Coverage', 'Frequency', 'History', 'Licensing', 'Accessibility', 'Assessment']
for r in required:
    assert r.lower() in content.lower(), f'Missing section: {r}'
print('Survey document structure OK')
"

# 2. If diagnostic script exists, run it
if [ -f research/run_microcap_exploratory.py ]; then
    python3 research/run_microcap_exploratory.py
fi

# 3. Verify experiment report exists (if diagnostic ran)
if [ -f research/experiments/mom121_microcap_exploratory_001.md ]; then
    python3 -c "
    import os
    path = 'research/experiments/mom121_microcap_exploratory_001.md'
    with open(path) as f:
        content = f.read()
    assert 'exploratory' in content.lower(), 'Must label as exploratory'
    assert 'microcap' in content.lower() or 'momentum' in content.lower(), 'Must discuss microcap/momentum'
    print('Experiment report structure OK')
    "
fi
```

## Scope Boundaries
- **Do not** claim a net-of-cost trading edge.
- **Do not** use paid data sources (Bloomberg, CRSP, Compustat, FactSet, etc.) — only free/accessible sources.
- **Do not** add new dependencies unless absolutely necessary for a free data source (document any new dependency).
- **Do** use only existing infrastructure where possible.
- **Do** follow the hypothesis documentation standard in AGENTS.md for any new hypothesis.
- **Do** disclose all limitations honestly.

## Evidence Base
- Overnight drift diagnostic complete: `research/experiments/overnight_drift_exploratory_001.md`
- Microcap data gate audit: `research/experiments/mom121_microcap_001.md` (Section A)
- Data inventory: `research/reports/data_inventory.md` (if exists)
- Available free data sources to investigate: Yahoo Finance (yfinance), Alpha Vantage (free tier), Twelve Data (free tier), EODHD (free tier), Nasdaq Data Link (free datasets), SEC EDGAR (fundamentals), IEX Cloud (free tier), Polygon.io (free tier), Tiingo (free tier), Kenneth French Data Library, WRDS (if academic access), QuantConnect Lean data, Stooq, Tiingo, FirstRate Data (free samples), Kaggle datasets.

## Suggested Approach
1. Start with the data source survey — this is the primary deliverable.
2. For each source, test programmatic access with a small query (e.g., get AAPL market cap history).
3. Focus on sources that provide **historical market cap** or **shares outstanding × price** at point-in-time.
4. Note: yfinance `Ticker.info` only provides *current* marketCap, not historical. `Ticker.quarterly_balance_sheet` may have shares outstanding but with reporting lag.
5. If a viable source is found, run a minimal exploratory diagnostic on a small universe (e.g., current S&P 500 constituents with historical data) to characterize data quality.
6. If no viable source, document clearly and recommend archiving the microcap hypothesis.

(End of file - total 65 lines)