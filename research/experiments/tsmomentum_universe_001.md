# Experiment: Alternative Universe Test (tsmomentum_universe_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_003.md`. Uses the best Cycle 4 configuration
(lookback=226, vol_target=0.10, dd=0.15).

**Objective**: Test whether alternative asset universes — sector ETFs and a
global multi-asset class basket — improve the test-period net Sharpe of the
226-day TSMOM + combined risk overlay toward the 0.9 promotion gate.

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached parquet in `data/raw/`)
- **Date Range**: 1993-01-01 to 2026-10-09
- **Frequency**: Daily (end-of-day OHLCV)
- **Test Period**: 2018-01-01 to 2026-10-09
- **Point-in-Time**: Same as baseline — momentum (226-day, 21-day skip),
  weights shifted 1 day; combined vol+dd overlay applied on the test-period
  slice.
- **Cost Model**: 1.0 bps + 2.0 bps = 3.0 bps round-trip
- **Configuration**: lookback=226, skip=21, top_fraction=0.5, vol_target=0.10,
  dd_threshold=0.15 (identical to Cycle 4 best config)

---

## Pre-Specified Universes

1. **Sector ETFs** (9 assets): XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY —
   a cross-sectional momentum play on US sector rotation.
2. **Global Asset Classes** (7 assets): SPY, EFA, EEM, TLT, GLD, DBC, VNQ —
   a global multi-asset basket (same as baseline but substituting VNQ for QQQ
   and IWM, and adding DBC for commodity exposure).

Both use the *same* Cycle 4 best-config parameters; only the symbol universe
changes.

---

## Results (Test Period, Net of Costs)

| Universe | Assets | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades | Avg Exposure | Ann. Turnover |
|----------|--------|--------|-------------|--------|---------|---------------|--------|---------------|---------------|
| Baseline (SPY,QQQ,IWM,TLT,GLD,EFA,EEM) | 7 | 0.7458 | 0.0929 | -0.1660 | 0.9791 | 1.18 | 1812 | 0.7092 | 9.95 |
| Sector ETFs (XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY) | 9 | 0.4415 | 0.0643 | -0.1510 | 0.5826 | 1.12 | 1964 | 0.6846 | 12.54 |
| Global Asset Classes (SPY,EFA,EEM,TLT,GLD,DBC,VNQ) | 7 | 0.5515 | 0.0735 | -0.1516 | 0.7195 | 1.14 | 1717 | 0.7984 | 10.33 |

---

## Best Universe

| Metric | Value |
|--------|-------|
| Best Universe | Baseline (SPY,QQQ,IWM,TLT,GLD,EFA,EEM) |
| Test Sharpe | 0.7458 |
| Annualized Return | 0.0929 |
| Max Drawdown | -0.1660 |
| Trades | 1812 |
| Meets promotion gate | **NO** |

---

## Comparison to Baseline 7-Asset Universe

| Universe | Sharpe | vs Baseline Sharpe | Max DD | Trades |
|----------|--------|--------------------|--------|--------|
| Baseline (SPY,QQQ,IWM,TLT,GLD,EFA,EEM) | 0.7458 | +0.0000 | -0.1660 | 1812 |
| Sector ETFs (XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY) | 0.4415 | -0.3043 | -0.1510 | 1964 |
| Global Asset Classes (SPY,EFA,EEM,TLT,GLD,DBC,VNQ) | 0.5515 | -0.1944 | -0.1516 | 1717 |

---

## Interpretation

The baseline 7-asset universe achieves a test Sharpe of 0.7458. The best
alternative universe is **Baseline (SPY,QQQ,IWM,TLT,GLD,EFA,EEM)** with Sharpe = 0.7458.

**This does NOT meet the 0.9 promotion gate** — neither alternative universe clears the Sharpe threshold. The strategy remains an Exploratory Signal.

---

*Report generated: 2026-10-12*
*Code revision: 97e4b91*
