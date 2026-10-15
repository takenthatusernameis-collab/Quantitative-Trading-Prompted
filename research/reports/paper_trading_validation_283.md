# Paper Trading Validation Report — Cycle 283

## Timestamp & Gate

- **UTC time**: 2026-10-15T21:02:00Z
- **Post-close gate**: 2026-10-18T20:00:00Z
- **Gate state**: NOT MET (2026-10-15T21:02:00Z < 2026-10-18T20:00:00Z)
- **Fetch/replay performed**: NO — gate-mandated hold enforced

## State Snapshot

- **Track record**: 447 days (2025-01-02 → 2026-10-14)
- **NAV**: $135,043.35 (+35.04%)
- **Max drawdown**: -2.93%
- **Sharpe**: 1.9272
- **Rolling 63-day Sharpe**: 0.1133
- **Regime flips**: 6
- **Regime**: risk-on (132 days)

## Verification Results

### 1. Rolling 63-day Sharpe (independent recomputation)
- Recomputed from last 63 cumulative returns: **0.11333136870186278**
- Stored drift flag value: **0.11333136870186329**
- **Diff**: 5.13e-16 < 1e-12 tolerance → **MATCH**

### 2. Regime Flips (independent recomputation)
- Recomputed from run_history: **6 flips** over **447 entries** → **MATCH**

### 3. Supervisor Loop Tests
```
Ran 10 tests in 0.756s
OK
```
**10/10 PASSED**

## Drift Status

- **Drift flag persists**: `low_rolling_sharpe` on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive trading days**
- Trajectory over last 18 days volatile (range -0.51 to +1.19)
- Not yet at the >20-day persistence threshold
- All primary go/no-go gates still pass (track record 447 > 126, Sharpe 1.93 > 0.9, max DD -2.93% < 15%, 6 regime flips > 1)

## Artifacts

- `data/processed/paper_trading_state.yaml`
- `research/reports/paper_trading_rolling.md`
- `research/reports/paper_trading_validation_283.md` (this report)

## Next Task

Prepare Cycle 284: continue gate monitoring — record UTC time, if < 2026-10-18T20:00:00Z do not fetch or replay, re-run the three verifications, write validation report 284, advance NEXT_AGENT_TASK.md.