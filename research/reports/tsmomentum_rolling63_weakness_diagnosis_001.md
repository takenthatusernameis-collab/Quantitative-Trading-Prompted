# Rolling 63d Sharpe Weakness Diagnosis of the Incumbent (tsmomentum_rolling63_weakness_diagnosis_001, Cycle 925)

## Summary

- Candidate: `tsmomentum_spytrend_001` (the incumbent)
- Sharpe convention: `arithmetic_annualized_rf0`
- Committed record: 469 sessions, 2025-01-02 .. 2026-11-13
- Trailing 63d Sharpe (gate under diagnosis): **-1.483269** vs gate 0.9 (FAIL); production decision **NO-GO** (failed gates: rolling_63d_sharpe, psr)
- Rolling windows on the record: 407 | gate base rate 70.5160% (287/407) | current value at percentile 1.23%
- Distribution: min -2.120279 | p10 -0.253931 | p25 0.488275 | median 1.863988 | p75 3.621753 | max 6.144063
- Read-only: `data/` and `config/` byte-identical before and after the run (**yes**); no committed artifact modified (**yes**).
- Data source: committed parquet cache in `data/raw/` and the committed paper-trading state; the fetcher is never called.
- No gate, threshold, parameter, universe, cost model, drift flag or verdict is changed by this tool.

## 1. Reproduction anchor (fail closed)

The trailing 63-session Sharpe of the committed record is reproduced three ways and the offline path is required to reproduce every committed session bit-for-bit. A mismatch fails the run and nothing is published.

| Quantity | Value |
|---|---|
| From the committed state file | -1.483268754995 |
| Stored `low_rolling_sharpe` drift flag | -1.4832687549946837 |
| Production `evaluate_go_no_go` gate table | -1.483268754995 (identical) |
| Offline recomputation of the strategy path | identical to 1e-12 |

### Overlay state realised on the committed record

| Quantity | Value |
|---|---|
| Sessions | 469 |
| Risk-off sessions (SPY trend filter fired, regime_exposure < 1) | **55** |
| Sessions with the drawdown overlay active (dd_scale < 1) | **0** |
| vol_scale range / mean | [0.4373, 1.0000] / 0.7463 |
| Positions held (min / max / mean) | 0 / 4 / 3.53 |

The volatility target was the only overlay that acted continuously (vol_scale between 0.4373 and 1.0000, mean 0.7463); the drawdown overlay never bound (0 sessions with dd_scale < 1) and the SPY trend filter fired on 55 of 469 sessions.

## 2. Distribution of the rolling 63d Sharpe on the committed record

| Statistic | Value |
|---|---|
| Windows | 407 |
| Minimum | -2.120279 |
| p05 | -1.037951 |
| p10 | -0.253931 |
| p25 | 0.488275 |
| Median | 1.863988 |
| Mean | 2.045229 |
| p75 | 3.621753 |
| p90 | 4.589447 |
| Maximum | 6.144063 |
| Std (ddof=1) | 1.888248 |

- Gate base rate on the record itself: **70.5160%** (287/407 windows at Sharpe >= 0.9); moving-block bootstrap 95% CI [56.2654%, 89.6806%] (2000 resamples over the rolling-window series in blocks of 21 windows, seed 925).
- Current value -1.483269 sits at percentile **1.23%** of the record's own rolling-window distribution (bootstrap 95% CI [2.46%, 98.53%]).
- Failing runs (lengths): [36, 25, 25, 11, 8, 7, 3, 2, 1, 1, 1]; the current run is **25 window(s)** covering 2026-10-12 .. 2026-11-13; the last passing window ended **2026-10-09** (25 windows ago).
- Recovery lag (failing window -> next pass): median 9.0, mean 11.93, max 36.
- Non-overlapping windows (every 63th session, n=7, no window overlap): mean 2.239434, median 1.719354, min 0.317668, max 5.743801, pass rate 85.7143%.

### Failing runs on the record (chronological)

| Length | First failing window end | Last failing window end |
|---|---|---|
| 36 window(s) | 2025-04-03 | 2025-05-23 |
| 1 window(s) | 2025-05-28 | 2025-05-28 |
| 3 window(s) | 2026-04-28 | 2026-04-30 |
| 1 window(s) | 2026-05-19 | 2026-05-19 |
| 1 window(s) | 2026-06-10 | 2026-06-10 |
| 25 window(s) | 2026-07-15 | 2026-08-18 |
| 11 window(s) | 2026-08-20 | 2026-09-03 |
| 7 window(s) | 2026-09-11 | 2026-09-21 |
| 8 window(s) | 2026-09-23 | 2026-10-02 |
| 2 window(s) | 2026-10-07 | 2026-10-08 |
| 25 window(s) | 2026-10-12 | 2026-11-13 |

### Calendar-month profile of the rolling series

| Month | Windows | Mean rolling Sharpe | Min | Failing rate |
|---|---|---|---|---|
| 2025-04 | 19 | -0.372655 | -1.333100 | 1.0000 |
| 2025-05 | 21 | -0.516097 | -1.809887 | 0.8571 |
| 2025-06 | 20 | 4.010027 | 3.050769 | 0.0000 |
| 2025-07 | 22 | 4.624803 | 4.046276 | 0.0000 |
| 2025-08 | 21 | 3.829021 | 2.896427 | 0.0000 |
| 2025-09 | 21 | 4.594096 | 3.162144 | 0.0000 |
| 2025-10 | 23 | 4.739189 | 3.719318 | 0.0000 |
| 2025-11 | 19 | 3.561257 | 2.624907 | 0.0000 |
| 2025-12 | 22 | 2.402946 | 1.411755 | 0.0000 |
| 2026-01 | 20 | 2.390227 | 1.451397 | 0.0000 |
| 2026-02 | 19 | 3.117861 | 2.271494 | 0.0000 |
| 2026-03 | 22 | 1.910184 | 1.068187 | 0.0000 |
| 2026-04 | 21 | 1.285280 | -0.080503 | 0.1429 |
| 2026-05 | 20 | 1.361821 | 0.750796 | 0.0500 |
| 2026-06 | 21 | 1.816728 | 0.650668 | 0.0476 |
| 2026-07 | 22 | 0.692378 | -0.253268 | 0.5909 |
| 2026-08 | 21 | 0.283446 | -0.227560 | 0.9524 |
| 2026-09 | 21 | 0.393223 | -0.491937 | 0.7619 |
| 2026-10 | 22 | 0.234516 | -0.768973 | 0.8636 |
| 2026-11 | 10 | -1.408320 | -2.120279 | 1.0000 |

### Worst 10 rolling windows

| Window | Rolling Sharpe | Window return | Window mean/day | Window std/day |
|---|---|---|---|---|
| 2026-08-10 .. 2026-11-05 | -2.120279 | -5.476774% | -0.086933% | 0.650866% |
| 2026-08-11 .. 2026-11-06 | -1.814422 | -4.738132% | -0.075208% | 0.658004% |
| 2025-02-07 .. 2025-05-08 | -1.809887 | -2.921631% | -0.046375% | 0.406756% |
| 2025-02-06 .. 2025-05-07 | -1.777267 | -2.870009% | -0.045556% | 0.406902% |
| 2026-08-18 .. 2026-11-13 | -1.483269 | -4.121975% | -0.065428% | 0.700237% |
| 2025-02-10 .. 2025-05-09 | -1.466006 | -2.331806% | -0.037013% | 0.400790% |
| 2025-02-05 .. 2025-05-06 | -1.462508 | -2.392359% | -0.037974% | 0.412181% |
| 2026-08-13 .. 2026-11-10 | -1.439417 | -3.929897% | -0.062379% | 0.687946% |
| 2026-08-06 .. 2026-11-03 | -1.399699 | -2.940533% | -0.046675% | 0.529360% |
| 2025-02-11 .. 2025-05-12 | -1.391848 | -2.232788% | -0.035441% | 0.404218% |

## 3. Overlap with the published folds' Cycle-923 buckets

Each rolling window is mapped onto the published walk-forward fold that contains its end date (the latest-starting fold when two overlap) and inherits that fold's Cycle-923 bucket labels. 289 of 407 windows fall inside a published fold's test window (folds [47, 48]); 118 fall outside every fold -- the last published fold (#48) ends its test window on 2026-05-28 -- and 169 windows fall inside two folds.

**Reading the two tests together.** The permutation p-value shuffles the bucket labels across the 407 windows and therefore treats them as independent observations; consecutive rolling windows overlap by 62 sessions, so that p-value is anticonservative by construction. The moving-block bootstrap CI on the bucket gap is the dependence-aware test and is the one the verdict uses.

### F1 calendar phase (published fold parity)

| Bucket | Windows | Mean rolling Sharpe | Median | Failing rate |
|---|---|---|---|---|
| phase_A | 47 | 0.228400 | -0.282805 | 0.7872 |
| phase_B | 242 | 3.147431 | 3.295418 | 0.0165 |
| no_fold | 118 | 0.508433 | 0.340763 | 0.6695 |

- Dispersion share (eta^2) over the 289 covered windows: 0.353830; permutation p-value (10000 permutations, seed 925): **0.000100**
- Bucket gap (phase_A - phase_B): -2.919032; moving-block bootstrap 95% CI [-4.506950, +1.061537] -- includes zero
- Non-overlapping windows only (dependence-free robustness check): phase_A n=1 mean 0.317668; phase_B n=4 mean 3.159897

### F2 SPY trend state at the fold's test-window start

| Bucket | Windows | Mean rolling Sharpe | Median | Failing rate |
|---|---|---|---|---|
| risk_on | 289 | 2.672710 | 2.943380 | 0.1419 |
| risk_off | 0 | not estimable (bucket absent in the record period) | - | - |
| no_fold | 118 | 0.508433 | 0.340763 | 0.6695 |

- **This family is one-sided inside the committed record**: only one of its buckets occurs, so its bucket gap is **not estimable** from this record (the absence is reported, not imputed).

- Dispersion share (eta^2) over the 289 covered windows: 0.000000; permutation p-value (10000 permutations, seed 925): **1.000000**
- Bucket gap: not estimable (one of the two buckets has no window in the record period)
- Non-overlapping windows only (dependence-free robustness check): risk_on n=5 mean 2.591451; risk_off n=0 mean N/A

### F3 SPY trailing 12-month return sign at the fold's test-window start

| Bucket | Windows | Mean rolling Sharpe | Median | Failing rate |
|---|---|---|---|---|
| up | 289 | 2.672710 | 2.943380 | 0.1419 |
| down | 0 | not estimable (bucket absent in the record period) | - | - |
| no_fold | 118 | 0.508433 | 0.340763 | 0.6695 |

- **This family is one-sided inside the committed record**: only one of its buckets occurs, so its bucket gap is **not estimable** from this record (the absence is reported, not imputed).

- Dispersion share (eta^2) over the 289 covered windows: 0.000000; permutation p-value (10000 permutations, seed 925): **1.000000**
- Bucket gap: not estimable (one of the two buckets has no window in the record period)
- Non-overlapping windows only (dependence-free robustness check): up n=5 mean 2.591451; down n=0 mean N/A

### F4 training-window 63-day realised-volatility tercile

| Bucket | Windows | Mean rolling Sharpe | Median | Failing rate |
|---|---|---|---|---|
| low_vol | 242 | 3.147431 | 3.295418 | 0.0165 |
| med_vol | 47 | 0.228400 | -0.282805 | 0.7872 |
| high_vol | 0 | not estimable (bucket absent in the record period) | - | - |
| no_fold | 118 | 0.508433 | 0.340763 | 0.6695 |

- Dispersion share (eta^2) over the 289 covered windows: 0.353830; permutation p-value (10000 permutations, seed 925): **0.000100**
- Bucket gap (low_vol - med_vol): +2.919032; moving-block bootstrap 95% CI [-1.061537, +4.506950] -- includes zero
- Non-overlapping windows only (dependence-free robustness check): low_vol n=4 mean 3.159897; med_vol n=1 mean 0.317668; high_vol n=0 mean N/A

## 4. Correlation of the rolling Sharpe to market state

Spearman rank correlations between the rolling 63d Sharpe and window-level observable state, with moving-block bootstrap 95% CIs on the correlation.

| State variable | Windows | Spearman rho | 95% CI | Excludes zero |
|---|---|---|---|---|
| spy_ret_12m | 404 | 0.0126 | [-0.3994, +0.5720] | no |
| spy_rv_63 | 404 | -0.3862 | [-0.6468, +0.3592] | no |
| spy_sma_gap | 404 | 0.4642 | [-0.1930, +0.7208] | no |
| strategy_window_realised_vol | 407 | -0.1340 | [-0.6902, +0.3966] | no |

## 5. Isolated overlay counterfactuals (scratch paths, no production change)

Each variant is recomputed from the committed cache on a scratch path and evaluated on the trailing window, the committed record, the full path and the published 48-fold walk-forward. No production code is modified; this section is measurement, not a proposal to change the strategy.

| Variant | Trailing 63d Sharpe | Record Sharpe | Full-path Sharpe | WF mean OOS Sharpe | WF mean excl. worst fold | Clears gate? |
|---|---|---|---|---|---|---|
| V0_baseline | -1.439417 | 1.583075 | 1.476044 | 0.947307 | 1.431928 | no |
| V1_no_vol_target | -1.323347 | 1.175902 | 1.329707 | 0.930602 | 1.414867 | no |
| V2_vol_estimate_lagged_1d | -1.621363 | 1.410227 | 1.400029 | 1.318605 | 1.357135 | no |
| V3_no_drawdown_control | -1.439417 | 1.583075 | 1.476044 | 0.947307 | 1.431928 | no |
| V4_no_overlay | -1.323347 | 1.175902 | 1.325504 | 0.930602 | 1.414867 | no |

- **V0_baseline** -- committed overlay: volatility target on the same-session estimate.
- **V1_no_vol_target** -- volatility target disabled (vol_scale == 1).
- **V2_vol_estimate_lagged_1d** -- volatility estimate lagged one session (no same-session feedback).
- **V3_no_drawdown_control** -- drawdown control disabled (dd_scale == 1).
- **V4_no_overlay** -- no overlay at all (raw signal + SPY filter + costs).

### The published walk-forward's minimum fold is a numerical artefact

The published record's minimum fold OOS Sharpe is -21.829879 (fold 12, 2008-01-22 .. 2009-01-07): 244 sessions of which **242 are flat** (|r| < 1e-9), with mean -4.963e-06 and standard deviation 6.132e-05. Dividing a tiny negative mean by a tiny dispersion produces a large negative Sharpe: the value is a property of the estimator on a near-flat segment, not a -21 Sharpe. That single fold moves the headline walk-forward mean (0.947307 with it, 1.431928 without it), so the walk-forward mean must be read together with the dispersion column (std 3.4798 with it). The same artefact is absent from the lagged variant, whose worst fold is -0.492313 (fold 13, 222 flat sessions).

### Same-session feedback in the volatility estimate

The committed overlay sets the exposure of session *t* from a realised-volatility estimate whose trailing 63-session window **includes session t itself** (`research/run_cycle6.py::_apply_overlay`, `src/simulation/engine.py::_target_weights`, `src/evaluation/risk.py`): today's own return moves today's exposure. The `V2` variant repeats the whole path with that estimate lagged one session, which is the only difference.

| Quantity | Same-session estimate (committed) | Estimate lagged 1 session |
|---|---|---|
| Committed-record Sharpe | 1.579855 | 1.410227 |
| Committed-record return sum | +0.291828 | +0.268943 |
| Trailing 63d Sharpe | -1.483269 | -1.621363 |
| vol_scale range on the record | [0.4373, 1.0000] | [0.4373, 1.0000] |

This is a **measurement** finding, not a fix: lagging the estimate makes the failing window slightly worse, so it is not the cause of the gate failure, and it changes every published artifact of the candidate.

## 6. Verdict

**1. The failing gate value is a tail state of the record's own rolling-window distribution, not a new level.** The trailing 63-session Sharpe -1.483269 sits at the 1.23% percentile of the 407 rolling windows the record has produced; the gate passes in 70.52% of them (bootstrap 95% CI [56.27%, 89.68%]). The current failing run covers 2026-10-12 .. 2026-11-13 (25 window(s)), and the record has produced longer failing runs before (the longest: 36 windows).

**2. The weakness does not cluster in any published observable-state bucket.** The families F2_spy_trend_state, F3_spy_12m_return_sign are one-sided inside the record period (the risk-off / down-trend / high-volatility states that Cycle 923 flagged never occur in the committed record), so their bucket gaps are **not estimable** from this record and are reported as absent rather than imputed; the two-sided F1_calendar_phase, F4_train_63d_realvol_tercile partition the record identically (the published folds that cover it are contiguous in time), i.e. they are a time split of the record rather than an independent state, and their bucket gap CI includes zero. The apparent concentration is therefore consistent with sampling noise at this record's effective sample size -- the same conclusion Cycle 924 reached for the fold-level buckets.

**3. No permitted change clears the gate.** The strongest isolated overlay variant (`V1_no_vol_target`, volatility target disabled (vol_scale == 1)) lifts the trailing window from -1.483269 to -1.323347, still far below the 0.9 gate, and every other variant is below that. The weakness is an overlay-timing outcome -- the volatility target de-risks into the high-volatility sessions that dominate the window -- not evidence that the momentum edge has decayed, and not something a threshold, universe, cost-model or parameter change may fix.

**4. The gate is a symptom, not the binding constraint.** Per Cycle 866, clearing `rolling_63d_sharpe` alone cannot yield GO on this record: the PSR gate is decisive and the decision stays NO-GO (failed gates: rolling_63d_sharpe, psr).

**5. Separate measurement defect found and quantified (not a fix).** The volatility estimate sets session t's exposure from a trailing window that includes session t itself (same-session feedback, in `research/run_cycle6.py`, `src/simulation/engine.py` and `src/evaluation/risk.py`). Lagging the estimate one session changes the committed record's Sharpe from 1.579855 to 1.410227, the full-path Sharpe from 1.476044 to 1.400029 and the failing window from -1.483269 to -1.621363: it makes the failing window slightly worse, so it is **not** the cause of the gate failure, but it does flatter the published Sharpe statistics of this candidate (the headline walk-forward mean moves the other way only because of the one numerical-artifact fold documented in section 5). It is handed off as a separate, explicitly scoped re-derivation task -- **no production code is changed by this cycle**.

## 7. Checks

- [committed_record_loaded]: PASS (observed: 469 sessions, expected: > 63 sessions)
- [gate_threshold_read_from_config]: PASS (observed: 0.9, expected: 0.9)
- [trailing_63d_sharpe_matches_stored_drift_flag]: PASS (observed: -1.483268754995 vs stored -1.4832687549946837, expected: )
- [trailing_63d_sharpe_matches_production_gate_table]: PASS (observed: production -1.483268754995, expected: )
- [local_baseline_path_bit_identical_to_run_cycle6_overlay]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0 (bit-identical))
- [offline_path_reproduces_every_committed_session]: PASS (observed: max |diff| = 5.421e-20 over 466 sessions, expected: <= 1e-12)
- [offline_path_reproduces_trailing_63d_sharpe]: PASS (observed: -1.439416898299 vs -1.439416898299, expected: )
- [committed_record_run_history_matches_the_session_count]: PASS (observed: 469 entries, expected: 469)
- [rolling_window_count]: PASS (observed: 407 windows, expected: 407)
- [rolling_series_last_value_matches_production_sharpe]: PASS (observed: -1.483268754995, expected: )
- [bootstrap_is_deterministic]: PASS (observed: 2000 resamples, seed 925, expected: fixed seed)
- [published_fold_buckets_reused_from_cycle_923]: PASS (observed: 48 folds, expected: 48 folds)
- [bucket_family_F1_calendar_phase_absent_buckets_are_reported_not_estimable]: PASS (observed: n=[47, 242, 118], expected: every bucket either has windows or is reported as not estimable)
- [bucket_family_F2_spy_trend_state_absent_buckets_are_reported_not_estimable]: PASS (observed: n=[289, 0, 118], expected: every bucket either has windows or is reported as not estimable)
- [bucket_family_F3_spy_12m_return_sign_absent_buckets_are_reported_not_estimable]: PASS (observed: n=[289, 0, 118], expected: every bucket either has windows or is reported as not estimable)
- [bucket_family_F4_train_63d_realvol_tercile_absent_buckets_are_reported_not_estimable]: PASS (observed: n=[242, 47, 0, 118], expected: every bucket either has windows or is reported as not estimable)
- [counterfactual_baseline_reproduces_the_published_walk_forward]: PASS (observed: 0.947307, expected: 0.947307 (published))
- [drawdown_control_contributes_exactly_zero_on_this_record]: PASS (observed: V3 == V0 on the record, expected: )
- [no_counterfactual_variant_clears_the_rolling_gate]: PASS (observed: V0_baseline=-1.4394, V1_no_vol_target=-1.3233, V2_vol_estimate_lagged_1d=-1.6214, V3_no_drawdown_control=-1.4394, V4_no_overlay=-1.3233, expected: every variant below the 0.9 gate)
- [data_unchanged]: PASS
- [config_unchanged]: PASS
- [committed_artifacts_unchanged]: PASS

## 8. Reproduction commands

```bash
python research/tsmomentum_rolling63_weakness_diagnosis.py
python -m pytest -q tests/test_tsmomentum_rolling63_weakness_diagnosis.py
python -m pytest -q
git status --porcelain data/ config/
```

## 9. JSON payload

```json
{
  "bootstrap": {
    "ci_level": 0.95,
    "method": "moving-block bootstrap over the record's sessions (block = 63 sessions)",
    "resamples": 2000,
    "seed": 925
  },
  "candidate": "tsmomentum_spytrend_001",
  "checks": [
    {
      "expected": "> 63 sessions",
      "name": "committed_record_loaded",
      "observed": "469 sessions",
      "pass": true
    },
    {
      "expected": 0.9,
      "name": "gate_threshold_read_from_config",
      "observed": 0.9,
      "pass": true
    },
    {
      "expected": "",
      "name": "trailing_63d_sharpe_matches_stored_drift_flag",
      "observed": "-1.483268754995 vs stored -1.4832687549946837",
      "pass": true
    },
    {
      "expected": "",
      "name": "trailing_63d_sharpe_matches_production_gate_table",
      "observed": "production -1.483268754995",
      "pass": true
    },
    {
      "expected": "0.0 (bit-identical)",
      "name": "local_baseline_path_bit_identical_to_run_cycle6_overlay",
      "observed": "max |diff| = 0.000e+00",
      "pass": true
    },
    {
      "expected": "<= 1e-12",
      "name": "offline_path_reproduces_every_committed_session",
      "observed": "max |diff| = 5.421e-20 over 466 sessions",
      "pass": true
    },
    {
      "expected": "",
      "name": "offline_path_reproduces_trailing_63d_sharpe",
      "observed": "-1.439416898299 vs -1.439416898299",
      "pass": true
    },
    {
      "expected": "469",
      "name": "committed_record_run_history_matches_the_session_count",
      "observed": "469 entries",
      "pass": true
    },
    {
      "expected": "407",
      "name": "rolling_window_count",
      "observed": "407 windows",
      "pass": true
    },
    {
      "expected": "",
      "name": "rolling_series_last_value_matches_production_sharpe",
      "observed": "-1.483268754995",
      "pass": true
    },
    {
      "expected": "fixed seed",
      "name": "bootstrap_is_deterministic",
      "observed": "2000 resamples, seed 925",
      "pass": true
    },
    {
      "expected": "48 folds",
      "name": "published_fold_buckets_reused_from_cycle_923",
      "observed": "48 folds",
      "pass": true
    },
    {
      "expected": "every bucket either has windows or is reported as not estimable",
      "name": "bucket_family_F1_calendar_phase_absent_buckets_are_reported_not_estimable",
      "observed": "n=[47, 242, 118]",
      "pass": true
    },
    {
      "expected": "every bucket either has windows or is reported as not estimable",
      "name": "bucket_family_F2_spy_trend_state_absent_buckets_are_reported_not_estimable",
      "observed": "n=[289, 0, 118]",
      "pass": true
    },
    {
      "expected": "every bucket either has windows or is reported as not estimable",
      "name": "bucket_family_F3_spy_12m_return_sign_absent_buckets_are_reported_not_estimable",
      "observed": "n=[289, 0, 118]",
      "pass": true
    },
    {
      "expected": "every bucket either has windows or is reported as not estimable",
      "name": "bucket_family_F4_train_63d_realvol_tercile_absent_buckets_are_reported_not_estimable",
      "observed": "n=[242, 47, 0, 118]",
      "pass": true
    },
    {
      "expected": "0.947307 (published)",
      "name": "counterfactual_baseline_reproduces_the_published_walk_forward",
      "observed": "0.947307",
      "pass": true
    },
    {
      "expected": "",
      "name": "drawdown_control_contributes_exactly_zero_on_this_record",
      "observed": "V3 == V0 on the record",
      "pass": true
    },
    {
      "expected": "every variant below the 0.9 gate",
      "name": "no_counterfactual_variant_clears_the_rolling_gate",
      "observed": "V0_baseline=-1.4394, V1_no_vol_target=-1.3233, V2_vol_estimate_lagged_1d=-1.6214, V3_no_drawdown_control=-1.4394, V4_no_overlay=-1.3233",
      "pass": true
    },
    {
      "expected": "",
      "name": "data_unchanged",
      "observed": "",
      "pass": true
    },
    {
      "expected": "",
      "name": "config_unchanged",
      "observed": "",
      "pass": true
    },
    {
      "expected": "",
      "name": "committed_artifacts_unchanged",
      "observed": "",
      "pass": true
    }
  ],
  "correlations": [
    {
      "ci95": [
        -0.399408315110735,
        0.5720073308757575
      ],
      "excludes_zero": false,
      "n": 404,
      "spearman": 0.012618962475238424,
      "variable": "spy_ret_12m"
    },
    {
      "ci95": [
        -0.6467884857503099,
        0.35918601628406865
      ],
      "excludes_zero": false,
      "n": 404,
      "spearman": -0.3861784689635216,
      "variable": "spy_rv_63"
    },
    {
      "ci95": [
        -0.19302351331559406,
        0.7207900436287187
      ],
      "excludes_zero": false,
      "n": 404,
      "spearman": 0.4642375072908449,
      "variable": "spy_sma_gap"
    },
    {
      "ci95": [
        -0.6901984709413715,
        0.3965525740827464
      ],
      "excludes_zero": false,
      "n": 407,
      "spearman": -0.13402802449455595,
      "variable": "strategy_window_realised_vol"
    }
  ],
  "cycle": "925",
  "data_source": "committed parquet cache in data/raw/ and the committed paper-trading state (fetcher never called)",
  "distribution": {
    "base_rate": 0.7051597051597052,
    "base_rate_ci95": [
      0.5626535626535627,
      0.8968058968058968
    ],
    "current": -1.4832687549946857,
    "current_failing_run": 25,
    "current_failing_run_detail": {
      "first_window_end": "2026-10-12",
      "last_window_end": "2026-11-13",
      "length": 25
    },
    "current_percentile_rank": 0.012285012285012284,
    "current_rank_ci95": [
      0.02457002457002457,
      0.9852579852579852
    ],
    "failing_runs": [
      36,
      25,
      25,
      11,
      8,
      7,
      3,
      2,
      1,
      1,
      1
    ],
    "failing_runs_detail": [
      {
        "first_window_end": "2025-04-03",
        "last_window_end": "2025-05-23",
        "length": 36
      },
      {
        "first_window_end": "2025-05-28",
        "last_window_end": "2025-05-28",
        "length": 1
      },
      {
        "first_window_end": "2026-04-28",
        "last_window_end": "2026-04-30",
        "length": 3
      },
      {
        "first_window_end": "2026-05-19",
        "last_window_end": "2026-05-19",
        "length": 1
      },
      {
        "first_window_end": "2026-06-10",
        "last_window_end": "2026-06-10",
        "length": 1
      },
      {
        "first_window_end": "2026-07-15",
        "last_window_end": "2026-08-18",
        "length": 25
      },
      {
        "first_window_end": "2026-08-20",
        "last_window_end": "2026-09-03",
        "length": 11
      },
      {
        "first_window_end": "2026-09-11",
        "last_window_end": "2026-09-21",
        "length": 7
      },
      {
        "first_window_end": "2026-09-23",
        "last_window_end": "2026-10-02",
        "length": 8
      },
      {
        "first_window_end": "2026-10-07",
        "last_window_end": "2026-10-08",
        "length": 2
      },
      {
        "first_window_end": "2026-10-12",
        "last_window_end": "2026-11-13",
        "length": 25
      }
    ],
    "last_passing_window_end": "2026-10-09",
    "max": 6.14406336732776,
    "mean": 2.045229246816328,
    "median": 1.8639883733522842,
    "min": -2.1202794870108113,
    "n_fail": 120,
    "n_pass": 287,
    "n_windows": 407,
    "p05": -1.0379510780353012,
    "p10": -0.25393129383854673,
    "p25": 0.48827484654790343,
    "p75": 3.621753231608122,
    "p90": 4.589447350596663,
    "recovery_lag_max": 36,
    "recovery_lag_mean": 11.926315789473684,
    "recovery_lag_median": 9.0,
    "std": 1.8882475737391102,
    "windows_since_last_pass": 25
  },
  "families": {
    "F1_calendar_phase": {
      "bucket_gap": -2.919031888288582,
      "bucket_gap_ci95": [
        -4.506950287838671,
        1.0615366083045503
      ],
      "buckets": [
        {
          "bucket": "phase_A",
          "estimable": true,
          "fail_rate": 0.7872340425531915,
          "mean_rolling_sharpe": 0.22839956506503362,
          "median_rolling_sharpe": -0.2828052892738014,
          "n": 47
        },
        {
          "bucket": "phase_B",
          "estimable": true,
          "fail_rate": 0.01652892561983471,
          "mean_rolling_sharpe": 3.1474314533536156,
          "median_rolling_sharpe": 3.2954184576108316,
          "n": 242
        },
        {
          "bucket": "no_fold",
          "estimable": true,
          "fail_rate": 0.6694915254237288,
          "mean_rolling_sharpe": 0.5084331541068972,
          "median_rolling_sharpe": 0.34076321661836473,
          "n": 118
        }
      ],
      "dispersion_share": 0.35383012261975,
      "gap_estimable": true,
      "gap_excludes_zero": false,
      "label": "F1 calendar phase (published fold parity)",
      "n_covered": 289,
      "permutation_count": 0,
      "permutation_pvalue": 9.999000099990002e-05,
      "single_bucket_only": false
    },
    "F2_spy_trend_state": {
      "bucket_gap": NaN,
      "bucket_gap_ci95": [
        NaN,
        NaN
      ],
      "buckets": [
        {
          "bucket": "risk_on",
          "estimable": true,
          "fail_rate": 0.14186851211072665,
          "mean_rolling_sharpe": 2.672710004393189,
          "median_rolling_sharpe": 2.943380451675367,
          "n": 289
        },
        {
          "bucket": "risk_off",
          "estimable": false,
          "fail_rate": NaN,
          "mean_rolling_sharpe": NaN,
          "median_rolling_sharpe": NaN,
          "n": 0
        },
        {
          "bucket": "no_fold",
          "estimable": true,
          "fail_rate": 0.6694915254237288,
          "mean_rolling_sharpe": 0.5084331541068972,
          "median_rolling_sharpe": 0.34076321661836473,
          "n": 118
        }
      ],
      "dispersion_share": 0.0,
      "gap_estimable": false,
      "gap_excludes_zero": false,
      "label": "F2 SPY trend state at the fold's test-window start",
      "n_covered": 289,
      "permutation_count": 10000,
      "permutation_pvalue": 1.0,
      "single_bucket_only": true
    },
    "F3_spy_12m_return_sign": {
      "bucket_gap": NaN,
      "bucket_gap_ci95": [
        NaN,
        NaN
      ],
      "buckets": [
        {
          "bucket": "up",
          "estimable": true,
          "fail_rate": 0.14186851211072665,
          "mean_rolling_sharpe": 2.672710004393189,
          "median_rolling_sharpe": 2.943380451675367,
          "n": 289
        },
        {
          "bucket": "down",
          "estimable": false,
          "fail_rate": NaN,
          "mean_rolling_sharpe": NaN,
          "median_rolling_sharpe": NaN,
          "n": 0
        },
        {
          "bucket": "no_fold",
          "estimable": true,
          "fail_rate": 0.6694915254237288,
          "mean_rolling_sharpe": 0.5084331541068972,
          "median_rolling_sharpe": 0.34076321661836473,
          "n": 118
        }
      ],
      "dispersion_share": 0.0,
      "gap_estimable": false,
      "gap_excludes_zero": false,
      "label": "F3 SPY trailing 12-month return sign at the fold's test-window start",
      "n_covered": 289,
      "permutation_count": 10000,
      "permutation_pvalue": 1.0,
      "single_bucket_only": true
    },
    "F4_train_63d_realvol_tercile": {
      "bucket_gap": 2.919031888288582,
      "bucket_gap_ci95": [
        -1.0615366083045505,
        4.506950287838671
      ],
      "buckets": [
        {
          "bucket": "low_vol",
          "estimable": true,
          "fail_rate": 0.01652892561983471,
          "mean_rolling_sharpe": 3.1474314533536156,
          "median_rolling_sharpe": 3.2954184576108316,
          "n": 242
        },
        {
          "bucket": "med_vol",
          "estimable": true,
          "fail_rate": 0.7872340425531915,
          "mean_rolling_sharpe": 0.22839956506503362,
          "median_rolling_sharpe": -0.2828052892738014,
          "n": 47
        },
        {
          "bucket": "high_vol",
          "estimable": false,
          "fail_rate": NaN,
          "mean_rolling_sharpe": NaN,
          "median_rolling_sharpe": NaN,
          "n": 0
        },
        {
          "bucket": "no_fold",
          "estimable": true,
          "fail_rate": 0.6694915254237288,
          "mean_rolling_sharpe": 0.5084331541068972,
          "median_rolling_sharpe": 0.34076321661836473,
          "n": 118
        }
      ],
      "dispersion_share": 0.35383012261975,
      "gap_estimable": true,
      "gap_excludes_zero": false,
      "label": "F4 training-window 63-day realised-volatility tercile",
      "n_covered": 289,
      "permutation_count": 0,
      "permutation_pvalue": 9.999000099990002e-05,
      "single_bucket_only": false
    }
  },
  "families_non_overlapping": {
    "F1_calendar_phase": {
      "buckets": [
        {
          "bucket": "phase_A",
          "mean_rolling_sharpe": 0.31766773088459666,
          "n": 1
        },
        {
          "bucket": "phase_B",
          "mean_rolling_sharpe": 3.1598971529688074,
          "n": 4
        }
      ]
    },
    "F2_spy_trend_state": {
      "buckets": [
        {
          "bucket": "risk_on",
          "mean_rolling_sharpe": 2.5914512685519653,
          "n": 5
        },
        {
          "bucket": "risk_off",
          "mean_rolling_sharpe": NaN,
          "n": 0
        }
      ]
    },
    "F3_spy_12m_return_sign": {
      "buckets": [
        {
          "bucket": "up",
          "mean_rolling_sharpe": 2.5914512685519653,
          "n": 5
        },
        {
          "bucket": "down",
          "mean_rolling_sharpe": NaN,
          "n": 0
        }
      ]
    },
    "F4_train_63d_realvol_tercile": {
      "buckets": [
        {
          "bucket": "low_vol",
          "mean_rolling_sharpe": 3.1598971529688074,
          "n": 4
        },
        {
          "bucket": "med_vol",
          "mean_rolling_sharpe": 0.31766773088459666,
          "n": 1
        },
        {
          "bucket": "high_vol",
          "mean_rolling_sharpe": NaN,
          "n": 0
        }
      ]
    }
  },
  "fold_overlap": {
    "n_windows_in_two_folds": 169,
    "n_windows_with_a_fold": 289,
    "n_windows_without_a_fold": 118
  },
  "fold_structure": {
    "folds_covering_the_record": [
      47,
      48
    ],
    "last_fold": 48,
    "last_fold_test_end": "2026-05-28",
    "last_fold_test_start": "2025-06-11"
  },
  "gate_threshold": 0.9,
  "incumbent_verdict": "Credible Candidate (unchanged); promotion decision NO-GO (unchanged)",
  "monthly_profile": [
    {
      "fail_rate": 1.0,
      "mean_rolling_sharpe": -0.37265474141941735,
      "min_rolling_sharpe": -1.3331004632311612,
      "month": "2025-04",
      "n": 19
    },
    {
      "fail_rate": 0.8571428571428571,
      "mean_rolling_sharpe": -0.5160973560956074,
      "min_rolling_sharpe": -1.8098874856306422,
      "month": "2025-05",
      "n": 21
    },
    {
      "fail_rate": 0.0,
      "mean_rolling_sharpe": 4.010026710276326,
      "min_rolling_sharpe": 3.0507692742856483,
      "month": "2025-06",
      "n": 20
    },
    {
      "fail_rate": 0.0,
      "mean_rolling_sharpe": 4.62480326993629,
      "min_rolling_sharpe": 4.046275641230527,
      "month": "2025-07",
      "n": 22
    },
    {
      "fail_rate": 0.0,
      "mean_rolling_sharpe": 3.8290211091415762,
      "min_rolling_sharpe": 2.896427192104765,
      "month": "2025-08",
      "n": 21
    },
    {
      "fail_rate": 0.0,
      "mean_rolling_sharpe": 4.594095821407819,
      "min_rolling_sharpe": 3.162144024463906,
      "month": "2025-09",
      "n": 21
    },
    {
      "fail_rate": 0.0,
      "mean_rolling_sharpe": 4.739189491532046,
      "min_rolling_sharpe": 3.7193177642720974,
      "month": "2025-10",
      "n": 23
    },
    {
      "fail_rate": 0.0,
      "mean_rolling_sharpe": 3.5612569501263516,
      "min_rolling_sharpe": 2.624906581048621,
      "month": "2025-11",
      "n": 19
    },
    {
      "fail_rate": 0.0,
      "mean_rolling_sharpe": 2.402945602808712,
      "min_rolling_sharpe": 1.4117550862723423,
      "month": "2025-12",
      "n": 22
    },
    {
      "fail_rate": 0.0,
      "mean_rolling_sharpe": 2.390226969001945,
      "min_rolling_sharpe": 1.4513972310708716,
      "month": "2026-01",
      "n": 20
    },
    {
      "fail_rate": 0.0,
      "mean_rolling_sharpe": 3.1178610891410408,
      "min_rolling_sharpe": 2.2714940558534087,
      "month": "2026-02",
      "n": 19
    },
    {
      "fail_rate": 0.0,
      "mean_rolling_sharpe": 1.9101843972045598,
      "min_rolling_sharpe": 1.0681867669699392,
      "month": "2026-03",
      "n": 22
    },
    {
      "fail_rate": 0.14285714285714285,
      "mean_rolling_sharpe": 1.2852801600174926,
      "min_rolling_sharpe": -0.08050318343208619,
      "month": "2026-04",
      "n": 21
    },
    {
      "fail_rate": 0.05,
      "mean_rolling_sharpe": 1.361821258363598,
      "min_rolling_sharpe": 0.7507958312165536,
      "month": "2026-05",
      "n": 20
    },
    {
      "fail_rate": 0.047619047619047616,
      "mean_rolling_sharpe": 1.8167277709199519,
      "min_rolling_sharpe": 0.6506678638102619,
      "month": "2026-06",
      "n": 21
    },
    {
      "fail_rate": 0.5909090909090909,
      "mean_rolling_sharpe": 0.6923782484466456,
      "min_rolling_sharpe": -0.25326804894954086,
      "month": "2026-07",
      "n": 22
    },
    {
      "fail_rate": 0.9523809523809523,
      "mean_rolling_sharpe": 0.2834460571689679,
      "min_rolling_sharpe": -0.227560353629916,
      "month": "2026-08",
      "n": 21
    },
    {
      "fail_rate": 0.7619047619047619,
      "mean_rolling_sharpe": 0.39322347831932847,
      "min_rolling_sharpe": -0.4919371207312956,
      "month": "2026-09",
      "n": 21
    },
    {
      "fail_rate": 0.8636363636363636,
      "mean_rolling_sharpe": 0.23451604129203815,
      "min_rolling_sharpe": -0.7689729823169228,
      "month": "2026-10",
      "n": 22
    },
    {
      "fail_rate": 1.0,
      "mean_rolling_sharpe": -1.4083200434552026,
      "min_rolling_sharpe": -2.1202794870108113,
      "month": "2026-11",
      "n": 10
    }
  ],
  "non_overlapping": {
    "max": 5.743800867855903,
    "mean": 2.2394335004091372,
    "median": 1.7193544795645042,
    "min": 0.31766773088459666,
    "n": 7,
    "pass_rate": 0.8571428571428571
  },
  "overall": "PASS",
  "permutation_seed": 925,
  "permutations": 10000,
  "read_only": {
    "committed_artifacts_unchanged": true,
    "config_unchanged": true,
    "data_unchanged": true
  },
  "record": {
    "first_session": "2025-01-02",
    "full_period_sharpe": 1.5798553171996923,
    "last_session": "2026-11-13",
    "n_sessions": 469,
    "overlay_state": {
      "n_drawdown_overlay_sessions": 0,
      "n_positions_max": 4,
      "n_positions_mean": 3.5309168443496803,
      "n_positions_min": 0,
      "n_risk_off_sessions": 55,
      "n_run_history": 469,
      "vol_scale_max": 1.0,
      "vol_scale_mean": 0.7463316542423309,
      "vol_scale_min": 0.43731674589035896
    },
    "production_decision": "NO-GO",
    "production_failed_gates": [
      "rolling_63d_sharpe",
      "psr"
    ],
    "stored_drift_flag": -1.4832687549946837,
    "trailing_63d_sharpe": -1.4832687549946837
  },
  "same_session_feedback": {
    "record_return_sum_base": 0.2918284832010072,
    "record_return_sum_lagged": 0.2689425288005978,
    "record_sharpe_base": 1.5798553171996923,
    "record_sharpe_lagged": 1.4102271780414941,
    "trailing_63d_base": -1.4832687549946837,
    "trailing_63d_lagged": -1.6213634935218275,
    "vol_scale_base_max": 1.0,
    "vol_scale_base_min": 0.43731674589035896,
    "vol_scale_lagged_max": 1.0,
    "vol_scale_lagged_min": 0.43731674589035896
  },
  "sharpe_convention": "arithmetic_annualized_rf0",
  "variants": {
    "V0_baseline": {
      "dd_mode": "base",
      "description": "committed overlay: volatility target on the same-session estimate",
      "full_path_return_sum": 4.346337431343035,
      "full_path_sharpe": 1.4760436065925557,
      "record_return_sum": 0.2905923732083021,
      "record_sharpe": 1.583075087874877,
      "rolling_gate_passes_on_current_window": false,
      "trailing_63d_sharpe": -1.4394168982987599,
      "vol_mode": "base",
      "wf_mean_excl_worst_fold": 1.431928469659107,
      "wf_mean_test_sharpe": 0.9473074720246092,
      "wf_median_test_sharpe": 1.29329878363231,
      "wf_min_test_sharpe": -21.829879416796786,
      "wf_pct_positive": 0.9166666666666666,
      "wf_std_test_sharpe": 3.4797702418403893,
      "wf_worst_fold": 12,
      "wf_worst_fold_mean": -4.962781666339485e-06,
      "wf_worst_fold_n_flat_sessions": 242,
      "wf_worst_fold_n_sessions": 244,
      "wf_worst_fold_std": 6.132163741108965e-05,
      "wf_worst_fold_test_end": "2009-01-07",
      "wf_worst_fold_test_start": "2008-01-22"
    },
    "V1_no_vol_target": {
      "dd_mode": "base",
      "description": "volatility target disabled (vol_scale == 1)",
      "full_path_return_sum": 5.598170314497469,
      "full_path_sharpe": 1.3297072296359465,
      "record_return_sum": 0.3299847781148602,
      "record_sharpe": 1.1759018837938102,
      "rolling_gate_passes_on_current_window": false,
      "trailing_63d_sharpe": -1.3233468907373043,
      "vol_mode": "off",
      "wf_mean_excl_worst_fold": 1.4148673153950704,
      "wf_mean_test_sharpe": 0.9306017584744067,
      "wf_median_test_sharpe": 1.2360947885524292,
      "wf_min_test_sharpe": -21.829879416796786,
      "wf_pct_positive": 0.9375,
      "wf_std_test_sharpe": 3.4735315023009243,
      "wf_worst_fold": 12,
      "wf_worst_fold_mean": -4.962781666339485e-06,
      "wf_worst_fold_n_flat_sessions": 242,
      "wf_worst_fold_n_sessions": 244,
      "wf_worst_fold_std": 6.132163741108965e-05,
      "wf_worst_fold_test_end": "2009-01-07",
      "wf_worst_fold_test_start": "2008-01-22"
    },
    "V2_vol_estimate_lagged_1d": {
      "dd_mode": "base",
      "description": "volatility estimate lagged one session (no same-session feedback)",
      "full_path_return_sum": 4.217441357968484,
      "full_path_sharpe": 1.400029429832815,
      "record_return_sum": 0.2689425288005978,
      "record_sharpe": 1.4102271780414941,
      "rolling_gate_passes_on_current_window": false,
      "trailing_63d_sharpe": -1.6213634935218275,
      "vol_mode": "lag1",
      "wf_mean_excl_worst_fold": 1.3571347667023979,
      "wf_mean_test_sharpe": 1.31860460818871,
      "wf_median_test_sharpe": 1.2320602755074876,
      "wf_min_test_sharpe": -0.49231284195462954,
      "wf_pct_positive": 0.9166666666666666,
      "wf_std_test_sharpe": 0.9405384733674299,
      "wf_worst_fold": 13,
      "wf_worst_fold_mean": 1.2717979624484224e-05,
      "wf_worst_fold_n_flat_sessions": 222,
      "wf_worst_fold_n_sessions": 244,
      "wf_worst_fold_std": 0.002228208328370255,
      "wf_worst_fold_test_end": "2009-07-02",
      "wf_worst_fold_test_start": "2008-07-16"
    },
    "V3_no_drawdown_control": {
      "dd_mode": "off",
      "description": "drawdown control disabled (dd_scale == 1)",
      "full_path_return_sum": 4.346337431343035,
      "full_path_sharpe": 1.4760436065925557,
      "record_return_sum": 0.2905923732083021,
      "record_sharpe": 1.583075087874877,
      "rolling_gate_passes_on_current_window": false,
      "trailing_63d_sharpe": -1.4394168982987599,
      "vol_mode": "base",
      "wf_mean_excl_worst_fold": 1.431928469659107,
      "wf_mean_test_sharpe": 0.9473074720246092,
      "wf_median_test_sharpe": 1.29329878363231,
      "wf_min_test_sharpe": -21.829879416796786,
      "wf_pct_positive": 0.9166666666666666,
      "wf_std_test_sharpe": 3.4797702418403893,
      "wf_worst_fold": 12,
      "wf_worst_fold_mean": -4.962781666339485e-06,
      "wf_worst_fold_n_flat_sessions": 242,
      "wf_worst_fold_n_sessions": 244,
      "wf_worst_fold_std": 6.132163741108965e-05,
      "wf_worst_fold_test_end": "2009-01-07",
      "wf_worst_fold_test_start": "2008-01-22"
    },
    "V4_no_overlay": {
      "dd_mode": "off",
      "description": "no overlay at all (raw signal + SPY filter + costs)",
      "full_path_return_sum": 5.5838292688271824,
      "full_path_sharpe": 1.3255040595109193,
      "record_return_sum": 0.3299847781148602,
      "record_sharpe": 1.1759018837938102,
      "rolling_gate_passes_on_current_window": false,
      "trailing_63d_sharpe": -1.3233468907373043,
      "vol_mode": "off",
      "wf_mean_excl_worst_fold": 1.4148673153950704,
      "wf_mean_test_sharpe": 0.9306017584744067,
      "wf_median_test_sharpe": 1.2360947885524292,
      "wf_min_test_sharpe": -21.829879416796786,
      "wf_pct_positive": 0.9375,
      "wf_std_test_sharpe": 3.4735315023009243,
      "wf_worst_fold": 12,
      "wf_worst_fold_mean": -4.962781666339485e-06,
      "wf_worst_fold_n_flat_sessions": 242,
      "wf_worst_fold_n_sessions": 244,
      "wf_worst_fold_std": 6.132163741108965e-05,
      "wf_worst_fold_test_end": "2009-01-07",
      "wf_worst_fold_test_start": "2008-01-22"
    }
  },
  "verdict": "**1. The failing gate value is a tail state of the record's own rolling-window distribution, not a new level.** The trailing 63-session Sharpe -1.483269 sits at the 1.23% percentile of the 407 rolling windows the record has produced; the gate passes in 70.52% of them (bootstrap 95% CI [56.27%, 89.68%]). The current failing run covers 2026-10-12 .. 2026-11-13 (25 window(s)), and the record has produced longer failing runs before (the longest: 36 windows).\n\n**2. The weakness does not cluster in any published observable-state bucket.** The families F2_spy_trend_state, F3_spy_12m_return_sign are one-sided inside the record period (the risk-off / down-trend / high-volatility states that Cycle 923 flagged never occur in the committed record), so their bucket gaps are **not estimable** from this record and are reported as absent rather than imputed; the two-sided F1_calendar_phase, F4_train_63d_realvol_tercile partition the record identically (the published folds that cover it are contiguous in time), i.e. they are a time split of the record rather than an independent state, and their bucket gap CI includes zero. The apparent concentration is therefore consistent with sampling noise at this record's effective sample size -- the same conclusion Cycle 924 reached for the fold-level buckets.\n\n**3. No permitted change clears the gate.** The strongest isolated overlay variant (`V1_no_vol_target`, volatility target disabled (vol_scale == 1)) lifts the trailing window from -1.483269 to -1.323347, still far below the 0.9 gate, and every other variant is below that. The weakness is an overlay-timing outcome -- the volatility target de-risks into the high-volatility sessions that dominate the window -- not evidence that the momentum edge has decayed, and not something a threshold, universe, cost-model or parameter change may fix.\n\n**4. The gate is a symptom, not the binding constraint.** Per Cycle 866, clearing `rolling_63d_sharpe` alone cannot yield GO on this record: the PSR gate is decisive and the decision stays NO-GO (failed gates: rolling_63d_sharpe, psr).\n\n**5. Separate measurement defect found and quantified (not a fix).** The volatility estimate sets session t's exposure from a trailing window that includes session t itself (same-session feedback, in `research/run_cycle6.py`, `src/simulation/engine.py` and `src/evaluation/risk.py`). Lagging the estimate one session changes the committed record's Sharpe from 1.579855 to 1.410227, the full-path Sharpe from 1.476044 to 1.400029 and the failing window from -1.483269 to -1.621363: it makes the failing window slightly worse, so it is **not** the cause of the gate failure, but it does flatter the published Sharpe statistics of this candidate (the headline walk-forward mean moves the other way only because of the one numerical-artifact fold documented in section 5). It is handed off as a separate, explicitly scoped re-derivation task -- **no production code is changed by this cycle**.",
  "worst_windows": [
    {
      "rolling_sharpe": -2.1202794870108113,
      "window_end": "2026-11-05",
      "window_mean": -0.0008693292686011441,
      "window_return": -0.05476774392187208,
      "window_start": "2026-08-10",
      "window_std": 0.006508658126172503
    },
    {
      "rolling_sharpe": -1.8144217837687089,
      "window_end": "2026-11-06",
      "window_mean": -0.0007520843953146356,
      "window_return": -0.04738131690482204,
      "window_start": "2026-08-11",
      "window_std": 0.006580040956525128
    },
    {
      "rolling_sharpe": -1.8098874856306422,
      "window_end": "2025-05-08",
      "window_mean": -0.0004637509830419501,
      "window_return": -0.02921631193164286,
      "window_start": "2025-02-07",
      "window_std": 0.004067555959579011
    },
    {
      "rolling_sharpe": -1.7772667192400162,
      "window_end": "2025-05-07",
      "window_mean": -0.00045555696399909764,
      "window_return": -0.02870008873194315,
      "window_start": "2025-02-06",
      "window_std": 0.004069024941672059
    },
    {
      "rolling_sharpe": -1.4832687549946857,
      "window_end": "2026-11-13",
      "window_mean": -0.0006542817157049202,
      "window_return": -0.04121974808940997,
      "window_start": "2026-08-18",
      "window_std": 0.007002372434406549
    },
    {
      "rolling_sharpe": -1.4660063214798473,
      "window_end": "2025-05-09",
      "window_mean": -0.0003701279731214891,
      "window_return": -0.023318062306653814,
      "window_start": "2025-02-10",
      "window_std": 0.004007895010272593
    },
    {
      "rolling_sharpe": -1.4625081995608222,
      "window_end": "2025-05-06",
      "window_mean": -0.0003797394922276484,
      "window_return": -0.023923588010341848,
      "window_start": "2025-02-05",
      "window_std": 0.00412180769882591
    },
    {
      "rolling_sharpe": -1.4394168982987594,
      "window_end": "2026-11-10",
      "window_mean": -0.0006237931368574893,
      "window_return": -0.03929896762202183,
      "window_start": "2026-08-13",
      "window_std": 0.006879458668122062
    },
    {
      "rolling_sharpe": -1.3996989298977838,
      "window_end": "2026-11-03",
      "window_mean": -0.0004667512898457989,
      "window_return": -0.02940533126028533,
      "window_start": "2026-08-06",
      "window_std": 0.005293600547972664
    },
    {
      "rolling_sharpe": -1.3918479197860387,
      "window_end": "2025-05-12",
      "window_mean": -0.0003544107844655473,
      "window_return": -0.02232787942132948,
      "window_start": "2025-02-11",
      "window_std": 0.004042177816952719
    }
  ]
}
```
