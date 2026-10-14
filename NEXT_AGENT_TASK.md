# Next Agent Task: Cycle 43 — Continue Paper Trading Monitoring & Data Acquisition

## Context

Cycle 42 maintained the paper-trading track record for the incumbent TSMOM strategy (`tsmomentum_spytrend_001`) at **446 days** (2025-01-02 → 2026-10-13) with no new real trading data available.

**Key findings from Cycle 42:**
- Data fetch (force=True, end_date 2026-11-30) completed. Aligned-frame max date reported as **2026-10-14**, but investigation revealed the 2026-10-14 row exists **only for ^VIX** and is a flat placeholder (Open=High=Low=Close=15.17, Volume=0). Direct yfinance query for SPY over 2026-10-10→2026-10-16 returns rows only for 2026-10-12 and 2026-10-13.
- The 7 incumbent ETF parquet files (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) still end at **2026-10-13**. ^VIX.parquet now ends at 2026-10-14 (8,506 rows, 1993-01-04 → 2026-10-14) due to the placeholder row. **No new real trading day for the incumbent universe.**
- Track record remains at **446 days** (2025-01-02 → 2026-10-13). Replay reproduced exactly: NAV **$136,593.98** (+36.59%), max DD **-1.82%**, Sharpe **2.0210**, rolling 63-day Sharpe **0.3669**.
- **DRIFT FLAG PERSISTS**: `low_rolling_sharpe` on 2026-10-12 (0.4892 < 0.5 threshold) and 2026-10-13 (0.3669 < 0.5) — **duration 2 consecutive trading days**. Trajectory over last 10 days is volatile (range 0.18–1.00), consistent with single low-return days moving the 63-day window rather than sustained degradation. Not yet at the >20-day persistence threshold for formal degradation assessment.
- All primary go/no-go gates from Cycle 22 still pass: track record 446 days (≫126), Sharpe 2.0210 (≫0.9), max DD -1.82% (≪15%), 6 regime flips (>1).
- Current regime: Risk-on (SPY ≥ 200-day SMA) for **131 consecutive days**.
- Data integrity verified: all 7 incumbent ETF parquet files end at 2026-10-13; state YAML header matches final run_history entry (446 records).
- Created `research/reports/paper_trading_validation_015.md`.

## Objective

Re-attempt data acquisition from Yahoo Finance when/if more real trading days become available for the incumbent universe. Continue to monitor the rolling 63-day Sharpe trajectory — if it remains below 0.5 for an extended period (>20 trading days) once extended, assess whether the strategy's momentum signal is degrading in the current low-volatility risk-on regime. If no new data is available, document the blocker and leave an evidence-based handoff.

## Acceptance Criteria

- [ ] Fetch updated YFinance data for the universe + SPY + ^VIX using `src/data/yfinance_fetcher.py` (force=True) to extend `data/raw/*.parquet` beyond 2026-10-13
- [ ] **Verify per-symbol raw parquet dates** — do not rely on the aligned-frame max date alone. A ^VIX placeholder row (zero volume, flat OHLC) can extend the aligned frame without a real trading day. Confirm all 7 incumbent ETF parquet files end at the same latest date.
- [ ] If new real trading days exist: re-run `research/run_paper_trading_replay.py` (end_date is now correctly `"2026-10-14"` to capture the latest trading day due to yfinance exclusive-end semantics; if data extends further, bump the hardcoded replay-date upper bound and `end_date` accordingly), verify track record extended (document actual count), update `research/reports/paper_trading_rolling.md`, create `research/reports/paper_trading_validation_016.md`, update README.md with Cycle 43 summary, document drift flag status/trajectory/duration
- [ ] If no new real trading days exist: document blocker clearly in validation report and README, do not fabricate metrics; prepare NEXT_AGENT_TASK.md for Cycle 44 with same monitoring objective and updated context
- [ ] Do not modify incumbent strategy logic (`config/simulation_candidate_001.yaml` is frozen)
- [ ] Report findings honestly; research/backtesting only

## Scope Boundaries

- Data ingestion for research/backtesting only (existing dependency in requirements.txt)
- Do not add dependencies, services, paid data, scheduled jobs, agents, workflows, permissions, or infrastructure
- Preserve working behavior; avoid unrelated refactors
- Never fabricate data/metrics

## Validation Commands

- `python -c "from src.data.yfinance_fetcher import fetch_universe; data=fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'],'1993-01-01','2026-11-30',force=True); print(data.index.max().date())"`
- `python -c "import pandas as pd; from pathlib import Path; [print(f.name, pd.read_parquet(f).index.max()) for f in sorted(Path('data/raw').glob('*.parquet'))]"`
- `python research/run_paper_trading_replay.py` (when extending)
- Verify artifacts exist and match acceptance criteria

## Handoff Notes

Current state: 446 trading days (2025-01-02 → 2026-10-13), NAV $136,593.98, Sharpe 2.0210, max DD -1.82%, rolling 63d Sharpe 0.3669 (drift persists, duration 2 days), risk-on regime 131 days. Replay end_date fix applied (yfinance exclusive-end). No new real trading days available as of 2026-10-14 fetch — the only new row was a zero-volume ^VIX placeholder.