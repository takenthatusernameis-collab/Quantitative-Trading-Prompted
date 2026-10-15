# Paper Trading Validation Report - Cycle 368

**Generated**: 2026-10-15T23:06:32Z UTC
**Run ID**: 38762216276 (attempt 1), worker session index: 209
**Gate**: Post-close gate 2026-10-18T20:00:00Z UTC (not met)

## Objective Status

1. **Timestamp gate enforcement**: 2026-10-15T23:06:32Z < 2026-10-18T20:00:00Z → **DO NOT FETCH OR REPLAY**. Performed minimal verifications only.
2. **Independent verification**: Rolling 63d Sharpe recomputed from last 63 cumulative returns; matches stored drift flag value within float precision. Regime flips recomputed from run_history.
3. **Supervisor loop tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` passed 10/10.
4. **Reporting**: Validation report 368 written.
5. **Supervisor disposition**: Recording disposition in `.kilo-runtime/worker-disposition.json` (recommendation_id copied from current supervisor recommendation).

## Gate State
- Current UTC: 2026-10-15T23:06:32Z
- Gate time: 2026-10-18T20:00:00Z UTC
- Gate met: false
- Fetch performed: false
- Replay performed: false

## State Snapshot
- `run_history` entries: 447 (2025-01-02 → 2026-10-14)
- Regime flips: 6
- Regime: risk-on (132 days as of last entry)
- NAV: $135,043.35 (+35.04%)
- Max drawdown: -2.93%
- Sharpe: 1.9272
- Rolling 63d Sharpe (stored/drift flag): 0.1133

## Verification Results
- **Rolling 63d Sharpe diff**: |recomputed - stored| = 5.134781488891349e-16 < 1e-12 ✓
- **Regime flips**: 6 (recomputed from run_history; matches expected) ✓
- **Supervisor loop tests**: Ran 10 tests in 0.384s, OK (10/10) ✓

## Data Freshness
- Last real trading day reflected: 2026-10-14 (as per prior cycles). No new fetch/replay triggered while gate unmet.

## Notes
- Supervisor runtime files remain outside version control (.kilo-runtime/). Disposition follows two-way dialogue protocol.
