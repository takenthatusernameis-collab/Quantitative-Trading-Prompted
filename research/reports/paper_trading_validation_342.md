# Paper Trading Validation Report 342 — Post-Close Gate Readiness

## UTC Timestamp
- Session time: **2026-10-15T22:28:03Z**
- Post-close gate: **2026-10-18T20:00:00Z**
- Gate state: **NOT MET** (session time < gate)

## Fetch / Replay Status
- **No fetch attempted.** Gate protocol prohibits data ingestion before 2026-10-18T20:00:00Z.
- **No replay executed.** Track record unchanged.
- State snapshot: 447 run_history entries, last_run_date 2026-10-14, 6 regime flips.

## Verification Results

### 1. Rolling 63d Sharpe vs stored drift flag
- Recomputed from last 63 cumulative returns: mean, sample variance, annualized Sharpe.
- Stored drift flag value: 0.11333136870186329
- Absolute difference: **5.134781488891349e-16** (< 1e-12 threshold) — **PASS**

### 2. Regime flips
- Recomputed from run_history regime_exposure transitions.
- Flips: **6**
- run_history length: **447**
- Consistent with stored state — **PASS**

### 3. Supervisor loop tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: **10/10 tests passed** (Ran 10 tests in 0.573s, OK) — **PASS**

## Drift Flag Status
- `low_rolling_sharpe`: value 0.1133 on 2026-10-14, persists 3 consecutive trading days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133).
- Trajectory over last 18 days volatile (range -0.51 to +1.19). Not yet at >20-day persistence threshold.
- All primary go/no-go gates still pass: track record 447 > 126, Sharpe 1.93 > 0.9, max DD -2.93% < 15%, 6 regime flips > 1. Regime risk-on (132 days).

## Supervisor Disposition
- Recorded in `.kilo-runtime/worker-disposition.json` (schema_version 1, recommendation_id `38762216276-attempt-1-review-0005-6996e9659a28`, disposition `verified`).

## Next Cycle
- Advance to Cycle 343. Re-check gate; continue monitoring only while unmet.
