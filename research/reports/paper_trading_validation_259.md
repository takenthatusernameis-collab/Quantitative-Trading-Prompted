# Paper Trading Validation Report — Cycle 259

Generated: 2026-10-15T20:27:30Z (UTC)

## Gate enforcement
- Timestamp (UTC): 2026-10-15T20:27:30Z
- Post-close gate: 2026-10-18T20:00:00Z UTC
- Gate met: false
- Action taken: No fetch/replay performed (gate not met). Performed verifications only.

## State snapshot
- run_history entries: 447
- regime flips: 6
- last_run_date: 2026-10-14
- current_nav: 135043.35187742324
- peak_nav: 139120.07235486925
- max_drawdown: -0.0293036109631043
- rolling_63d_sharpe (stored): 0.11333136870186329 (active: false)
- low_rolling_sharpe drift flag: active False

## Verifications
- Rolling 63d Sharpe (computed from last 63 cumulative returns):
  - calc = 0.11333136870186278
  - stored = 0.11333136870186329
  - diff = 5.13e-16 < 1e-12 ✓
- Regime flips (transitions in run_history.regime_exposure): 6 (over 447 entries) ✓
- Supervisor loop tests: python3 .github/scripts/test_kilo_supervisor_loop.py -v → 10/10 passed ✓

## Notes
- State unchanged; no data fetch/replay occurred.
- All checks passed; gate still pending (2026-10-18T20:00:00Z).
