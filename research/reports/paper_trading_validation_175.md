# Paper Trading Validation Report — Cycle 175

**Session UTC:** 2026-10-15T17:54:37Z
**Post-close gate:** 2026-10-18T20:00:00Z
**Gate status:** NOT MET — session time < gate time
**Fetch/Replay:** NONE (gate not met)

## State Snapshot (from `data/processed/paper_trading_state.yaml`)

- **Last run date:** 2026-10-14
- **Track record length:** 447 days (2025-01-02 → 2026-10-14)
- **Current NAV:** $135,043.35
- **Full-period Sharpe:** 1.8170
- **Max drawdown:** -2.93%
- **Rolling 63d Sharpe (stored drift flag):** 0.11333136870186329
- **Regime flips (total):** 6
- **Drift flag:** `low_rolling_sharpe` active (3 consecutive days: 2026-10-12, 2026-10-13, 2026-10-14)
- **Run history records:** 447
- **Current positions:** SPY=0.1615, QQQ=0.1615, IWM=0.1615, EEM=0.1615, TLT=0.0, GLD=0.0, EFA=0.0
- **Regime exposure:** 1.0 (risk-on, 132 days)

## Independent Verification

### Rolling 63d Sharpe Recomputation
```python
# From last 63 cumulative_returns entries
recomputed = 0.11333136870186278
stored     = 0.11333136870186329
diff       = 5.13e-16  (within float precision — MATCH)
```

### Regime Flips Recomputation
```python
# From run_history regime_exposure transitions
recomputed = 6
expected   = 6  (MATCH)
```

### Supervisor Loop Tests
```
python3 .github/scripts/test_kilo_supervisor_loop.py -v
Ran 10 tests in 0.397s — OK (10/10 passed)
```

## Diff vs Prior Cycle (Cycle 174)
- No state change (gate not met, no fetch/replay)
- Session time advanced from 2026-10-15T17:51:31Z to 2026-10-15T17:54:37Z
- All verification values identical

## Conclusion
Gate remains pending. Strategy remains frozen. Next cycle should re-evaluate gate at next scheduled run.