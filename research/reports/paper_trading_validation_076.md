# Paper Trading Validation — Cycle 76

**Timestamp:** 2026-10-15T04:35:29Z

## Timestamp Gate
- Session time: 2026-10-15T04:35:29Z
- Post-close gate: 2026-10-16T20:00:00Z
- Since session time < gate, **no fetch attempted** per protocol.

## Post-Close Fetch (Skipped)
- Gate not met; skipping data acquisition and replay.

## Independent Verifications
1. **Rolling 63‑day Sharpe**
   - Recomputed from `data/processed/paper_trading_state.yaml` `cumulative_returns` (last 63 entries):
     - Mean = 3.5658e‑05
     - Std (ddof=1) = 0.0049947
     - Sharpe = (mean × 252) / (std × √252) = **0.11333136870186329**
   - Matches `state.drift_flags.low_rolling_sharpe.value` = 0.11333136870186329 ✓

2. **Regime Flips**
   - Counted transitions in `run_history` `regime_exposure`: **6** flips ✓

## Test Suite
- `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v`
  - **10/10 passed** ✓

## Current State (Unchanged)
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35
- Sharpe: 1.9272
- Max drawdown: -2.93%
- Rolling 63‑day Sharpe: 0.1133
- Drift flag: `low_rolling_sharpe` on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — 3 consecutive days (< 0.5 threshold)
- Regime: risk‑on (132 days)

## Blocker
- No new real trading day available for incumbent ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) beyond 2026-10-14; ^VIX extends to 2026-10-14 but is not used by the incumbent strategy.

## Next Action
- Re‑evaluate after the post‑close gate (2026-10-16T20:00:00Z) in the following cycle.
