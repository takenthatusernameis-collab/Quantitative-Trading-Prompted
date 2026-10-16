# Paper Trading Validation Report — Cycle 425

## Timestamp
- Recorded UTC: `2026-10-16T00:44:01Z`
- Gate: `2026-10-18T20:00:00Z`
- Gate state: **UNMET** (now < gate)

## Objective
Post-gate data acquisition check. Per protocol, no fetch or replay is performed when the post-close gate is unmet. This cycle is monitoring/verification/reporting only.

## Fetch / Replay Status
- Fetch attempted: **NO** (gate unmet)
- Replay run: **NO** (gate unmet)
- Reason: protocol forbids data acquisition before the post-close gate.

## State Snapshot (unchanged)
- Track record length: **447 days** (2025-01-02 → 2026-10-14)
- NAV: **$135,043.35** (+35.04%)
- Max drawdown: **-2.93%**
- Sharpe: **1.9272**
- Rolling 63-day Sharpe: **0.11333136870186329**
- Regime flips: **6**
- Regime: risk-on (132 days)
- Drift flag: `low_rolling_sharpe` persists (3 consecutive days: 2026-10-12, 2026-10-13, 2026-10-14)

## Verification

### Rolling 63-day Sharpe recomputation
- Recomputed from last 63 cumulative returns in `data/processed/paper_trading_state.yaml`
- Recomputed value: `0.11333136870186278`
- Stored value: `0.11333136870186329`
- **Diff: 5.134781488891349e-16** — matches within float precision

### Regime flips recomputation
- Recomputed from `run_history` in `data/processed/paper_trading_state.yaml`
- **Flips: 6**, run_history length: **447** — matches stored state

### Supervisor loop tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: **10/10 tests passed** (`OK`)

## Drift Assessment
- `low_rolling_sharpe` flag persists for 3 consecutive trading days (2026-10-12 → 2026-10-14).
- Trajectory over last 18 days is volatile (range -0.51 to +1.19), consistent with single low-return days moving the 63-day window rather than sustained degradation.
- Not yet at the >20-day persistence threshold.
- All primary go/no-go gates still pass:
  - Track record 447 > 126
  - Sharpe 1.93 > 0.9
  - Max DD -2.93% < 15%
  - Regime flips 6 > 1

## Artifacts
- `data/processed/paper_trading_state.yaml` (unchanged)
- `research/reports/paper_trading_validation_425.md` (this report)

## Next Cycle
- Re-evaluate after post-close gate (`2026-10-18T20:00:00Z`).
- If gate met: re-attempt data acquisition from Yahoo Finance (force=True, end_date=2026-11-30) for the 7-ETF incumbent universe plus SPY and ^VIX, verify per-symbol max dates, re-run `research/run_paper_trading_replay.py`, confirm track record extension/regime/drift state, and write the next validation report.
- Continue monitoring the rolling Sharpe trajectory and drift flag persistence.

## Scope Boundaries
- No strategy changes or dependency modifications.
- Data ingestion/replay only if the post-close gate is met; otherwise monitoring/verification and reporting only.
- No commits unless explicitly requested.