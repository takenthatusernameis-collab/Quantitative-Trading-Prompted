# Next Agent Task: Cycle 2 - Baseline US Equity Time-Series Momentum

## Context

Cycle 1 completed data inventory and opportunity scoping. The highest-scoring opportunity is US Equity Time-Series Momentum (28/35), selected for:
- Longest verified data history (SPY from 1993, QQQ from 1999, IWM from 2000, 25-30+ years)
- Lowest implementation complexity (daily rebalancing, simple ranking)
- Best diversification from existing large-cap crypto exposure
- Realistic cost model available in `config/settings.yaml`
- Well-documented structural mechanism (time-series momentum anomaly)

Data availability verified via live API:
- yfinance provides daily OHLCV for SPY (8,482 days), QQQ (6,940 days), IWM (6,632 days)
- Settings.yaml defines: 1.0 bps commission, 2.0 bps slippage, 2.0% risk-free rate
- No data currently cached locally; pipeline must fetch at runtime

## Objective

Implement a transparent baseline time-series momentum strategy on US equity ETFs, run a chronological split backtest (train/validation/test), and document results. This validates the end-to-end research pipeline (data ingestion → strategy → backtest → evaluation → documentation) before advancing to more complex opportunities.

## Acceptance Criteria

1. **Data pipeline** created at `src/data/yfinance_fetcher.py` that:
   - Fetches daily OHLCV from yfinance for SPY, QQQ, IWM, TLT, GLD, EFA, EEM
   - Caches results to `data/raw/` as parquet files
   - Returns timezone-normalized daily data with no missing dates
   - Accepts start_date, end_date, and symbol list as parameters

2. **Strategy module** created at `src/features/momentum.py` that:
   - Computes 12-month price momentum (12-month return excluding most recent 1 month) for each asset
   - Ranks assets and selects top decile (or top 50% for small universe)
   - Returns position weights (long-only, dollar-neutral not required)
   - Uses only lagged data (point-in-time, no look-ahead bias)

3. **Backtest engine** created at `src/backtest/engine.py` that:
   - Executes daily rebalancing per strategy signals
   - Applies commission (1.0 bps) and slippage (2.0 bps) from settings.yaml
   - Uses chronological train/validation/test split:
     - Train: 1993-01-01 to 2009-12-31
     - Validation: 2010-01-01 to 2017-12-31
     - Test: 2018-01-01 to 2026-10-09 (most recent)
   - Computes: cumulative returns, annualized return, annualized volatility, Sharpe ratio, max drawdown, turnover, trade count

4. **Baseline results** written to `research/experiments/tsmomentum_baseline_001.md` containing:
   - Hypothesis reference (documented here inline)
   - Data used (source, date range, frequency, universe)
   - Point-in-time treatment description
   - Configuration (parameters, hyperparameters)
   - Train/validation/test split dates
   - Results: all metrics for each period
   - Number of trades/observations
   - Cost assumptions used
   - Reproduction commands

5. **Hypothesis document** created at `research/hypotheses/tsmomentum_001.md` containing:
   - Mechanism description (time-series momentum via underreaction/slow diffusion)
   - Expected direction and magnitude (positive carry, 3-8% annualized gross)
   - Holding horizon (monthly rebalance, 20-day holding)
   - Asset universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM)
   - Features and data sources (12-month price momentum, yfinance daily)
   - Entry/exit rules (rank by 12-month return, go long top 50%, rebalance monthly)
   - Benchmark (equal-weighted portfolio of same assets)
   - Known confounders (regime changes, volatility clustering, transaction costs)
   - Falsification condition (test Sharpe < 0.5 net of costs OR test Sharpe < train Sharpe - 1 std)
   - Cost model assumptions (1.0 bps commission, 2.0 bps slippage, 2.0% risk-free rate)

## Validation Commands

```bash
# Verify source files exist
test -f src/data/yfinance_fetcher.py && wc -l src/data/yfinance_fetcher.py
test -f src/features/momentum.py && wc -l src/features/momentum.py
test -f src/backtest/engine.py && wc -l src/backtest/engine.py
test -f research/hypotheses/tsmomentum_001.md && wc -l research/hypotheses/tsmomentum_001.md
test -f research/experiments/tsmomentum_baseline_001.md && wc -l research/experiments/tsmomentum_baseline_001.md

# Run the backtest reproduction
python3 src/backtest/engine.py --output-dir research/experiments

# Check experiment report has required sections
grep -c "Hypothesis" research/experiments/tsmomentum_baseline_001.md
grep -c "Data Used" research/experiments/tsmomentum_baseline_001.md
grep -c "Results" research/experiments/tsmomentum_baseline_001.md

# Check hypothesis doc has required sections
grep -c "Mechanism" research/hypotheses/tsmomentum_001.md
grep -c "Falsification" research/hypotheses/tsmomentum_001.md
```

## Scope Boundaries

- **Do not** attempt live trading or connect to broker APIs
- **Do not** add new dependencies beyond those in requirements.txt (yfinance, ccxt, pandas, numpy, vectorbt may be used)
- **Do not** claim statistical significance beyond what data supports
- **Do not** tune parameters to maximize test-period returns (predefined 12-month lookback, top 50% selection, monthly rebalance)
- **Do** implement the strategy as a transparent baseline before any parameter exploration or ML enhancement (per AGENTS.md: baseline before complexity)
- **Do** document all results honestly, including negative outcomes
- **Do** label results as exploratory signal or rejected even if positive, pending further validation
