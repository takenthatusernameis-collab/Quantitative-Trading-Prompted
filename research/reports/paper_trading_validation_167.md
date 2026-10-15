# Paper Trading Validation Report — Cycle 167

## Session Timestamp
- UTC session time: **2026-10-15T17:36:12Z**
- Post-close gate: **2026-10-18T20:00:00Z**
- Gate state: **NOT MET** (session_time < gate)

## Fetch / Replay Status
- **No fetch performed.** Gate not met; per protocol, no data fetch or replay executed this cycle.
- **No replay performed.** Track record unchanged from Cycle 166.

## State Snapshot (data/processed/paper_trading_state.yaml)
- Track record: **447 days** (2025-01-02 → 2026-10-14)
- Current NAV: **$135,043.35** (+35.04%)
- Peak NAV: $139,120.07
- Max drawdown: **-2.93%**
- Sharpe (full period): **1.9272**
- Rolling 63-day Sharpe: **0.1133**
- Regime: risk-on (exposure 1.0), persistence **132 days**
- Regime flips (cumulative): **6**
- Turnover median: 0.12%, p95: 50.0%
- Last run date: 2026-10-14

## Independent Verification

### 1. Rolling 63-day Sharpe recomputation
- Recomputed from last 63 cumulative returns: **0.11333136870186278**
- Stored drift flag value: **0.11333136870186329**
- Absolute difference: **5.13e-16** (within float precision)
- **VERIFIED: exact match**

### 2. Regime flips recomputation
- Recomputed from run_history transitions: **6**
- run_history length: **447**
- **VERIFIED: match** (6 flips, consistent with prior cycles)

### 3. Supervisor loop tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: **10/10 tests passed** (Ran 10 tests in 0.388s — OK)

## Drift Flag Status
- `low_rolling_sharpe` flag active on **2026-10-14** (value 0.1133 < 0.5 threshold)
- Persistence: **3 consecutive trading days** (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133)
- Threshold for escalation: >20 days persistence — **not met**
- Trajectory over last 18 days volatile (range -0.51 to +1.19), consistent with single low-return days moving the 63-day window rather than sustained degradation.

## Primary Go/No-Go Gates
| Gate | Value | Threshold | Status |
|------|-------|-----------|--------|
| Track record length | 447 days | >126 days | PASS |
| Net-of-cost Sharpe | 1.9272 | >0.9 | PASS |
| Max drawdown | -2.93% | <15% | PASS |
| Regime flips | 6 | >1 | PASS |

## Conclusion
All verifications passed. Post-close gate not met; no fetch/replay performed. Strategy remains frozen pending gate. Next cycle: continue gate monitoring.