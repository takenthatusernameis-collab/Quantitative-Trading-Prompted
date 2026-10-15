# Paper Trading Validation Report — Cycle 193

**UTC Session Time:** 2026-10-15T18:38:27Z
**Post-Close Gate:** 2026-10-18T20:00:00Z UTC
**Gate Status:** NOT MET — no fetch/replay performed

---

## State Snapshot (from `data/processed/paper_trading_state.yaml`)

| Metric | Value |
|--------|-------|
| Run History Entries | 447 |
| Last Run Date | 2026-10-14 |
| Current NAV | $135,043.35 |
| Peak NAV | $139,120.07 |
| Max Drawdown | -2.93% |
| Regime Flips (recomputed) | 6 |
| Stored Rolling 63d Sharpe | 0.11333136870186329 |
| Drift Flag (`low_rolling_sharpe`) | value=0.11333, active=False |

---

## Independent Verification

### Rolling 63d Sharpe Recomputation
- **Formula:** Annualized Sharpe from last 63 daily cumulative returns
- **Computed:** 0.11333136870186278
- **Stored:** 0.11333136870186329
- **Difference:** 5.13e-16 (within float precision) ✓

### Regime Flips Recomputation
- **Method:** Count transitions in `regime_exposure` across `run_history`
- **Computed:** 6 flips
- **Expected:** 6 flips ✓

### Supervisor Loop Tests
- **Command:** `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- **Result:** 10/10 tests passed ✓

---

## Fetch/Replay Status

**SKIPPED** — Session time (2026-10-15T18:38:27Z) is before post-close gate (2026-10-18T20:00:00Z).
No data fetched. No replay executed. State unchanged from Cycle 192.

---

## Drift Flag Trajectory

| Date | Rolling 63d Sharpe | Flag Triggered |
|------|-------------------|----------------|
| 2026-10-12 | 0.4892 | low_rolling_sharpe |
| 2026-10-13 | 0.3669 | low_rolling_sharpe |
| 2026-10-14 | 0.1133 | low_rolling_sharpe (active=False, persistence threshold not met) |

3 consecutive days below 0.5 threshold. Trajectory over last 18 days: -0.51 to +1.19 (volatile). Not at >20-day persistence threshold.

---

## Primary Go/No-Go Gates (All Pass)

| Gate | Threshold | Current | Status |
|------|-----------|---------|--------|
| Track Record Length | >126 days | 447 days | PASS |
| Net Sharpe | >0.9 | 1.9272 | PASS |
| Max Drawdown | <15% | -2.93% | PASS |
| Regime Flips | >1 | 6 | PASS |

---

## Supervisor Disposition

- **Recommendation ID:** 38762216276-attempt-1-review-0005-6996e9659a28
- **Disposition:** `verified` — Gate hold respected; verifications completed; advancing to Cycle 194 monitoring task.

---

## Next Action

Continue post-close gate monitoring. Next cycle (194) will re-evaluate at next scheduled run.