# Paper Trading Validation — Cycle 78

**Timestamp:** 2026-10-15T04:44:11Z

## Timestamp Gate

- Session time (UTC): 2026-10-15T04:44:11Z
- Post-close gate: 2026-10-16T20:00:00Z (per NEXT_AGENT_TASK.md for cycle 78)
- Comparison: session_time (04:44:11Z 2026-10-15) < gate (20:00:00Z 2026-10-16)
- **Decision:** session_time < gate, so NO fetch attempted per protocol.
- Documentation: Timing recorded; handing off with the same gate (2026-10-16T20:00:00Z) for the next cycle.

## Post-Close Fetch (Skipped)

- Gate not met; skipping `fetch_universe` and the paper-trading replay.
- Raw cache baseline (unchanged by this cycle): incumbent ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) end at 2026-10-14 with real (nonzero volume) data; ^VIX ends at 2026-10-14 (Volume=0 placeholder).
- Confirmed blocker: no new real trading day exists for the incumbent universe beyond 2026-10-14 in the cached/raw data as of this session.

## Independent Verifications

1. **Rolling 63-day Sharpe**
   - Recomputed from `data/processed/paper_trading_state.yaml` `cumulative_returns` (last 63 entries):
     - Mean = 3.565835173325281e-05
     - Std (ddof=1) = 0.004994722922486234
     - Sharpe = (mean × 252) / (std × √252) = **0.11333136870186329**
     - (Code formula in `src/simulation/paper_trading.py:280-282`: `recent_ann_ret = np.mean(recent_returns) * 252`; `recent_vol = np.std(recent_returns, ddof=1) * np.sqrt(252)`; `rolling_sharpe = recent_ann_ret / recent_vol`.)
   - Matches `state.drift_flags.low_rolling_sharpe.value` = 0.11333136870186329 — **exactly** (diff = 0.0) ✓
   - Note: NEXT_AGENT_TASK.md quotes the Sharpe formula as `(mean*252)/(std(ddof=1)*sqrt(256/252))`. That literal variant yields `1.7849690570543468`, which does not match the stored value. The formula actually implemented by the simulation code (and that reproduces the stored drift flag exactly) uses `sqrt(252)`, i.e. `(mean*252)/(std(ddof=1)*sqrt(252))`. The acceptance criterion — "Must match `state.drift_flags.low_rolling_sharpe.value`" — is met with the code's `sqrt(252)` formula.

2. **Regime flips**
   - Recomputed from `run_history` `regime_exposure` transitions: **6** flips ✓
   - (Matches documented count of 6.)

3. **Test suite**
   - Command: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v`
   - Result: **10/10 passed** (10 passed in 0.38s) ✓

## Current State (Unchanged)

- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35
- Sharpe: 1.9272
- Max drawdown: -2.93%
- Rolling 63-day Sharpe: 0.1133 (stored drift flag value)
- Drift flag: `low_rolling_sharpe` on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — 3 consecutive trading days (< 0.5 threshold)
- Trajectory volatile over last 18 days (range -0.51 to +1.19)
- Not yet at >20-day persistence threshold
- Regime: risk-on (exposure 1.0, 132 days)

## Go/No-Go Gate Summary

| Gate | Value | Threshold | Status |
|------|-------|-----------|--------|
| Track record length | 447 days | > 126 days | PASS |
| Net Sharpe | 1.9272 | >= 0.9 | PASS |
| Max drawdown | -2.93% | < 15% | PASS |
| Regime flips | 6 | >= 1 | PASS |
| Rolling 63-day Sharpe | 0.1133 | >= 0.9 | FAIL (drift flag, not yet at >20-day persistence) |
| Trade count (pooled) | 447 | > 100 | PASS |

## Conclusion

No fetch or replay was performed — the session ran before the post-close gate (2026-10-15T04:44:11Z < 2026-10-16T20:00:00Z). All non-fetch verifications passed independently:

- Rolling 63-day Sharpe recomputed from the last 63 `cumulative_returns` = `0.11333136870186329`, exact match to `state.drift_flags.low_rolling_sharpe.value`.
- Regime flips recomputed from `run_history` `regime_exposure` transitions = 6, matching the documented count.
- `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v` → 10/10 passed.

The paper-trading track record (tsmomentum_spytrend_001) remains at 447 days, NAV $135,043.35, with the `low_rolling_sharpe` drift flag persisting at 3 consecutive days (below the >20-day persistence threshold).

## Next Action

Re-evaluate after the post-close gate (2026-10-16T20:00:00Z) in the following cycle. Only if `session_time >= 2026-10-16T20:00:00Z`, attempt the post-close fetch and (if a new real trading day exists for the incumbent ETFs) re-run the replay to extend the track record.