# Paper Trading Validation Report — Cycle 484

## UTC Time
2026-10-16T02:31:45Z

## Gate State
Session time 2026-10-16T02:31:45Z < post-close gate 2026-10-18T20:00:00Z. No fetch or replay performed per protocol.

## Status
Monitoring/verification only. Track record unchanged: 447 days (2025-01-02 → 2026-10-14).

## Verification Numbers

### Rolling 63d Sharpe Recomputation
- Computed from last 63 cumulative_returns: **0.11333136870186278**
- Stored drift flag value: **0.11333136870186329**
- Absolute difference: **5.13e-16** (within float precision)
- Verdict: **MATCH**

### Regime Flips Recomputation
- Recomputed from run_history: **6**
- Expected: **6**
- run_history length: **447**
- Verdict: **MATCH**

### Supervisor Loop Tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: **10/10 PASSED**

## Track Record Summary
- NAV: $135,043.35 (+35.04%)
- Max drawdown: -2.93%
- Sharpe: 1.9272
- Rolling 63-day Sharpe: 0.1133
- Regime: risk-on (132 days)
- Drift flag: `low_rolling_sharpe` persists (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133) — 3 consecutive trading days, below >20-day persistence threshold

## Artifacts
- `data/processed/paper_trading_state.yaml`
- `research/reports/paper_trading_rolling.md`