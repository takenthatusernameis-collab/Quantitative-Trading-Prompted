# Paper Trading Validation Report — Cycle 165

## Session
- **UTC session time**: 2026-10-15T17:31:12Z
- **Post-close gate**: 2026-10-18T20:00:00Z — **NOT MET** (session_time < gate)

## Gate Enforcement
Per protocol, because `session_time < 2026-10-18T20:00:00Z`, **no fetch or replay was performed**.

## State Snapshot (data/processed/paper_trading_state.yaml)
| Metric | Value |
|---|---|
| Track record length | 447 days (2025-01-02 → 2026-10-14) |
| NAV | $135,043.35 |
| Sharpe | 1.9272 |
| Max DD | -2.93% |
| Rolling 63d Sharpe (stored) | 0.11333136870186329 |
| Regime flips | 6 |
| Regime | risk-on (132 days) |
| Drift flag | `low_rolling_sharpe` — 3 consecutive days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133) |
| Run history length | 447; last run date 2026-10-14 |

## Independent Verification

### Rolling 63d Sharpe recomputation
```python
ret = cumulative_returns[-63:]
m = mean(ret); v = var(ret, ddof=1)
s = (m*252) / (sqrt(v)*sqrt(252))
```
- **Recomputed**: 0.11333136870186278
- **Stored drift flag value**: 0.11333136870186329
- **Absolute difference**: 5.13e-16 — **MATCH within float precision**

### Regime flips recomputation
- Transitions in `run_history` where `regime_exposure` changes: **6**
- Run history length: **447**
- Last run date: **2026-10-14**
- **MATCH** (expected 6 unless data changed)

### Supervisor loop tests
```
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```
- **Result: 10/10 PASSED** (Ran 10 tests in 0.517s, OK)

## Diff / Changes
No fetch or replay performed. State unchanged from Cycle 164. No source modifications.

## Decision
- **Label**: Blocked by gate (pending) — no fetch/replay until `session_time >= 2026-10-18T20:00:00Z`.
- All primary go/no-go gates still pass: track record 447 > 126, Sharpe 1.93 > 0.9, max DD -2.93% < 15%, 6 regime flips > 1.
- Drift flag (`low_rolling_sharpe`) persists at 3 consecutive days; not yet at >20-day persistence threshold.

## Next Task
Update `NEXT_AGENT_TASK.md` with one narrow, testable next task: continue post-close gate monitoring (Cycle 166), re-checking UTC session time against the gate, re-running the same minimal verifications, and writing `paper_trading_validation_166.md`.