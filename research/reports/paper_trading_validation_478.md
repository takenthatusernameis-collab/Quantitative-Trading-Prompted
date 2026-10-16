# Paper Trading Validation Report — Cycle 478

Generated: 2026-10-16T02:22:22Z (UTC)

## Cycle Metadata
- Cycle: 478
- Previous cycle: 477 (completed 2026-10-16T02:20:30Z)
- Gate: 2026-10-18T20:00:00Z (post-close)
- Current UTC time: 2026-10-16T02:22:22Z
- Gate met: No

## State Snapshot
- Run history entries: 447
- Date range: 2025-01-02 → 2026-10-14
- Last run date: 2026-10-14
- Regime flips: 6
- Regime exposure: risk-on (132 days, per state)

## Drift Monitoring
- low_rolling_sharpe (3-day persistence observed, not >20-day threshold)
  - 2026-10-12: 0.4892
  - 2026-10-13: 0.3669
  - 2026-10-14: 0.1133

## Primary Gates (as recorded)
- track record 447 > 126: PASS
- Sharpe 1.93 > 0.9: PASS
- max drawdown -2.93% < 15%: PASS
- regime flips 6 > 1: PASS

## Actions Taken
- Gate not met (< 2026-10-18T20:00:00Z). No data fetch or replay performed.
- Ran verification commands as specified in NEXT_AGENT_TASK.md.

## Verification Results
- Rolling 63d Sharpe recomputation (from last 63 cumulative returns):
  - |computed - stored| = 5.134781488891349e-16
  - Matches within float precision: PASS
- Regime flips recomputation from run_history:
  - flips = 6, len = 447
  - Matches: PASS

## Supervisor Loop Tests
- python3 .github/scripts/test_kilo_supervisor_loop.py -v: 10/10 tests passed (OK)

## Conclusion
Cycle 478: Gate not met. Verification complete. No replay/fetch performed. State consistent with cycle 477.

## Next Steps
Prepare next narrow task with same gate condition and bounded verification scope (unless gate becomes met).
