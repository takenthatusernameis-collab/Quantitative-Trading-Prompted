# Experiment: Walk-Forward & Plateau Validation of SPY Trend Filter (tsmomentum_regime_filter_wf_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_004.md` (Cycle 5 promoted candidate).

**Objective**: Validate that the Cycle 5 promoted candidate — 226-day TSMOM with
combined volatility-targeting (10%) + drawdown-control (15%) and SPY 200-day
SMA trend filter — is not a single-period or single-parameter artifact, via:
1. Walk-forward evaluation (fixed parameters, no re-optimization per fold)
2. SMA window parameter plateau check (pre-specified window set)

**Candidate Configuration (Fixed)**:
- Universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- Signal: 226-day TSMOM (lookback=226, skip=21, top_fraction=0.5)
- Risk Overlay: Combined vol-targeting (10%) + drawdown control (15%)
- Regime Filter: SPY trend filter (0% exposure when SPY < SMA; 100% otherwise)
- Cost Model: 3 bps round-trip (1 bps commission + 2 bps slippage)

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached parquet in `data/raw/`)
- **Date Range**: 1993-01-01 to 2026-10-09
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- **Regime Driver**: SPY (trend via SMA)
- **Test Period**: 2018-01-01 to 2026-10-09
- **Point-in-Time**: All signals use only data available at formation; weights
  shifted 1 day; SPY SMA computed point-in-time; purge/embargo in walk-forward.
- **Cost Model**: 1.0 bps + 2.0 bps = 3.0 bps round-trip

---

## 1. Walk-Forward Evaluation

### Walk-Forward Design (Pre-Specified, Matches Cycle 3)

- **Rolling Window**: 10-year training, 1-year test, 6-month step
- **Purge**: 21 days between train and test
- **Embargo**: 21 days after test period end
- **Parameters**: Fixed across all folds (no per-fold re-optimization)
- **Candidate**: SPY 200d SMA trend filter on Cycle 4 best config

### Per-Fold Results

| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |
|------|-------------|-----------|------------|----------|-------------|------------|---------------|-------------|-------------|
| 1 | 1993-01-01 | 2002-08-29 | 2002-09-30 | 2003-09-16 | 1.2280 | 2.5550 | 0.2376 | -0.0307 | 94 |
| 2 | 1993-06-28 | 2003-02-21 | 2003-03-25 | 2004-03-10 | 1.2213 | 2.5821 | 0.3009 | -0.0346 | 215 |
| 3 | 1993-12-21 | 2003-08-18 | 2003-09-17 | 2004-09-02 | 1.3993 | 0.3027 | 0.0486 | -0.0797 | 211 |
| 4 | 1994-06-15 | 2004-02-10 | 2004-03-11 | 2005-02-25 | 1.5441 | 1.2700 | 0.1438 | -0.0761 | 154 |
| 5 | 1994-12-08 | 2004-08-04 | 2004-09-03 | 2005-08-22 | 1.4240 | 1.9494 | 0.2102 | -0.0601 | 146 |
| 6 | 1995-06-02 | 2005-01-27 | 2005-02-28 | 2006-02-14 | 1.3279 | 2.1849 | 0.2427 | -0.0601 | 146 |
| 7 | 1995-11-27 | 2005-07-22 | 2005-08-23 | 2006-08-09 | 1.2888 | 2.3382 | 0.2625 | -0.0691 | 163 |
| 8 | 1996-05-21 | 2006-01-16 | 2006-02-15 | 2007-02-01 | 1.3808 | 1.8912 | 0.2035 | -0.0691 | 207 |
| 9 | 1996-11-13 | 2006-07-11 | 2006-08-10 | 2007-07-27 | 1.3005 | 1.3166 | 0.1580 | -0.0512 | 230 |
| 10 | 1997-05-08 | 2007-01-03 | 2007-02-02 | 2008-01-21 | 1.3682 | 2.0815 | 0.2275 | -0.0512 | 198 |
| 11 | 1997-10-31 | 2007-06-28 | 2007-07-30 | 2008-07-15 | 1.3671 | 2.7409 | 0.1882 | -0.0167 | 78 |
| 12 | 1998-04-27 | 2007-12-21 | 2008-01-22 | 2009-01-07 | 1.4088 | -21.8299 | -0.0013 | -0.0012 | 2 |
| 13 | 1998-10-20 | 2008-06-16 | 2008-07-16 | 2009-07-02 | 1.4459 | -0.2665 | 0.0104 | -0.0287 | 8 |
| 14 | 1999-04-14 | 2008-12-09 | 2009-01-08 | 2009-12-25 | 1.2816 | 1.7670 | 0.1799 | -0.0446 | 114 |
| 15 | 1999-10-07 | 2009-06-03 | 2009-07-03 | 2010-06-21 | 1.3580 | 1.5242 | 0.1893 | -0.0585 | 212 |
| 16 | 2000-03-31 | 2009-11-26 | 2009-12-28 | 2010-12-14 | 1.4469 | 1.0671 | 0.1240 | -0.0585 | 150 |
| 17 | 2000-09-25 | 2010-05-21 | 2010-06-22 | 2011-06-08 | 1.3349 | 1.0960 | 0.1255 | -0.0484 | 164 |
| 18 | 2001-03-20 | 2010-11-15 | 2010-12-15 | 2011-12-01 | 1.4237 | 0.2426 | 0.0400 | -0.0563 | 162 |
| 19 | 2001-09-12 | 2011-05-10 | 2011-06-09 | 2012-05-25 | 1.4900 | 0.9429 | 0.0805 | -0.0426 | 50 |
| 20 | 2002-03-07 | 2011-11-02 | 2011-12-02 | 2012-11-19 | 1.3917 | 1.2267 | 0.1225 | -0.0478 | 24 |
| 21 | 2002-08-30 | 2012-04-26 | 2012-05-28 | 2013-05-14 | 1.5007 | 2.2063 | 0.2369 | -0.0478 | 131 |
| 22 | 2003-02-24 | 2012-10-19 | 2012-11-20 | 2013-11-06 | 1.4860 | 2.1734 | 0.2356 | -0.0574 | 238 |
| 23 | 2003-08-19 | 2013-04-15 | 2013-05-15 | 2014-05-01 | 1.4046 | 0.8107 | 0.1013 | -0.0574 | 236 |
| 24 | 2004-02-11 | 2013-10-08 | 2013-11-07 | 2014-10-24 | 1.3381 | 0.4830 | 0.0669 | -0.0558 | 184 |
| 25 | 2004-08-05 | 2014-04-02 | 2014-05-02 | 2015-04-20 | 1.5174 | 1.1702 | 0.1268 | -0.0414 | 102 |
| 26 | 2005-01-28 | 2014-09-25 | 2014-10-27 | 2015-10-13 | 1.4013 | 0.8976 | 0.0920 | -0.0421 | 35 |
| 27 | 2005-07-25 | 2015-03-20 | 2015-04-21 | 2016-04-06 | 1.4039 | 0.2792 | 0.0377 | -0.0399 | 18 |
| 28 | 2006-01-17 | 2015-09-14 | 2015-10-14 | 2016-09-29 | 1.1924 | 1.3453 | 0.1099 | -0.0342 | 28 |
| 29 | 2006-07-12 | 2016-03-08 | 2016-04-07 | 2017-03-24 | 1.1945 | 0.2969 | 0.0442 | -0.0993 | 29 |
| 30 | 2007-01-04 | 2016-08-31 | 2016-09-30 | 2017-09-18 | 1.1734 | 0.6332 | 0.0780 | -0.0865 | 60 |
| 31 | 2007-06-29 | 2017-02-23 | 2017-03-27 | 2018-03-13 | 1.0889 | 1.6764 | 0.1906 | -0.0867 | 75 |
| 32 | 2007-12-24 | 2017-08-18 | 2017-09-19 | 2018-09-05 | 0.9464 | 1.1373 | 0.1303 | -0.0867 | 148 |
| 33 | 2008-06-17 | 2018-02-12 | 2018-03-14 | 2019-02-28 | 1.0242 | 0.2472 | 0.0395 | -0.0614 | 130 |
| 34 | 2008-12-10 | 2018-08-07 | 2018-09-06 | 2019-08-23 | 1.0866 | 1.0883 | 0.1055 | -0.0591 | 28 |
| 35 | 2009-06-04 | 2019-01-30 | 2019-03-01 | 2020-02-17 | 1.0399 | 3.2521 | 0.2508 | -0.0371 | 26 |
| 36 | 2009-11-27 | 2019-07-25 | 2019-08-26 | 2020-08-11 | 0.9801 | 3.9121 | 0.3062 | -0.0392 | 24 |
| 37 | 2010-05-24 | 2020-01-17 | 2020-02-18 | 2021-02-03 | 1.1593 | 2.3629 | 0.2446 | -0.0574 | 124 |
| 38 | 2010-11-16 | 2020-07-13 | 2020-08-12 | 2021-07-29 | 1.2404 | 0.7952 | 0.1023 | -0.0574 | 233 |
| 39 | 2011-05-11 | 2021-01-05 | 2021-02-04 | 2022-01-21 | 1.2415 | -0.0836 | 0.0112 | -0.0632 | 243 |
| 40 | 2011-11-03 | 2021-06-30 | 2021-07-30 | 2022-07-18 | 1.2987 | -0.1073 | 0.0111 | -0.0632 | 148 |
| 41 | 2012-04-27 | 2021-12-23 | 2022-01-24 | 2023-01-10 | 1.1737 | 0.8947 | 0.0556 | -0.0145 | 29 |
| 42 | 2012-10-22 | 2022-06-17 | 2022-07-19 | 2023-07-05 | 1.1517 | 1.5584 | 0.1341 | -0.0497 | 32 |
| 43 | 2013-04-16 | 2022-12-12 | 2023-01-11 | 2023-12-28 | 1.0904 | 1.8332 | 0.2003 | -0.0779 | 118 |
| 44 | 2013-10-09 | 2023-06-06 | 2023-07-06 | 2024-06-21 | 1.1322 | 1.8186 | 0.2022 | -0.0779 | 185 |
| 45 | 2014-04-03 | 2023-11-29 | 2023-12-29 | 2024-12-16 | 1.0731 | 1.8342 | 0.2073 | -0.0646 | 220 |
| 46 | 2014-09-26 | 2024-05-23 | 2024-06-24 | 2025-06-10 | 1.2036 | 1.1148 | 0.1249 | -0.0646 | 186 |
| 47 | 2015-03-23 | 2024-11-15 | 2024-12-17 | 2025-12-03 | 1.1557 | 1.9609 | 0.2033 | -0.0499 | 115 |
| 48 | 2015-09-15 | 2025-05-12 | 2025-06-11 | 2026-05-28 | 1.1903 | 2.8969 | 0.3197 | -0.0382 | 160 |


### Aggregate Walk-Forward Statistics

| Metric | Value |
|--------|-------|
| Folds | 48 |
| Mean Test Sharpe | 0.9473 |
| Std Test Sharpe | 3.4798 |
| Median Test Sharpe | 1.2933 |
| Min Test Sharpe | -21.8299 |
| Max Test Sharpe | 3.9121 |
| % Positive Sharpe Folds | 91.7% |
| Mean Test Ann. Return | 14.71% |
| Mean Test Max DD | -5.41% |
| Mean Test Trades | 125.3 |
| Total Pooled OOS Trades | 6013 |

---

## 2. SMA Window Parameter Plateau Check

### Pre-Specified SMA Windows

From NEXT_AGENT_TASK.md: `[150, 175, 200, 226, 250, 277]` (6 values spanning ~150-277 days)

### Results (Test Period 2018-2026, Fixed Candidate Config)

| SMA Window | Test Sharpe | Ann. Return | Max DD | Trades | Sortino | Profit Factor | Meets 0.9? |
|------------|-------------|-------------|--------|--------|---------|---------------|------------|
| 150 | 1.5504 | 0.1570 | -0.0682 | 1170 | 1.9052 | 1.38 | **YES** |
| 175 | 1.4933 | 0.1517 | -0.0682 | 1204 | 1.8386 | 1.37 | **YES** |
| 200 | 1.4178 | 0.1446 | -0.0779 | 1196 | 1.7477 | 1.35 | **YES** |
| 226 | 1.3178 | 0.1359 | -0.0779 | 1233 | 1.6205 | 1.32 | **YES** |
| 250 | 1.2781 | 0.1324 | -0.0820 | 1279 | 1.5826 | 1.31 | **YES** |
| 277 | 1.2270 | 0.1282 | -0.0876 | 1303 | 1.5266 | 1.30 | **YES** |


### Plateau Verdict

**Windows with Sharpe >= 0.9: 6/6**

**Threshold**: >= 2 of 6 windows (including the baseline 200d) must achieve Sharpe >= 0.9
for the result to be considered robust (not won/lost on the single 200d value).

**Result**: **ROBUST — Plateau holds**

---

## 3. Promotion-Gate Verdict (Final)

### Gate Criteria

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| Walk-Forward Mean OOS Sharpe >= 0.9 | 0.90 | 0.9473 | PASS |
| >= 50% of WF folds positive Sharpe | 50% | 91.7% | PASS |
| SMA Plateau Check (>= 2/6 windows >= 0.9) | 2 | 6 | PASS |

### Final Classification

## **Credible Candidate**

All three validation gates are met. The SPY trend-filter candidate is
confirmed as a **Credible Candidate** for advancement to simulation/paper-trading.

The walk-forward mean OOS Sharpe of 0.9473 with 91.7% positive
folds and 6013 pooled trades, combined with a robust SMA plateau
(6/6 windows >= 0.9), indicates the effect generalizes across time and
is not sensitive to the exact 200-day window choice.

---

## Walk-Forward Interpretation

The walk-forward test uses **fixed parameters** (no re-optimization) across all
folds. This is a true out-of-sample validation: the candidate configuration
(226-day TSMOM + combined overlay + 200d SPY SMA filter) is evaluated on each
test fold exactly as specified, using only data available up to the test start.

Mean OOS Sharpe = 0.9473 (above the 0.9 gate)
Positive fold rate = 91.7% (above the 50% gate)
Total OOS trades = 6013

This result should be compared to Cycle 3's unfiltered baseline walk-forward
(mean test Sharpe 0.679, 97.9% positive folds). The SPY trend filter is expected
to improve OOS consistency by removing bear-regime exposure.

---

## Plateau Interpretation

The parameter plateau check tests whether the promotion-gate result depends
critically on the specific 200-day SMA window. If the gate is only passed at
exactly 200 days and fails at neighboring values (150, 175, 226, 250, 277),
the result is likely a parameter peak rather than a structural effect.

The plateau holds: 6 of 6 pre-specified windows clear the 0.9 Sharpe gate, including the baseline 200d. The effect is robust to the SMA window choice.

---

## Reproducibility

### Reproduction Commands

```bash
python3 research/run_cycle6.py
```

### Code Revision

97e4b91

### Configuration Hash

Candidate config: lookback=226, skip=21, top_fraction=0.5, vol_target=0.1, dd_threshold=0.15, spy_sma=200
Walk-forward: train_years=10.0, test_months=12.0, step_months=6.0, purge=21, embargo=21
Plateau SMA windows: [150, 175, 200, 226, 250, 277]

---

## Artifacts Referenced

| Artifact | Path |
|----------|------|
| Cycle 5 Regime Analysis | `research/experiments/tsmomentum_regime_001.md` |
| Cycle 5 Regime Filter Test | `research/experiments/tsmomentum_regime_filter_001.md` |
| Cycle 5 Decision | `research/reports/tsmomentum_decision_003.md` |
| Cycle 5 Hypothesis | `research/hypotheses/tsmomentum_004.md` |
| Cycle 3 Walk-Forward | `research/experiments/tsmomentum_walkforward_001.md` |

---

*Report generated: 2026-10-12*
*Code revision: 97e4b91*
