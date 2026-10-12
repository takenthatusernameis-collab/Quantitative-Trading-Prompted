# Experiment: Regime Filter Test (tsmomentum_regime_filter_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_003.md`. Builds on the regime analysis in
`research/experiments/tsmomentum_regime_001.md`.

**Objective**: Test whether two *pre-specified* regime filters, applied on top
of the Cycle 4 best configuration (lookback=226, vol_target=0.10, dd=0.15),
can elevate the test-period net Sharpe to >= 0.9 (the promotion gate).

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached)
- **Date Range**: 1993-01-01 to 2026-10-09
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- **Regime drivers**: SPY (trend), ^VIX (volatility sentiment)
- **Test Period**: 2018-01-01 to 2026-10-09
- **Cost Model**: 1.0 bps + 2.0 bps = 3.0 bps round-trip

---

## Pre-Specified Regime Filters

Both filters are defined exactly as in NEXT_AGENT_TASK.md (no tuning):

1. **SPY Trend Filter**: Set exposure to 0% (go to cash) when SPY < 200-day SMA.
   Re-enter (100% exposure) when SPY > 200-day SMA.
   - Applied by multiplying the base momentum test-period weights by an
     exposure factor (0.0 when SPY below SMA, 1.0 otherwise), then running the
     combined vol+dd overlay.
   - Fraction of test days in cash: **19.9%**

2. **VIX Volatility Filter**: Reduce exposure to 50% when VIX > 30. Full exposure
   (100%) when VIX <= 30. (^VIX from Yahoo Finance.)
   - Applied by multiplying base weights by exposure factor (0.5 when VIX>30,
     1.0 otherwise), then running the combined vol+dd overlay.
   - Fraction of test days at 50% exposure: **7.0%**

---

## Methodology

The regime exposure factor is applied to the **base 226-day momentum weights**
on the test-period slice, *before* the combined volatility-targeting (10%) and
drawdown-control (15%) overlay. This isolates the marginal effect of the regime
filter from the risk overlay. The combined overlay is then applied identically
to the unfiltered case, so the only difference between filtered and unfiltered
is the regime exposure gate.

---

## Results: Filtered vs. Unfiltered (Test Period)

| Configuration | Sharpe | Ann. Return | Max DD | Sortino | Profit Factor | Trades | Avg Exposure | Meets Gate? |
|---------------|--------|-------------|--------|---------|---------------|--------|---------------|-------------|
| Unfiltered (Cycle 4 best) | 0.7458 | 0.0929 | -0.1660 | 0.9791 | 1.18 | 1812 | 0.7092 | No |
| SPY Trend Filter (cash when SPY<200d SMA) | 1.4178 | 0.1446 | -0.0779 | 1.7477 | 1.35 | 1196 | 0.6506 | **YES** |
| VIX Filter (50% exposure when VIX>30) | 1.0463 | 0.1211 | -0.1227 | 1.4460 | 1.23 | 1768 | 0.7271 | **YES** |

---

## Best Filter Configuration

| Metric | Value |
|--------|-------|
| Best Filter | SPY Trend Filter (cash when SPY<200d SMA) |
| Test Sharpe | 1.4178 |
| Annualized Return | 0.1446 |
| Max Drawdown | -0.0779 |
| Trades | 1196 |
| Gap to 0.9 Sharpe | 0.0000 |
| Meets promotion gate | **YES** |

---

## Interpretation

The **SPY Trend Filter (cash when SPY<200d SMA)** filter achieves a test Sharpe of 1.4178, meeting the 0.9 promotion gate.


---

## Cost-Model Note (Honest Accounting)

The hypothesis documents a **3 bps round-trip** transaction cost model
(1.0 bps commission + 2.0 bps slippage, see `config/settings.yaml` and
`tsmomentum_001.md`). Cycle 5 applies this cost model consistently.

**Cycle 4 caveat**: Cycle 4's combined-risk-overlay artifacts
(`tsmomentum_combined_risk_001.md`, `tsmomentum_risk_001.md`) were generated via
`src/evaluation/risk.py::combined_risk_overlay`. That overlay path computes
`cost_per_trade = commission_bps/10000 + slippage_bps/10000`, but
`get_cost_params()` already returns the bps values *divided by 10000* (i.e. as
per-unit fractions: 0.0001 and 0.0002). Dividing a second time yields an
effective transaction cost of ~3e-8 (effectively zero), which is why Cycle 4's
own report states "Cost Model: 0.0 bps commission + 0.0 bps slippage". The
non-overlay TSMOM backtest path (`eval_config` / `utils.run_backtest_for_config`,
which uses `cost_per_trade = commission_bps + slippage_bps`) does apply the
correct 3 bps; only the overlay path under-applies costs.

Cycle 5's own overlay helper applies the **correct** 3 bps cost model
(`cost_per_trade = commission_bps + slippage_bps`, the documented 3 bps). Under
this honest cost model the numbers in this report are computed; they are the
figures used for the promotion-gate assessment below.

| Configuration (correct 3 bps costs) | Sharpe | Max DD | Trades |
|-------------------------------------|--------|--------|--------|
| Unfiltered (Cycle 4 best) | 0.7458 | -0.1660 | 1812 |
| SPY Trend Filter (cash when SPY<200d SMA) | 1.4178 | -0.0779 | 1196 |
| VIX Filter (50% exposure when VIX>30) | 1.0463 | -0.1227 | 1768 |
For reference, Cycle 4's *documented* (under-costed, ~0 bps effective) combined overlay reported an unfiltered Sharpe of 0.7794; under the correct 3 bps model used here the unfiltered baseline is 0.7458. The regime filters clear the 0.9 gate under **both** cost treatments, so the promotion-gate conclusion is robust.
---

*Report generated: 2026-10-12*
*Code revision: 97e4b91*
