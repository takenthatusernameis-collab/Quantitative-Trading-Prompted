# Paper Trading Validation Report — Cycle 426

## Metadata
- Cycle: 426
- UTC time recorded: 2026-10-16T00:45:09Z
- Gate time: 2026-10-18T20:00:00Z
- Now vs gate: before gate (< 2026-10-18T20:00:00Z)
- Run attempt: 1, Worker session index: 53

## Gate State
- Gate not met. No fetch/replay performed per task instructions.
- Data acquisition from Yahoo Finance (force=True, end_date 2026-11-30) deferred until gate is met.

## State Snapshot (from data/processed/paper_trading_state.yaml)
- Run history count: 447 (2025-01-02 → 2026-10-14)
- Last run date: 2026-10-14
- Regime flips: 6
- Cumulative returns count: 447
- Rolling 63d Sharpe (stored): 0.11333136870186329
- Rolling 63d Sharpe (computed from last 63 cumulative returns): 0.11333136870186278
- Diff (|computed - stored|): 5.134781488891349e-16 (within float precision)
- Regime flips recomputed from run_history: 6 (matches)

## Verification Results
1. UTC time: 2026-10-16T00:45:09Z ✓
2. Rolling 63d Sharpe consistency: match within float precision ✓
3. Regime flips consistency: 6 flips from 447 run_history entries ✓
4. Supervisor loop tests: python3 .github/scripts/test_kilo_supervisor_loop.py -v passed 10/10 ✓

## Fetch/Replay Status
- Status: not performed (pre-gate)
- Reason: current time 2026-10-16T00:45:09Z < gate 2026-10-18T20:00:00Z

## Supervisor Disposition
- Schema version: 1
- Recommendation ID: from .kilo-runtime/current-supervisor-recommendation.json (if exists)
- Disposition: accepted
- Reason: Task executed as specified - pre-gate state verified, tests passed
- Evidence: Verification commands executed and results recorded
- Verification: All checks passed (UTC < gate, Sharpe diff < 1e-12, regime flips match, 10/10 supervisor tests)
- Updated at: 2026-10-16T00:45:09Z

## Next Task (narrow, same gate)
Prepare to repeat this check on/after 2026-10-18T20:00:00Z. If gate met at that time, execute gate-met protocol: re-attempt data acquisition from Yahoo Finance (force=True, end_date 2026-11-30) for 7-ETF incumbent universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) plus SPY and ^VIX, verify per-symbol max dates, re-run research/run_paper_trading_replay.py (end_date per yfinance exclusive-end semantics), confirm track record extension/regime/drift state, write validation report 427 with full results. Independent verification of rolling Sharpe and regime flips remains required; supervisor loop tests must still pass 10/10.
