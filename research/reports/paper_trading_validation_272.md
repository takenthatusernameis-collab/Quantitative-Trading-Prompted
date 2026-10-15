# Paper Trading Validation Report 272

**UTC Time:** 2026-10-15T20:47:18Z
**Gate:** 2026-10-18T20:00:00Z UTC (not met)
**Fetch/Replay:** No fetch or replay performed
**Worker Session:** 112 (invocation 1)

## State Snapshot
- Run history: 447 entries (last run date 2026-10-14)
- Regime flips: 6
- Current NAV: $135,043.35187742324
- Peak NAV: $139,120.07235486925
- Max drawdown: -0.0293036109631043 (-2.93%)
- Drift (low_rolling_sharpe): active/triggered; value 0.11333136870186329
- Rolling 63d Sharpe: 0.11333136870186278 (stored matches)

## Verification
- Rolling Sharpe recomputed from last 63 cumulative returns: 0.11333136870186278
- Stored value: 0.11333136870186329
- Difference: 5.13e-16 (< 1e-12) ✓
- Regime flips recomputed from run_history: 6 ✓

## Supervisor Loop Tests
- `python3 .github/scripts/test_kilo_supervisor_loop.py -v`: 10/10 passed ✓

## Notes
Post-close gate (2026-10-18T20:00:00Z) not met. No fetch/replay executed. State unchanged. Supervisor disposition recorded.
