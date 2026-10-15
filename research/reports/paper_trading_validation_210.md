# Paper Trading Validation Report — Cycle 210

**Timestamp (UTC):** 2026-10-15T19:18:00Z
**Post-close gate:** 2026-10-18T20:00:00Z — **NOT MET** (2026-10-15T19:18:00Z < 2026-10-18T20:00:00Z)
**Fetch/replay performed:** None (gate not met; protocol hold)

## State Snapshot

| Metric | Value |
|---|---|
| run_history length | 447 |
| last_run_date | 2026-10-14 |
| current NAV | $135,043.35 |
| peak NAV | $139,120.07 |
| max drawdown | -2.93% |
| full-period Sharpe | 1.9272 |
| rolling 63d Sharpe (stored) | 0.11333136870186329 |
| drift flag `low_rolling_sharpe` active | False |
| regime flips | 6 |
| regime | risk-on (132 days) |

## Independent Verification

1. **Rolling 63d Sharpe recompute** — recomputed from last 63 cumulative returns:
   - calculated: 0.11333136870186278
   - stored: 0.11333136870186329
   - **diff: 5.13e-16** — matches within float precision

2. **Regime flips recompute** — recomputed from run_history transitions:
   - flips: 6 (matches stored)
   - run_history length: 447 (matches stored)

3. **Supervisor loop tests** — `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
   - **10/10 passed** in 0.429s

4. **Git status** — clean (no unstaged/staged changes), confirming no fetch/replay occurred.

## Conclusion

Gate not met; no fetch or replay performed per protocol. All verification checks passed. Strategy frozen pending gate.