# Paper-Trading Validation Report — Cycle 38

**Generated:** 2026-10-14 07:16:00 UTC
**Hypothesis:** Incumbent TSMOM (tsmomentum_spytrend_001) prospective validation via deterministic historical replay.
**Cycle:** 38

## Objective

Re-attempt data acquisition from Yahoo Finance when/if more trading days become available. Continue to monitor the rolling 63-day Sharpe trajectory.

## Data Acquisition

- Command: `python -c "from src.data.yfinance_fetcher import fetch_universe; data=fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'],'1993-01-01','2026-11-30',force=True); print(data.index.max().date())"`
- Result: Latest available date = **2026-10-13** (1 new trading day beyond 2026-10-12). No further trading days available as of the 2026-10-14 fetch.
- Raw cache after fetch: all 7 incumbent ETFs end at 2026-10-13; ^VIX ends at 2026-10-13 (8,505 rows, 1993-01-04 → 2026-10-13).

## Root-Cause Finding: Off-by-One in Replay `end_date`

Investigation revealed that **yfinance treats the `end` parameter as EXCLUSIVE**. The replay script requested `end_date="2026-10-13"`, which returned data only through 2026-10-12, silently truncating the cache and the track record by one trading day. This explains why Cycles 31, 35, and 37 reported the track record ending at 2026-10-12 despite the raw cache showing 2026-10-13 — the replay's own `force=True` re-fetch overwrote the cache back to 2026-10-12 on every run.

**Fix applied** (`research/run_paper_trading_replay.py:44`): changed `end_date` from `"2026-10-13"` to `"2026-10-14"` (yfinance exclusive-end semantics), with a comment documenting the off-by-one. The replay-date upper bound is now hardcoded to `"2026-10-13"` so the replayed window is invariant regardless of the fetch end date.

## Replay Results (after fix)

Command: `python research/run_paper_trading_replay.py`

| Metric | Value |
|---|---|
| Track record length | **446 days** (2025-01-02 → 2026-10-13) |
| Current NAV | $136,593.98 |
| Total Return | +36.59% |
| Annualized Return | 19.27% |
| Volatility (ann.) | 9.53% |
| Sharpe Ratio | 2.0210 |
| Max Drawdown | -1.82% |
| Regime flips | 6 (3 risk-on→risk-off, 3 risk-off→risk-on) |
| Regime persistence | 131 days (risk-on, SPY ≥ 200-day SMA) |

## Drift Flag Status

- **`low_rolling_sharpe`**: value **0.3669** on 2026-10-13 (threshold 0.5) — **PERSISTS**.
- **Duration: 2 consecutive trading days** (2026-10-12: 0.4892; 2026-10-13: 0.3669).
- Rolling 63-day Sharpe trajectory (last 10 days): 0.1789, 0.3330, 0.3077, 0.9920, 0.9994, 0.4728, 0.1902, 0.9356, 0.4892, 0.3669.
- The trajectory is volatile day-to-day (range 0.18–1.00 over the last 10 days), consistent with a single low-return day moving the 63-day window rather than sustained degradation. Not yet at the >20-day persistence threshold for formal degradation assessment.

## Go/No-Go Gates

All primary gates from Cycle 22 still pass with margin:

| Gate | Threshold | Actual | Status |
|---|---|---|---|
| Track record length | >126 days | 446 days | PASS |
| Net-of-Cost Sharpe | ≥0.9 | 2.0210 | PASS |
| Maximum drawdown | <15% | -1.82% | PASS |
| Regime flips | >1 | 6 | PASS |

## Data Integrity

- All 7 incumbent ETF parquet files (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) end at **2026-10-13**.
- ^VIX.parquet: 8,505 rows, 1993-01-04 → 2026-10-13 (not used by incumbent strategy).
- State YAML header (`last_run_date: 2026-10-13`) matches final `run_history` entry. `run_history` length = 446.

## Scope Boundaries

- No modification to incumbent strategy logic (`config/simulation_candidate_001.yaml` is frozen).
- No new dependencies, services, or infrastructure added.
- Research/backtesting only; no live trades.

## Next Cycle Recommendation

Re-attempt data acquisition when more trading days elapse. Continue monitoring the rolling 63-day Sharpe trajectory. If the `low_rolling_sharpe` flag persists beyond 20 consecutive trading days once extended, assess whether the momentum signal is degrading in the current low-volatility risk-on regime.