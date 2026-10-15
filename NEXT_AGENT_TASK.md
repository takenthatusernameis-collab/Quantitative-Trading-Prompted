# Next Agent Task: Overnight Drift Exploratory Diagnostic

## Context
The ETF OHLCV data pipeline has been verified and is functioning correctly (data fetch, caching, schema, integrity, feature pipeline). The microcap mom121 hypothesis remains blocked by lack of point-in-time market cap and delisting data. All previously tested hypotheses (cross-sectional momentum C3, sector rotation C4, calendar effects C6, macro regime overlay C5) have been rejected via pre-registered walk-forward tests. Paper trading monitoring of the incumbent TSMOM strategy continues but no new data has arrived recently.

The available data in `data/raw/` includes daily OHLCV for 19 ETFs/indices (SPY, QQQ, IWM, TLT, GLD, EFA, EEM, DBC, VNQ, XLB–XLY, ^VIX) with sufficient history (1993–2026). A well-documented structural mechanism testable with daily OHLCV is **overnight drift**: the tendency for equity returns to accrue predominantly during the overnight session (close-to-open) rather than the intraday session (open-to-close), driven by information accumulation, market maker inventory management, and institutional rebalancing flows outside regular hours.

## Objective
Conduct a clearly-labelled exploratory diagnostic of overnight drift on the ETF universe using existing daily OHLCV data. Document the hypothesis, compute overnight/intraday/total returns, and produce a summary report — without claiming a tradable edge.

## Acceptance Criteria
1. **Hypothesis document created**: `research/hypotheses/overnight_drift_001.md` with mechanism, expected direction, holding horizon, universe, features, entry/exit rules, benchmark, confounders, falsification condition, and cost model assumptions.
2. **Diagnostic script created**: `research/run_overnight_drift_exploratory.py` that:
   - Loads daily OHLCV for all 19 symbols from `data/raw/`
   - Computes overnight return (Open_t / Close_{t-1} - 1), intraday return (Close_t / Open_t - 1), total return (Close_t / Close_{t-1} - 1)
   - Computes cumulative sums and annualized statistics for each session
   - Tests session effect across multiple sub-periods (pre-2008, 2008-2020, 2020+)
   - Outputs results to `research/experiments/overnight_drift_exploratory_001.md`
3. **Report includes**: per-symbol session return decomposition, statistical significance (t-test vs zero), sub-period stability, turnover/feasibility notes, and explicit limitations (no intraday execution data, bid-ask spreads not observed, survivorship bias in ETF universe).
4. **No alpha claims**: Report must explicitly label results as "exploratory diagnostic only" and disclose all biases.

## Validation Commands
```bash
# 1. Verify hypothesis document exists and has required sections
python3 -c "
import os
path = 'research/hypotheses/overnight_drift_001.md'
assert os.path.exists(path), 'Hypothesis document missing'
with open(path) as f:
    content = f.read()
required = ['Mechanism', 'Expected direction', 'Holding horizon', 'Asset universe', 'Features', 'Entry/exit rules', 'Benchmark', 'Known confounders', 'Falsification condition', 'Cost model']
for r in required:
    assert r.lower() in content.lower(), f'Missing section: {r}'
print('Hypothesis document structure OK')
"

# 2. Run diagnostic script
python3 research/run_overnight_drift_exploratory.py

# 3. Verify experiment report exists
python3 -c "
import os
path = 'research/experiments/overnight_drift_exploratory_001.md'
assert os.path.exists(path), 'Experiment report missing'
with open(path) as f:
    content = f.read()
assert 'exploratory' in content.lower(), 'Must label as exploratory'
assert 'overnight' in content.lower(), 'Must discuss overnight returns'
assert 'intraday' in content.lower(), 'Must discuss intraday returns'
print('Experiment report structure OK')
"
```

## Scope Boundaries
- **Do not** claim a net-of-cost trading edge.
- **Do not** add new data sources or dependencies.
- **Do not** run walk-forward optimization or backtest a strategy.
- **Do** use only existing `data/raw/` parquet files.
- **Do** follow the hypothesis documentation standard in AGENTS.md.
- **Do** disclose all limitations (daily data only, no spread/slippage, ETF survivorship, no point-in-time universe).

## Evidence Base
- Data pipeline verified: `src/data/yfinance_fetcher.py` produces timezone-aware UTC OHLCV with forward-filled alignment.
- Available symbols: SPY, QQQ, IWM, TLT, GLD, EFA, EEM, DBC, VNQ, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY, ^VIX.
- Prior rejected hypotheses archived in `research/experiments/` and `research/reports/`.