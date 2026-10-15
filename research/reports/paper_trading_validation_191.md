# Paper Trading Validation Report — Cycle 191

**UTC Session Time**: 2026-10-15T18:33:34Z
**Post-Close Gate**: 2026-10-18T20:00:00Z UTC
**Gate Status**: NOT MET (session time < gate)

## Fetch/Replay Status
**NO FETCH/REPLAY PERFORMED** — Gate not met per protocol.

## State Snapshot (from `data/processed/paper_trading_state.yaml`)

| Metric | Value |
|--------|-------|
| Run History Entries | 447 |
| Last Run Date | 2026-10-14 |
| Current NAV | $135,043.35 |
| Peak NAV | $139,120.07 |
| Max Drawdown | -2.93% |
| Rolling 63d Sharpe (stored) | 0.11333136870186329 |
| Drift Flag: low_rolling_sharpe | value=0.11333136870186329, active=False |
| Regime Flips (total) | 6 |
| Current Regime | risk-on (132 days) |

## Independent Verifications

### 1. Rolling 63-Day Sharpe Recomputation
```
sharpe_calc = 0.11333136870186278
stored      = 0.11333136870186329
diff        = 5.13e-16  (within float precision)
```
**Result**: MATCH ✓

### 2. Regime Flips Recomputation
```
flips = 6 (over 447 run_history entries)
last_run_date = 2026-10-14
```
**Result**: MATCHES stored count of 6 ✓

### 3. Supervisor Loop Tests
```
python3 .github/scripts/test_kilo_supervisor_loop.py -v
Ran 10 tests in 0.486s
OK (10/10 passed)
```
**Result**: ALL PASSED ✓

## Supervisor Disposition
- Recommendation ID: `38762216276-attempt-1-review-0005-6996e9659a28`
- Disposition: `verified`
- Worker correctly skipped fetch/replay; verifications passed; continuing gate monitoring.

## Drift Flag Trajectory
| Date | Rolling 63d Sharpe | Note |
|------|-------------------|------|
| 2026-10-12 | 0.4892 | |
| 2026-10-13 | 0.3669 | |
| 2026-10-14 | 0.1185 | |
| **2026-10-15 (current)** | **0.1133** | 3 consecutive days < 0.5 threshold; active=False (persistence threshold >20 days not met) |

## Go/No-Go Gates (All Primary Gates Still Pass)
| Gate | Threshold | Current | Status |
|------|-----------|---------|--------|
| Track Record Length | >126 days | 447 days | PASS |
| Net Sharpe | >0.9 | 1.9272 | PASS |
| Max Drawdown | <15% | -2.93% | PASS |
| Regime Flips | >1 | 6 | PASS |

## Next Action
Continue gate monitoring. Next cycle (Cycle 192) will re-evaluate post-close gate at 2026-10-18T20:00:00Z UTC.