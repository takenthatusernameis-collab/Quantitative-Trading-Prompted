# Paper-Trading Validation Report — Cycle 42

**Generated:** 2026-10-14 07:35:00 UTC
**Hypothesis:** Incumbent TSMOM (tsmomentum_spytrend_001) prospective validation via deterministic historical replay.
**Cycle:** 42

## Objective

Re-attempt data acquisition from Yahoo Finance when/if more trading days become available. Continue to monitor the rolling 63-day Sharpe trajectory — if it remains below 0.5 for an extended period (>20 trading days) once extended, assess whether the strategy's momentum signal is degrading in the current low-volatility risk-on regime. If no new data is available, document the blocker and leave an evidence-based handoff.

## Data Acquisition

- Command: `python -c "from src.data.yfinance_fetcher import fetch_universe; data=fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'],'1993-01-01','2026-11-30',force=True); print(data.index.max().date())"`
- Result: Latest aligned-frame date = **2026-10-14** (one row beyond prior cycle's 2026-10-13).
- Investigation: the 2026-10-14 row exists **only for ^VIX** and is a flat placeholder (Open=High=Low=Close=15.17, Volume=0). Direct yfinance query for SPY over 2026-10-10→2026-10-16 returns rows only for 2026-10-12 and 2026-10-13. The 7 incumbent ETF parquet files still end at **2026-10-13**; ^VIX.parquet now ends at 2026-10-14 (8,506 rows, 1993-01-04 → 2026-10-14).
- Conclusion: **No new real trading day for the incumbent universe.** The 2026-10-14 ^VIX row is not a usable trading observation (zero volume, identical OHLC) and is not consumed by the incumbent strategy.

## Replay Execution

- Command: `python research/run_paper_trading_replay.py`
- Replay reproduced the existing track record exactly (deterministic, cached data only).
- Track record length: **446 days** (2025-01-02 → 2026-10-13). No extension.
- State YAML verified: `last_run_date: 2026-10-13`, `run_history` length = 446, first entry 2025-01-02, last entry 2026-10-13.

## Performance Metrics (Reproduced Exactly)

| Metric | Value |
|---|---|
| Track record length | 446 days (2025-01-02 → 2026-10-13) |
| Current NAV | $136,593.98 |
| Total Return | +36.59% |
| Annualized Return | 19.27% |
| Volatility (ann.) | 9.53% |
| Sharpe Ratio | 2.0210 |
| Max Drawdown | -1.82% |
| Regime flips | 6 (3 risk-on→risk-off, 3 risk-off→risk-on) |
| Regime persistence | 131 days (risk-on, SPY ≥ 200-day SMA) |

## Drift Flag Status (Unchanged)

- **`low_rolling_sharpe`**: value **0.3669** on 2026-10-13 (threshold 0.5) — **PERSISTS**.
- **Duration: 2 consecutive trading days** (2026-10-12: 0.4892; 2026-10-13: 0.3669).
- Rolling 63-day Sharpe trajectory (last 10 days): 0.1789, 0.3330, 0.3077, 0.9920, 0.9994, 0.4728, 0.1902, 0.9356, 0.4892, 0.3669.
- The trajectory is volatile day-to-day (range 0.18–1.00 over the last 10 days), consistent with a single low-return day moving the 63-day window rather than sustained degradation. Not yet at the >20-day persistence threshold for formal degradation assessment.

## Go/No-Go Gates (Unchanged)

All primary gates from Cycle 22 still pass with margin:

| Gate | Threshold | Actual | Status |
|---|---|---|---|
| Track record length | >126 days | 446 days | PASS |
| Net-of-Cost Sharpe | ≥0.9 | 2.0210 | PASS |
| Maximum drawdown | <15% | -1.82% | PASS |
| Regime flips | >1 | 6 | PASS |

## Data Integrity

- All 7 incumbent ETF parquet files (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) end at **2026-10-13**.
- ^VIX.parquet: 8,506 rows, 1993-01-04 → 2026-10-14 (one flat placeholder row added; not used by incumbent strategy).
- State YAML header (`last_run_date: 2026-10-13`) matches final `run_history` entry. `run_history` length = 446.

## Blocker Documentation

No new real trading data is available from Yahoo Finance for the incumbent universe constituents as of the 2026-10-14 fetch. The only new row (2026-10-14) is a zero-volume ^VIX placeholder and does not represent a usable trading observation. The paper trading replay cannot be extended, and all performance metrics remain unchanged from Cycle 41.

## Scope Boundaries

- No modification to incumbent strategy logic (`config/simulation_candidate_001.yaml` is frozen).
- No new dependencies, services, or infrastructure added.
- Research/backtesting only; no live trades.

## Next Cycle Recommendation

Re-attempt data acquisition when more trading days elapse. Continue monitoring the rolling 63-day Sharpe trajectory. If the `low_rolling_sharpe` flag persists beyond 20 consecutive trading days once extended, assess whether the momentum signal is degrading in the current low-volatility risk-on regime.

**Note:** The track record remains at 446 days. The next cycle should attempt data acquisition again when additional real trading days are expected to be available.