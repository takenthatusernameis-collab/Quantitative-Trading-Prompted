# CSMomentum Plateau-Gate Evaluation (csmomentum_001, Cycle 922)

## Summary

The C3 baseline was **already executed** (Cycle 13, `research/run_cycle13.py`) and its config-faithful gate table was published in Cycle 907; the candidate's label is unchanged. What was still open is the **last of the four pre-registered promotion gates**: the **parameter-plateau gate** (gate 4). This cycle evaluates it on the config-faithful month-end path, publishes the pre-registered 18-configuration grid on that path, and completes the multiple-testing record.

- Candidate: `csmomentum_001` (pre-registered baseline 252/21/0.5)
- Git rev: 9d610a9
- Frozen config SHA-256: `296a619f794262d05f2b00f044fbab706b4dbf3429e3ac3302282a66aa67f57f`
- Decision: **NO-GO** -- research label **Rejected/Failed**
- Failed gates: wf_mean_oos_sharpe

## 1. Method

The price panel is read **directly from the committed cache** (`data/raw/*.parquet`); the fetcher is never called, nothing is downloaded, and every file under `data/` and `config/` is SHA-256 fingerprinted before and after the run. The path is the **config-faithful month-end schedule** (`src/backtest/rebalance.py:build_month_end_weights`): the signal is formed on the last session of the calendar month, the positions become effective on the next session, the costs are the frozen 3 bps round trip on the weight changes and the signal lag is 1 day.

| Item | Value |
|---|---|
| Universe | 18 ETFs |
| Union sample | 1993-01-29 .. 2026-10-09 (8482 sessions, price width 1..18) |
| Common-inception slice (pre-registered evaluation sample) | 2006-02-06 .. 2026-10-09 (5202 sessions, price width 18..18) |
| Splits | train 1993-01-29..2009-12-31, validation 2010-01-04..2017-12-29, test 2018-01-02..2026-10-09 |
| Walk-forward | 10y train / 12m test / 6m step, 21d purge, 21d embargo, **fixed parameters** (no per-fold re-optimisation) |

## 2. Reproduction anchors

The tool fails closed if it does not reproduce the published config-faithful record of `research/reports/csmomentum_common_inception_gate_001.md`.

| Metric | Published | Observed | Tolerance | Result |
|---|---|---|---|---|
| `sharpe_backtest_scale` (union_path) | 0.4247 | 0.424692 | 1e-04 | MATCH |
| `sharpe_canonical` (union_path) | 0.6051 | 0.605113 | 1e-04 | MATCH |
| `max_drawdown` (union_path) | -0.4474 | -0.447353 | 1e-04 | MATCH |
| `annualized_turnover` (union_path) | 2.16 | 2.155081 | 1e-02 | MATCH |
| `trade_days` (union_path) | 232 | 232.000000 | 1e+00 | MATCH |
| `mean_positions` (union_path) | 7.56 | 7.559892 | 1e-02 | MATCH |
| `n_folds` (union_walk_forward) | 48 | 48.000000 | 1e+00 | MATCH |
| `mean_test_sharpe` (union_walk_forward) | 0.6975 | 0.697524 | 1e-04 | MATCH |
| `mean_test_sharpe_canonical` (union_walk_forward) | 0.8404 | 0.840389 | 1e-04 | MATCH |
| `median_test_sharpe` (union_walk_forward) | 0.6179 | 0.617881 | 1e-04 | MATCH |
| `pct_positive_sharpe` (union_walk_forward) | 0.7917 | 0.791667 | 1e-04 | MATCH |
| `total_test_trades` (union_walk_forward) | 400 | 400.000000 | 1e+00 | MATCH |
| `n_folds` (slice_walk_forward) | 21 | 21.000000 | 1e+00 | MATCH |
| `mean_test_sharpe` (slice_walk_forward) | 0.5861 | 0.586081 | 1e-04 | MATCH |
| `mean_test_sharpe_canonical` (slice_walk_forward) | 0.7577 | 0.757729 | 1e-04 | MATCH |
| `median_test_sharpe` (slice_walk_forward) | 0.6311 | 0.631134 | 1e-04 | MATCH |
| `pct_positive_sharpe` (slice_walk_forward) | 0.7619 | 0.761905 | 1e-04 | MATCH |
| `total_test_trades` (slice_walk_forward) | 166 | 166.000000 | 1e+00 | MATCH |

## 3. The pre-registered gate table (baseline 252/21/0.5)

| Gate | Threshold | Observed (union) | Result | Observed (common-inception slice) | Result |
|---|---|---|---|---|---|
| wf_mean_oos_sharpe | >= 0.9 | 0.6975 | FAIL | 0.5861 | FAIL |
| positive_fold_rate | >= 0.5 | 0.7917 | PASS | 0.7619 | PASS |
| pooled_oos_trades | > 100 | 400 | PASS | 166 | PASS |
| plateau | >= 2 of 3 lookbacks | 3 | PASS | 3 | PASS |

**Decision: NO-GO -- Rejected/Failed.** The pre-registered falsification condition (`research/hypotheses/csmomentum_001.md`: gate 1 or gate 2 fails) is met, so the candidate is rejected/failed. The plateau gate (gate 4) is now **EVALUATED** instead of NOT EVALUATED; it does not enter the falsification condition, so it does not change the verdict.

## 4. The parameter-plateau gate (gate 4)

- Baseline test Sharpe: **0.4878**; tolerance **0.1000** (`max(0.1, 10% x |baseline test Sharpe|)`)
- Lookbacks within tolerance: **3 of 3**
- Gate (">= 2 of 3 lookbacks"): **PASS**

| Lookback | Skip | Top fraction | Test Sharpe | Abs. diff | Within tolerance |
|---|---|---|---|---|---|
| 189 | 21 | 0.5 | 0.5186 | 0.0308 | yes |
| 252 (baseline) | 21 | 0.5 | 0.4878 | 0.0000 | yes |
| 315 | 21 | 0.5 | 0.4656 | 0.0222 | yes |

**Threshold-reading disclosure.** The hypothesis states the gate in the count form (">= 2 of 3 lookbacks"), which is what this tool applies. The frozen config expresses the same threshold as a fraction (`plateau_fraction_min: 0.667`); because 2/3 = 0.6667 rounds to 0.667, a literal `>=` comparison on the rounded fraction would demand 3 of 3 rather than 2 of 3. Both readings are published and they agree here: the observed fraction is 1.0000 (3 of 3), which passes under the literal fraction reading as well.

The gate is **invariant to the sample definition**: the test split lies entirely after the 252+21 warm-up ramp, so the union sample and the pre-registered common-inception slice measure the identical numbers (slice: 3 of 3 within 0.1000).

## 5. The pre-registered grid on the config-faithful path

All 18 unique pre-specified combinations (3 lookbacks x 2 skips x 3 top fractions) evaluated on the identical test split with the identical execution convention. The grid is **diagnostic**: the baseline is pre-specified and no configuration is selected on any of these results.

| Lookback | Skip | Top fraction | Train Sharpe | Val Sharpe | Test Sharpe | Test ann. ret. | Test max DD | Test trades | Test turnover | WF mean OOS Sharpe | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 315 | 42 | 0.3 | 0.3041 | 0.4671 | 0.6566 | 0.1307 | -0.2359 | 79 | 4.23 | 0.6939 | 1 |
| 189 | 42 | 0.3 | 0.3714 | 0.4181 | 0.5847 | 0.1207 | -0.2554 | 86 | 5.10 | 0.6996 | 2 |
| 189 | 21 | 0.7 | 0.3731 | 0.5785 | 0.5823 | 0.1127 | -0.2971 | 87 | 2.04 | 0.7189 | 3 |
| 252 | 21 | 0.3 | 0.4232 | 0.4836 | 0.5589 | 0.1151 | -0.2878 | 85 | 4.65 | 0.7261 | 4 |
| 189 | 42 | 0.7 | 0.3640 | 0.5785 | 0.5540 | 0.1090 | -0.2900 | 86 | 1.97 | 0.7370 | 5 |
| 189 | 42 | 0.5 | 0.4110 | 0.5245 | 0.5282 | 0.1083 | -0.2884 | 87 | 3.18 | 0.7368 | 6 |
| 315 | 42 | 0.5 | 0.3474 | 0.5848 | 0.5263 | 0.1081 | -0.2647 | 73 | 2.33 | 0.7325 | 7 |
| 189 | 21 | 0.5 | 0.4317 | 0.5856 | 0.5186 | 0.1036 | -0.2671 | 86 | 2.97 | 0.7395 | 8 |
| 315 | 21 | 0.3 | 0.3489 | 0.4005 | 0.5182 | 0.1069 | -0.2123 | 83 | 4.04 | 0.6503 | 9 |
| 252 | 21 | 0.7 | 0.3451 | 0.5458 | 0.5104 | 0.1031 | -0.3063 | 71 | 1.58 | 0.6941 | 10 |
| 252 | 21 | 0.5 | 0.3431 | 0.5691 | 0.4878 | 0.0999 | -0.2940 | 77 | 2.47 | 0.6975 | 11 |
| 315 | 21 | 0.7 | 0.3558 | 0.6021 | 0.4835 | 0.0990 | -0.2895 | 65 | 1.34 | 0.7236 | 12 |
| 315 | 42 | 0.7 | 0.3497 | 0.5882 | 0.4821 | 0.0989 | -0.2903 | 71 | 1.55 | 0.7177 | 13 |
| 189 | 21 | 0.3 | 0.4064 | 0.4369 | 0.4794 | 0.0976 | -0.2300 | 85 | 4.80 | 0.6654 | 14 |
| 315 | 21 | 0.5 | 0.3423 | 0.6168 | 0.4656 | 0.0976 | -0.2870 | 71 | 2.33 | 0.7121 | 15 |
| 252 | 42 | 0.7 | 0.3618 | 0.5411 | 0.4298 | 0.0934 | -0.3343 | 75 | 1.62 | 0.6885 | 16 |
| 252 | 42 | 0.5 | 0.3675 | 0.5342 | 0.4225 | 0.0938 | -0.3380 | 75 | 2.38 | 0.6747 | 17 |
| 252 | 42 | 0.3 | 0.3890 | 0.3843 | 0.3867 | 0.0895 | -0.3158 | 84 | 4.76 | 0.5917 | 18 |

### Robustness of the rejection across the pre-registered neighbourhood

- Configurations clearing gate 1 (walk-forward mean OOS Sharpe >= 0.9): **0 of 18**
- Baseline (252/21/0.5) walk-forward mean OOS Sharpe: **0.6975**
- Best configuration in the grid: (189, 21, 0.5) at **0.7395**

> diagnostic only: the pre-registered decision subject is the baseline (252, 21, 0.5); no configuration is selected on any of these results.

## 6. Multiple-testing control

- Deflated Sharpe Ratio at the **pre-registered trial count N=27** (primary, conservative): **0.1248** (DSR probability 0.5496); observed test Sharpe 0.6635, deflation threshold 0.6215, SE 0.3373, E[max of N] 1.8422
- Deflated Sharpe Ratio at the **actual evaluated count N=18** (disclosure; the pre-registration's label of 27 is a mislabel -- 3 x 2 x 3 yields 18 unique combinations, and no configuration was invented to reach 27): **0.3098** (DSR probability 0.6216)
- Probabilistic Sharpe Ratio vs SR=0: 0.9754 (empirical 0.9800); vs the 0.9 gate: 0.2417 (empirical 0.2240)
- Block-bootstrap Sharpe 95% CI: [0.0248, 1.3435]
- **Scale disclosure.** The DSR and PSR above use the repository's *current* Sharpe convention (`arithmetic_annualized_rf0`, unified in Cycle 861), on which the baseline's test-split Sharpe is 0.6635. The committed Cycle 13 record's DSR (**-0.6484** at N=27) was computed with the *pre*-Cycle-861 estimator (the backtest-baseline-scale Sharpe 0.4878 as the numerator), so the two numbers are **not comparable**. Reconstructed with the record's own estimator and the same bootstrap standard error, this path's DSR is **-0.3961** at N=27 and **-0.2111** at N=18 -- negative, i.e. on the record's own scale the observed test Sharpe does **not** survive the multiple-testing deflation either. The DSR is not part of the pre-registered falsification condition and does not enter the verdict.
- IS-OOS Spearman rank correlation: 0.0630; mean IS Sharpe 0.3686 vs mean OOS Sharpe 0.5098; 18 of 18 configurations have a positive test Sharpe; the best-IS configuration's test Sharpe is 0.5186
- Bootstrap settings: 1000 samples, block 22, seed 42 (the repository's own settings)

## 7. A measured disclosure: the selection breadth

The shared selection module (`src/features/momentum.py:select_top_decile`) holds every asset whose cross-sectional **rank** is >= max_rank x (1 - top_fraction) -- the rule documented in `research/hypotheses/sectorrotation_001.md` and used by every committed record. The boundary rank is inclusive, so at 18 assets and top_fraction 0.5 the rule holds the top **10 of 18** (55.6%) -- one asset more than the literal "top 50%" reading of the csmomentum hypothesis prose, which would be 9 of 18. Measured: over the full sample the held count runs from 0 to 10 (mean 7.57); over the test window it is 10 of 18 on every one of the 2205 sessions. The rule is applied identically to the baseline and to every configuration of the grid, so it does not bias the plateau comparison; it is disclosed here so that the published breadth cannot be misread as a different selection rule.

## 8. Checks

| Check | Result | Observed | Expected |
|---|---|---|---|
| `config_is_consumed_as_frozen` | PASS | {'lookback': 252, 'skip': 21, 'top_fraction': 0.5} | {'lookback': 252, 'skip': 21, 'top_fraction': 0.5} |
| `pre_registered_grid_still_declared_in_the_frozen_config` | PASS | lookback {189, 252, 315} x skip {21, 42} x top_fraction {0.3, 0.5, 0.7} | the grid literals of the frozen config's comment block |
| `pre_registered_trial_count_is_read_from_the_config` | PASS | 27 | 27 |
| `cost_model_matches_the_frozen_config` | PASS | 0.00030000000000000003 | 0.00030000000000000003 |
| `evaluation_window_ends_at_the_frozen_test_end` | PASS | 2026-10-09 | 2026-10-09 |
| `union_sample_reproduces_the_published_config_faithful_path` | PASS | {'sharpe_canonical': 0.6051131803909181, 'sharpe_backtest_scale': 0.4246924532684473, 'max_drawdown': -0.44735270979791464, 'annualized_turnover': 2.155081348738505, 'trade_days': 232, 'mean_positions': 7.559891535015327} | {'sharpe_backtest_scale': '0.4247', 'sharpe_canonical': '0.6051', 'max_drawdown': '-0.4474', 'annualized_turnover': '2.16', 'trade_days': '232', 'mean_positions': '7.56'} |
| `union_sample_reproduces_the_published_walk_forward` | PASS | {'n_folds': 48, 'mean_test_sharpe': 0.6975243375140185, 'median_test_sharpe': 0.6178806353181572, 'pct_positive_sharpe': 0.7916666666666666, 'total_test_trades': 400} | {'n_folds': '48', 'mean_test_sharpe': '0.6975', 'mean_test_sharpe_canonical': '0.8404', 'median_test_sharpe': '0.6179', 'pct_positive_sharpe': '0.7917', 'total_test_trades': '400'} |
| `common_inception_sample_reproduces_the_published_walk_forward` | PASS | {'n_folds': 21, 'mean_test_sharpe': 0.586080732009725, 'median_test_sharpe': 0.631133614003499, 'pct_positive_sharpe': 0.7619047619047619, 'total_test_trades': 166} | {'n_folds': '21', 'mean_test_sharpe': '0.5861', 'mean_test_sharpe_canonical': '0.7577', 'median_test_sharpe': '0.6311', 'pct_positive_sharpe': '0.7619', 'total_test_trades': '166'} |
| `plateau_measurement_is_invariant_to_the_sample_definition` | PASS | {'union_baseline_test_sharpe': 0.4878327876750592, 'slice_baseline_test_sharpe': 0.4878327876750592, 'union_n_within': 3, 'slice_n_within': 3} | the test split lies entirely after the warm-up ramp, so both samples measure the same gate |
| `selection_follows_the_documented_rank_rule` | PASS | {'rule': 'rank >= max_rank x (1 - top_fraction)', 'held_in_the_test_window': '10..10 of 18', 'mask_equals_the_documented_rule': True} | the mask is exactly the documented rank rule |
| `data_and_config_unchanged` | PASS | {'data': True, 'config': True} | {'data': True, 'config': True} |
| `committed_artifacts_unchanged` | PASS | [] | no committed artifact modified |
| `the_fetcher_is_never_called` | PASS | the tool's source carries no fetcher call | no fetcher call |
| `walk_forward_uses_fixed_parameters` | PASS | {'baseline_paths_built': 1, 'paths_built_in_total': 22, 'parameter': {'lookback': 252, 'skip': 21, 'top_fraction': 0.5}, 'folds': 48, 'note': 'the baseline path is built once and every fold is a slice of that one continuously computed point-in-time path, so no per-fold re-optimisation is possible'} | the baseline path is built exactly once and reused by every fold |
| `grid_size_is_the_pre_registered_unique_combination_count` | PASS | 18 | 18 |
| `plateau_gate_reading_is_disclosed` | PASS | {'count_form': '>= 2 of 3', 'n_within': 3, 'fraction': 1.0, 'config_fraction_threshold': 0.667, 'literal_fraction_reading_would_pass': True} | both readings published (2/3 = 0.6667 rounds to the config's 0.667) |

STRUCTURAL: PASS

## 9. Reproduction

```bash
python research/csmomentum_plateau_gate_eval.py
python -m pytest -q tests/test_csmomentum_plateau_gate_eval.py
git status --porcelain data/ config/
```

## 10. Provenance

- Data: the committed raw cache `data/raw/*.parquet`, read-only (the fetcher is never called; every file under `data/` and `config/` is SHA-256 fingerprinted before and after the run and compared).
- Committed artifacts used as the reproduction reference: `research/experiments/csmomentum_001_experiment_001.md`, `research/experiments/csmomentum_baseline_wf_001.md`, `research/experiments/csmomentum_common_inception_001.md`, `research/reports/month_end_candidate_reaudit_001.md`, `research/reports/csmomentum_common_inception_gate_001.md`, `research/reports/promotion_feasibility_backtest_001.md`, `research/hypotheses/csmomentum_001.md` (read-only, byte-identical before and after the run).
- Shared machinery: `src/backtest/rebalance.py` (month-end schedule), `src/features/momentum.py` (momentum, selection), `src/evaluation/walkforward.py` (fold calendar), `src/evaluation/statistics.py` (DSR/PSR), `src/backtest/engine.py` (cost parameters, metrics) -- all unchanged by this cycle.
- Gate thresholds, decision mapping, candidate configuration, cost model and Sharpe convention: unchanged. The plateau gate is now EVALUATED; no other gate is touched.
