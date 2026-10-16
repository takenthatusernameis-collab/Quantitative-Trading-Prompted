# Paper Trading Validation Report — Cycle 435

## Timestamp
- Recorded UTC: 2026-10-16T01:02:04Z
- Post-close gate: 2026-10-18T20:00:00Z
- Gate state: **NOT MET** (current time < gate). No fetch or replay performed.

## State Snapshot (unchanged from Cycle 434)
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35 (+35.04%)
- Max drawdown: -2.93%
- Sharpe: 1.9272
- Rolling 63-day Sharpe: 0.11333136870186329
- Regime: risk-on (132 days), 6 regime flips total
- Drift flag `low_rolling_sharpe` persists: 3 consecutive trading days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133)

## Verification Results

### 1. Rolling 63d Sharpe recomputation
- Recomputed from last 63 cumulative returns: **0.11333136870186278**
- Stored drift flag value: **0.11333136870186329**
- Absolute difference: **5.13e-16** (within float precision)
- Verdict: **MATCH**

### 2. Regime flips recomputation
- Recomputed from run_history: **6 flips** over **447 entries**
- Verdict: **MATCH**

### 3. Supervisor loop tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: **10/10 tests passed** (Ran 10 tests in 0.429s, OK)

## Data Freshness
- Raw parquet files for the 7 incumbent ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) end at 2026-10-14.
- ^VIX.parquet ends at 2026-10-14 (8,506 rows) with placeholder row (Volume=0).
- No new real trading day available beyond 2026-10-14 as of this session.

## Action Taken
- No fetch attempted (gate not met).
- No replay run (no new data).
- Supervisor disposition recorded in `.kilo-runtime/worker-disposition.json` (disposition: verified, recommendation_id 38817660960-attempt-1-review-0003-2ac0cb7d6609).

## Next Task
- Re-evaluate at next cycle after the post-close gate (2026-10-18T20:00:00Z). If gate is met, proceed with data acquisition (force=True, end_date 2026-11-30) for the 7-ETF universe + SPY + ^VIX, verify per-symbol max dates, re-run `research/run_paper_trading_replay.py`, and write validation report 436.
