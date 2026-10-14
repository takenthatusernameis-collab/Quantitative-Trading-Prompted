# Paper-Trading Validation Report #009 (Cycle 36)

## Executive Summary

**Cycle 36** re-attempted data acquisition from Yahoo Finance to extend the paper-trading track record for the incumbent strategy `tsmomentum_spytrend_001` beyond 2026-10-12. As of 2026-10-14, no additional trading days were available for the 7-symbol incumbent universe beyond 2026-10-12; the replay reproduced the existing 445-day track record exactly (NAV $136,905.02, max drawdown -1.59%, Sharpe 2.0404). The rolling 63-day Sharpe remains below 0.5 (0.4892) with drift flag persisting.

All primary go/no-go gates from Cycle 22 remain passing.

---

## Data Acquisition

| Metric | Value |
|--------|-------|
| Fetch timestamp | 2026-10-14 |
| Requested end date | 2026-11-30 (force=True) |
| Latest available (equities: SPY,QQQ,IWM,TLT,GLD,EFA,EEM) | 2026-10-12 |
| Latest available (^VIX) | 2026-10-13 (not used by incumbent) |
| New trading days added | 0 |
| Cache end (7 incumbent symbols) | 2026-10-12 |

Data integrity verified: all 7 incumbent ETF parquet files end at 2026-10-12; ^VIX ends at 2026-10-13 (8,505 rows, 1993-01-04 → 2026-10-13). Replay used end_date "2026-10-13" with force refresh; final cached data for the incumbent universe remains at 2026-10-12 (445 trading days, 2025-01-02 → 2026-10-12).

---

## Track Record Status (Period: 2025-01-02 → 2026-10-12)

| Metric | Value |
|--------|-------|
| Track Record Length | 445 days |
| Last Date | 2026-10-12 |
| Current NAV | $136,905.02 |
| Total Return | 36.91% |
| Annualized Return | 19.47% |
| Volatility (ann.) | 9.54% |
| Sharpe Ratio | 2.0404 |
| Max Drawdown | -1.59% |
| Regime Flips | 6 |
| Rolling 63-day Sharpe | 0.4892 |

---

## Go/No-Go Gate Status (Cycle 22 Criteria)

| Gate | Threshold | Value | Status |
|------|-----------|-------|--------|
| Min Track Record | ≥63 days | 445 | **PASS** |
| Net Sharpe | ≥0.9 | 2.0404 | **PASS** |
| Max Drawdown | ≤15% | -1.59% | **PASS** |
| Regime Diversity | ≥1 flip | 6 | **PASS** |
| Rolling 63d Sharpe | ≥0.9 | 0.4892 | **FAIL (drift flag)** |

Note: Rolling 63-day Sharpe is a drift monitoring metric, not a disqualifying condition for primary go/no-go.

---

## Drift Monitoring Status

**DRIFT FLAG PERSISTS**: `low_rolling_sharpe` active

- **Current Value**: 0.4892
- **Threshold**: 0.5
- **Date**: 2026-10-12
- **Days Below Threshold**: 1 (cannot extend until new trading days available)

**Current regime**: Risk-on (SPY ≥ 200-day SMA), **130 consecutive days**. The rolling window remains below threshold despite strong full-period performance.

Since no new trading days were available, trajectory cannot be updated. If rolling Sharpe remains below 0.5 for >20 trading days once extended, reassess regime-specific performance decomposition per prior guidance.
