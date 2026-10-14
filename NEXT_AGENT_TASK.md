# Next Agent Task: Cycle 49 - Continue Paper Trading Monitoring & Data Acquisition

## Context

Cycle 48 successfully acquired 2026-10-14 data for all 7 incumbent ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) — the first new real trading day since 2026-10-13. The paper-trading replay was re-run with updated `end_date` (2026-10-15, yfinance exclusive-end) and replay-date upper bound (2026-10-14), extending the track record from 446 to 447 days.

**Key findings from Cycle 48:**
- Track record: **447 days** (2025-01-02 → 2026-10-14), NAV **$135,057.00** (+35.06%), max DD **-2.92%**, Sharpe **1.9302**, rolling 63-day Sharpe **0.1185**.
- **DRIFT FLAG PERSISTS**: `low_rolling_sharpe` on 2026-10-12 (0.4892), 2026-10-13 (0.3669), and 2026-10-14 (0.1185) — **3 consecutive trading days**. Trajectory over last 18 days is volatile (range -0.51 to +1.19), consistent with single low-return days moving the 63-day window rather than sustained degradation. Not yet at the >20-day persistence threshold.
- All primary go/no-go gates from Cycle 22 still pass: track record 447 ≫ 126, Sharpe 1.93 ≫ 0.9, max DD -2.92% ≪ 15%, 6 regime flips > 1.
- Current regime: Risk-on (SPY ≥ 200-day SMA) for **132 consecutive days**.
- Data integrity verified: all 7 incumbent ETF parquet files end at 2026-10-14 (real data, nonzero volume); ^VIX.parquet ends at 2026-10-14 (8,506 rows) with placeholder row (Volume=0); state YAML matches 447 run_history records.

**Critical detail:** The session date is 2026-10-14 (Wednesday). The next real trading day is 2026-10-15 (Thursday). Cycle 49 should detect whether 2026-10-15 data has arrived for the ETFs. If it has, the replay script's `end_date` and replay-date upper bound must be bumped (yfinance treats `end` as exclusive: to capture 2026-10-15 data, request `end_date="2026-10-16"` and set replay bound to `"2026-10-15"`).

## Objective

Re-attempt data acquisition from Yahoo Finance to detect whether 2026-10-15 (or later) data has arrived for the incumbent ETF universe. If new real trading days exist, re-run the paper-trading replay to extend the track record, update reports, and document drift flag status. If no new data is available, document the blocker and prepare the next cycle task with updated context.

## Acceptance Criteria

- [ ] Fetch updated YFinance data for the universe + SPY + ^VIX using `src/data/yfinance_fetcher.py` (force=True) to extend `data/raw/*.parquet` beyond 2026-10-14
- [ ] **Verify per-symbol raw parquet dates** — do not rely on the aligned-frame max date alone. A ^VIX placeholder row (zero volume, flat OHLC) can extend the aligned frame without a real trading day. Confirm all 7 incumbent ETF parquet files end at the same latest date.
- [ ] If new real trading days exist (e.g., 2026-10-15 for the 7 ETFs):
    - Update `research/run_paper_trading_replay.py`: bump `end_date` to `"2026-10-16"` (or later) and replay-date upper bound to `"2026-10-15"` (or later) to capture the new day(s)
    - Re-run `research/run_paper_trading_replay.py`
    - Verify track record extended (document actual day count)
    - Update `research/reports/paper_trading_rolling.md`
    - Create `research/reports/paper_trading_validation_022.md`
    - Update README.md with Cycle 49 summary (include new metrics, drift flag status/trajectory/duration)
    - Document drift flag status, trajectory, and duration
- [ ] If no new real trading days exist: document blocker clearly in validation report and README, do not fabricate metrics; prepare NEXT_AGENT_TASK.md for Cycle 50 with same monitoring objective and updated context
- [ ] Do not modify incumbent strategy logic (`config/simulation_candidate_001.yaml` is frozen)
- [ ] Report findings honestly; research/backtesting only

## Scope Boundaries

- Data ingestion for research/backtesting only (existing dependency in requirements.txt)
- Do not add dependencies, services, paid data, scheduled jobs, agents, workflows, permissions, or infrastructure
- Preserve working behavior; avoid unrelated refactors
- Never fabricate data/metrics
- Do not alter the replay script's logic or the paper-trading engine — only update the hardcoded `end_date` and replay-date upper bound if new data arrives

## Validation Commands

- `python -c "from src.data.yfinance_fetcher import fetch_universe; data=fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'],'1993-01-01','2026-11-30',force=True); print(data.index.max().date())"`
- `python -c "import pandas as pd; from pathlib import Path; [print(f.name, pd.read_parquet(f).index.max()) for f in sorted(Path('data/raw').glob('*.parquet'))]"`
- `python -c "import yfinance as yf; import pandas as pd; [print(s, [d.date().isoformat() for d in yf.download(s, start='2026-10-12', end='2026-10-18', progress=False, auto_adjust=False, group_by='ticker').index]) for s in ['SPY','^VIX']]"`
- `python research/run_paper_trading_replay.py` (only when new ETF data exists)

## Handoff Notes

Current state: 447 trading days (2025-01-02 → 2026-10-14), NAV $135,057.00, Sharpe 1.9302, max DD -2.92%, rolling 63d Sharpe 0.1185 (drift persists, 3 consecutive days since 2026-10-12), risk-on regime 132 days. 2026-10-14 data acquired successfully. Key question for next cycle: has Yahoo Finance published 2026-10-15 data for the 7 ETFs?
