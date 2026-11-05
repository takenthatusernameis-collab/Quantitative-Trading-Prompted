# Rolling 63d Sharpe Weakness Diagnosis of the Incumbent (tsmomentum_rolling63_weakness_diagnosis_001, Cycle 925)

## Summary

- Candidate: `tsmomentum_spytrend_001` (the incumbent)
- Sharpe convention: `arithmetic_annualized_rf0`
- Committed record: 463 sessions, 2025-01-02 .. 2026-11-05
- Trailing 63d Sharpe (gate under diagnosis): **-2.120279** vs gate 0.9 (FAIL); production decision **NO-GO** (failed gates: rolling_63d_sharpe, psr)
- Rolling windows on the record: 401 | gate base rate 71.5711% (287/401) | current value at percentile 0.25%
- Distribution: min -2.120279 | p10 -0.211884 | p25 0.518717 | median 1.877372 | p75 3.688758 | max 6.144063
- Read-only: `data/` and `config/` byte-identical before and after the run (**yes**); no committed artifact modified (**yes**).
- Data source: committed parquet cache in `data/raw/` and the committed paper-trading state; the fetcher is never called.
- No gate, threshold, parameter, universe, cost model, drift flag or verdict is changed by this tool.

## 1. Reproduction anchor (fail closed)

The trailing 63-session Sharpe of the committed record is reproduced three ways and the offline path is required to reproduce every committed session bit-for-bit. A mismatch fails the run and nothing is published.

| Quantity | Value |
|---|---|
| From the committed state file | -2.120279487011 |
| Stored `low_rolling_sharpe` drift flag | -2.1202794870108126 |
| Production `evaluate_go_no_go` gate table | -2.120279487011 (identical) |
| Offline recomputation of the strategy path | identical to 1e-12 |

### Overlay state realised on the committed record

| Quantity | Value |
|---|---|
| Sessions | 463 |
| Risk-off sessions (SPY trend filter fired, regime_exposure < 1) | **55** |
| Sessions with the drawdown overlay active (dd_scale < 1) | **0** |
| vol_scale range / mean | [0.4373, 1.0000] / 0.7492 |
| Positions held (min / max / mean) | 0 / 4 / 3.52 |

The volatility target was the only overlay that acted continuously (vol_scale between 0.4373 and 1.0000, mean 0.7492); the drawdown overlay never bound (0 sessions with dd_scale < 1) and the SPY trend filter fired on 55 of 463 sessions.

## 2. Distribution of the rolling 63d Sharpe on the committed record

| Statistic | Value |
|---|---|
| Windows | 401 |
| Minimum | -2.120279 |
| p05 | -0.865361 |
| p10 | -0.211884 |
| p25 | 0.518717 |
| Median | 1.877372 |
| Mean | 2.096560 |
| p75 | 3.688758 |
| p90 | 4.604665 |
| Maximum | 6.144063 |
| Std (ddof=1) | 1.854441 |

- Gate base rate on the record itself: **71.5711%** (287/401 windows at Sharpe >= 0.9); moving-block bootstrap 95% CI [57.3566%, 90.5299%] (2000 resamples over the rolling-window series in blocks of 21 windows, seed 925).
- Current value -2.120279 sits at percentile **0.25%** of the record's own rolling-window distribution (bootstrap 95% CI [1.25%, 98.25%]).
- Failing runs (lengths): [36, 25, 19, 11, 8, 7, 3, 2, 1, 1, 1]; the current run is **19 window(s)** covering 2026-10-12 .. 2026-11-05; the last passing window ended **2026-10-09** (19 windows ago).
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
| 19 window(s) | 2026-10-12 | 2026-11-05 |

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
| 2026-11 | 4 | -1.442715 | -2.120279 | 1.0000 |

### Worst 10 rolling windows

| Window | Rolling Sharpe | Window return | Window mean/day | Window std/day |
|---|---|---|---|---|
| 2026-08-10 .. 2026-11-05 | -2.120279 | -5.476774% | -0.086933% | 0.650866% |
| 2025-02-07 .. 2025-05-08 | -1.809887 | -2.921631% | -0.046375% | 0.406756% |
| 2025-02-06 .. 2025-05-07 | -1.777267 | -2.870009% | -0.045556% | 0.406902% |
| 2025-02-10 .. 2025-05-09 | -1.466006 | -2.331806% | -0.037013% | 0.400790% |
| 2025-02-05 .. 2025-05-06 | -1.462508 | -2.392359% | -0.037974% | 0.412181% |
| 2026-08-06 .. 2026-11-03 | -1.399699 | -2.940533% | -0.046675% | 0.529360% |
| 2025-02-11 .. 2025-05-12 | -1.391848 | -2.232788% | -0.035441% | 0.404218% |
| 2026-08-05 .. 2026-11-02 | -1.378443 | -2.897754% | -0.045996% | 0.529703% |
| 2025-01-24 .. 2025-04-24 | -1.333100 | -2.471766% | -0.039234% | 0.467202% |
| 2025-01-31 .. 2025-05-01 | -1.309711 | -2.227362% | -0.035355% | 0.428524% |

## 3. Overlap with the published folds' Cycle-923 buckets

Each rolling window is mapped onto the published walk-forward fold that contains its end date (the latest-starting fold when two overlap) and inherits that fold's Cycle-923 bucket labels. 289 of 401 windows fall inside a published fold's test window (folds [47, 48]); 112 fall outside every fold -- the last published fold (#48) ends its test window on 2026-05-28 -- and 169 windows fall inside two folds.

**Reading the two tests together.** The permutation p-value shuffles the bucket labels across the 401 windows and therefore treats them as independent observations; consecutive rolling windows overlap by 62 sessions, so that p-value is anticonservative by construction. The moving-block bootstrap CI on the bucket gap is the dependence-aware test and is the one the verdict uses.

### F1 calendar phase (published fold parity)

| Bucket | Windows | Mean rolling Sharpe | Median | Failing rate |
|---|---|---|---|---|
| phase_A | 47 | 0.228400 | -0.282805 | 0.7872 |
| phase_B | 242 | 3.147431 | 3.295418 | 0.0165 |
| no_fold | 112 | 0.609888 | 0.406404 | 0.6518 |

- Dispersion share (eta^2) over the 289 covered windows: 0.353830; permutation p-value (10000 permutations, seed 925): **0.000100**
- Bucket gap (phase_A - phase_B): -2.919032; moving-block bootstrap 95% CI [-4.506950, +1.061537] -- includes zero
- Non-overlapping windows only (dependence-free robustness check): phase_A n=1 mean 0.317668; phase_B n=4 mean 3.159897

### F2 SPY trend state at the fold's test-window start

| Bucket | Windows | Mean rolling Sharpe | Median | Failing rate |
|---|---|---|---|---|
| risk_on | 289 | 2.672710 | 2.943380 | 0.1419 |
| risk_off | 0 | not estimable (bucket absent in the record period) | - | - |
| no_fold | 112 | 0.609888 | 0.406404 | 0.6518 |

- **This family is one-sided inside the committed record**: only one of its buckets occurs, so its bucket gap is **not estimable** from this record (the absence is reported, not imputed).

- Dispersion share (eta^2) over the 289 covered windows: 0.000000; permutation p-value (10000 permutations, seed 925): **1.000000**
- Bucket gap: not estimable (one of the two buckets has no window in the record period)
- Non-overlapping windows only (dependence-free robustness check): risk_on n=5 mean 2.591451; risk_off n=0 mean N/A

### F3 SPY trailing 12-month return sign at the fold's test-window start

| Bucket | Windows | Mean rolling Sharpe | Median | Failing rate |
|---|---|---|---|---|
| up | 289 | 2.672710 | 2.943380 | 0.1419 |
| down | 0 | not estimable (bucket absent in the record period) | - | - |
| no_fold | 112 | 0.609888 | 0.406404 | 0.6518 |

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
| no_fold | 112 | 0.609888 | 0.406404 | 0.6518 |

- Dispersion share (eta^2) over the 289 covered windows: 0.353830; permutation p-value (10000 permutations, seed 925): **0.000100**
- Bucket gap (low_vol - med_vol): +2.919032; moving-block bootstrap 95% CI [-1.061537, +4.506950] -- includes zero
- Non-overlapping windows only (dependence-free robustness check): low_vol n=4 mean 3.159897; med_vol n=1 mean 0.317668; high_vol n=0 mean N/A

## 4. Correlation of the rolling Sharpe to market state

Spearman rank correlations between the rolling 63d Sharpe and window-level observable state, with moving-block bootstrap 95% CIs on the correlation.

| State variable | Windows | Spearman rho | 95% CI | Excludes zero |
|---|---|---|---|---|
| spy_ret_12m | 400 | -0.0140 | [-0.4035, +0.5632] | no |
| spy_rv_63 | 400 | -0.3857 | [-0.6597, +0.3782] | no |
| spy_sma_gap | 400 | 0.4514 | [-0.2004, +0.7126] | no |
| strategy_window_realised_vol | 401 | -0.1290 | [-0.6862, +0.3600] | no |

## 5. Isolated overlay counterfactuals (scratch paths, no production change)

Each variant is recomputed from the committed cache on a scratch path and evaluated on the trailing window, the committed record, the full path and the published 48-fold walk-forward. No production code is modified; this section is measurement, not a proposal to change the strategy.

| Variant | Trailing 63d Sharpe | Record Sharpe | Full-path Sharpe | WF mean OOS Sharpe | WF mean excl. worst fold | Clears gate? |
|---|---|---|---|---|---|---|
| V0_baseline | -0.872440 | 1.705935 | 1.483498 | 0.947307 | 1.431928 | no |
| V1_no_vol_target | -0.643454 | 1.304318 | 1.339127 | 0.930602 | 1.414867 | no |
| V2_vol_estimate_lagged_1d | -1.002801 | 1.569148 | 1.410069 | 1.318605 | 1.357135 | no |
| V3_no_drawdown_control | -0.872440 | 1.705935 | 1.483498 | 0.947307 | 1.431928 | no |
| V4_no_overlay | -0.643454 | 1.304318 | 1.334899 | 0.930602 | 1.414867 | no |

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
| Committed-record Sharpe | 1.494563 | 1.569148 |
| Committed-record return sum | +0.271334 | +0.284994 |
| Trailing 63d Sharpe | -2.120279 | -1.002801 |
| vol_scale range on the record | [0.4373, 1.0000] | [0.4373, 1.0000] |

This is a **measurement** finding, not a fix: lagging the estimate makes the failing window slightly worse, so it is not the cause of the gate failure, and it changes every published artifact of the candidate.

## 6. Verdict

**1. The failing gate value is a tail state of the record's own rolling-window distribution, not a new level.** The trailing 63-session Sharpe -2.120279 sits at the 0.25% percentile of the 401 rolling windows the record has produced; the gate passes in 71.57% of them (bootstrap 95% CI [57.36%, 90.53%]). The current failing run covers 2026-10-12 .. 2026-11-05 (19 window(s)), and the record has produced longer failing runs before (the longest: 36 windows).

**2. The weakness does not cluster in any published observable-state bucket.** The families F2_spy_trend_state, F3_spy_12m_return_sign are one-sided inside the record period (the risk-off / down-trend / high-volatility states that Cycle 923 flagged never occur in the committed record), so their bucket gaps are **not estimable** from this record and are reported as absent rather than imputed; the two-sided F1_calendar_phase, F4_train_63d_realvol_tercile partition the record identically (the published folds that cover it are contiguous in time), i.e. they are a time split of the record rather than an independent state, and their bucket gap CI includes zero. The apparent concentration is therefore consistent with sampling noise at this record's effective sample size -- the same conclusion Cycle 924 reached for the fold-level buckets.

**3. No permitted change clears the gate.** The strongest isolated overlay variant (`V1_no_vol_target`, volatility target disabled (vol_scale == 1)) lifts the trailing window from -2.120279 to -0.643454, still far below the 0.9 gate, and every other variant is below that. The weakness is an overlay-timing outcome -- the volatility target de-risks into the high-volatility sessions that dominate the window -- not evidence that the momentum edge has decayed, and not something a threshold, universe, cost-model or parameter change may fix.

**4. The gate is a symptom, not the binding constraint.** Per Cycle 866, clearing `rolling_63d_sharpe` alone cannot yield GO on this record: the PSR gate is decisive and the decision stays NO-GO (failed gates: rolling_63d_sharpe, psr).

**5. Separate measurement defect found and quantified (not a fix).** The volatility estimate sets session t's exposure from a trailing window that includes session t itself (same-session feedback, in `research/run_cycle6.py`, `src/simulation/engine.py` and `src/evaluation/risk.py`). Lagging the estimate one session changes the committed record's Sharpe from 1.494563 to 1.569148, the full-path Sharpe from 1.483498 to 1.410069 and the failing window from -2.120279 to -1.002801: it makes the failing window slightly worse, so it is **not** the cause of the gate failure, but it does flatter the published Sharpe statistics of this candidate (the headline walk-forward mean moves the other way only because of the one numerical-artifact fold documented in section 5). It is handed off as a separate, explicitly scoped re-derivation task -- **no production code is changed by this cycle**.

## 7. Checks

- [committed_record_loaded]: PASS (observed: 463 sessions, expected: > 63 sessions)
- [gate_threshold_read_from_config]: PASS (observed: 0.9, expected: 0.9)
- [trailing_63d_sharpe_matches_stored_drift_flag]: PASS (observed: -2.120279487011 vs stored -2.1202794870108126, expected: )
- [trailing_63d_sharpe_matches_production_gate_table]: PASS (observed: production -2.120279487011, expected: )
- [local_baseline_path_bit_identical_to_run_cycle6_overlay]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0 (bit-identical))
- [offline_path_reproduces_every_committed_session]: PASS (observed: max |diff| = 5.421e-20 over 462 sessions, expected: <= 1e-12)
- [offline_path_reproduces_trailing_63d_sharpe]: PASS (observed: -0.872439579425 vs -0.872439579425, expected: )
- [committed_record_run_history_matches_the_session_count]: PASS (observed: 463 entries, expected: 463)
- [rolling_window_count]: PASS (observed: 401 windows, expected: 401)
- [rolling_series_last_value_matches_production_sharpe]: PASS (observed: -2.120279487011, expected: )
- [bootstrap_is_deterministic]: PASS (observed: 2000 resamples, seed 925, expected: fixed seed)
- [published_fold_buckets_reused_from_cycle_923]: PASS (observed: 48 folds, expected: 48 folds)
- [bucket_family_F1_calendar_phase_absent_buckets_are_reported_not_estimable]: PASS (observed: n=[47, 242, 112], expected: every bucket either has windows or is reported as not estimable)
- [bucket_family_F2_spy_trend_state_absent_buckets_are_reported_not_estimable]: PASS (observed: n=[289, 0, 112], expected: every bucket either has windows or is reported as not estimable)
- [bucket_family_F3_spy_12m_return_sign_absent_buckets_are_reported_not_estimable]: PASS (observed: n=[289, 0, 112], expected: every bucket either has windows or is reported as not estimable)
- [bucket_family_F4_train_63d_realvol_tercile_absent_buckets_are_reported_not_estimable]: PASS (observed: n=[242, 47, 0, 112], expected: every bucket either has windows or is reported as not estimable)
- [counterfactual_baseline_reproduces_the_published_walk_forward]: PASS (observed: 0.947307, expected: 0.947307 (published))
- [drawdown_control_contributes_exactly_zero_on_this_record]: PASS (observed: V3 == V0 on the record, expected: )
- [no_counterfactual_variant_clears_the_rolling_gate]: PASS (observed: V0_baseline=-0.8724, V1_no_vol_target=-0.6435, V2_vol_estimate_lagged_1d=-1.0028, V3_no_drawdown_control=-0.8724, V4_no_overlay=-0.6435, expected: every variant below the 0.9 gate)
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
      "observed": "463 sessions",
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
      "observed": "-2.120279487011 vs stored -2.1202794870108126",
      "pass": true
    },
    {
      "expected": "",
      "name": "trailing_63d_sharpe_matches_production_gate_table",
      "observed": "production -2.120279487011",
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
      "observed": "max |diff| = 5.421e-20 over 462 sessions",
      "pass": true
    },
    {
      "expected": "",
      "name": "offline_path_reproduces_trailing_63d_sharpe",
      "observed": "-0.872439579425 vs -0.872439579425",
      "pass": true
    },
    {
      "expected": "463",
      "name": "committed_record_run_history_matches_the_session_count",
      "observed": "463 entries",
      "pass": true
    },
    {
      "expected": "401",
      "name": "rolling_window_count",
      "observed": "401 windows",
      "pass": true
    },
    {
      "expected": "",
      "name": "rolling_series_last_value_matches_production_sharpe",
      "observed": "-2.120279487011",
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
      "observed": "n=[47, 242, 112]",
      "pass": true
    },
    {
      "expected": "every bucket either has windows or is reported as not estimable",
      "name": "bucket_family_F2_spy_trend_state_absent_buckets_are_reported_not_estimable",
      "observed": "n=[289, 0, 112]",
      "pass": true
    },
    {
      "expected": "every bucket either has windows or is reported as not estimable",
      "name": "bucket_family_F3_spy_12m_return_sign_absent_buckets_are_reported_not_estimable",
      "observed": "n=[289, 0, 112]",
      "pass": true
    },
    {
      "expected": "every bucket either has windows or is reported as not estimable",
      "name": "bucket_family_F4_train_63d_realvol_tercile_absent_buckets_are_reported_not_estimable",
      "observed": "n=[242, 47, 0, 112]",
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
      "observed": "V0_baseline=-0.8724, V1_no_vol_target=-0.6435, V2_vol_estimate_lagged_1d=-1.0028, V3_no_drawdown_control=-0.8724, V4_no_overlay=-0.6435",
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
        -0.4035396765789772,
        0.5631955649328477
      ],
      "excludes_zero": false,
      "n": 400,
      "spearman": -0.013959837248982806,
      "variable": "spy_ret_12m"
    },
    {
      "ci95": [
        -0.6596665096180881,
        0.3781642618598212
      ],
      "excludes_zero": false,
      "n": 400,
      "spearman": -0.38567847299045616,
      "variable": "spy_rv_63"
    },
    {
      "ci95": [
        -0.20038155877698569,
        0.7126339961360773
      ],
      "excludes_zero": false,
      "n": 400,
      "spearman": 0.4514068212926331,
      "variable": "spy_sma_gap"
    },
    {
      "ci95": [
        -0.686150718559475,
        0.35998668336593526
      ],
      "excludes_zero": false,
      "n": 401,
      "spearman": -0.12898853612238062,
      "variable": "strategy_window_realised_vol"
    }
  ],
  "cycle": "925",
  "data_source": "committed parquet cache in data/raw/ and the committed paper-trading state (fetcher never called)",
  "distribution": {
    "base_rate": 0.71571072319202,
    "base_rate_ci95": [
      0.57356608478803,
      0.9052992518703239
    ],
    "current": -2.1202794870108113,
    "current_failing_run": 19,
    "current_failing_run_detail": {
      "first_window_end": "2026-10-12",
      "last_window_end": "2026-11-05",
      "length": 19
    },
    "current_percentile_rank": 0.0024937655860349127,
    "current_rank_ci95": [
      0.012468827930174564,
      0.9825436408977556
    ],
    "failing_runs": [
      36,
      25,
      19,
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
        "last_window_end": "2026-11-05",
        "length": 19
      }
    ],
    "last_passing_window_end": "2026-10-09",
    "max": 6.14406336732776,
    "mean": 2.0965602070112763,
    "median": 1.877372464699826,
    "min": -2.1202794870108113,
    "n_fail": 114,
    "n_pass": 287,
    "n_windows": 401,
    "p05": -0.8653608629989898,
    "p10": -0.21188351222842974,
    "p25": 0.5187173137963188,
    "p75": 3.688757944598669,
    "p90": 4.604665232373154,
    "recovery_lag_max": 36,
    "recovery_lag_mean": 11.926315789473684,
    "recovery_lag_median": 9.0,
    "std": 1.8544407803623473,
    "windows_since_last_pass": 19
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
          "fail_rate": 0.6517857142857143,
          "mean_rolling_sharpe": 0.609887961981163,
          "median_rolling_sharpe": 0.4064043209675955,
          "n": 112
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
          "fail_rate": 0.6517857142857143,
          "mean_rolling_sharpe": 0.609887961981163,
          "median_rolling_sharpe": 0.4064043209675955,
          "n": 112
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
          "fail_rate": 0.6517857142857143,
          "mean_rolling_sharpe": 0.609887961981163,
          "median_rolling_sharpe": 0.4064043209675955,
          "n": 112
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
          "fail_rate": 0.6517857142857143,
          "mean_rolling_sharpe": 0.609887961981163,
          "median_rolling_sharpe": 0.4064043209675955,
          "n": 112
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
    "n_windows_without_a_fold": 112
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
      "mean_rolling_sharpe": -1.4427152193189081,
      "min_rolling_sharpe": -2.1202794870108113,
      "month": "2026-11",
      "n": 4
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
    "full_period_sharpe": 1.4945625492186219,
    "last_session": "2026-11-05",
    "n_sessions": 463,
    "overlay_state": {
      "n_drawdown_overlay_sessions": 0,
      "n_positions_max": 4,
      "n_positions_mean": 3.524838012958963,
      "n_positions_min": 0,
      "n_risk_off_sessions": 55,
      "n_run_history": 463,
      "vol_scale_max": 1.0,
      "vol_scale_mean": 0.7491946963036896,
      "vol_scale_min": 0.43731674589035896
    },
    "production_decision": "NO-GO",
    "production_failed_gates": [
      "rolling_63d_sharpe",
      "psr"
    ],
    "stored_drift_flag": -2.1202794870108126,
    "trailing_63d_sharpe": -2.1202794870108126
  },
  "same_session_feedback": {
    "record_return_sum_base": 0.27133424769749737,
    "record_return_sum_lagged": 0.28499351579479415,
    "record_sharpe_base": 1.4945625492186219,
    "record_sharpe_lagged": 1.569148003802638,
    "trailing_63d_base": -2.1202794870108126,
    "trailing_63d_lagged": -1.00280081005823,
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
      "full_path_return_sum": 4.356968840601184,
      "full_path_sharpe": 1.4834980805013829,
      "record_return_sum": 0.3012237824664511,
      "record_sharpe": 1.7059348900291404,
      "rolling_gate_passes_on_current_window": false,
      "trailing_63d_sharpe": -0.872439579425076,
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
      "full_path_return_sum": 5.615293057924518,
      "full_path_sharpe": 1.33912742458811,
      "record_return_sum": 0.34710752154191016,
      "record_sharpe": 1.3043176999228907,
      "rolling_gate_passes_on_current_window": false,
      "trailing_63d_sharpe": -0.6434535005954656,
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
      "full_path_return_sum": 4.233492344962681,
      "full_path_sharpe": 1.4100689099632386,
      "record_return_sum": 0.28499351579479415,
      "record_sharpe": 1.569148003802638,
      "rolling_gate_passes_on_current_window": false,
      "trailing_63d_sharpe": -1.00280081005823,
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
      "full_path_return_sum": 4.356968840601184,
      "full_path_sharpe": 1.4834980805013829,
      "record_return_sum": 0.3012237824664511,
      "record_sharpe": 1.7059348900291404,
      "rolling_gate_passes_on_current_window": false,
      "trailing_63d_sharpe": -0.872439579425076,
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
      "full_path_return_sum": 5.600952012254232,
      "full_path_sharpe": 1.33489877823927,
      "record_return_sum": 0.34710752154191016,
      "record_sharpe": 1.3043176999228907,
      "rolling_gate_passes_on_current_window": false,
      "trailing_63d_sharpe": -0.6434535005954656,
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
  "verdict": "**1. The failing gate value is a tail state of the record's own rolling-window distribution, not a new level.** The trailing 63-session Sharpe -2.120279 sits at the 0.25% percentile of the 401 rolling windows the record has produced; the gate passes in 71.57% of them (bootstrap 95% CI [57.36%, 90.53%]). The current failing run covers 2026-10-12 .. 2026-11-05 (19 window(s)), and the record has produced longer failing runs before (the longest: 36 windows).\n\n**2. The weakness does not cluster in any published observable-state bucket.** The families F2_spy_trend_state, F3_spy_12m_return_sign are one-sided inside the record period (the risk-off / down-trend / high-volatility states that Cycle 923 flagged never occur in the committed record), so their bucket gaps are **not estimable** from this record and are reported as absent rather than imputed; the two-sided F1_calendar_phase, F4_train_63d_realvol_tercile partition the record identically (the published folds that cover it are contiguous in time), i.e. they are a time split of the record rather than an independent state, and their bucket gap CI includes zero. The apparent concentration is therefore consistent with sampling noise at this record's effective sample size -- the same conclusion Cycle 924 reached for the fold-level buckets.\n\n**3. No permitted change clears the gate.** The strongest isolated overlay variant (`V1_no_vol_target`, volatility target disabled (vol_scale == 1)) lifts the trailing window from -2.120279 to -0.643454, still far below the 0.9 gate, and every other variant is below that. The weakness is an overlay-timing outcome -- the volatility target de-risks into the high-volatility sessions that dominate the window -- not evidence that the momentum edge has decayed, and not something a threshold, universe, cost-model or parameter change may fix.\n\n**4. The gate is a symptom, not the binding constraint.** Per Cycle 866, clearing `rolling_63d_sharpe` alone cannot yield GO on this record: the PSR gate is decisive and the decision stays NO-GO (failed gates: rolling_63d_sharpe, psr).\n\n**5. Separate measurement defect found and quantified (not a fix).** The volatility estimate sets session t's exposure from a trailing window that includes session t itself (same-session feedback, in `research/run_cycle6.py`, `src/simulation/engine.py` and `src/evaluation/risk.py`). Lagging the estimate one session changes the committed record's Sharpe from 1.494563 to 1.569148, the full-path Sharpe from 1.483498 to 1.410069 and the failing window from -2.120279 to -1.002801: it makes the failing window slightly worse, so it is **not** the cause of the gate failure, but it does flatter the published Sharpe statistics of this candidate (the headline walk-forward mean moves the other way only because of the one numerical-artifact fold documented in section 5). It is handed off as a separate, explicitly scoped re-derivation task -- **no production code is changed by this cycle**.",
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
    },
    {
      "rolling_sharpe": -1.3784428809419638,
      "window_end": "2026-11-02",
      "window_mean": -0.0004599609592717992,
      "window_return": -0.028977540434123348,
      "window_start": "2026-08-05",
      "window_std": 0.005297030415363836
    },
    {
      "rolling_sharpe": -1.3331004632311612,
      "window_end": "2025-04-24",
      "window_mean": -0.000392343858876241,
      "window_return": -0.024717663109203182,
      "window_start": "2025-01-24",
      "window_std": 0.004672015235043651
    },
    {
      "rolling_sharpe": -1.3097113809647982,
      "window_end": "2025-05-01",
      "window_mean": -0.00035354955446028003,
      "window_return": -0.02227362193099764,
      "window_start": "2025-01-31",
      "window_std": 0.004285238156289927
    }
  ]
}
```
