# Paper Trading Validation Report — Cycle 376

## Timestamp & Gate State

- **Session UTC time**: 2026-10-15T23:16:09Z
- **Post-close gate**: 2026-10-18T20:00:00Z
- **Gate state**: NOT MET (2026-10-15T23:16:09Z < 2026-10-18T20:00:00Z)
- **Fetch/replay status**: NOT PERFORMED (gate-mandated hold)

## State Snapshot

- **Track record length**: 447 days (2025-01-02 → 2026-10-14)
- **Regime flips**: 6
- **Run history entries**: 447
- **Last run date**: 2026-10-14
- **Current NAV**: $135,043.35
- **Max drawdown**: -2.93%

## Verification Results

### 1. Rolling 63d Sharpe vs stored drift flag

- Recomputed from last 63 cumulative returns: 0.11333136870186278
- Stored value `low_rolling_sharpe`: 0.11333136870186329
- Diff = **5.134781488891349e-16** (< 1e-12 tolerance) — PASS

### 2. Regime flips from run_history

- Recomputed: **6 flips** over 447 run_history entries — matches stored

### 3. Supervisor loop tests

```
python3 .github/scripts/test_kilo_supervisor_loop.py -v
Ran 10 tests in 0.478s
OK
```
10/10 passed.

## Supervisor Disposition

- Recorded in `.kilo-runtime/worker-disposition.json`
- `recommendation_id`: null (no current-supervisor-recommendation.json present)
- Disposition: `verified`

## Next Task

Advance to Cycle 377: repeat timestamp gate check, verifications, and reporting while gate remains unmet.
