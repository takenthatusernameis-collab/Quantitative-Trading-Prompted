# Cycle 959 — Execute Gate-Met Protocol (paper-trading data refresh)

## Context
- Gate 2026-10-18T20:00:00Z reached; paper-trading state last run 2026-10-19 (450 cumulative returns).
- SMA-175 candidate remains NO-GO (Cycle 958); incumbent monitoring continues.

## Objective
Execute Cycle 486 gate-met protocol: refresh incumbent 7-ETF universe (SPY,QQQ,IWM,TLT,GLD,EFA,EEM) plus SPY,^VIX via Yahoo Finance (force=True, end_date 2026-11-30), verify per-symbol max dates and real (nonzero volume) data, run paper-trading replay, confirm state, write validation report.

## Acceptance criteria
1. Yahoo fetch completed with verification of per-symbol max dates and nonzero volume (except ^VIX).
2. `research/run_paper_trading_replay.py` executed with appropriate end_date.
3. State confirmed: track length/dates, NAV, Sharpe, max DD, rolling 63d Sharpe, regime flips, drift flag status.
4. Validation report written under research/reports/paper_trading_validation_*.md.
5. Existing tests still pass.

## Scope boundaries
- No strategy/parameter changes.
- No promotion of SMA-175.
- No commits unless explicitly requested.
