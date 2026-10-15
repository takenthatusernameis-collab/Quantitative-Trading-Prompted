# Paper Trading Validation Report — Cycle 174

**Cycle**: 174 (Pending Gate)
**Session UTC**: 2026-10-15T17:51:31Z
**Gate Target**: 2026-10-18T20:00:00Z UTC
**Gate Status**: NOT MET — no fetch/replay performed

---

## State Snapshot (from `data/processed/paper_trading_state.yaml`)

| Metric | Value |
|--------|-------|
| Track record length | 447 days (2025-01-02 → 2026-10-14) |
| NAV | $135,043.35 |
| Full-period Sharpe | 1.8170 |
| Max drawdown | -2.93% |
| Rolling 63d Sharpe (stored) | 0.11333136870186329 |
| Regime flips | 6 |
| Drift flag | `low_rolling_sharpe` active (3 consecutive days: 2026-10-12, 2026-10-13, 2026-10-14) |
| Run history length | 447 |
| Last run date | 2026-10-14 |
| Current positions | SPY: 0.1615, QQQ: 0.1615, IWM: 0.1615, EEM: 0.1615, TLT: 0.0, GLD: 0.0, EFA: 0.0 |

---

## Independent Verification

### Rolling 63-day Sharpe Recomputation
```python
ret = d['cumulative_returns'][-63:]
m = sum(ret)/len(ret)
v = sum((r-m)**2 for r in ret)/(len(ret)-1)
s = (m*252)/(math.sqrt(v)*math.sqrt(252))
```
**Result**: `0.11333136870186278`
**Stored value**: `0.11333136870186329`
**Absolute difference**: `5.13e-16` (within float precision) ✓

### Regime Flip Count
```python
rh = d['run_history']
t = 0; prev = rh[0]['regime_exposure']
for i in range(1, len(rh)):
    if rh[i]['regime_exposure'] != prev:
        t += 1; prev = rh[i]['regime_exposure']
```
**Result**: 6 flips (447 records) ✓

### Supervisor Loop Tests
```bash
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```
**Result**: 10/10 tests passed ✓

---

## Gate Enforcement

- Session time (2026-10-15T17:51:31Z) < Gate target (2026-10-18T20:00:00Z)
- **No data fetch attempted**
- **No replay executed**
- Strategy remains frozen per protocol

---

## Drift Flag Trajectory

| Date | Rolling 63d Sharpe |
|------|-------------------|
| 2026-10-12 | 0.4892 |
| 2026-10-13 | 0.3669 |
| 2026-10-14 | 0.1133 |

**Status**: 3 consecutive days below 0.5 threshold. Trajectory volatile over last 18 days (-0.51 to +1.19). Not yet at >20-day persistence threshold.

---

## Primary Go/No-Go Gates (All Pass)

| Gate | Threshold | Current | Status |
|------|-----------|---------|--------|
| Track record length | >126 days | 447 days | ✓ PASS |
| Net-of-cost Sharpe | >0.9 | 1.8170 | ✓ PASS |
| Max drawdown | <15% | -2.93% | ✓ PASS |
| Regime flips | >1 | 6 | ✓ PASS |
| Rolling 63d Sharpe | >0.9 (target) | 0.1133 | ⚠ BELOW (drift flag) |

---

## Artifacts

- State: `data/processed/paper_trading_state.yaml`
- Prior validation: `research/reports/paper_trading_validation_173.md`
- This report: `research/reports/paper_trading_validation_174.md`

---

## Next Action

Continue gate monitoring. Next cycle should re-evaluate gate at session start and proceed to post-close fetch/replay only when `session_time >= 2026-10-18T20:00:00Z`.