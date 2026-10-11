# Experiment: Regime-Aware Performance Analysis (tsmomentum_regime_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_003.md` (best Cycle 4 config).

**Objective**: Determine whether the best Cycle 4 configuration — combined
volatility targeting (10%) + drawdown control (15%) applied to 226-day TSMOM —
performs differently across market regimes. If performance is regime-conditional,
a regime filter may improve the risk-adjusted return toward the 0.9 promotion gate.

**Strategy analyzed**: combined_vol_0.1_dd_0.15, lookback=226, skip=21,
top_fraction=0.5 (unfiltered baseline from Cycle 4).

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached parquet in `data/raw/`)
- **Date Range**: 1993-01-01 to 2026-10-09
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- **Regime drivers**: SPY (trend / volatility) and ^VIX (volatility sentiment),
  both from Yahoo Finance daily OHLCV.
- **Test Period**: 2018-01-01 to 2026-10-09 (2205 test days)
- **Point-in-Time**: Regime classifications use only contemporaneous driver
  prices; the SPY 200-day SMA and 63-day realized vol are computed from data
  available up to (and including) each day — these are descriptive regime tags,
  not forward-looking signals.
- **Cost Model**: 1.0 bps + 2.0 bps = 3.0 bps round-trip

---

## Unfiltered Strategy Baseline (Test Period)

| Metric | Value |
|--------|-------|
| Test Sharpe | 0.7458 |
| Annualized Return | 0.0929 |
| Annualized Vol | 0.0978 |
| Max Drawdown | -0.1660 |
| Profit Factor | 1.18 |
| Trades | 1812 |
| Avg Exposure | 0.7092 |

---

## Regime Classification Methods

Three pre-specified regime classification methods (defined before seeing results):

1. **SPY Trend Regime** — Bull when SPY close > 200-day SMA; Bear otherwise.
   Captures the dominant market-direction regime (risk-on vs risk-off).
2. **VIX Level Regime** — Low vol when VIX <= 20; High vol when VIX > 20.
   Captures volatility-sentiment regime (calm vs stressed markets).
3. **SPY Realized Volatility Regime** — Low vol when 63-day rolling annualized
   vol of SPY <= its median; High vol otherwise. Captures realized-price
   volatility regime independent of the VIX level.

(An inflation-proxy regime via 10-year yield ^TNX was considered but not used,
because the yfinance fetch path does not return a clean Close field for ^TNX in
this environment; realized volatility is used as the third lens instead.)

---

## Per-Regime Performance

### spy_trend

| Regime | N Days | Sharpe | Ann. Return | Ann. Vol | Max DD | Trades | Avg Exposure |
|--------|--------|--------|-------------|----------|--------|--------|---------------|
| Bull (SPY > 200d SMA) | 1573 | 1.6674 | 0.1797 | 0.0957 | -0.0779 | 1275 | 0.7890 |
| Bear (SPY < 200d SMA) | 433 | -1.3748 | -0.1345 | 0.1124 | -0.2500 | 426 | 0.4980 |

**Outperformer**: Bull (SPY > 200d SMA) (Sharpe 1.6674, 78.4% of test days)

**Underperformer**: Bear (SPY < 200d SMA) (Sharpe -1.3748, 21.6% of test days)

**Overall test Sharpe**: 0.7458
**Regime Sharpe gap** (best - worst): 3.0422

The strategy's Sharpe varies meaningfully across regimes, indicating regime-conditional performance — a regime filter may add value.


### vix

| Regime | N Days | Sharpe | Ann. Return | Ann. Vol | Max DD | Trades | Avg Exposure |
|--------|--------|--------|-------------|----------|--------|--------|---------------|
| Low vol (VIX <= 20) | 1427 | 3.0935 | 0.2751 | 0.0825 | -0.0779 | 1075 | 0.7720 |
| High vol (VIX > 20) | 778 | -1.6494 | -0.1763 | 0.1190 | -0.4559 | 741 | 0.5939 |

**Outperformer**: Low vol (VIX <= 20) (Sharpe 3.0935, 64.7% of test days)

**Underperformer**: High vol (VIX > 20) (Sharpe -1.6494, 35.3% of test days)

**Overall test Sharpe**: 0.7458
**Regime Sharpe gap** (best - worst): 4.7430

The strategy's Sharpe varies meaningfully across regimes, indicating regime-conditional performance — a regime filter may add value.


### spy_vol

| Regime | N Days | Sharpe | Ann. Return | Ann. Vol | Max DD | Trades | Avg Exposure |
|--------|--------|--------|-------------|----------|--------|--------|---------------|
| Low vol (63d vol <= 14.3%) | 1071 | 0.9045 | 0.1124 | 0.1022 | -0.1001 | 813 | 0.8574 |
| High vol (63d vol > 14.3%) | 1071 | 0.6054 | 0.0782 | 0.0961 | -0.1349 | 998 | 0.6023 |

**Outperformer**: Low vol (63d vol <= 14.3%) (Sharpe 0.9045, 50.0% of test days)

**Underperformer**: High vol (63d vol > 14.3%) (Sharpe 0.6054, 50.0% of test days)

**Overall test Sharpe**: 0.7458
**Regime Sharpe gap** (best - worst): 0.2990

The strategy's Sharpe varies meaningfully across regimes, indicating regime-conditional performance — a regime filter may add value.

---

## Regime Day Counts (Test Period)

| Method | Regime | N Days | % of Test |
|--------|--------|--------|-----------|
| spy_trend | Bull (SPY > 200d SMA) | 1573 | 78.4% |
| spy_trend | Bear (SPY < 200d SMA) | 433 | 21.6% |
| vix | Low vol (VIX <= 20) | 1427 | 64.7% |
| vix | High vol (VIX > 20) | 778 | 35.3% |
| spy_vol | Low vol (63d vol <= 14.3%) | 1071 | 50.0% |
| spy_vol | High vol (63d vol > 14.3%) | 1071 | 50.0% |

---

## Interpretation

The unfiltered best Cycle 4 config achieves an overall test Sharpe of
0.7458. Performance is not uniform across regimes:
the weakest regime band is **vix: High vol (VIX > 20)** (Sharpe
-1.6494) versus the strongest band. This regime-conditional
behavior motivates the regime filters tested next in
`tsmomentum_regime_filter_001.md`.

---

*Report generated: 2026-10-11*
*Code revision: f7cbf05*
