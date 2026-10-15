# Paper Trading Validation — Cycle 80

**Session UTC**: 2026-10-15T04:48:12Z
**Post-close gate**: 2026-10-16T20:00:00Z
**Gate status**: **PRE-GATE** (session time < gate) — **NO FETCH ATTEMPTED**

---

## Summary

- **Cycle type**: Post-close data acquisition & track record extension (pre-gate hold)
- **Fetch attempted**: No (protocol requires `session_time >= 2026-10-16T20:00:00Z`)
- **Track record**: Unchanged at 447 days (2025-01-02 → 2026-10-14)
- **NAV**: $135,043.35 (+35.04% since inception)
- **Full-period Sharpe**: 1.9272
- **Max drawdown**: -2.93%
- **Rolling 63-day Sharpe**: 0.1133
- **Drift flag**: `low_rolling_sharpe` persists for 3 consecutive days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133) — **not yet at >20-day persistence threshold**
- **Regime**: Risk-on (132 days since last flip)
- **Regime flips (total)**: 6 (verified)
- **Tests**: `pytest .github/scripts/test_kilo_supervisor_loop.py -v` → **10/10 passed**

---

## Independent Verifications

### Rolling 63-day Sharpe Recomputation
- Source: `data/processed/paper_trading_state.yaml` → `cumulative_returns` (last 63 entries)
- Formula: `(mean * 252) / (std(ddof=1) * sqrt(252))`
- Computed: **0.11333136870186329**
- Stored in state: **0.11333136870186329**
- **Match**: Exact (diff < 1e-15, float64 rounding)

### Regime Flip Recomputation
- Source: `run_history` → `regime_exposure` transitions (0.0 ↔ 1.0)
- Counted: **6 flips**
- Documented count: **6**
- **Match**: Exact

---

## Gate Status

| Gate | Threshold | Current | Status |
|------|-----------|---------|--------|
| Track record length | >126 days | 447 days | ✅ PASS |
| Full-period Sharpe | >0.9 | 1.9272 | ✅ PASS |
| Max drawdown | <15% | -2.93% | ✅ PASS |
| Regime flips observed | >1 | 6 | ✅ PASS |
| Rolling 63-day Sharpe | >0.9 | 0.1133 | ⚠️ DRIFT FLAG (3 consecutive days) |

**Note**: Drift flag duration (3 days) is below the >20-day persistence threshold that would trigger strategy review.

---

## Artifacts

- `data/processed/paper_trading_state.yaml` (unchanged)
- `research/reports/paper_trading_validation_080.md` (this report)

---

## Next Action

Next cycle (Cycle 81) will re-evaluate after the post-close gate (2026-10-16T20:00:00Z). If new real trading day data (nonzero volume for incumbent ETFs) exists beyond 2026-10-14, the replay script will be run with bumped `end_date` (preserving yfinance exclusive-end semantics) and the extended track record recorded. If no new data, the blocker will be documented and the gate carried forward.