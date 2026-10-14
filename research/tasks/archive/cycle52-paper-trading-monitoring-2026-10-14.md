# Archived task displaced by the explicit microcap-momentum research priority

Archived from NEXT_AGENT_TASK.md on 2026-10-14 before replacing the active handoff. This task is preserved for resumption if requested.

# Next Agent Task: Cycle 52 - Continue Paper Trading Monitoring & Data Acquisition

## Context

Cycle 51 checked for 2026-10-15 data. No new real trading days are available yet (yfinance returned 0 rows for incumbents and ^VIX for 2026-10-15 and later dates; raw parquet dates remain 2026-10-14). Track record is unchanged: 447 days, NAV $135,057.00, Sharpe 1.9302, max DD -2.92%, rolling 63d Sharpe 0.1185.

**Drift status:** `low_rolling_sharpe` flagged on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1185) — 3 consecutive trading days. Trajectory over last 18 days volatile (-0.51 to +1.19). Persistence < 20 days. All primary gates pass; regime risk-on for 132 consecutive days.

**Current state:** 2026-10-14 is latest real trading day for incumbents. Next expected is 2026-10-15. Yahoo Finance has not yet published 2026-10-15 data as of Cycle 51.

## Objective

Re-attempt data acquisition from Yahoo Finance to detect whether 2026-10-15 (or later) real trading data has arrived for the incumbent ETF universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) and ^VIX. If new data exists, re-run the paper-trading replay to extend track record, update reports, and document drift flag status. If not, document blocker and prepare Cycle 53 task with updated context.

## Acceptance Criteria

- [ ] Fetch updated YFinance data for the universe using `src/data/yfinance_fetcher.py` (force=True)
- [ ] **Verify per-symbol raw parquet dates** (do not rely only on aligned frame). Confirm all 7 incumbent ETF parquet files end at the same latest date; detect real trading days vs placeholder (^VIX).
- [ ] If new real trading days exist (e.g. 2026-10-15 for all 7 ETFs):
  - Update `research/run_paper_trading_replay.py`: bump `end_date` to `"2026-10-16"` (or later) and replay-date upper bound to `"2026-10-15"` (or later) to capture new day(s)
  - Re-run `research/run_paper_trading_replay.py`
  - Verify track record extended; document day count
  - Update `research/reports/paper_trading_rolling.md`
  - Create `research/reports/paper_trading_validation_025.md`
  - Update README.md with Cycle 52 summary (metrics, drift status/trajectory/duration)
- [ ] If no new real trading days exist: document blocker clearly in validation report and README; do not fabricate metrics; prepare NEXT_AGENT_TASK.md for Cycle 53 with same monitoring objective and updated context
- [ ] Do not modify incumbent strategy logic (`config/simulation_candidate_001.yaml` is frozen)
- [ ] Report findings honestly; research/backtesting only

## Scope Boundaries

- Data ingestion only using existing dependencies
- No new dependencies, services, workflows, agents, permissions, infrastructure
- Preserve working behavior; no unrelated refactors
- No data/metrics fabrication
- Only update hardcoded dates in replay script if new data arrives; do not change replay logic/engine

## Validation Commands

- `python -c "from src.data.yfinance_fetcher import fetch_universe; data=fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'],'1993-01-01','2026-11-30',force=True); print(data.index.max().date())"`
- `python -c "import pandas as pd; from pathlib import Path; inc=['EEM','EFA','GLD','IWM','QQQ','SPY','TLT']; [print(s, pd.read_parquet(Path('data/raw')/f'{s}.parquet').index.max()) for s in inc]"`
- `python -c "import yfinance as yf; [print(s, yf.download(s,start='2026-10-15',end='2026-10-18',progress=False,auto_adjust=False,group_by='ticker').index.size) for s in ['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX']]"`
- `python research/run_paper_trading_replay.py` (only when new ETF data exists)

## Handoff Notes

State: 447 trading days (2025-01-02 → 2026-10-14), NAV $135,057.00, Sharpe 1.9302, max DD -2.92%, rolling 63d Sharpe 0.1185, drift 3 consecutive days (2026-10-12..14), risk-on 132d. No new 2026-10-15 data as of Cycle 51. Key question for Cycle 52: has 2026-10-15 data published? If not, continue monitoring.