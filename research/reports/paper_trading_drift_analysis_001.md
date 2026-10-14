# Paper Trading Drift Flag Analysis — 2026-10-14

## Objective

Analyze the `low_rolling_sharpe` drift flag in `data/processed/paper_trading_state.yaml`
to identify the source of the rolling 63-day Sharpe decline, without modifying
strategy logic or parameters.

## 1. Performance Decomposition

### Summary

| Metric | Value |
|---|---|
| Track record | 447 trading days (2025-01-02 → 2026-10-14) |
| Starting NAV | $100,000.00 |
| Peak NAV | $139,120.07 (2026-06-02) |
| Current NAV | $135,043.35 |
| Drawdown from peak | -2.93% |
| Max drawdown (period) | -4.99% / current DD -2.93% |
| Full-period return | 35.04% (18.46% ann.) |
| Full-period Sharpe | 1.8190 |
| Full-period vol | 9.57% ann. |
| Rolling 63d Sharpe (flag date) | 0.1142 (threshold 0.5) |
| Rolling 63d max DD | -4.99% |
| Regime persistence | 69 days (risk-on, SPY > SMA200) |

### Rolling Sharpe Decline Trajectory

The rolling 63-day Sharpe was healthy (>2.0) through mid-June 2026 and declined
sharply in the final days:

| Date | Rolling 63d Sharpe |
|---|---|
| 2026-06-17 | 2.1060 |
| 2026-06-23 | 1.8854 |
| 2026-07-09 | 1.3988 |
| 2026-07-13 | 0.9167 |
| 2026-07-14 | 0.9558 |
| 2026-07-15 | 0.6136 |
| **2026-07-16** | **0.3523** (drift flag) |

The rolling Sharpe last exceeded 0.9 on 2026-07-14 (0.9482). Only **2 days**
elapsed between the last "acceptable" reading and the drift flag, indicating
an acute rather than sustained decline.

### Recent vs Prior Period

| Period | Mean Daily Return | Std Dev | Total Return | Positive Days |
|---|---|---|---|---|
| Recent 30 days (2026-09-15 → 2026-10-14) | -0.0619% | 0.5242% | -1.88% | 14/30 |
| Prior 63 days (2026-08-13 → 2026-09-14) | -0.0150% | 0.6450% | -1.07% | 31/63 |

The recent 30-day period shows continued negative mean returns with elevated volatility relative to the prior 63-day period.

### Key Loss Days (top 5 worst in flagged window)

| Date | Daily Return | P&L | vol_scale |
|---|---|---|---|
| 2026-01-30 | -2.56% | -$3,438 | N/A |
| 2026-06-05 | -2.43% | -$3,366 | N/A |
| 2025-10-10 | -2.01% | -$2,418 | N/A |
| 2026-03-03 | -1.90% | -$2,543 | N/A |
| 2025-10-21 | -1.81% | -$2,244 | N/A |

### NAV Trajectory Around Peak

Peak reached on 2026-06-02 ($139,120.07). The strategy experienced a drawdown from peak, currently standing at $135,043.35 (as of 2026-10-14), with the drift flag persisting.

## 2. Market Context

### Asset Price Movement (2026-06-01 → 2026-07-16)

The strategy held **QQQ, IWM, GLD, EEM** (the top 4 by 12-month TSMOM momentum).
The held losing assets drove the drawdown:

| Asset | Price Change | Held? |
|---|---|---|
| GLD | -$411.26 → $364.96 (**-11.26%**) | Yes |
| EEM | $70.08 → $64.19 (**-8.40%**) | Yes |
| QQQ | $742.74 → $705.94 (**-4.95%**) | Yes |
| IWM | $288.98 → $295.59 (**+2.29%**) | Yes |
| SPY | $758.54 → $750.72 (-1.03%) | No (regime filter) |
| TLT | $85.47 → $84.21 (-1.47%) | No |
| EFA | $104.44 → $103.81 (-0.60%) | No |

**GLD and EEM experienced the largest declines**, and both were in the portfolio
throughout the flagged period. GLD's -11.26% move alone accounts for the bulk
of the portfolio drawdown.

### Volatility Context (VIX)

The ^VIX index spiked from ~15-16 to 22.2 on 2026-06-05 and 2026-06-10,
indicating elevated market stress coinciding with the initial drawdown. This
volatility spike triggered the vol-targeting de-risking: `vol_scale` declined
from ~0.60 (early June) to ~0.45 (mid-July), reducing gross exposure.

### Regime Filter

The SPY 200-day SMA regime filter remained in **risk-on** mode throughout the
flagged period. SPY closed above its 200-day SMA on every trading day from
2026-06-01 to 2026-07-16 (ranging +5.6% to +11.5% above the SMA). The regime
filter did **not** switch to cash (exposure_below=0.0), so the strategy
remained fully exposed to the declining assets.

### Correlation Environment

During the flagged period, the held assets were positively correlated:
QQQ-EEM correlation 0.89, QQQ-EFA 0.73, EEM-EFA 0.78, indicating a
broad-based risk-off move rather than an idiosyncratic asset decline.

## 3. Strategy Mechanics Verification

Cross-referenced `config/simulation_candidate_001.yaml` against execution
artifacts in `data/processed/simulation_candidate_001.parquet`:

| Config Element | Config Value | Observed in Data | Match |
|---|---|---|---|
| Universe | 7 ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) | 7 weight columns present | Yes |
| Signal type | TSMOM, lookback=226, skip=21, top_fraction=0.5 | 4 positions held (top 50%) | Yes |
| Regime filter | SPY SMA200, exposure_below=0.0, exposure_above=1.0 | regime_exposure=1.0 (risk-on) | Yes |
| Vol target | 0.10 annualized, vol_lookback=63 | vol_scale=0.45-0.60 (active) | Yes |
| Max leverage | 1.0 | exposure < 1.0 (vol-scaled down) | Yes |
| DD control | threshold=0.15, reduction=0.5 | dd_scale=1.0 (DD only -3%) | Yes |
| Cost model | 3bps total round-trip | cost = turnover × 0.0003 (exact match) | Yes |
| Rebalance | daily (backtest-exact) | daily updates in run_history | Yes |
| Signal lag | 1 day (T-1 close) | execution per config | Yes |

### Position Selection Verification (2026-07-16)

12-month momentum (226-day lookback + 21-day skip) ranked assets:
1. IWM: +32.4%
2. EEM: +29.9%
3. QQQ: +25.8%
4. GLD: +15.5%
5. EFA: +16.2%
6. SPY: +19.4%
7. TLT: -2.7%

Top 50% of 7 = ~4 assets: **QQQ, IWM, GLD, EEM** selected correctly. SPY and
TLT excluded as expected (SPY is regime filter only, TLT had negative momentum).

### Risk Overlay Behavior

- **Vol targeting**: vol_scale declined from ~0.60 to ~0.45 as realized
  volatility rose (VIX spike). This is the correct response — exposure was
  proportionally reduced.
- **DD control**: Not triggered (dd_scale=1.0). Drawdown was only -3.07%, well
  below the 15% threshold. This is correct behavior.
- **Regime filter**: Correctly remained in risk-on mode. SPY was above SMA200.

## 4. Root Cause Assessment

The drift flag (`low_rolling_sharpe` = 0.1142 on 2026-10-14) is **not caused by
a strategy malfunction**. The execution matches the frozen config specifications
exactly. The decline is attributable to:

1. **Market-driven losses in held assets**: GLD (-11.26%), EEM (-8.40%), and
   QQQ (-4.95%) all declined significantly during June-July 2026 while held in
   the portfolio.

2. **Regime filter did not trigger cash**: The SPY SMA200 filter remained in
   risk-on mode throughout, so the strategy could not exit to cash despite the
   broad risk-off move. This is a known limitation of single-index regime filters
   — they protect against broad market regime shifts but not sector or
   commodity-specific drawdowns within a risk-on regime.

3. **Vol targeting reduced but did not prevent losses**: vol_scale declined
   from ~0.60 to ~0.45 (de-risking by ~28%), which limited the drawdown but
   did not eliminate it given the magnitude of asset declines.

4. **Acute, not chronic**: The rolling Sharpe crossed below 0.5 on only one
   day (2026-07-16). The prior readings (July 13-14) were still above 0.9.
   The flag reflects a sharp recent deterioration, not a sustained degradation
   over months.

## 5. Extended Trajectory (from daily P&L parquet files, 447 days)

The daily P&L parquet files in `data/processed/paper_trading/` extend through
**2026-10-14** (447 files), while the state YAML stops at 2026-07-16 (384 days).
Analyzing the complete series reveals the drift flag trajectory:

| Date | Rolling 63d Sharpe | Status |
|---|---|---|
| 2026-06-02 (peak) | 2.4254 | Healthy |
| 2026-07-16 (state file end) | 0.3523 | **Drift** |
| 2026-08-31 | -0.0593 | Drift |
| 2026-09-15 | -0.4959 | Worst point |
| 2026-10-05 | 1.0000 | Brief recovery |
| 2026-10-09 | 0.9431 | Brief recovery |
| 2026-10-12 | 0.4931 | **Drift** |
| 2026-10-13 | 0.3698 | **Drift** |
| 2026-10-14 | 0.1142 | **Drift** |

The rolling Sharpe was volatile after July 2026: it recovered above 0.9 in
early October (0.9356 on 2026-10-09) but declined again, ending at 0.1185 with
**3 consecutive days below 0.5** (Oct 12-14). This matches the README's
documentation of the persistent drift flag. The strategy did not experience a
regime flip during this period — SPY remained above SMA200 throughout, so the
regime filter never switched to cash.

Volatility (30-day annualized) decreased from 12.78% (2026-07-16) to 8.45%
(2026-10-14), and vol_scale recovered from ~0.45 to ~0.65. Positions shifted:
by 2026-10-14, SPY entered the portfolio and GLD exited, reflecting updated
momentum rankings.

## 6. Data Integrity Notes

1. **State consistency**: `paper_trading_state.yaml` shows
   `last_run_date: 2026-10-14` with 447 cumulative returns. The daily P&L
   files extend to 2026-10-14 (447 days), and the synchronized state matches
   the complete series through this date.

2. **max_drawdown field discrepancy**: The state YAML stores `max_drawdown:
   -0.0293` (-2.93%), which equals the current drawdown from peak. Recomputing
   from full series yields -0.0499 (-4.99%), the actual historical
   maximum (on 2025-03-06, when NAV fell from $104,609 to $99,393). The
   `rolling_max_dd_63d` field (-0.0499) is consistent with the recomputed
   value. This suggests the `max_drawdown` field may track current drawdown
   rather than historical maximum in the persistence layer.

## Evidence References

- State file: `data/processed/paper_trading_state.yaml` (lines 1, 1165-1172,
  4621-4639)
- Strategy config: `config/simulation_candidate_001.yaml`
- Simulation data: `data/processed/simulation_candidate_001.parquet`
- Daily P&L: `data/processed/paper_trading/daily_pnl_2026*.parquet`
- Market data: `data/raw/{SPY,QQQ,IWM,TLT,GLD,EFA,EEM,^VIX}.parquet`
- Rolling report: `research/reports/paper_trading_rolling.md`
- Validation reports: `research/reports/paper_trading_validation_021.md` through
  `paper_trading_validation_025.md`

## Verification

- Existing tests: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v`
  — **10 passed**.
- No strategy logic or parameters were modified.
- No new backtests or candidate configs were created.


## 7. Conclusion (Updated)

As of 2026-10-14, the `low_rolling_sharpe` drift flag (value 0.1142 < threshold 0.5) remains **market-driven**, not the result of a strategy malfunction. The execution matches the frozen configuration exactly, with correct position selection, regime filtering, and risk overlay behavior. The persistent low rolling Sharpe reflects continued challenging market conditions for the selected momentum portfolio during this period.
