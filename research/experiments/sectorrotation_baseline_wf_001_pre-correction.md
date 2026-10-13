# Experiment: Baseline Backtest & Walk-Forward — Sector Rotation (sectorrotation_baseline_wf_001)

## Hypothesis Reference

`research/hypotheses/sectorrotation_001.md` (Cycle 12 pre-registration, v001).
Candidate C4 from the Cycle 11 Opportunity Shortlist (28/35 — Exploratory
signal): long-only cross-sectional momentum over the 9 GICS sector ETFs.

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
  `data/raw/` (9 sector ETF caches plus 7 incumbent-benchmark ETF caches). A cache preflight runs before the shared fetcher; missing or invalid caches fail before network access.
- **Date Range**: 1998-12-22 to 2026-10-09 (6,991 aligned trading days)
- **Frequency**: Daily (end-of-day OHLCV)
- **Universe**: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY
- **Price Field**: Close (EOD), forward-filled onto the union trading calendar
- **Point-in-Time Treatment**: Momentum at date t uses only prices through
  t-skip-lookback; weights shifted 1 day (signal on T-1 close, positions
  effective T); monthly month-end rebalance calendar carries weights forward
  intra-month (no intra-month trading); walk-forward uses 21-day purge and
  21-day embargo between train and test.
- **Missing-Data Handling**: The frozen C4 universe requires all 9 sector ETFs to share the 1998-12-22 to 2026-10-08 window. The runner validates 6,991 aligned observations, full Close completeness, and unique dates before computing any result.
- **Content hash (aligned Close frame)**: 5e2d48e6579a53cd

| Symbol | Rows | Start | End | Close Complete (aligned) |
|--------|------|-------|-----|--------------------------|
| XLB | 6,991 | 1998-12-22 | 2026-10-08 | 100.0% |
| XLE | 6,991 | 1998-12-22 | 2026-10-08 | 100.0% |
| XLF | 6,991 | 1998-12-22 | 2026-10-08 | 100.0% |
| XLI | 6,991 | 1998-12-22 | 2026-10-08 | 100.0% |
| XLK | 6,991 | 1998-12-22 | 2026-10-08 | 100.0% |
| XLP | 6,991 | 1998-12-22 | 2026-10-08 | 100.0% |
| XLU | 6,991 | 1998-12-22 | 2026-10-08 | 100.0% |
| XLV | 6,991 | 1998-12-22 | 2026-10-08 | 100.0% |
| XLY | 6,991 | 1998-12-22 | 2026-10-08 | 100.0% |

---

## Configuration

**Baseline (pre-registered, frozen in `config/sectorrotation_candidate_001.yaml`)**:

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

**Pre-registered configuration count**: 3 lookbacks x 2 skips x 3 top fractions = **18 unique combinations**. The corrected runner rejects execution unless both the grid and frozen trial count equal 18. No configurations are added post hoc; the pre-registered and actual trial counts both equal 18.

**Config file SHA-256 (first 12 hex)**: `cd31734e1743`

---

## Train/Validation/Test Splits & Walk-Forward Design

| Split | Period | Purpose |
|-------|--------|---------|
| Train | 1998-12-22 to 2009-12-31 | Parameter selection (NOT used — baseline is pre-specified) |
| Validation | 2010-01-01 to 2017-12-31 | Robustness screening (diagnostic only) |
| Test | 2018-01-01 to 2026-10-09 | Final holdout, promotion-gate decision |

**Walk-Forward Design (matches Cycle 6 `tsmomentum_regime_filter_wf_001.md` exactly)**:

- Rolling window: 10-year train, 12-month test, 6-month step
- Purge: 21 days between train end and test start
- Embargo: 21 days after test period end
- Parameters: FIXED across all folds (no per-fold re-optimization)
- Folds: 36

---

## 1. Baseline Backtest (Test Period 2018-01-01 to 2026-10-09)

| Period | Total Return | Ann. Return | Ann. Vol | Sharpe | Sortino | Max DD | Ann. Turnover | Trades | Profit Factor | Avg Exposure |
|--------|--------------|-------------|----------|--------|---------|--------|---------------|--------|---------------|--------------|
| Test (2018-2026) | 1.3929 | 0.1049 | 0.1814 | 0.4679 | 0.5719 | -0.3525 | 2.24 | 39 | 1.13 | 1.0000 |
| Validation (2010-2017) | 1.2048 | 0.1040 | 0.1508 | 0.5574 | 0.7074 | -0.2275 | 2.10 | 37 | 1.14 | 1.0000 |
| Train (1998-2009) | 0.1287 | 0.0111 | 0.1885 | -0.0474 | -0.0608 | -0.4905 | 2.60 | 61 | 1.03 | 0.8998 |

**Tail metrics (test period, daily net returns)**:

| Metric | Value |
|--------|-------|
| 95% VaR (daily) | 0.0169 (1.69%) |
| 95% CVaR (daily) | 0.0271 (2.71%) |
| Worst day | -0.1166 (-11.66%) |
| Trade count (test) | 39 |

**Artifacts**:

| Artifact | Path | Rows |
|----------|------|------|
| Daily simulation series | `data/processed/simulation_sectorrotation_001.parquet` | 6,991 |
| Trade log | `data/processed/trades_sectorrotation_001.parquet` | 325 |
| Point-in-time weights | `data/processed/weights_sectorrotation_001.parquet` | 6,991 |

---

## 2. Walk-Forward Evaluation (36 Folds, Fixed Parameters)

### Walk-Forward Design

10-year train / 1-year test / 6-month step, 21-day purge, 21-day embargo,
fixed pre-registered parameters (252, 21, 0.5), monthly
rebalance, 1-day lag, 3 bps round-trip costs. No per-fold re-optimization.

### Per-Fold Results

| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |
|------|-------------|-----------|------------|----------|--------------|------------|----------------|--------------|-------------|
| 1 | 1998-12-22 | 2008-08-18 | 2008-09-17 | 2009-09-03 | 0.0392 | -0.4921 | -0.1686 | -0.3976 | 3 |
| 2 | 1999-06-16 | 2009-02-10 | 2009-03-12 | 2010-02-26 | -0.1675 | 2.6418 | 0.4832 | -0.0861 | 3 |
| 3 | 1999-12-09 | 2009-08-05 | 2009-09-04 | 2010-08-23 | -0.0956 | 0.2331 | 0.0665 | -0.1818 | 4 |
| 4 | 2000-06-02 | 2010-01-28 | 2010-03-01 | 2011-02-15 | -0.0829 | 0.9759 | 0.2088 | -0.1818 | 7 |
| 5 | 2000-11-27 | 2010-07-23 | 2010-08-24 | 2011-08-10 | -0.0438 | 0.0287 | 0.0253 | -0.2080 | 8 |
| 6 | 2001-05-22 | 2011-01-17 | 2011-02-16 | 2012-02-02 | 0.0188 | -0.3435 | -0.0618 | -0.2275 | 6 |
| 7 | 2001-11-14 | 2011-07-12 | 2011-08-11 | 2012-07-27 | 0.1086 | 1.1940 | 0.2497 | -0.1150 | 4 |
| 8 | 2002-05-09 | 2012-01-04 | 2012-02-03 | 2013-01-21 | 0.0409 | 1.1627 | 0.1471 | -0.0691 | 4 |
| 9 | 2002-11-01 | 2012-06-28 | 2012-07-30 | 2013-07-16 | 0.1653 | 1.4807 | 0.1937 | -0.0691 | 5 |
| 10 | 2003-04-28 | 2012-12-21 | 2013-01-22 | 2014-01-08 | 0.1854 | 2.1239 | 0.2659 | -0.0634 | 5 |
| 11 | 2003-10-21 | 2013-06-17 | 2013-07-17 | 2014-07-03 | 0.1816 | 1.4992 | 0.1912 | -0.0602 | 6 |
| 12 | 2004-04-14 | 2013-12-10 | 2014-01-09 | 2014-12-26 | 0.2004 | 0.7333 | 0.1111 | -0.0824 | 5 |
| 13 | 2004-10-07 | 2014-06-04 | 2014-07-04 | 2015-06-22 | 0.2088 | 0.3165 | 0.0591 | -0.0824 | 4 |
| 14 | 2005-04-01 | 2014-11-27 | 2014-12-29 | 2015-12-15 | 0.1910 | -0.1188 | 0.0019 | -0.1138 | 2 |
| 15 | 2005-09-26 | 2015-05-22 | 2015-06-23 | 2016-06-08 | 0.1808 | -0.0850 | 0.0059 | -0.1346 | 2 |
| 16 | 2006-03-21 | 2015-11-16 | 2015-12-16 | 2016-12-01 | 0.1571 | 0.1004 | 0.0331 | -0.1252 | 5 |
| 17 | 2006-09-13 | 2016-05-10 | 2016-06-09 | 2017-05-26 | 0.1736 | 0.6679 | 0.0877 | -0.0504 | 4 |
| 18 | 2007-03-08 | 2016-11-02 | 2016-12-02 | 2017-11-20 | 0.1313 | 1.5967 | 0.1554 | -0.0471 | 3 |
| 19 | 2007-08-31 | 2017-04-27 | 2017-05-29 | 2018-05-15 | 0.1765 | 0.8846 | 0.1370 | -0.1079 | 4 |
| 20 | 2008-02-25 | 2017-10-20 | 2017-11-21 | 2018-11-07 | 0.2275 | 0.2675 | 0.0618 | -0.1225 | 4 |
| 21 | 2008-08-19 | 2018-04-16 | 2018-05-16 | 2019-05-02 | 0.2670 | 0.2199 | 0.0533 | -0.2002 | 5 |
| 22 | 2009-02-11 | 2018-10-09 | 2018-11-08 | 2019-10-25 | 0.6420 | 0.6176 | 0.1084 | -0.1470 | 3 |
| 23 | 2009-08-06 | 2019-04-03 | 2019-05-03 | 2020-04-20 | 0.5490 | -0.1504 | -0.0286 | -0.3525 | 4 |
| 24 | 2010-01-29 | 2019-09-26 | 2019-10-28 | 2020-10-13 | 0.5378 | 0.3228 | 0.1293 | -0.3525 | 5 |
| 25 | 2010-07-26 | 2020-03-20 | 2020-04-21 | 2021-04-07 | 0.2870 | 2.1737 | 0.3851 | -0.0826 | 2 |
| 26 | 2011-01-18 | 2020-09-14 | 2020-10-14 | 2021-09-30 | 0.4201 | 1.1452 | 0.1872 | -0.0635 | 4 |
| 27 | 2011-07-13 | 2021-03-09 | 2021-04-08 | 2022-03-25 | 0.4623 | 1.0663 | 0.1938 | -0.0799 | 6 |
| 28 | 2012-01-05 | 2021-09-01 | 2021-10-01 | 2022-09-19 | 0.6271 | 0.1892 | 0.0562 | -0.1384 | 4 |
| 29 | 2012-06-29 | 2022-02-24 | 2022-03-28 | 2023-03-14 | 0.5856 | -0.3927 | -0.0552 | -0.1471 | 5 |
| 30 | 2012-12-24 | 2022-08-19 | 2022-09-20 | 2023-09-06 | 0.5915 | 0.2534 | 0.0591 | -0.1036 | 8 |
| 31 | 2013-06-18 | 2023-02-13 | 2023-03-15 | 2024-02-29 | 0.4925 | 1.1317 | 0.1605 | -0.1033 | 6 |
| 32 | 2013-12-11 | 2023-08-08 | 2023-09-07 | 2024-08-23 | 0.4092 | 1.1263 | 0.1644 | -0.0958 | 4 |
| 33 | 2014-06-05 | 2024-01-31 | 2024-03-01 | 2025-02-17 | 0.4003 | 0.8273 | 0.1261 | -0.0847 | 4 |
| 34 | 2014-11-28 | 2024-07-25 | 2024-08-26 | 2025-08-12 | 0.4120 | 0.4809 | 0.1007 | -0.1639 | 4 |
| 35 | 2015-05-25 | 2025-01-17 | 2025-02-18 | 2026-02-04 | 0.4549 | 0.4038 | 0.0852 | -0.1639 | 3 |
| 36 | 2015-11-17 | 2025-07-14 | 2025-08-13 | 2026-07-30 | 0.4719 | 0.7164 | 0.1028 | -0.0865 | 3 |

### Aggregate Walk-Forward Statistics

| Metric | Value |
|--------|-------|
| Folds | 36 |
| Mean OOS Sharpe | 0.6944 |
| Std OOS Sharpe | 0.7437 |
| Median OOS Sharpe | 0.6428 |
| Min / Max OOS Sharpe | -0.4921 / 2.6418 |
| % Positive Sharpe Folds | 83.3% |
| Mean Test Ann. Return | 11.34% |
| Mean Test Max DD | -13.59% |
| Mean Test Trades | 4.4 |
| Total Pooled OOS Trades | 158 |

---

## 3. Robustness Grid (18 Pre-Specified Configurations, Test Period)

All 18 pre-specified combinations evaluated on the identical test period
(2018-01-01 to 2026-10-09) with the identical execution convention.
The grid is diagnostic only: the baseline is pre-specified and no
configuration is selected on these results. Its 18 combinations are frozen
in the hypothesis and config and checked before execution.

### Heatmap — Test Sharpe by Configuration

| Lookback | skip=21, tf=0.3 | skip=21, tf=0.5 | skip=21, tf=0.7 | skip=42, tf=0.3 | skip=42, tf=0.5 | skip=42, tf=0.7 |
|----------|--------|--------|--------|--------|--------|--------|
| **189** | 0.2478 | 0.4182 | 0.4156 | 0.5494 | 0.4207 | 0.4024 |
| **252** | 0.4377 | 0.4679 | 0.3550 | 0.4626 | 0.3614 | 0.3770 |
| **315** | 0.5091 | 0.4509 | 0.4229 | 0.6502 | 0.5204 | 0.4495 |

### Full Grid Results

| Lookback | Skip | Top Fraction | Train Sharpe | Val Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades | Test Turnover | Test Sortino | Rank |
|----------|------|--------------|--------------|------------|------------|----------------|--------------|-------------|---------------|--------------|------|
| 189 | 21 | 0.3 | -0.1045 | 0.5443 | 0.2478 | 0.0686 | -0.3339 | 48 | 4.42 | 0.3136 | 18 |
| 189 | 21 | 0.5 | 0.0117 | 0.5994 | 0.4182 | 0.0957 | -0.3284 | 51 | 2.97 | 0.5260 | 12 |
| 189 | 21 | 0.7 | -0.0101 | 0.6239 | 0.4156 | 0.0933 | -0.3348 | 41 | 1.50 | 0.5103 | 13 |
| 189 | 42 | 0.3 | -0.0261 | 0.5235 | 0.5494 | 0.1295 | -0.3339 | 50 | 4.50 | 0.7005 | 2 |
| 189 | 42 | 0.5 | 0.0439 | 0.6124 | 0.4207 | 0.0976 | -0.3388 | 42 | 2.70 | 0.5231 | 11 |
| 189 | 42 | 0.7 | 0.0105 | 0.6313 | 0.4024 | 0.0918 | -0.3549 | 34 | 1.18 | 0.4934 | 14 |
| 252 | 21 | 0.3 | -0.0332 | 0.5219 | 0.4377 | 0.1055 | -0.3630 | 46 | 4.65 | 0.5398 | 9 |
| 252 | 21 | 0.5 | -0.0474 | 0.5574 | 0.4679 | 0.1049 | -0.3525 | 39 | 2.24 | 0.5719 | 5 |
| 252 | 21 | 0.7 | -0.0049 | 0.5763 | 0.3550 | 0.0838 | -0.3549 | 40 | 1.44 | 0.4321 | 17 |
| 252 | 42 | 0.3 | 0.0451 | 0.4870 | 0.4626 | 0.1108 | -0.3591 | 38 | 3.35 | 0.5707 | 6 |
| 252 | 42 | 0.5 | 0.0236 | 0.5504 | 0.3614 | 0.0874 | -0.3731 | 49 | 2.52 | 0.4385 | 16 |
| 252 | 42 | 0.7 | 0.0346 | 0.5333 | 0.3770 | 0.0877 | -0.3549 | 43 | 1.50 | 0.4590 | 15 |
| 315 | 21 | 0.3 | -0.0926 | 0.4767 | 0.5091 | 0.1193 | -0.3068 | 37 | 3.13 | 0.6520 | 4 |
| 315 | 21 | 0.5 | -0.0444 | 0.5735 | 0.4509 | 0.1030 | -0.3284 | 42 | 2.24 | 0.5611 | 7 |
| 315 | 21 | 0.7 | 0.0032 | 0.6125 | 0.4229 | 0.0948 | -0.3348 | 38 | 1.37 | 0.5179 | 10 |
| 315 | 42 | 0.3 | -0.0723 | 0.6307 | 0.6502 | 0.1499 | -0.3068 | 43 | 3.74 | 0.8343 | 1 |
| 315 | 42 | 0.5 | -0.0366 | 0.5961 | 0.5204 | 0.1162 | -0.3077 | 44 | 2.33 | 0.6549 | 3 |
| 315 | 42 | 0.7 | 0.0286 | 0.5680 | 0.4495 | 0.1011 | -0.3433 | 40 | 1.40 | 0.5487 | 8 |

### Baseline Rank & Plateau Check

- **Baseline (252, 21, 0.5) test Sharpe**: 0.4679
  — rank **5** of 18 by test Sharpe
- **Plateau check** (skip=21, top_fraction=0.5; lookbacks 189/252/315):
  **3 of 3** lookbacks within +/-0.1000
  of the baseline test Sharpe (threshold = max(0.1, 10% x |baseline|), the
  repository plateau convention from `src/evaluation/statistics.py`)
  — **PASS** (gate: >= 2 of 3)

---

## 4. Benchmark Comparison

Both benchmarks are evaluated on the identical test period (2018-01-01 to
2026-10-09) and the identical walk-forward folds with the same 3 bps cost model
and one-day signal lag. The incumbent TSMOM benchmark uses its own cached CORE7
input universe; the sector candidate uses the nine frozen GICS sector ETFs.
The 1/N benchmark is represented as constant 1/9 target weights with a one-day
lag and monthly schedule. Under the engine's exogenous-weight framework this
implies no observed turnover drag, a known upward bias documented as a limitation.

### Test-Period Comparison

| Benchmark | Ann. Return | Sharpe | Max DD | Excess Return (ann.) | Excess Sharpe (IR) | Sharpe Diff. | Correlation | Relative Max DD |
|-----------|-------------|--------|--------|----------------------|--------------------|--------------|-------------|-----------------|
| 1/N Equal-Weight (9 sector ETFs) | 0.0996 | 0.4430 | -0.3743 | 0.0036 | 0.0665 | 0.0250 | 0.954 | -0.1357 |
| Incumbent TSMOM (tsmomentum_spytrend_001) | 0.1442 | 1.4122 | -0.0779 | -0.0341 | -0.2170 | -0.9442 | 0.502 | -0.4286 |

Excess return/Sharpe are computed on the daily CS-minus-benchmark series
(excess Sharpe = annualized excess return / annualized excess volatility,
i.e. an information ratio). Relative max DD is the max drawdown of the
cumulative excess return.

### Walk-Forward Comparison (identical folds)

| Benchmark | Folds | Mean OOS Sharpe | Std | Median | % Positive | Pooled Trades |
|-----------|-------|-----------------|-----|--------|------------|---------------|
| Sector Rotation C4 (baseline) | 36 | 0.6944 | 0.7437 | 0.6428 | 83.3% | 158 |
| 1/N Equal-Weight (9 sector ETFs) | 36 | 0.7817 | 0.8070 | 0.6794 | 80.6% | 0 |
| Incumbent TSMOM (tsmomentum_spytrend_001) | 36 | 1.2799 | 0.8401 | 1.3742 | 97.2% | 4249 |

---

## 5. Multiple-Testing Control

- **Exact configuration count tracked**: 18 unique pre-specified
  combinations (3 x 2 x 3) evaluated; both the frozen and evaluated trial counts are 18. No configuration selected on test-period
  results; the baseline is pre-specified and the grid is diagnostic
  (plateau + multiple-testing control) only.
- **Deflated Sharpe Ratio** (`src/evaluation/statistics.py:compute_dsr`,
  1000 block-bootstrap samples, seed=42):
  - At the pre-registered N=18 (primary, conservative):
    **DSR = -0.2742** (DSR probability = 0.3920).
    Observed test Sharpe 0.4679 vs deflation threshold
    0.5607 (SE = 0.3383,
    E[max of 18] = 1.6572).
  - At the actual evaluated count N=18 (disclosure):
    DSR = -0.2742 (DSR probability = 0.3920).
  Interpret the reported DSR values as computed; the runner does not hard-code their sign or significance.
- **Probabilistic Sharpe Ratio** (PSR vs SR=0): 0.9167
  (empirical 0.9450); PSR vs the 0.9 gate:
  0.1008.
- **Block-bootstrap Sharpe 95% CI**: [-0.1092, 1.2167].
- **PBO / CSCV** (`src/evaluation/statistics.py:compute_pbo` over the
  18-config grid, train=1998-2009 vs test=2018-2026):
  PBO not computable — degenerate: all 18 evaluated configs have positive test-period Sharpe, so the top-k OOS-below-threshold rate is 0 for every k and the logit-normal PBO model has no variation. Overfitting diagnostics therefore rely on the IS-OOS rank correlation and the mean-IS vs mean-OOS gap reported below; best-IS config OOS Sharpe =
  0.4626;
  IS-OOS Spearman rank correlation = -0.3230;
  mean IS Sharpe = -0.0150 vs mean OOS Sharpe =
  0.4399; 18 of
  18 configs have positive OOS Sharpe.

---

## Promotion-Gate Verdict

Pre-registered promotion gates (ALL must pass before further development; this baseline contains no risk overlay):

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| 1. Walk-forward mean OOS Sharpe >= 0.9 | 0.6944 | FAIL |
| 2. Positive fold rate >= 50% | 83.3% | PASS |
| 3. Pooled OOS trades > 100 | 158 | PASS |
| 4. Parameter plateau: >= 2 of 3 lookbacks within 10% | 3/3 | PASS |

**Pre-registered falsification condition**: WF mean OOS Sharpe < 0.9
OR positive-fold rate < 50% —
**MET (hypothesis falsified)**.

### Final Classification

## **Rejected/Failed**

The candidate did not clear the pre-registered promotion/falsification rules.
Per the frozen decision discipline, sectorrotation_001 (long-only cross-sectional
momentum across the 9 GICS sector ETFs, monthly rebalance) is rejected/failed and archived.

Observed evidence:
- Test period (2018-2026) net Sharpe 0.4679, max DD
  -35.25%, 39 trades,
  2.24x annualized turnover.
- Walk-forward mean OOS Sharpe 0.6944 over
  36 folds; 158 pooled OOS trades.
- Baseline rank 5 of 18; plateau
  3/3 (passes).
- DSR is reported at both trial counts above; this narrative does not
  hard-code its sign or significance.

The conclusion is limited to the frozen nine-sector ETF universe, execution
rules, transaction-cost assumptions, and historical window evaluated here.

---

## Decision & Next Steps

**Label**: Rejected/Failed

**Next scheduled task**: the pre-registered C6 calendar-effects evaluation in `NEXT_AGENT_TASK.md`.
Per the pre-registered plan, C4 is archived under its observed
promotion-gate result. The next scheduled task evaluates the already
pre-registered C6 calendar-effects hypothesis; its frozen design is not tuned
in response to this C4 outcome.

---

## Reproducibility

### Reproduction Commands

```bash
# Corrected Cycle 15 C4 evaluation (regenerates C4 artifacts and this report)
python3 research/run_cycle15_c4_corrected.py

# Verify frozen pre-registration parses
python3 -c "import yaml; yaml.safe_load(open('config/sectorrotation_candidate_001.yaml'))"
```

### Code Revision

`c6de353`

### Configuration

- Frozen config: `config/sectorrotation_candidate_001.yaml` (SHA-256[:12] = `cd31734e1743`)
- Baseline: lookback=252, skip=21, top_fraction=0.5
- Grid: 18 unique configs (pre-registered trial count 18;
  see disclosed pre-registered count above)
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
| Pre-registered hypothesis | `research/hypotheses/sectorrotation_001.md` |
| Frozen configuration | `config/sectorrotation_candidate_001.yaml` |
| Daily simulation series | `data/processed/simulation_sectorrotation_001.parquet` |
| Trade log | `data/processed/trades_sectorrotation_001.parquet` |
| Point-in-time weights | `data/processed/weights_sectorrotation_001.parquet` |
| Cycle 6 walk-forward design | `research/experiments/tsmomentum_regime_filter_wf_001.md` |
| Cycle 11 shortlist (C3 = 29/35) | `research/reports/opportunity_shortlist.md` |

---

*Report generated: 2026-10-13 by `research/run_cycle15_c4_corrected.py` (corrected Cycle 15 C4 evaluation)*
*Code revision: c6de353*
