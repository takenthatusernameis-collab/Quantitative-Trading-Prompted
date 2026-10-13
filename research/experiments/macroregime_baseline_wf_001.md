# Experiment: Baseline Backtest & Walk-Forward — Macro Regime Overlay Extension (macroregime_001)

## Hypothesis Reference

`research/hypotheses/macroregime_001.md` (Cycle 19 pre-registration, v001).
Candidate C5 from the Cycle 11 Opportunity Shortlist (24/35 — Exploratory
signal, rank 6 of 10). Parent cycle: Cycle 11 Opportunity Shortlist.

**Mechanism**: The incumbent 226-day TSMOM + combined vol-target (10%) +
drawdown-control (15%) + SPY 200d SMA trend filter is extended with a VIX-level
regime exposure multiplier. Volatility regimes are persistent and VIX spikes
lead equity drawdowns; reducing exposure in high-volatility regimes is a
defensive overlay. C5 is an *overlay-on-overlay* extension — it tests whether the
VIX gate adds value over the already-gated (SPY trend-filtered) incumbent.

**Pre-registered falsification condition** (stated BEFORE any backtest
execution): the hypothesis is rejected if the walk-forward mean OOS Sharpe
< 0.9 OR < 50% of walk-forward folds
have positive test Sharpe.

---

## Data Used

- **Source**: Yahoo Finance via yfinance, cached as daily parquet in
  `data/raw/` (7 ETF files + `^VIX.parquet`). No new data was fetched
  (`fetch_universe(..., force=False)`; cache-only).
- **Date Range**: 2004-11-18 to 2026-10-09 (common-calendar intersection of the 7 ETFs,
  bounded by GLD inception 2004-11-18)
- **Frequency**: Daily (end-of-day OHLCV)
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM (n=7)
- **Regime Driver**: ^VIX (index, INPUT ONLY — never a position, not tradeable)
- **Price Field**: Close (EOD), forward-filled onto the union trading calendar
- **Point-in-Time Treatment**: Momentum at date t uses only prices through
  t-skip-lookback; base momentum weights shifted 1 day (signal on T-1 close,
  positions effective T); monthly month-end rebalance calendar carries weights
  forward intra-month (no intra-month trading); SPY 200d SMA and VIX regime use
  the prior day's close (1-day lag, no look-ahead); walk-forward uses 21-day
  purge and 21-day embargo between train and test.
- **Missing-Data Handling**: Pre-inception cells are NaN (not back-filled) and
  would be excluded from cross-sectional ranking via `na_option="keep"`. All 7
  ETFs are incepted by 2004-11-18, so cross-sectional breadth is constant at 7
  for the full strategy history (no point-in-time breadth growth).
- **Cost Model**: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip per
  unit of weight change, identical across candidate and all benchmarks.

| Symbol | Rows | Start | End | Close NaN | Dup dates |
|--------|------|-------|-----|-----------|-----------|
| Aligned 7-ETF Close frame | 5,507 | 2004-11-18 | 2026-10-09 | 0 | 0 |
| ^VIX Close frame | 5,507 | 2004-11-18 | 2026-10-09 | 0 | 0 |
| Aligned frame hash | 7393bf74d806c40b | | | | |
| Config hash (SHA-256[:12]) | 76a8c320b25b | | | | |

---

## Configuration

**Baseline (pre-specified, frozen in `config/macroregime_candidate_001.yaml`)**:

| Parameter | Value |
|-----------|-------|
| Signal | Time-series momentum (226-day return, 21-day skip, top-50% equal-weight) |
| Lookback | 226 trading days (~11 months) |
| Skip | 21 trading days (~1 month) |
| Top fraction | 0.5 |
| Vol targeting | 10% annualized (63-day trailing realized vol, cap 100%) |
| Drawdown control | Reduce exposure by 50% when cumulative DD exceeds 15% |
| SPY trend filter | 0% exposure when SPY < 200d SMA; 100% otherwise (incumbent) |
| VIX regime gate | 50% exposure when ^VIX > 30; full exposure otherwise |
| Rebalance | Monthly (month-end calendar) |
| Signal lag | 1 day (T-1 close -> T position) |
| VIX lag | 1 day (prior day VIX close, point-in-time) |
| Commission | 1.0 bps |
| Slippage | 2.0 bps |
| Round-trip cost | 3.0 bps per unit of weight change |
| Risk-free rate | 2.0% annualized (flat) |

**Pre-specified Robustness Grid (fixed count for multiple-testing control)**:

`vix_threshold` in {20, 25, 30, 35} x `vix_exposure` in {0.0, 0.5, 1.0} =
**12 unique configurations**. Baseline (threshold=30,
exposure=0.5) is a grid member. The `vix_exposure=1.0`
arm is the **incumbent control** (no VIX gate — isolates the marginal effect of the VIX gate).
No configurations were added post-hoc; no configuration was selected on test-period results.

**Grid arithmetic assertion (pre-registered)**: `len(vix_thresholds) * len(vix_exposures) == 12`.

**Config file SHA-256[:12]**: `76a8c320b25b`

---

## Train/Validation/Test Splits & Walk-Forward Design

| Split | Period | Purpose |
|-------|--------|---------|
| Train | 2004-11-18 to 2009-12-31 | Parameter selection (NOT used — baseline is pre-specified) |
| Validation | 2010-01-01 to 2017-12-31 | Robustness screening (diagnostic only) |
| Test | 2018-01-01 to 2026-10-09 | Final holdout, promotion-gate decision |

**Walk-Forward Design (pre-registered, matches Cycle 6 convention)**:

- Rolling window: 10-year train, 12-month test, 6-month step
- Purge: 21 days between train end and test start
- Embargo: 21 days after test period end
- Parameters: FIXED across all folds (no per-fold re-optimization)
- Folds: 24 (from the 2004-11-18 common-calendar start)
- Fold 1: train 2004-11-18 → 2014-07-16, test 2014-08-15 → 2015-08-03
- Fold 24: train 2015-12-29 → 2025-08-25, test 2025-09-24 → 2026-09-10

**Point-in-time treatment**: momentum signals use only data available at formation (1-day lag);
SPY 200-day SMA and VIX regime use only prior day's close; combined overlay uses only realized
volatility and drawdown history up to the period start. No look-ahead in any split.

---

## 1. Baseline Backtest (Test Period 2018-01-01 to 2026-10-09)

Configuration: lookback=226, skip=21,
top_fraction=0.5, vix_threshold=30,
vix_exposure=0.5.

| Period | Total Return | Ann. Return | Ann. Vol | Sharpe | Sortino | Max DD | Ann. Turnover | Trades | Profit Factor | Avg Exposure |
|--------|--------------|-------------|----------|--------|---------|--------|---------------|--------|---------------|--------------|
| Test (2018-2026) | 0.5571 | 0.0519 | 0.1082 | 0.2950 | 0.3289 | -0.1807 | 3.13 | 58 | 1.11 | 0.6758 |
| Validation (2010-2017) | 0.8130 | 0.0773 | 0.0942 | 0.6085 | 0.7578 | -0.0965 | 2.77 | 45 | 1.17 | 0.7724 |
| Train (2004-2009) | 0.5580 | 0.0906 | 0.0879 | 0.8025 | 0.7939 | -0.1160 | 1.73 | 24 | 1.27 | 0.3726 |

**Tail metrics (test period, daily net returns)**:

| Metric | Value |
|--------|-------|
| 95% VaR (daily) | 0.0111 (1.11%) |
| 95% CVaR (daily) | 0.0174 (1.74%) |
| Worst day | -0.0553 (-5.53%) |

**Artifacts**:

| Artifact | Path | Rows |
|----------|------|------|
| Daily simulation series | `data/processed/simulation_macroregime_001.parquet` | 5,507 |
| Trade log | `data/processed/trades_macroregime_001.parquet` | 528 |
| Point-in-time weights | `data/processed/weights_macroregime_001.parquet` | 5,507 |

---

## 2. Walk-Forward Evaluation (24 Folds, Fixed Parameters)

10-year train / 1-year test / 6-month step, 21-day purge, 21-day embargo,
fixed pre-registered baseline parameters (vix_threshold=30,
vix_exposure=0.5), monthly rebalance, 1-day lag, 3 bps round-trip costs.
No per-fold re-optimization.

### Per-Fold Results

| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |
|------|-------------|-----------|------------|----------|--------------|------------|----------------|--------------|-------------|
| 1 | 2004-11-18 | 2014-07-16 | 2014-08-15 | 2015-08-03 | 0.7076 | 0.6953 | 0.0856 | -0.0641 | 4 |
| 2 | 2005-05-13 | 2015-01-08 | 2015-02-09 | 2016-01-26 | 0.7537 | -0.7906 | -0.0530 | -0.0965 | 5 |
| 3 | 2005-11-07 | 2015-07-03 | 2015-08-04 | 2016-07-20 | 0.7276 | -0.3339 | -0.0051 | -0.0833 | 4 |
| 4 | 2006-05-02 | 2015-12-28 | 2016-01-27 | 2017-01-12 | 0.5236 | 0.3603 | 0.0443 | -0.0805 | 3 |
| 5 | 2006-10-25 | 2016-06-21 | 2016-07-21 | 2017-07-07 | 0.5687 | 0.5256 | 0.0657 | -0.0805 | 4 |
| 6 | 2007-04-19 | 2016-12-14 | 2017-01-13 | 2018-01-01 | 0.4559 | 2.2613 | 0.2155 | -0.0286 | 5 |
| 7 | 2007-10-12 | 2017-06-08 | 2017-07-10 | 2018-06-26 | 0.5495 | 1.1878 | 0.1558 | -0.1045 | 6 |
| 8 | 2008-04-07 | 2017-12-01 | 2018-01-02 | 2018-12-19 | 0.6561 | -0.4340 | -0.0355 | -0.1252 | 6 |
| 9 | 2008-09-30 | 2018-05-28 | 2018-06-27 | 2019-06-13 | 0.6779 | -0.9367 | -0.0664 | -0.1180 | 6 |
| 10 | 2009-03-25 | 2018-11-20 | 2018-12-20 | 2019-12-06 | 0.5736 | 0.4339 | 0.0463 | -0.0521 | 4 |
| 11 | 2009-09-17 | 2019-05-15 | 2019-06-14 | 2020-06-01 | 0.4794 | 0.3096 | 0.0627 | -0.1548 | 4 |
| 12 | 2010-03-12 | 2019-11-07 | 2019-12-09 | 2020-11-24 | 0.4398 | 0.5864 | 0.1105 | -0.1548 | 6 |
| 13 | 2010-09-06 | 2020-05-01 | 2020-06-02 | 2021-05-19 | 0.5132 | 0.5417 | 0.0794 | -0.0724 | 7 |
| 14 | 2011-03-01 | 2020-10-26 | 2020-11-25 | 2021-11-11 | 0.4981 | 0.4644 | 0.0648 | -0.0724 | 7 |
| 15 | 2011-08-24 | 2021-04-20 | 2021-05-20 | 2022-05-06 | 0.5392 | -0.9791 | -0.0895 | -0.1616 | 8 |
| 16 | 2012-02-16 | 2021-10-13 | 2021-11-12 | 2022-10-31 | 0.5080 | -1.7481 | -0.1492 | -0.1766 | 6 |
| 17 | 2012-08-10 | 2022-04-07 | 2022-05-09 | 2023-04-25 | 0.4172 | 0.5654 | 0.0710 | -0.0680 | 4 |
| 18 | 2013-02-04 | 2022-09-30 | 2022-11-01 | 2023-10-18 | 0.2843 | 0.4326 | 0.0684 | -0.0767 | 5 |
| 19 | 2013-07-30 | 2023-03-27 | 2023-04-26 | 2024-04-11 | 0.2487 | 1.0874 | 0.1252 | -0.0767 | 6 |
| 20 | 2014-01-22 | 2023-09-19 | 2023-10-19 | 2024-10-04 | 0.1924 | 2.1567 | 0.2417 | -0.0624 | 8 |
| 21 | 2014-07-17 | 2024-03-13 | 2024-04-12 | 2025-03-31 | 0.2198 | 0.8624 | 0.1125 | -0.0640 | 9 |
| 22 | 2015-01-09 | 2024-09-05 | 2024-10-07 | 2025-09-23 | 0.2496 | 1.0023 | 0.1017 | -0.0640 | 7 |
| 23 | 2015-07-06 | 2025-02-28 | 2025-04-01 | 2026-03-18 | 0.3263 | 1.7727 | 0.1973 | -0.0502 | 5 |
| 24 | 2015-12-29 | 2025-08-25 | 2025-09-24 | 2026-09-10 | 0.3794 | 0.3714 | 0.0633 | -0.0907 | 8 |

### Aggregate Walk-Forward Statistics

| Metric | Value |
|--------|-------|
| Folds | 24 |
| Mean OOS Sharpe | 0.4331 |
| Std OOS Sharpe | 0.9609 |
| Median OOS Sharpe | 0.4950 |
| Min / Max OOS Sharpe | -1.7481 / 2.2613 |
| % Positive Sharpe Folds | 75.0% |
| Mean Test Ann. Return | 6.30% |
| Mean Test Max DD | -9.08% |
| Mean Test Trades | 5.7 |
| Total Pooled OOS Trades | 137 |

---

## 3. Robustness Grid (12 Pre-Specified Configurations, Test Period)

All 12 pre-specified combinations evaluated on the identical test period
(2018-01-01 to 2026-10-09) with the identical execution convention. The grid is diagnostic
only: the baseline is pre-specified and no configuration is selected on these results.

### Heatmap — Test Sharpe by VIX Gate Configuration

| VIX Threshold | expo=0.0 | expo=0.5 | expo=1.0 |
|---------------|--------|--------|--------|
| **20** | 0.1326 | 0.2519 | 0.3371 |
| **25** | 0.1939 | 0.2723 | 0.3371 |
| **30** | 0.2596 | 0.2950 | 0.3371 |
| **35** | 0.3311 | 0.3326 | 0.3371 |

### Full Grid Results

| VIX Threshold | VIX Exposure | Train Sharpe | Val Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades | Test Turnover | Test Sortino | Rank |
|---------------|--------------|--------------|------------|------------|----------------|--------------|-------------|---------------|--------------|------|
| 20 | 0.0 | 0.4307 | 0.3259 | 0.1326 | 0.0337 | -0.2421 | 50 | 3.47 | 0.1277 | 12 |
| 20 | 0.5 | 0.7002 | 0.4689 | 0.2519 | 0.0463 | -0.2124 | 57 | 3.27 | 0.2730 | 10 |
| 20 | 1.0 | 0.8003 | 0.6085 | 0.3371 | 0.0562 | -0.1794 | 58 | 3.11 | 0.3763 | 1 |
| 25 | 0.0 | 0.4129 | 0.5985 | 0.1939 | 0.0409 | -0.2008 | 55 | 3.23 | 0.2102 | 11 |
| 25 | 0.5 | 0.6521 | 0.6010 | 0.2723 | 0.0494 | -0.1938 | 57 | 3.17 | 0.3018 | 8 |
| 25 | 1.0 | 0.8003 | 0.6085 | 0.3371 | 0.0562 | -0.1794 | 58 | 3.11 | 0.3763 | 1 |
| 30 | 0.0 | 0.8031 | 0.6085 | 0.2596 | 0.0481 | -0.1811 | 57 | 3.12 | 0.2888 | 9 |
| 30 | 0.5 | 0.8025 | 0.6085 | 0.2950 | 0.0519 | -0.1807 | 58 | 3.13 | 0.3289 | 7 |
| 30 | 1.0 | 0.8003 | 0.6085 | 0.3371 | 0.0562 | -0.1794 | 58 | 3.11 | 0.3763 | 1 |
| 35 | 0.0 | 0.8003 | 0.6085 | 0.3311 | 0.0558 | -0.1794 | 58 | 3.12 | 0.3699 | 6 |
| 35 | 0.5 | 0.8003 | 0.6085 | 0.3326 | 0.0559 | -0.1794 | 58 | 3.12 | 0.3715 | 5 |
| 35 | 1.0 | 0.8003 | 0.6085 | 0.3371 | 0.0562 | -0.1794 | 58 | 3.11 | 0.3763 | 1 |

### Baseline Rank & VIX-Gate Plateau Check

- **Baseline (threshold=30, exposure=0.5) test Sharpe**: 0.2950 — rank **7 of 12** by test Sharpe
- **Plateau check** (vix_exposure=0.5; all 4 vix_thresholds 20, 25, 30, 35):
  **4 of 4** thresholds within +/-0.1000
  of the baseline test Sharpe (threshold = max(0.1, 10% x |baseline|), the repository
  plateau convention from `src/evaluation/statistics.py`) — **PASS** (gate: >= 2 of 4)

---

## 4. Benchmark Comparison

Both benchmarks evaluated on the identical test period (2018-01-01 to 2026-10-09) and the
identical walk-forward folds, with the identical 3 bps round-trip cost model and 1-day signal lag.

The **incumbent control arm** (tsmomentum_spytrend_001: 226d TSMOM + vol-target 10% + DD
control 15% + SPY 200d SMA filter, NO VIX gate) is evaluated with its validated overlay-warmup
conventions: "slice" (overlay state initializes at the period start) for the test period —
reproducing the Cycle 7 test record — and "full" (overlay state initializes at history_start,
then sliced) for the walk-forward folds — reproducing the Cycle 6 fold record.

The **1/N equal-weight** benchmark is constant 1/7 target weights with a 1-day lag and the
monthly calendar, 3 bps round-trip costs.

### Test-Period Comparison

| Benchmark | Ann. Return | Sharpe | Max DD | Excess Return (ann.) | Excess Sharpe (IR) | Sharpe Diff. | Correlation | Relative Max DD |
|-----------|-------------|--------|--------|----------------------|--------------------|--------------|-------------|-----------------|
| 1/N Equal-Weight (7-ETF) | 0.0889 | 0.4716 | -0.2797 | -0.0428 | -0.4629 | -0.1766 | 0.775 | -0.3922 |
| Incumbent TSMOM (tsmomentum_spytrend_001) | 0.0533 | 0.3241 | -0.1794 | -0.0013 | -0.0405 | -0.0291 | 0.955 | -0.1045 |

Excess return/Sharpe are computed on the daily candidate-minus-benchmark series (excess
Sharpe = annualized excess return / annualized excess volatility, i.e. an information ratio).

### Walk-Forward Comparison (identical folds)

| Benchmark | Folds | Mean OOS Sharpe | Std | % Positive | Pooled Trades |
|-----------|-------|-----------------|-----|------------|---------------|
| VIX-regime overlay (C5 baseline) | 24 | 0.4331 | 0.9609 | 75.0% | 137 |
| 1/N Equal-Weight (7-ETF) | 24 | 0.6440 | 1.0959 | 75.0% | 0 |
| Incumbent TSMOM (control arm) | 24 | 0.4628 | 0.9693 | 75.0% | 137 |

---

## 5. Multiple-Testing Control

- **Exact configuration count tracked**: 12 unique pre-specified combinations
  (4 thresholds x 3 exposures), with an explicit arithmetic assertion in the Cycle 19 script
  (`assert len(vix_thresholds) * len(vix_exposures) == 12`). The pre-registered trial count
  is 12 — the pre-registered count equals the evaluated count.
  No configuration was selected on test-period results.
- **Deflated Sharpe Ratio** (`src/evaluation.statistics:compute_dsr`,
  1000 block-bootstrap samples, block=22d, seed=42):
  - At the pre-registered and evaluated count N=12:
    **DSR = -0.5061** (DSR probability = 0.3064).
    Observed test Sharpe 0.2950 vs deflation threshold
    0.4520 (SE = 0.3101,
    E[max of 12] = 1.4575).
- **Probabilistic Sharpe Ratio** (PSR vs SR=0):
  0.8293 (empirical 0.8290);
  PSR vs the 0.9 gate: 0.0255.
- **Block-bootstrap Sharpe 95% CI**: [-0.2934, 0.9147].
- **PBO / CSCV** (`src/evaluation/statistics:compute_pbo` over the 12-config
  grid, train=2004-2009 vs test=2018-2026):
  PBO not computable — degenerate: all 12 evaluated configs have identical OOS classification (all above or all below threshold), so the logit-normal PBO model has no variation. Overfitting diagnostics rely on IS-OOS rank correlation and mean-IS vs mean-OOS gap below.; best-IS config OOS Sharpe = 0.2596;
  IS-OOS Spearman rank correlation = 0.4977;
  mean IS Sharpe = 0.7169 vs mean OOS Sharpe =
  0.2848; 12 of
  12 configs have positive OOS Sharpe.

---

## Promotion-Gate Verdict

Pre-registered promotion gates (ALL must pass to advance):

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| 1. Walk-forward mean OOS Sharpe >= 0.9 | 0.4331 | FAIL |
| 2. Positive fold rate >= 50% | 75.0% | PASS |
| 3. Pooled OOS trades > 100 | 137 | PASS |
| 4. VIX-gate plateau: >= 2 of 4 vix_thresholds within 10% of baseline | 4/4 | PASS |

**Pre-registered falsification condition**: WF mean OOS Sharpe < 0.9
OR positive-fold rate < 50% — **MET (hypothesis falsified)**.

### Final Classification

## **Rejected/Failed**
The pre-registered falsification condition is met.

**Observed evidence**:
- Walk-forward mean OOS Sharpe: 0.4331 over 24 folds
  (75.0% positive fold rate).
- Pooled OOS trades: 137.
- Baseline test Sharpe: 0.2950 (rank 7/12).
- VIX-gate plateau: 4/4 thresholds within tolerance.
- Deflated Sharpe Ratio: -0.5061 (p=0.3064) does not survive
  multiple-testing deflation at N=12.
- Incumbent benchmark test Sharpe: 0.3241 (control arm, vix_exposure=1.0).

**Classification rationale**: The candidate does not clear the WF mean OOS Sharpe >= 0.9
gate and/or the >= 50% positive-fold-rate gate. Per the pre-registered
decision discipline in `research/hypotheses/macroregime_001.md`, the result is labeled
**Rejected/Failed** and archived.

**Structural interpretation**: C5 is an overlay-on-overlay extension of an already-gated
candidate (the SPY trend filter already captures the equity-downturn regime). The VIX regime gate
adds a second regime indicator on top of the SPY SMA filter. As the pre-registered prior
explicitly acknowledged, the prior probability of *raising* the incumbent's already-validated
OOS Sharpe is low — the more likely outcomes are (a) no change (the SPY trend filter already
captures the equity-downturn regime) or (b) a decline (over-trimming exits winning positions in
rebounding high-vol windows). ^VIX is an index (not tradeable), so the gate is a position-sizing
rule on the cached ETF universe, not a volatility risk-premium harvest. The result is consistent
with the overlay-only constraint and the diminishing-returns expectation documented in the
pre-registration.

---

## Decision & Next Steps

**Label**: Rejected/Failed

**Code revision**: `d620179`
**Config SHA-256[:12]**: `76a8c320b25b`
**Code revision (git)**: `d620179`

---

## Reproducibility

### Reproduction Commands

```bash
# Cycle 19: Execute the pre-registered C5 evaluation (baseline + WF + grid + benchmarks + stats)
python3 research/run_cycle19.py

# Verify frozen pre-registration parses
python3 -c "import yaml; yaml.safe_load(open('config/macroregime_candidate_001.yaml'))"
```

### Determinism

The backtest, walk-forward, grid, and benchmark computations are fully deterministic
(no RNG). The block-bootstrap statistics (DSR/PSR/CIs) use seed=42 for reproducibility.

### Configuration

- Frozen config: `config/macroregime_candidate_001.yaml` (SHA-256[:12] = `76a8c320b25b`)
- Baseline: lookback=226, skip=21, top_fraction=0.5, vix_threshold=30, vix_exposure=0.5
- Grid: 12 unique configs (4 thresholds x 3 exposures)
- Walk-forward: train=10y, test=12m, step=6m, purge=21d, embargo=21d
- Bootstrap: 1000 samples, block=22d, seed=42
- Costs: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip; risk-free rate 2.0%

---

## Artifacts Referenced

| Artifact | Path |
|----------|------|
| Pre-registered hypothesis | `research/hypotheses/macroregime_001.md` |
| Frozen configuration | `config/macroregime_candidate_001.yaml` |
| Daily simulation series | `data/processed/simulation_macroregime_001.parquet` |
| Trade log | `data/processed/trades_macroregime_001.parquet` |
| Point-in-time weights | `data/processed/weights_macroregime_001.parquet` |
| Cycle 6 walk-forward design | `research/experiments/tsmomentum_regime_filter_wf_001.md` |
| Cycle 11 shortlist (C5 = 24/35) | `research/reports/opportunity_shortlist.md` |
| Prior C5 VIX filter test | `research/experiments/tsmomentum_regime_filter_001.md` |

---

*Report generated: 2026-10-13 by `research/run_cycle19.py` (Cycle 19)*
*Code revision: d620179*
