# Paper Trading Validation Report — Cycle 214

## Session Time & Gate State

- **UTC session time**: 2026-10-15T19:22:37Z
- **Post-close gate**: 2026-10-18T20:00:00Z
- **Gate met**: NO — session time < gate
- **Fetch/replay performed**: NO (gate not met; protocol hold respected)

## State Snapshot

| Metric | Value |
|---|---|
| run_history entries | 447 |
| regime flips | 6 |
| last_run_date | 2026-10-14 |
| current NAV | 135043.35187742324 |
| peak NAV | 139120.07235486925 |
| max drawdown | -2.93% |
| stored rolling 63d Sharpe | 0.11333136870186329 |
| drift flag `low_rolling_sharpe` | active=False |

## Independent Verification

### Rolling 63d Sharpe Recompute
- Recomputed from last 63 cumulative returns: **0.11333136870186278**
- Stored drift flag value: **0.11333136870186329**
- **Difference: 5.13e-16** — matches within float precision

### Regime Flips Recompute
- Recomputed from run_history transitions: **6**
- run_history length: **447**
- Matches stored value exactly

### Git Status
- `git status --short` returned **no output** — clean working tree, confirming no fetch/replay occurred

### Supervisor Loop Tests
- `python3 .github/scripts/test_kilo_supervisor_loop.py -v` — **10/10 passed**

## Drift Flag Status

`low_rolling_sharpe` remains inactive (active=False). The stored value 0.1133 is below the 0.5 trigger threshold but the flag is not active, consistent with prior cycles' persistence tracking (3 consecutive days below threshold as of 2026-10-14, not yet at >20-day persistence threshold).

## Conclusion

All verification checks passed. Gate not met; no fetch/replay performed per protocol. State unchanged from Cycle 213.
