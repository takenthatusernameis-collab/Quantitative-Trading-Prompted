# Experiment: Baseline Backtest & Walk-Forward — Cross-Sectional Momentum (csmomentum_baseline_wf_001)

## Hypothesis Reference

`research/hypotheses/csmomentum_001.md` (Cycle 12 pre-registration, v001).
Candidate C3 from the Cycle 11 Opportunity Shortlist (29/35 — Exploratory
signal): long-only cross-sectional momentum over the broad 18-ETF universe.

**Mechanism**: Assets with higher intermediate-term returns relative to the
universe tend to continue outperforming (investor underreaction, slow
information diffusion). Long-only top-fraction equal-weight implementation
avoids the borrow-cost gap that blocks short-side strategies.

**Pre-registered falsification condition** (stated BEFORE any backtest
execution): the hypothesis is rejected if the walk-forward mean OOS Sharpe
< 0.9 OR < 50% of walk-forward folds have positive test Sharpe.

---

## Data Used

- **Source**: Yahoo Finance via yfinance, cached as daily parquet in
  `data/raw/` (18 ETF files + ^VIX index). No new data was fetched
  (`fetch_universe(..., force=False)`; cache-only).
- **Date Range**: 1993-01-01 to 2026-10-09 (8,482 aligned trading days)
- **Frequency**: Daily (end-of-day OHLCV)
- **Universe**: SPY, QQQ, IWM, TLT, GLD, DBC, VNQ, EFA, EEM, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY
- **Price Field**: Close (EOD), forward-filled onto the union trading calendar
- **Point-in-Time Treatment**: Momentum at date t uses only prices through
  t-skip-lookback; weights shifted 1 day (signal on T-1 close, positions
  effective T); monthly month-end rebalance calendar carries weights forward
  intra-month (no intra-month trading); walk-forward uses 21-day purge and
  21-day embargo between train and test.
- **Missing-Data Handling**: Pre-inception cells are NaN (not back-filled)
  and are excluded from the cross-sectional ranking (`na_option="keep"`),
  so universe breadth grows point-in-time from 8 assets (1993-1998) to 17
  (1998-2006) to 18 (2006+). Aligned Close completeness below reflects this.
- **Content hash (aligned Close frame)**: bc5d600ce25c72fc

| Symbol | Rows | Start | End | Close Complete (aligned) |
|--------|------|-------|-----|--------------------------|
| SPY | 8,482 | 1993-01-29 | 2026-10-09 | 100.0% |
| QQQ | 8,482 | 1999-03-10 | 2026-10-09 | 81.8% |
| IWM | 8,482 | 2000-05-26 | 2026-10-09 | 78.2% |
| TLT | 8,482 | 2002-07-30 | 2026-10-09 | 71.8% |
| GLD | 8,482 | 2004-11-18 | 2026-10-09 | 64.9% |
| DBC | 8,482 | 2006-02-06 | 2026-10-09 | 61.3% |
| VNQ | 8,482 | 2004-09-29 | 2026-10-09 | 65.4% |
| EFA | 8,482 | 2001-08-27 | 2026-10-09 | 74.5% |
| EEM | 8,482 | 2003-04-14 | 2026-10-09 | 69.7% |
| XLB | 8,482 | 1998-12-22 | 2026-10-09 | 82.4% |
| XLE | 8,482 | 1998-12-22 | 2026-10-09 | 82.4% |
| XLF | 8,482 | 1998-12-22 | 2026-10-09 | 82.4% |
| XLI | 8,482 | 1998-12-22 | 2026-10-09 | 82.4% |
| XLK | 8,482 | 1998-12-22 | 2026-10-09 | 82.4% |
| XLP | 8,482 | 1998-12-22 | 2026-10-09 | 82.4% |
| XLU | 8,482 | 1998-12-22 | 2026-10-09 | 82.4% |
| XLV | 8,482 | 1998-12-22 | 2026-10-09 | 82.4% |
| XLY | 8,482 | 1998-12-22 | 2026-10-09 | 82.4% |

---

## Configuration

**Baseline (pre-registered, frozen in `config/csmomentum_candidate_001.yaml`)**:

| Parameter | Value |
|-----------|-------|
| Signal | Cross-sectional momentum (rank-based) |
| Lookback | 252 trading days (~12 months) |
| Skip | 21 trading days (~1 month, short-term reversal skip) |
| Top fraction | 0.5 (equal-weight top 50% by momentum rank) |
| Rebalance | Monthly (month-end calendar) |
| Signal lag | 1 day (T-1 close -> T position) |
| Risk overlay | NONE (baseline before complexity, AGENTS.md) |
| Commission | 1.0 bps |
| Slippage | 2.0 bps |
| Round-trip cost | 3.0 bps on weight changes |
| Risk-free rate | 2.0% annualized (flat) |

**Pre-specified Robustness Grid (fixed count for multiple-testing control)**:

lookback in {189, 252, 315}, skip in {21, 42},
top_fraction in {0.3, 0.5, 0.7}. Baseline is the center point
(252, 21, 0.5). No configurations were added post-hoc and no
configuration is selected on test-period results.

**Pre-registration count discrepancy (disclosed)**: the frozen hypothesis
and config label the grid "27 configurations", but the pre-specified
parameter values (3 lookbacks x 2 skips x 3 top-fractions) yield
**18 unique combinations**. All 18 pre-specified
combinations were evaluated; no additional configurations were invented to
reach the mislabeled count. The multiple-testing deflation is reported at
the pre-registered N=27 (conservative, primary) and at
the actual evaluated count N=18 (disclosure).

**Config file SHA-256 (first 12 hex)**: `296a619f7942`

---

## Train/Validation/Test Splits & Walk-Forward Design

| Split | Period | Purpose |
|-------|--------|---------|
| Train | 1993-01-01 to 2009-12-31 | Parameter selection (NOT used — baseline is pre-specified) |
| Validation | 2010-01-01 to 2017-12-31 | Robustness screening (diagnostic only) |
| Test | 2018-01-01 to 2026-10-09 | Final holdout, promotion-gate decision |

**Walk-Forward Design (matches Cycle 6 `tsmomentum_regime_filter_wf_001.md` exactly)**:

- Rolling window: 10-year train, 12-month test, 6-month step
- Purge: 21 days between train end and test start
- Embargo: 21 days after test period end
- Parameters: FIXED across all folds (no per-fold re-optimization)
- Folds: 48

---

## 1. Baseline Backtest (Test Period 2018-01-01 to 2026-10-09)

| Period | Total Return | Ann. Return | Ann. Vol | Sharpe | Sortino | Max DD | Ann. Turnover | Trades | Profit Factor | Avg Exposure |
|--------|--------------|-------------|----------|--------|---------|--------|---------------|--------|---------------|--------------|
| Test (2018-2026) | 1.1383 | 0.0907 | 0.1725 | 0.4101 | 0.4922 | -0.3571 | 2.06 | 62 | 1.12 | 1.0000 |
| Validation (2010-2017) | 1.1057 | 0.0977 | 0.1421 | 0.5468 | 0.6815 | -0.2188 | 2.03 | 50 | 1.14 | 1.0000 |
| Train (1993-2009) | 3.2076 | 0.0886 | 0.1767 | 0.3884 | 0.5188 | -0.4267 | 1.68 | 72 | 1.11 | 0.9306 |

**Tail metrics (test period, daily net returns)**:

| Metric | Value |
|--------|-------|
| 95% VaR (daily) | 0.0161 (1.61%) |
| 95% CVaR (daily) | 0.0257 (2.57%) |
| Worst day | -0.1236 (-12.36%) |
| Trade count (test) | 62 |

**Artifacts**:

| Artifact | Path | Rows |
|----------|------|------|
| Daily simulation series | `data/processed/simulation_csmomentum_001.parquet` | 8,482 |
| Trade log | `data/processed/trades_csmomentum_001.parquet` | 581 |
| Point-in-time weights | `data/processed/weights_csmomentum_001.parquet` | 8,482 |

---

## 2. Walk-Forward Evaluation (48 Folds, Fixed Parameters)

### Walk-Forward Design

10-year train / 1-year test / 6-month step, 21-day purge, 21-day embargo,
fixed pre-registered parameters (252, 21, 0.5), monthly
rebalance, 1-day lag, 3 bps round-trip costs. No per-fold re-optimization.

### Per-Fold Results

| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |
|------|-------------|-----------|------------|----------|--------------|------------|----------------|--------------|-------------|
| 1 | 1993-01-01 | 2002-08-29 | 2002-09-30 | 2003-09-16 | 0.4227 | 1.1974 | 0.2605 | -0.1392 | 6 |
| 2 | 1993-06-28 | 2003-02-21 | 2003-03-25 | 2004-03-10 | 0.3565 | 2.1950 | 0.3370 | -0.0547 | 6 |
| 3 | 1993-12-21 | 2003-08-18 | 2003-09-17 | 2004-09-02 | 0.4526 | 0.6586 | 0.1132 | -0.0854 | 6 |
| 4 | 1994-06-15 | 2004-02-10 | 2004-03-11 | 2005-02-25 | 0.5147 | 1.4645 | 0.2093 | -0.0854 | 5 |
| 5 | 1994-12-08 | 2004-08-04 | 2004-09-03 | 2005-08-22 | 0.5069 | 1.5504 | 0.2009 | -0.0872 | 6 |
| 6 | 1995-06-02 | 2005-01-27 | 2005-02-28 | 2006-02-14 | 0.4782 | 0.5675 | 0.0914 | -0.0872 | 8 |
| 7 | 1995-11-27 | 2005-07-22 | 2005-08-23 | 2006-08-09 | 0.4500 | 0.5778 | 0.1058 | -0.1342 | 9 |
| 8 | 1996-05-21 | 2006-01-16 | 2006-02-15 | 2007-02-01 | 0.4267 | 1.1042 | 0.1680 | -0.1342 | 8 |
| 9 | 1996-11-13 | 2006-07-11 | 2006-08-10 | 2007-07-27 | 0.3981 | 0.7193 | 0.1090 | -0.0767 | 7 |
| 10 | 1997-05-08 | 2007-01-03 | 2007-02-02 | 2008-01-21 | 0.3841 | -0.1913 | -0.0151 | -0.1135 | 7 |
| 11 | 1997-10-31 | 2007-06-28 | 2007-07-30 | 2008-07-15 | 0.3626 | 0.2179 | 0.0608 | -0.1155 | 9 |
| 12 | 1998-04-27 | 2007-12-21 | 2008-01-22 | 2009-01-07 | 0.2595 | -0.7870 | -0.2183 | -0.4097 | 9 |
| 13 | 1998-10-20 | 2008-06-16 | 2008-07-16 | 2009-07-02 | 0.3045 | -0.8648 | -0.2579 | -0.3842 | 6 |
| 14 | 1999-04-14 | 2008-12-09 | 2009-01-08 | 2009-12-25 | -0.0708 | 1.3027 | 0.2592 | -0.1776 | 4 |
| 15 | 1999-10-07 | 2009-06-03 | 2009-07-03 | 2010-06-21 | -0.0198 | 1.1833 | 0.2502 | -0.1516 | 4 |
| 16 | 2000-03-31 | 2009-11-26 | 2009-12-28 | 2010-12-14 | 0.0288 | 0.3351 | 0.0899 | -0.1725 | 6 |
| 17 | 2000-09-25 | 2010-05-21 | 2010-06-22 | 2011-06-08 | 0.0275 | 0.9244 | 0.1612 | -0.0759 | 9 |
| 18 | 2001-03-20 | 2010-11-15 | 2010-12-15 | 2011-12-01 | 0.1830 | -0.1041 | -0.0032 | -0.2188 | 9 |
| 19 | 2001-09-12 | 2011-05-10 | 2011-06-09 | 2012-05-25 | 0.2890 | -0.1737 | -0.0169 | -0.2099 | 7 |
| 20 | 2002-03-07 | 2011-11-02 | 2011-12-02 | 2012-11-19 | 0.1764 | 0.6277 | 0.0791 | -0.0700 | 5 |
| 21 | 2002-08-30 | 2012-04-26 | 2012-05-28 | 2013-05-14 | 0.3277 | 2.0304 | 0.2360 | -0.0700 | 7 |
| 22 | 2003-02-24 | 2012-10-19 | 2012-11-20 | 2013-11-06 | 0.3970 | 2.2294 | 0.2803 | -0.0723 | 8 |
| 23 | 2003-08-19 | 2013-04-15 | 2013-05-15 | 2014-05-01 | 0.3517 | 0.9270 | 0.1344 | -0.0723 | 6 |
| 24 | 2004-02-11 | 2013-10-08 | 2013-11-07 | 2014-10-24 | 0.2991 | 0.5129 | 0.0809 | -0.0874 | 5 |
| 25 | 2004-08-05 | 2014-04-02 | 2014-05-02 | 2015-04-20 | 0.4042 | 0.6652 | 0.0932 | -0.0874 | 5 |
| 26 | 2005-01-28 | 2014-09-25 | 2014-10-27 | 2015-10-13 | 0.3352 | 0.0733 | 0.0293 | -0.1009 | 6 |
| 27 | 2005-07-25 | 2015-03-20 | 2015-04-21 | 2016-04-06 | 0.3302 | -0.2006 | -0.0087 | -0.1253 | 6 |
| 28 | 2006-01-17 | 2015-09-14 | 2015-10-14 | 2016-09-29 | 0.2408 | 0.4979 | 0.0779 | -0.1179 | 6 |
| 29 | 2006-07-12 | 2016-03-08 | 2016-04-07 | 2017-03-24 | 0.2245 | 0.7694 | 0.0839 | -0.0579 | 7 |
| 30 | 2007-01-04 | 2016-08-31 | 2016-09-30 | 2017-09-18 | 0.2325 | 1.1067 | 0.1127 | -0.0407 | 5 |
| 31 | 2007-06-29 | 2017-02-23 | 2017-03-27 | 2018-03-13 | 0.2304 | 1.5857 | 0.1975 | -0.1024 | 3 |
| 32 | 2007-12-24 | 2017-08-18 | 2017-09-19 | 2018-09-05 | 0.2180 | 0.8558 | 0.1329 | -0.1024 | 6 |
| 33 | 2008-06-17 | 2018-02-12 | 2018-03-14 | 2019-02-28 | 0.2734 | -0.4574 | -0.0539 | -0.2103 | 8 |
| 34 | 2008-12-10 | 2018-08-07 | 2018-09-06 | 2019-08-23 | 0.6405 | -0.1520 | -0.0027 | -0.2103 | 7 |
| 35 | 2009-06-04 | 2019-01-30 | 2019-03-01 | 2020-02-17 | 0.5283 | 2.4821 | 0.2332 | -0.0435 | 6 |
| 36 | 2009-11-27 | 2019-07-25 | 2019-08-26 | 2020-08-11 | 0.4672 | 0.1462 | 0.0664 | -0.3571 | 6 |
| 37 | 2010-05-24 | 2020-01-17 | 2020-02-18 | 2021-02-03 | 0.5924 | 0.0699 | 0.0429 | -0.3571 | 5 |
| 38 | 2010-11-16 | 2020-07-13 | 2020-08-12 | 2021-07-29 | 0.3820 | 1.3866 | 0.2121 | -0.0735 | 5 |
| 39 | 2011-05-11 | 2021-01-05 | 2021-02-04 | 2022-01-21 | 0.3862 | 0.4699 | 0.0874 | -0.0702 | 7 |
| 40 | 2011-11-03 | 2021-06-30 | 2021-07-30 | 2022-07-18 | 0.5497 | -0.3923 | -0.0465 | -0.1377 | 8 |
| 41 | 2012-04-27 | 2021-12-23 | 2022-01-24 | 2023-01-10 | 0.5343 | -0.0628 | 0.0083 | -0.1788 | 8 |
| 42 | 2012-10-22 | 2022-06-17 | 2022-07-19 | 2023-07-05 | 0.4228 | 0.2455 | 0.0574 | -0.1361 | 8 |
| 43 | 2013-04-16 | 2022-12-12 | 2023-01-11 | 2023-12-28 | 0.4024 | 0.1702 | 0.0391 | -0.1005 | 7 |
| 44 | 2013-10-09 | 2023-06-06 | 2023-07-06 | 2024-06-21 | 0.3371 | 0.9622 | 0.1257 | -0.1005 | 7 |
| 45 | 2014-04-03 | 2023-11-29 | 2023-12-29 | 2024-12-16 | 0.2724 | 1.4268 | 0.1873 | -0.0800 | 7 |
| 46 | 2014-09-26 | 2024-05-23 | 2024-06-24 | 2025-06-10 | 0.3208 | 0.5892 | 0.1189 | -0.1567 | 6 |
| 47 | 2015-03-23 | 2024-11-15 | 2024-12-17 | 2025-12-03 | 0.3288 | 0.7617 | 0.1420 | -0.1567 | 6 |
| 48 | 2015-09-15 | 2025-05-12 | 2025-06-11 | 2026-05-28 | 0.3784 | 1.7641 | 0.2342 | -0.0980 | 6 |

### Aggregate Walk-Forward Statistics

| Metric | Value |
|--------|-------|
| Folds | 48 |
| Mean OOS Sharpe | 0.6868 |
| Std OOS Sharpe | 0.7822 |
| Median OOS Sharpe | 0.6432 |
| Min / Max OOS Sharpe | -0.8648 / 2.4821 |
| % Positive Sharpe Folds | 79.2% |
| Mean Test Ann. Return | 10.18% |
| Mean Test Max DD | -13.51% |
| Mean Test Trades | 6.5 |
| Total Pooled OOS Trades | 313 |

---

## 3. Robustness Grid (18 Pre-Specified Configurations, Test Period)

All 18 pre-specified combinations evaluated on the identical test period
(2018-01-01 to 2026-10-09) with the identical execution convention.
The grid is diagnostic only: the baseline is pre-specified and no
configuration is selected on these results. (The pre-registration labels
the grid "27"; the pre-specified values yield 18 unique
combinations — see Configuration above.)

### Heatmap — Test Sharpe by Configuration

| Lookback | skip=21, tf=0.3 | skip=21, tf=0.5 | skip=21, tf=0.7 | skip=42, tf=0.3 | skip=42, tf=0.5 | skip=42, tf=0.7 |
|----------|--------|--------|--------|--------|--------|--------|
| **189** | 0.4644 | 0.5040 | 0.5723 | 0.6640 | 0.5311 | 0.5257 |
| **252** | 0.3717 | 0.4101 | 0.4242 | 0.6014 | 0.4944 | 0.4707 |
| **315** | 0.5855 | 0.5237 | 0.4528 | 0.7380 | 0.5434 | 0.4935 |

### Full Grid Results

| Lookback | Skip | Top Fraction | Train Sharpe | Val Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades | Test Turnover | Test Sortino | Rank |
|----------|------|--------------|--------------|------------|------------|----------------|--------------|-------------|---------------|--------------|------|
| 189 | 21 | 0.3 | 0.3929 | 0.4639 | 0.4644 | 0.0991 | -0.2798 | 68 | 4.30 | 0.5914 | 14 |
| 189 | 21 | 0.5 | 0.4211 | 0.5416 | 0.5040 | 0.1003 | -0.2565 | 66 | 2.56 | 0.6442 | 10 |
| 189 | 21 | 0.7 | 0.3568 | 0.5878 | 0.5723 | 0.1110 | -0.2913 | 65 | 1.74 | 0.7144 | 5 |
| 189 | 42 | 0.3 | 0.3883 | 0.4838 | 0.6640 | 0.1321 | -0.2556 | 66 | 4.23 | 0.8583 | 2 |
| 189 | 42 | 0.5 | 0.4119 | 0.5963 | 0.5311 | 0.1063 | -0.2719 | 65 | 2.54 | 0.6711 | 7 |
| 189 | 42 | 0.7 | 0.3786 | 0.6054 | 0.5257 | 0.1045 | -0.2924 | 63 | 1.46 | 0.6581 | 8 |
| 252 | 21 | 0.3 | 0.4316 | 0.4203 | 0.3717 | 0.0864 | -0.3561 | 58 | 4.04 | 0.4514 | 18 |
| 252 | 21 | 0.5 | 0.3884 | 0.5468 | 0.4101 | 0.0907 | -0.3571 | 62 | 2.06 | 0.4922 | 17 |
| 252 | 21 | 0.7 | 0.3753 | 0.5833 | 0.4242 | 0.0913 | -0.3300 | 56 | 1.37 | 0.5175 | 16 |
| 252 | 42 | 0.3 | 0.4140 | 0.4566 | 0.6014 | 0.1183 | -0.2282 | 52 | 3.31 | 0.7727 | 3 |
| 252 | 42 | 0.5 | 0.4142 | 0.5432 | 0.4944 | 0.1020 | -0.2906 | 61 | 2.10 | 0.6139 | 11 |
| 252 | 42 | 0.7 | 0.3576 | 0.5028 | 0.4707 | 0.0970 | -0.2958 | 59 | 1.44 | 0.5846 | 13 |
| 315 | 21 | 0.3 | 0.4173 | 0.3721 | 0.5855 | 0.1176 | -0.2209 | 64 | 3.66 | 0.7622 | 4 |
| 315 | 21 | 0.5 | 0.3815 | 0.5644 | 0.5237 | 0.1063 | -0.2659 | 57 | 1.87 | 0.6627 | 9 |
| 315 | 21 | 0.7 | 0.3482 | 0.5538 | 0.4528 | 0.0937 | -0.2924 | 53 | 1.23 | 0.5648 | 15 |
| 315 | 42 | 0.3 | 0.3083 | 0.4986 | 0.7380 | 0.1449 | -0.2105 | 62 | 3.39 | 0.9690 | 1 |
| 315 | 42 | 0.5 | 0.3351 | 0.6039 | 0.5434 | 0.1104 | -0.2550 | 53 | 1.87 | 0.6949 | 6 |
| 315 | 42 | 0.7 | 0.3517 | 0.6260 | 0.4935 | 0.1012 | -0.2924 | 52 | 1.18 | 0.6140 | 12 |

### Baseline Rank & Plateau Check

- **Baseline (252, 21, 0.5) test Sharpe**: 0.4101
  — rank **17** of 18 by test Sharpe
- **Plateau check** (skip=21, top_fraction=0.5; lookbacks 189/252/315):
  **2 of 3** lookbacks within +/-0.1000
  of the baseline test Sharpe (threshold = max(0.1, 10% x |baseline|), the
  repository plateau convention from `src/evaluation/statistics.py`)
  — **PASS** (gate: >= 2 of 3)

---

## 4. Benchmark Comparison

Both benchmarks evaluated on the identical test period (2018-01-01 to
2026-10-09) and the identical walk-forward folds, with the identical 3 bps
round-trip cost model and 1-day signal lag. The incumbent is evaluated with
its validated overlay-warmup conventions: "slice" (overlay state initializes
at the period start) for the test period — reproducing the Cycle 7 test-period
record — and "full" (overlay state initializes at history_start, then sliced)
for the walk-forward folds — reproducing the Cycle 6 fold record. The 1/N
benchmark is represented as constant 1/18 target weights with a 1-day lag and
the monthly calendar; within the engine's exogenous-weights framework this
implies zero observed turnover and zero cost drag (a mild upward bias in the
benchmark's net return, noted as a limitation).

### Test-Period Comparison

| Benchmark | Ann. Return | Sharpe | Max DD | Excess Return (ann.) | Excess Sharpe (IR) | Sharpe Diff. | Correlation | Relative Max DD |
|-----------|-------------|--------|--------|----------------------|--------------------|--------------|-------------|-----------------|
| 1/N Equal-Weight (18 ETFs) | 0.0918 | 0.4617 | -0.3177 | 0.0006 | 0.0131 | -0.0515 | 0.960 | -0.1053 |
| Incumbent TSMOM (tsmomentum_spytrend_001) | 0.1446 | 1.4178 | -0.0779 | -0.0464 | -0.3242 | -1.0076 | 0.562 | -0.4557 |

Excess return/Sharpe are computed on the daily CS-minus-benchmark series
(excess Sharpe = annualized excess return / annualized excess volatility,
i.e. an information ratio). Relative max DD is the max drawdown of the
cumulative excess return.

### Walk-Forward Comparison (identical folds)

| Benchmark | Folds | Mean OOS Sharpe | Std | Median | % Positive | Pooled Trades |
|-----------|-------|-----------------|-----|--------|------------|---------------|
| Cross-sectional momentum (baseline) | 48 | 0.6868 | 0.7822 | 0.6432 | 79.2% | 313 |
| 1/N Equal-Weight (18 ETFs) | 48 | 0.7145 | 0.7983 | 0.7088 | 77.1% | 0 |
| Incumbent TSMOM (tsmomentum_spytrend_001) | 48 | 0.9473 | 3.4798 | 1.2933 | 91.7% | 6013 |

---

## 5. Multiple-Testing Control

- **Exact configuration count tracked**: 18 unique pre-specified
  combinations (3 x 2 x 3) evaluated; the pre-registered trial count is
  27 (see Configuration above for the disclosed
  pre-registration mislabel). No configuration selected on test-period
  results; the baseline is pre-specified and the grid is diagnostic
  (plateau + multiple-testing control) only.
- **Deflated Sharpe Ratio** (`src/evaluation/statistics.py:compute_dsr`,
  1000 block-bootstrap samples, seed=42):
  - At the pre-registered N=27 (primary, conservative):
    **DSR = -0.6484** (DSR probability = 0.2584).
    Observed test Sharpe 0.4101 vs deflation threshold
    0.6329 (SE = 0.3435,
    E[max of 27] = 1.8422).
  - At the actual evaluated count N=18 (disclosure):
    DSR = -0.4634 (DSR probability = 0.3215).
  Both are negative: the observed test-period Sharpe does not survive
  multiple-testing deflation at either trial count.
- **Probabilistic Sharpe Ratio** (PSR vs SR=0): 0.8837
  (empirical 0.9170); PSR vs the 0.9 gate:
  0.0769.
- **Block-bootstrap Sharpe 95% CI**: [-0.1638, 1.1476].
- **PBO / CSCV** (`src/evaluation/statistics.py:compute_pbo` over the
  18-config grid, train=1993-2009 vs test=2018-2026):
  PBO not computable — degenerate: all 18 evaluated configs have positive test-period Sharpe, so the top-k OOS-below-threshold rate is 0 for every k and the logit-normal PBO model has no variation. Overfitting diagnostics therefore rely on the IS-OOS rank correlation and the mean-IS vs mean-OOS gap reported below; best-IS config OOS Sharpe =
  0.3717;
  IS-OOS Spearman rank correlation = -0.1496;
  mean IS Sharpe = 0.3818 vs mean OOS Sharpe =
  0.5206; 18 of
  18 configs have positive OOS Sharpe.

---

## Promotion-Gate Verdict

Pre-registered promotion gates (ALL must pass to advance to risk-overlay
exploration in Cycle 14):

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| 1. Walk-forward mean OOS Sharpe >= 0.9 | 0.6868 | FAIL |
| 2. Positive fold rate >= 50% | 79.2% | PASS |
| 3. Pooled OOS trades > 100 | 313 | PASS |
| 4. Parameter plateau: >= 2 of 3 lookbacks within 10% | 2/3 | PASS |

**Pre-registered falsification condition**: WF mean OOS Sharpe < 0.9
OR positive-fold rate < 50% —
**MET (hypothesis falsified)**.

### Final Classification

## **Rejected/Failed**

The pre-registered falsification condition is met: the walk-forward
mean OOS Sharpe of 0.6868 is below the 0.9 gate
(79.2% positive folds). Per the pre-registered decision
discipline, `csmomentum_001` (long-only cross-sectional momentum, broad
18-ETF universe, monthly rebalance) is **rejected/failed** and archived.

Observed evidence:
- Test period (2018-2026) net Sharpe 0.4101, max DD
  -35.71%, 62 trades,
  2.06x annualized turnover.
- Walk-forward mean OOS Sharpe 0.6868 over
  48 folds; 313 pooled OOS trades.
- Baseline rank 17 of 18 on the test period; plateau check
  2/3 (passes).
- Deflated Sharpe Ratio -0.6484 (N=27 pre-registered trials;
  -0.4634 at the actual evaluated N=18) — the observed
  Sharpe does not survive multiple-testing deflation at either count.
- Net of 3 bps costs the strategy does not clear the promotion gate on any
  pre-registered evaluation path; no configuration was selected on test
  results, so this is not a tuning artifact.

The structural interpretation: in this 18-ETF universe, the cross-sectional
rank signal's gross edge does not translate into a net-of-cost,
walk-forward-valid edge at the pre-registered (252, 21, 0.5) configuration.
The result is consistent with the known competition/maturation of
cross-sectional momentum in liquid US ETFs, and with the repository's own
parameter-peak caveat (Cycle 3).

---

## Decision & Next Steps

**Label**: Rejected/Failed

**Cycle 14 task**: see `NEXT_AGENT_TASK.md`.
Per the pre-registered plan, the next cycle moves to the next candidate on
the Cycle 11 shortlist: **C4 Sector rotation** (cross-sectional momentum
across the 9 GICS sector ETFs) — hypothesis pre-registration with the same
multiple-testing discipline.

---

## Reproducibility

### Reproduction Commands

```bash
# Full Cycle 13 evaluation (regenerates all artifacts and this report)
python3 research/run_cycle13.py

# Verify frozen pre-registration parses
python3 -c "import yaml; yaml.safe_load(open('config/csmomentum_candidate_001.yaml'))"
```

### Code Revision

`a5d5971`

### Configuration

- Frozen config: `config/csmomentum_candidate_001.yaml` (SHA-256[:12] = `296a619f7942`)
- Baseline: lookback=252, skip=21, top_fraction=0.5
- Grid: 18 unique configs (pre-registered trial count 27;
  see disclosed pre-registration mislabel above)
- Walk-forward: train=10y, test=12m, step=6m,
  purge=21d, embargo=21d
- Bootstrap: 1000 samples, block=22d, seed=42
- Costs: 1.0 bps commission + 2.0 bps slippage =
  3.0 bps round-trip; risk-free rate 2.0%

### Determinism

The backtest, walk-forward, grid, and benchmark computations are fully
deterministic (no RNG). The block-bootstrap statistics (DSR/PSR/CIs) use
seed=42 for reproducibility.

---

## Artifacts Referenced

| Artifact | Path |
|----------|------|
| Pre-registered hypothesis | `research/hypotheses/csmomentum_001.md` |
| Frozen configuration | `config/csmomentum_candidate_001.yaml` |
| Daily simulation series | `data/processed/simulation_csmomentum_001.parquet` |
| Trade log | `data/processed/trades_csmomentum_001.parquet` |
| Point-in-time weights | `data/processed/weights_csmomentum_001.parquet` |
| Cycle 6 walk-forward design | `research/experiments/tsmomentum_regime_filter_wf_001.md` |
| Cycle 11 shortlist (C3 = 29/35) | `research/reports/opportunity_shortlist.md` |

---

*Report generated: 2026-10-12 by `research/run_cycle13.py` (Cycle 13)*
*Code revision: a5d5971*
