# Paper Trading Validation Report — Cycle 424

## UTC Time
2026-10-16T00:42:52Z

## Gate State
Post-close gate: 2026-10-18T20:00:00Z. **Unmet** (now < gate). No fetch/replay performed per protocol.

## Fetch / Replay Status
- Fetch: **SKIPPED** (pre-gate)
- Replay: **SKIPPED** (pre-gate)

## State Snapshot (unchanged)
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35 (+35.04%)
- Max drawdown: -2.93%
- Sharpe: 1.9272
- Rolling 63-day Sharpe: 0.1133
- Regime flips: 6
- Regime: risk-on (132 days)
- Drift flag: `low_rolling_sharpe` persists 3 consecutive days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133)

## Verification
- Rolling 63d Sharpe recomputed from last 63 cumulative returns: 0.11333136870186278
- Stored drift flag value: 0.11333136870186329
- Diff: 5.134781488891349e-16 (within float precision) — **MATCH**
- Regime flips recomputed: 6 of 447 run_history entries — **MATCH**
- Supervisor loop tests: **10/10 PASSED**

## Artifacts
- `data/processed/paper_trading_state.yaml`
- `research/reports/paper_trading_rolling.md`

## Next Task
Cycle 425: same gate (2026-10-18T20:00:00Z). Re-attempt after gate if met.