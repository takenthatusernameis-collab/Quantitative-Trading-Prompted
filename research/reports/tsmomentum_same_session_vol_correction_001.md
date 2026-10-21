# Same-session volatility estimate: opt-in correction and side-by-side re-derivation for the incumbent (tsmomentum_same_session_vol_correction_001, Cycle 926)

## Summary

- Candidate: `tsmomentum_spytrend_001` (the incumbent)
- Sharpe convention: `arithmetic_annualized_rf0`
- Anchor: the published 48-fold walk-forward mean OOS Sharpe **0.947307** is reproduced from the committed cache (published: 0.947307), and the committed record's 450 sessions are reproduced with max |diff| = 5.421e-20.
- Default path: **bit-identical** to the pre-change implementation (max |diff| = 0.0e+00 research path, 0.0e+00 simulation path, 0.0e+00 risk overlays).
- Switch: `lag_vol_estimate` (default **off**), available in the shared risk helpers, the simulation engine and the published research path.
- Record on the corrected path: canonical Sharpe 1.771084 -> 1.635705, trailing 63-session Sharpe -0.448918 -> -0.515807, PSR vs 1.4178 0.695606 -> 0.623929.
- Decision: **unchanged** -- NO-GO on the published path and NO-GO on the corrected path (failed gates: rolling_63d_sharpe, psr).
- Read-only: `data/` and `config/` byte-identical before and after the run (**yes**); no committed artifact modified (**yes**); the published walk-forward record and the committed paper-trading state are **not** overwritten.
- Data source: committed parquet cache in `data/raw/` and the committed paper-trading state; the fetcher is never called.
- No gate, threshold, universe, cost model, Sharpe convention, parameter, hypothesis or drift flag is changed by this tool, and no candidate is promoted, re-fit or re-ranked.

## 1. The defect and the switch

The committed volatility target sets the exposure of session *t* from a realised-volatility estimate whose trailing 63-session window **includes session t itself**: today's own return moves today's exposure. The switch `lag_vol_estimate` (default **off**) computes the estimate from sessions up to and including *t-1* only.

| Entry point | Switch | Default |
|---|---|---|
| `src/evaluation/risk.py::realized_vol_scale` | `lag_vol_estimate` | `False` |
| `src/evaluation/risk.py::volatility_target_overlay` | `lag_vol_estimate` | `False` |
| `src/evaluation/risk.py::combined_risk_overlay` | `lag_vol_estimate` | `False` |
| `src/evaluation/risk.py::run_risk_overlays` | `lag_vol_estimate` | `False` |
| `src/evaluation/risk.py::run_combined_risk_overlays` | `lag_vol_estimate` | `False` |
| `src/simulation/engine.py::SimulationConfig.lag_vol_estimate` | `lag_vol_estimate` | `False` |
| `src/simulation/engine.py::_target_weights` | `lag_vol_estimate` | `False` |
| `src/simulation/paper_trading.py::PaperTradingConfig.from_paper_config_yaml` | `lag_vol_estimate` | `False` |
| `research/run_cycle6.py::_apply_overlay` | `lag_vol_estimate` | `False` |
| `research/run_cycle6.py::_eval_candidate` | `lag_vol_estimate` | `False` |
| `research/run_cycle6.py::_eval_candidate_period` | `lag_vol_estimate` | `False` |
| `research/run_cycle6.py::run_walkforward` | `lag_vol_estimate` | `False` |

Semantics: When True the realised-volatility estimate for session t is computed from sessions up to and including t-1 only (no same-session feedback). When False (the default) the trailing 63-session window includes session t, which is the committed behaviour. The lagged scale is exactly the same-session scale shifted one session (max |diff| = 0.0e+00), and the default scale is bit-identical to the committed inline computation. No config file sets the switch (0 file(s) mention it), and the default value is a code default, not a config-file edit.

## 2. Reproduction anchor (fail closed)

Nothing is published unless the default path reproduces the incumbent's published artefacts. A mismatch fails the run.

| Quantity | Published | Reproduced |
|---|---|---|
| 48-fold walk-forward mean OOS Sharpe | 0.947307 | 0.947307 |
| Same, from the published machinery (`research/run_cycle6.py::run_walkforward`) | 0.947307 | 0.947307 |
| Folds | 48 | 48 |
| Committed record sessions | 450 | 450 (max abs diff = 5.421e-20) |

The published record is resolved **by content** (the committed file that carries the published aggregate and fold tables), and all 48 published folds are reproduced: test windows exactly, OOS Sharpe to the published precision and trade counts exactly.

## 3. Default-path bit-identity

Each default-path result is compared with a **frozen copy of the pre-change implementation** (kept in the tool and in the test file), so the guarantee is checked, not asserted.

| Code path | max abs diff | Required |
|---|---|---|
| `research/run_cycle6.py::_apply_overlay` (net returns) | 0.0e+00 | 0.0 |
| `research/run_cycle6.py::_apply_overlay` (combined weights) | 0.0e+00 | 0.0 |
| `src/simulation/engine.py::_target_weights` (weights + vol_scale) | 0.0e+00 | 0.0 |
| `src/evaluation/risk.py` (both overlay helpers) | 0.0e+00 | 0.0 |

## 4. Side-by-side re-derivation

### 4.1 The published walk-forward record

| Statistic | Published (default path) | Corrected path |
|---|---|---|
| Folds | 48 | 48 |
| Mean OOS Sharpe (all folds) | 0.947307 | 1.318605 |
| Mean OOS Sharpe excl. the numerical-artefact fold | 1.431928 | 1.346660 |
| Mean OOS Sharpe excl. that path's own worst fold | 1.431928 | 1.357135 |
| Median OOS Sharpe | 1.293299 | 1.232060 |
| Std OOS Sharpe | 3.479770 | 0.940538 |
| Min OOS Sharpe | -21.829879 | -0.492313 |
| Max OOS Sharpe | 3.912105 | 3.912105 |
| Positive folds | 91.67% | 91.67% |
| Pooled OOS trades | 6013 | 6002 |

The default path's minimum fold is fold 12 (2008-01-22 .. 2009-01-07, OOS Sharpe -21.829879) -- the numerical artefact documented in Cycle 925 section 5. The published per-fold Sharpe is computed on the **backtest-baseline scale** (`(CAGR - 2%) / annualised volatility`, `src/backtest/engine.py::compute_metrics`), and on this fold that estimator divides a near-zero numerator by a near-zero denominator: **242 of 244 sessions are flat**, the segment's mean daily return is -4.963e-06 and its dispersion 6.132e-05. On the corrected path the same segment is **244 of 244 sessions flat** (zero dispersion), which the estimator returns as 0.000000 and the corrected path's own worst fold is fold 13 (-0.492313). **The corrected path's higher all-fold mean is therefore a zero replacing a pathology, not a better strategy**: on the strictest comparable statistic (both paths with the same fold 12 excluded) the corrected path is **lower** (1.346660 vs 1.431928), and so is each path's mean excluding its own worst fold (1.357135 vs 1.431928).

### 4.2 The committed paper-trading record

| Statistic | Published (default path) | Corrected path |
|---|---|---|
| Sessions | 450 | 450 |
| Canonical Sharpe | 1.771084 | 1.635705 |
| Trailing 63-session Sharpe (`rolling_63d_sharpe` gate value) | -0.448918 | -0.515807 |
| `rolling_63d_sharpe` gate (>= 0.9) | **FAIL** | **FAIL** |
| PSR (normal) vs 1.4178 | 0.695606 | 0.623929 |
| PSR (empirical) vs 1.4178 | 0.742000 | 0.676000 |
| PSR Sharpe SE | 0.690271 | 0.689975 |
| Max drawdown | -4.985740% | -5.105675% |
| `psr` gate (>= 0.95) | **FAIL** | **FAIL** |

PSR settings (the repository's own): `n_bootstrap=1000`, `block_size=22`, `seed=20240101`, target 1.4178.

### 4.3 The production promotion-gate table

| Gate | Published record | Corrected record | Threshold |
|---|---|---|---|
| `track_record_length` | 450.000000 | 450.000000 | >= 126 |
| `full_period_sharpe` | 1.771084 | 1.635705 | >= 0.9 |
| `rolling_63d_sharpe` | -0.448918 | -0.515807 | >= 0.9 |
| `max_drawdown` | -0.049857 | -0.051057 | >= -0.15 |
| `rolling_63d_max_dd` | -0.038564 | -0.039642 | >= -0.15 |
| `regime_flips` | 6.000000 | 6.000000 | >= 1 |
| `psr` | 0.695606 | 0.623929 | >= 0.95 |
| **decision** | **NO-GO** | **NO-GO** | failed gates: rolling_63d_sharpe, psr |

The corrected record's gate table is computed by the production code (`src/simulation/evaluation.py::evaluate_go_no_go`) on the corrected return series with the committed configuration; only the return series and the dates are substituted, because the promotion gates consume only the returns, the dates, the run-history turnover and the run-history regime exposure.

### 4.4 The PSR reference a corrected live record would face

The `psr` gate compares the live record's Sharpe with a **fixed backtest-baseline Sharpe of 1.4178**, which was measured on the **2018-2026 test period of the same-session path** (`research/run_cycle7.py::DOCUMENTED`). A live record produced on the corrected path would be measured against a reference computed on a different path, so the corrected equivalent of that reference is measured here, on the published **Cycle 7 data vintage** (panel truncated at 2026-10-09; the committed cache now extends 8 sessions further, which is why the published vintage is the reproducible one).

| Test-period statistic (2018-2026) | Published (same-session) | Corrected |
|---|---|---|
| Sharpe (the backtest-baseline scale) | 1.417752 | 1.335983 |
| Max drawdown | -0.077940 | -0.079543 |
| Trade count | 1196 | 1194 |
| Annualized return | 0.144648 | 0.139767 |
| Annualized turnover | 13.3206 | 13.3534 |
| Annualized volatility | 0.087919 | 0.089647 |

The published test-period reference **1.417752** is reproduced together with all 8 documented values of `research/run_cycle7.py::DOCUMENTED` (max DD -0.077940, 1196 trades, annualized return 0.144648). The corrected path's test-period Sharpe is **1.335983**, i.e. -0.081769 against the same-session path. A live record on the corrected path compared against the *unchanged* reference 1.4178 would therefore face a **stricter** bar than its own path's backtest -- the comparison stays conservative -- while compared against its own path's reference it would face the honest one. The fixed reference 1.4178 is **not** restated by this cycle: changing a gate target is a promotion decision and is out of scope here.

## 5. Blast radius

### 5.1 Code paths that use the same-session estimate

| Path | Kind | Role | State after this cycle |
|---|---|---|---|
| `src/evaluation/risk.py::volatility_target_overlay` | shared code | volatility-target overlay helper | opt-in switch added (lag_vol_estimate, default off) |
| `src/evaluation/risk.py::combined_risk_overlay` | shared code | combined volatility + drawdown overlay helper | opt-in switch added (lag_vol_estimate, default off) |
| `src/simulation/engine.py::_target_weights` | shared code | simulation engine / live paper-trading path | opt-in switch added (SimulationConfig.lag_vol_estimate, default off) |
| `research/run_cycle6.py::_apply_overlay` | research script | published research path of the incumbent (the published walk-forward record) | opt-in switch added (lag_vol_estimate, default off) |
| `research/run_cycle5.py` | research script | Cycle 5 candidate path of the incumbent | not changed (same-session estimate still used) |
| `research/run_cycle13.py` | research script | csmomentum_001 candidate path | not changed (same-session estimate still used) |
| `research/run_cycle15.py, research/run_cycle15_c4_corrected.py` | research script | csmomentum_001 candidate paths | not changed (same-session estimate still used) |
| `research/run_cycle18.py, research/run_cycle19.py` | research script | csmomentum_001 / macroregime_001 candidate paths | not changed (same-session estimate still used) |
| `research/run_cycle3.py, research/run_cycle4.py` | research script | consumers of the shared overlay helpers (no inline estimate of their own) | already routed through src/evaluation/risk.py (they inherit the switch) |
| `research/month_end_candidate_reaudit.py` | research script | config-faithful month-end re-audit of csmomentum_001 | not changed (same-session estimate still used) |
| `research/tsmomentum_rolling63_weakness_diagnosis.py::overlay_variant` | research script | Cycle 925 diagnosis (already carried a scratch lag-1 variant) | not changed (measurement only, scratch paths) |
| `research/trailing_window_attribution.py` | research script | consumes the simulation engine's vol_scale (indirect dependency) | not changed (inherits the engine's default) |

### 5.2 Committed artefacts that quote the affected statistics

Measured by searching the committed tree for the published numeric markers, so the inventory cannot drift from the repository's content: 66 distinct committed files quote at least one of them.

| Marker | Statistic | Committed files quoting it |
|---|---|---|
| `0.9473` | published 48-fold walk-forward mean OOS Sharpe | 56 |
| `1.771084` | committed record's canonical Sharpe | 12 |
| `0.448918` | committed record's trailing 63-session Sharpe (drift flag) | 18 |
| `1.486941` | full-path Sharpe of the committed record's path | 7 |

- `0.9473` (published 48-fold walk-forward mean OOS Sharpe):
  - `README.md`
  - `config/simulation_candidate_001.yaml`
  - `research/cost_admissibility_screen.py`
  - `research/cost_gate_break_even_audit.py`
  - `research/experiments/cost_admissibility_screen_001.md`
  - `research/experiments/cost_gate_break_even_001.md`
  - `research/experiments/csmomentum_baseline_wf_001.md`
  - `research/experiments/incumbent_phase_stability_001.md`
  - `research/experiments/tsmomentum_fold_regime_attribution_001.md`
  - `research/experiments/tsmomentum_fold_regime_bootstrap_ci_001.md`
  - `research/experiments/tsmomentum_fold_sensitivity_001.md`
  - `research/experiments/tsmomentum_phase_stability_fix_001.md`
  - `research/experiments/tsmomentum_regime_filter_wf_001.md`
  - `research/experiments/tsmomentum_rolling63_weakness_diagnosis_001.md`
  - `research/experiments/tsmomentum_same_session_vol_correction_001.md`
  - `research/experiments/tsmomentum_sma175_decision_001.md`
  - `research/experiments/tsmomentum_sma175_validation_001.md`
  - `research/experiments/tsmomentum_walkforward_embargo_001.md`
  - `research/experiments/tsmomentum_walkforward_mean_robustness_001.md`
  - `research/hypotheses/macroregime_001.md`
  - `research/incumbent_phase_stability_audit.py`
  - `research/reports/cost_admissibility_screen_001.md`
  - `research/reports/cost_gate_break_even_001.md`
  - `research/reports/cross_momentum_consolidation.md`
  - `research/reports/deployment_dossier_001.md`
  - `research/reports/go_nogo_evaluation_001.md`
  - `research/reports/incumbent_phase_stability_001.md`
  - `research/reports/opportunity_shortlist.md`
  - `research/reports/paper_trading_validation_001.md`
  - `research/reports/paper_trading_validation_002.md`
  - `research/reports/paper_trading_validation_003.md`
  - `research/reports/simulation_verification_001.md`
  - `research/reports/tsmomentum_fold_phase_decision_001.md`
  - `research/reports/tsmomentum_fold_regime_attribution_001.md`
  - `research/reports/tsmomentum_fold_regime_bootstrap_ci_001.md`
  - `research/reports/tsmomentum_fold_sensitivity_001.md`
  - `research/reports/tsmomentum_phase_stability_fix_001.md`
  - `research/reports/tsmomentum_rolling63_weakness_diagnosis_001.md`
  - `research/reports/tsmomentum_same_session_vol_correction_001.md`
  - `research/reports/tsmomentum_sma175_decision_001.md`
  - `research/reports/tsmomentum_sma175_phase_stability_001.md`
  - `research/reports/tsmomentum_sma175_validation_001.md`
  - `research/reports/tsmomentum_vol_estimate_consolidation_001.md`
  - `research/reports/tsmomentum_vol_estimate_consolidation_001_rerun.md`
  - `research/reports/tsmomentum_walkforward_embargo_001.md`
  - `research/reports/tsmomentum_walkforward_mean_robustness_001.md`
  - `research/run_cycle11.py`
  - `research/run_cycle7.py`
  - `research/tsmomentum_fold_regime_attribution.py`
  - `research/tsmomentum_fold_regime_bootstrap_ci.py`
  - `research/tsmomentum_fold_sensitivity_audit.py`
  - `research/tsmomentum_phase_stability_fix_audit.py`
  - `research/tsmomentum_rolling63_weakness_diagnosis.py`
  - `research/tsmomentum_same_session_vol_correction.py`
  - `research/tsmomentum_walkforward_embargo_audit.py`
  - `research/tsmomentum_walkforward_mean_robustness_audit.py`
- `1.771084` (committed record's canonical Sharpe):
  - `README.md`
  - `research/experiments/tsmomentum_rolling63_weakness_diagnosis_001.md`
  - `research/experiments/tsmomentum_same_session_vol_correction_001.md`
  - `research/reports/paper_trading_validation_535.md`
  - `research/reports/psr_continuation_horizon_001.md`
  - `research/reports/reference_sample_invariance_001.md`
  - `research/reports/sample_definition_hygiene_001.md`
  - `research/reports/tsmomentum_rolling63_weakness_diagnosis_001.md`
  - `research/reports/tsmomentum_same_session_vol_correction_001.md`
  - `research/reports/tsmomentum_vol_estimate_consolidation_001.md`
  - `research/reports/tsmomentum_vol_estimate_consolidation_001_rerun.md`
  - `research/tsmomentum_same_session_vol_correction.py`
- `0.448918` (committed record's trailing 63-session Sharpe (drift flag)):
  - `README.md`
  - `data/processed/paper_trading_state.yaml`
  - `research/experiments/tsmomentum_rolling63_weakness_diagnosis_001.md`
  - `research/experiments/tsmomentum_same_session_vol_correction_001.md`
  - `research/experiments/tsmomentum_sma175_promotion_gate_eval_001.md`
  - `research/reports/long_sample_overlay_attribution_001.json`
  - `research/reports/long_sample_overlay_attribution_001.md`
  - `research/reports/opportunity_shortlist.md`
  - `research/reports/paper_trading_rolling.md`
  - `research/reports/paper_trading_validation_535.md`
  - `research/reports/reference_sample_invariance_001.md`
  - `research/reports/sample_definition_hygiene_001.md`
  - `research/reports/tsmomentum_rolling63_weakness_diagnosis_001.md`
  - `research/reports/tsmomentum_same_session_vol_correction_001.md`
  - `research/reports/tsmomentum_sma175_promotion_gate_eval_001.md`
  - `research/reports/tsmomentum_vol_estimate_consolidation_001.md`
  - `research/reports/tsmomentum_vol_estimate_consolidation_001_rerun.md`
  - `research/tsmomentum_same_session_vol_correction.py`
- `1.486941` (full-path Sharpe of the committed record's path):
  - `README.md`
  - `research/experiments/tsmomentum_rolling63_weakness_diagnosis_001.md`
  - `research/reports/long_sample_overlay_attribution_001.json`
  - `research/reports/long_sample_overlay_attribution_001.md`
  - `research/reports/tsmomentum_rolling63_weakness_diagnosis_001.md`
  - `research/reports/tsmomentum_same_session_vol_correction_001.md`
  - `research/tsmomentum_same_session_vol_correction.py`

## 6. Decision recommendation

**Recommendation: adopt_only_for_new_live_paper_trading_records.**

The same-session estimate is a point-in-time error in the live path, so a new live record must not be produced with it; but the published backtest artefacts are frozen, are quoted by many committed files, and the correction lowers every record-level statistic of the incumbent while leaving the promotion decision NO-GO, so adopting it everywhere would invalidate published evidence for no decision-relevant gain.

### Re-derivation plan (a plan, not an execution)

0. The seven research scripts that still inline the same-session estimate (run_cycle5.py, run_cycle13.py, run_cycle15.py, run_cycle15_c4_corrected.py, run_cycle18.py, run_cycle19.py, month_end_candidate_reaudit.py) must route through the shared src/evaluation/risk.py::realized_vol_scale and accept the same default-off switch, so that a future adoption cannot be partial: one implementation, not two.
1. src/simulation/engine.py: keep the switch default-off until the live record is restarted, then set lag_vol_estimate: true in the (new) simulation config for records started from that point on; never rewrite a committed record.
2. research/experiments/tsmomentum_regime_filter_wf_001.md: publish a labelled successor record (new file) with the corrected 48-fold table; do not overwrite the published one.
3. The SMA-window plateau table of the same published record: re-derive on the corrected path in the same successor record.
4. data/processed/paper_trading_state.yaml: keep the committed 450-session record as published; if a corrected record is started, publish it as a new state file with its own drift flags and gate table.
5. research/reports/paper_trading_validation_002.md, go_no_go_evaluation_002.md and deployment_dossier_001.md: add dated addenda with the corrected gate values; do not rewrite the published values.
6. research/reports/opportunity_shortlist.md and the README cycle log: re-state the incumbent's score with the corrected statistics only after the successor record exists.
7. A corrected live record must be started fresh, not appended to the committed one: a record that mixes the two paths measures neither. The track_record_length gate needs 126 sessions, and the corrected path's own 2018-2026 backtest reference is 1.335983, so the unchanged PSR reference 1.4178 is a stricter bar than that record's own backtest.

## 7. What this cycle does NOT change

- It does **not** cause the `rolling_63d_sharpe` failure: the corrected failing window is *worse* (-0.515807 vs -0.448918).
- It does **not** rescue the promotion decision: the PSR gate still fails on the corrected path (0.623929 < 0.95), and the decision stays NO-GO.
- It does **not** change the incumbent's published verdict: the candidate remains a **Credible Candidate** by its published verdict and **NO-GO** for promotion.
- The corrected walk-forward mean is **not** an edge, a recovery or a promotion: on the comparable statistic it is lower than the published path.
- The published walk-forward record, the committed paper-trading state, the gate table, the thresholds, the universe, the cost model, the Sharpe convention and the hypotheses are **untouched**.

## 8. Checks

- [committed_record_loaded]: PASS (observed: 450 sessions, expected: 450 sessions)
- [default_path_reproduces_every_committed_session]: PASS (observed: max |diff| = 5.421e-20 over 450 sessions, expected: <= 1e-12)
- [default_research_path_is_bit_identical_to_the_pre_change_implementation]: PASS (observed: net max |diff| = 0.000e+00, weights max |diff| = 0.000e+00, expected: 0.0 (bit-identical))
- [default_simulation_path_is_bit_identical_to_the_pre_change_implementation]: PASS (observed: weights max |diff| = 0.000e+00, vol_scale max |diff| = 0.000e+00, expected: 0.0 (bit-identical))
- [default_risk_overlay_helpers_are_bit_identical_to_the_pre_change_implementation]: PASS (observed: vol-target max |diff| = 0.000e+00, combined max |diff| = 0.000e+00, expected: 0.0 (bit-identical))
- [published_walk_forward_mean_reproduced]: PASS (observed: 0.947307472025, expected: 0.947307472025 (published))
- [published_walk_forward_fold_count_reproduced]: PASS (observed: 48 folds, expected: 48 folds)
- [published_record_resolved_by_content]: PASS (observed: tsmomentum_regime_filter_wf_001.md, expected: 48 published folds)
- [published_fold_table_reproduced]: PASS (observed: windows 0, OOS Sharpe 0, trades 0 mismatching, expected: 0 mismatches (published precision: 1e-4))
- [published_machinery_still_reproduces_the_published_mean]: PASS (observed: 0.947307472025, expected: 0.947307472025 (published))
- [continuous_path_and_published_machinery_agree_fold_by_fold]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0 (the re-derivation shortcut used for the corrected path is exact))
- [lagged_estimate_is_the_same_session_estimate_shifted_one_session]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0 (exact shift))
- [default_scale_is_the_committed_same_session_estimate]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0 (bit-identical))
- [opt_in_switch_changes_the_path]: PASS (observed: max |diff| = 2.206e-02, expected: > 0 (the corrected path is a different path))
- [switch_defaults_are_off_in_every_entry_point]: PASS (observed: SimulationConfig(), SimulationConfig.from_yaml, PaperTradingConfig.from_paper_config_yaml -> all False, expected: all False (default off))
- [no_config_file_sets_the_switch]: PASS (observed: 0 non-corrected config file(s) mention the switch, expected: 0)
- [corrected_config_is_specification_only_exception]: PASS (observed: config/simulation_candidate_001_corrected.yaml sets lag_vol_estimate: true (specification-only, not an activated record), expected: declared exception present)
- [no_record_feeding_config_sets_the_switch]: PASS (observed: 0 record-feeding config(s) mention the switch, expected: 0)
- [committed_record_gate_value_reproduced]: PASS (observed: -0.448918151148, expected: -0.448918151148 (committed drift flag))
- [corrected_path_does_not_rescue_the_promotion_decision]: PASS (observed: default NO-GO, corrected NO-GO, expected: NO-GO on both paths (the decision is unchanged))
- [corrected_path_does_not_clear_the_rolling_gate]: PASS (observed: corrected trailing 63d Sharpe -0.515807, expected: < 0.9 (the corrected window is worse))
- [corrected_path_does_not_clear_the_psr_gate]: PASS (observed: corrected PSR 0.623929, expected: < 0.95)
- [published_numerical_artefact_fold_is_absent_on_the_corrected_path]: PASS (observed: fold 12: default -21.829879, corrected 0.000000, expected: the artefact disappears when the estimate is lagged)
- [published_test_period_baseline_reproduced]: PASS (observed: Sharpe 1.417752, max DD -0.077940, trades 1196, expected: the 8 documented values of research/run_cycle7.py::DOCUMENTED on the 2026-10-09 vintage (mismatching: none))
- [data_unchanged]: PASS
- [config_unchanged]: PASS
- [committed_artifacts_unchanged]: PASS

## 9. Reproduction commands

```bash
python research/tsmomentum_same_session_vol_correction.py
python -m pytest -q tests/test_tsmomentum_same_session_vol_correction.py
python -m pytest -q
git status --porcelain data/ config/
```

## 10. JSON payload

```json
{
  "anchor": {
    "committed_sessions": 450,
    "lagged_shift_max_abs_diff": 0.0,
    "machinery_wf_mean": 0.9473074720246092,
    "n_folds": 48,
    "published_machinery_run": true,
    "published_record": "tsmomentum_regime_filter_wf_001.md",
    "published_wf_mean": 0.9473074720246092,
    "record_max_abs_diff": 5.421010862427522e-20,
    "reproduced_wf_mean": 0.9473074720246092,
    "research_path_max_abs_diff": 0.0,
    "research_weights_max_abs_diff": 0.0,
    "risk_overlay_max_abs_diff": 0.0,
    "simulation_path_max_abs_diff": 0.0
  },
  "blast_radius": {
    "code_paths": [
      {
        "kind": "shared code",
        "path": "src/evaluation/risk.py::volatility_target_overlay",
        "role": "volatility-target overlay helper",
        "state": "opt-in switch added (lag_vol_estimate, default off)"
      },
      {
        "kind": "shared code",
        "path": "src/evaluation/risk.py::combined_risk_overlay",
        "role": "combined volatility + drawdown overlay helper",
        "state": "opt-in switch added (lag_vol_estimate, default off)"
      },
      {
        "kind": "shared code",
        "path": "src/simulation/engine.py::_target_weights",
        "role": "simulation engine / live paper-trading path",
        "state": "opt-in switch added (SimulationConfig.lag_vol_estimate, default off)"
      },
      {
        "kind": "research script",
        "path": "research/run_cycle6.py::_apply_overlay",
        "role": "published research path of the incumbent (the published walk-forward record)",
        "state": "opt-in switch added (lag_vol_estimate, default off)"
      },
      {
        "kind": "research script",
        "path": "research/run_cycle5.py",
        "role": "Cycle 5 candidate path of the incumbent",
        "state": "not changed (same-session estimate still used)"
      },
      {
        "kind": "research script",
        "path": "research/run_cycle13.py",
        "role": "csmomentum_001 candidate path",
        "state": "not changed (same-session estimate still used)"
      },
      {
        "kind": "research script",
        "path": "research/run_cycle15.py, research/run_cycle15_c4_corrected.py",
        "role": "csmomentum_001 candidate paths",
        "state": "not changed (same-session estimate still used)"
      },
      {
        "kind": "research script",
        "path": "research/run_cycle18.py, research/run_cycle19.py",
        "role": "csmomentum_001 / macroregime_001 candidate paths",
        "state": "not changed (same-session estimate still used)"
      },
      {
        "kind": "research script",
        "path": "research/run_cycle3.py, research/run_cycle4.py",
        "role": "consumers of the shared overlay helpers (no inline estimate of their own)",
        "state": "already routed through src/evaluation/risk.py (they inherit the switch)"
      },
      {
        "kind": "research script",
        "path": "research/month_end_candidate_reaudit.py",
        "role": "config-faithful month-end re-audit of csmomentum_001",
        "state": "not changed (same-session estimate still used)"
      },
      {
        "kind": "research script",
        "path": "research/tsmomentum_rolling63_weakness_diagnosis.py::overlay_variant",
        "role": "Cycle 925 diagnosis (already carried a scratch lag-1 variant)",
        "state": "not changed (measurement only, scratch paths)"
      },
      {
        "kind": "research script",
        "path": "research/trailing_window_attribution.py",
        "role": "consumes the simulation engine's vol_scale (indirect dependency)",
        "state": "not changed (inherits the engine's default)"
      }
    ],
    "committed_artifacts": [
      {
        "description": "published 48-fold walk-forward mean OOS Sharpe",
        "files": [
          "README.md",
          "config/simulation_candidate_001.yaml",
          "research/cost_admissibility_screen.py",
          "research/cost_gate_break_even_audit.py",
          "research/experiments/cost_admissibility_screen_001.md",
          "research/experiments/cost_gate_break_even_001.md",
          "research/experiments/csmomentum_baseline_wf_001.md",
          "research/experiments/incumbent_phase_stability_001.md",
          "research/experiments/tsmomentum_fold_regime_attribution_001.md",
          "research/experiments/tsmomentum_fold_regime_bootstrap_ci_001.md",
          "research/experiments/tsmomentum_fold_sensitivity_001.md",
          "research/experiments/tsmomentum_phase_stability_fix_001.md",
          "research/experiments/tsmomentum_regime_filter_wf_001.md",
          "research/experiments/tsmomentum_rolling63_weakness_diagnosis_001.md",
          "research/experiments/tsmomentum_same_session_vol_correction_001.md",
          "research/experiments/tsmomentum_sma175_decision_001.md",
          "research/experiments/tsmomentum_sma175_validation_001.md",
          "research/experiments/tsmomentum_walkforward_embargo_001.md",
          "research/experiments/tsmomentum_walkforward_mean_robustness_001.md",
          "research/hypotheses/macroregime_001.md",
          "research/incumbent_phase_stability_audit.py",
          "research/reports/cost_admissibility_screen_001.md",
          "research/reports/cost_gate_break_even_001.md",
          "research/reports/cross_momentum_consolidation.md",
          "research/reports/deployment_dossier_001.md",
          "research/reports/go_nogo_evaluation_001.md",
          "research/reports/incumbent_phase_stability_001.md",
          "research/reports/opportunity_shortlist.md",
          "research/reports/paper_trading_validation_001.md",
          "research/reports/paper_trading_validation_002.md",
          "research/reports/paper_trading_validation_003.md",
          "research/reports/simulation_verification_001.md",
          "research/reports/tsmomentum_fold_phase_decision_001.md",
          "research/reports/tsmomentum_fold_regime_attribution_001.md",
          "research/reports/tsmomentum_fold_regime_bootstrap_ci_001.md",
          "research/reports/tsmomentum_fold_sensitivity_001.md",
          "research/reports/tsmomentum_phase_stability_fix_001.md",
          "research/reports/tsmomentum_rolling63_weakness_diagnosis_001.md",
          "research/reports/tsmomentum_same_session_vol_correction_001.md",
          "research/reports/tsmomentum_sma175_decision_001.md",
          "research/reports/tsmomentum_sma175_phase_stability_001.md",
          "research/reports/tsmomentum_sma175_validation_001.md",
          "research/reports/tsmomentum_vol_estimate_consolidation_001.md",
          "research/reports/tsmomentum_vol_estimate_consolidation_001_rerun.md",
          "research/reports/tsmomentum_walkforward_embargo_001.md",
          "research/reports/tsmomentum_walkforward_mean_robustness_001.md",
          "research/run_cycle11.py",
          "research/run_cycle7.py",
          "research/tsmomentum_fold_regime_attribution.py",
          "research/tsmomentum_fold_regime_bootstrap_ci.py",
          "research/tsmomentum_fold_sensitivity_audit.py",
          "research/tsmomentum_phase_stability_fix_audit.py",
          "research/tsmomentum_rolling63_weakness_diagnosis.py",
          "research/tsmomentum_same_session_vol_correction.py",
          "research/tsmomentum_walkforward_embargo_audit.py",
          "research/tsmomentum_walkforward_mean_robustness_audit.py"
        ],
        "marker": "0.9473",
        "n_files": 56
      },
      {
        "description": "committed record's canonical Sharpe",
        "files": [
          "README.md",
          "research/experiments/tsmomentum_rolling63_weakness_diagnosis_001.md",
          "research/experiments/tsmomentum_same_session_vol_correction_001.md",
          "research/reports/paper_trading_validation_535.md",
          "research/reports/psr_continuation_horizon_001.md",
          "research/reports/reference_sample_invariance_001.md",
          "research/reports/sample_definition_hygiene_001.md",
          "research/reports/tsmomentum_rolling63_weakness_diagnosis_001.md",
          "research/reports/tsmomentum_same_session_vol_correction_001.md",
          "research/reports/tsmomentum_vol_estimate_consolidation_001.md",
          "research/reports/tsmomentum_vol_estimate_consolidation_001_rerun.md",
          "research/tsmomentum_same_session_vol_correction.py"
        ],
        "marker": "1.771084",
        "n_files": 12
      },
      {
        "description": "committed record's trailing 63-session Sharpe (drift flag)",
        "files": [
          "README.md",
          "data/processed/paper_trading_state.yaml",
          "research/experiments/tsmomentum_rolling63_weakness_diagnosis_001.md",
          "research/experiments/tsmomentum_same_session_vol_correction_001.md",
          "research/experiments/tsmomentum_sma175_promotion_gate_eval_001.md",
          "research/reports/long_sample_overlay_attribution_001.json",
          "research/reports/long_sample_overlay_attribution_001.md",
          "research/reports/opportunity_shortlist.md",
          "research/reports/paper_trading_rolling.md",
          "research/reports/paper_trading_validation_535.md",
          "research/reports/reference_sample_invariance_001.md",
          "research/reports/sample_definition_hygiene_001.md",
          "research/reports/tsmomentum_rolling63_weakness_diagnosis_001.md",
          "research/reports/tsmomentum_same_session_vol_correction_001.md",
          "research/reports/tsmomentum_sma175_promotion_gate_eval_001.md",
          "research/reports/tsmomentum_vol_estimate_consolidation_001.md",
          "research/reports/tsmomentum_vol_estimate_consolidation_001_rerun.md",
          "research/tsmomentum_same_session_vol_correction.py"
        ],
        "marker": "0.448918",
        "n_files": 18
      },
      {
        "description": "full-path Sharpe of the committed record's path",
        "files": [
          "README.md",
          "research/experiments/tsmomentum_rolling63_weakness_diagnosis_001.md",
          "research/reports/long_sample_overlay_attribution_001.json",
          "research/reports/long_sample_overlay_attribution_001.md",
          "research/reports/tsmomentum_rolling63_weakness_diagnosis_001.md",
          "research/reports/tsmomentum_same_session_vol_correction_001.md",
          "research/tsmomentum_same_session_vol_correction.py"
        ],
        "marker": "1.486941",
        "n_files": 7
      }
    ],
    "n_distinct_affected_files": 66
  },
  "candidate": "tsmomentum_spytrend_001",
  "checks": [
    {
      "expected": "450 sessions",
      "name": "committed_record_loaded",
      "observed": "450 sessions",
      "pass": true
    },
    {
      "expected": "<= 1e-12",
      "name": "default_path_reproduces_every_committed_session",
      "observed": "max |diff| = 5.421e-20 over 450 sessions",
      "pass": true
    },
    {
      "expected": "0.0 (bit-identical)",
      "name": "default_research_path_is_bit_identical_to_the_pre_change_implementation",
      "observed": "net max |diff| = 0.000e+00, weights max |diff| = 0.000e+00",
      "pass": true
    },
    {
      "expected": "0.0 (bit-identical)",
      "name": "default_simulation_path_is_bit_identical_to_the_pre_change_implementation",
      "observed": "weights max |diff| = 0.000e+00, vol_scale max |diff| = 0.000e+00",
      "pass": true
    },
    {
      "expected": "0.0 (bit-identical)",
      "name": "default_risk_overlay_helpers_are_bit_identical_to_the_pre_change_implementation",
      "observed": "vol-target max |diff| = 0.000e+00, combined max |diff| = 0.000e+00",
      "pass": true
    },
    {
      "expected": "0.947307472025 (published)",
      "name": "published_walk_forward_mean_reproduced",
      "observed": "0.947307472025",
      "pass": true
    },
    {
      "expected": "48 folds",
      "name": "published_walk_forward_fold_count_reproduced",
      "observed": "48 folds",
      "pass": true
    },
    {
      "expected": "48 published folds",
      "name": "published_record_resolved_by_content",
      "observed": "tsmomentum_regime_filter_wf_001.md",
      "pass": true
    },
    {
      "expected": "0 mismatches (published precision: 1e-4)",
      "name": "published_fold_table_reproduced",
      "observed": "windows 0, OOS Sharpe 0, trades 0 mismatching",
      "pass": true
    },
    {
      "expected": "0.947307472025 (published)",
      "name": "published_machinery_still_reproduces_the_published_mean",
      "observed": "0.947307472025",
      "pass": true
    },
    {
      "expected": "0.0 (the re-derivation shortcut used for the corrected path is exact)",
      "name": "continuous_path_and_published_machinery_agree_fold_by_fold",
      "observed": "max |diff| = 0.000e+00",
      "pass": true
    },
    {
      "expected": "0.0 (exact shift)",
      "name": "lagged_estimate_is_the_same_session_estimate_shifted_one_session",
      "observed": "max |diff| = 0.000e+00",
      "pass": true
    },
    {
      "expected": "0.0 (bit-identical)",
      "name": "default_scale_is_the_committed_same_session_estimate",
      "observed": "max |diff| = 0.000e+00",
      "pass": true
    },
    {
      "expected": "> 0 (the corrected path is a different path)",
      "name": "opt_in_switch_changes_the_path",
      "observed": "max |diff| = 2.206e-02",
      "pass": true
    },
    {
      "expected": "all False (default off)",
      "name": "switch_defaults_are_off_in_every_entry_point",
      "observed": "SimulationConfig(), SimulationConfig.from_yaml, PaperTradingConfig.from_paper_config_yaml -> all False",
      "pass": true
    },
    {
      "expected": "0",
      "name": "no_config_file_sets_the_switch",
      "observed": "0 non-corrected config file(s) mention the switch",
      "pass": true
    },
    {
      "expected": "declared exception present",
      "name": "corrected_config_is_specification_only_exception",
      "observed": "config/simulation_candidate_001_corrected.yaml sets lag_vol_estimate: true (specification-only, not an activated record)",
      "pass": true
    },
    {
      "expected": "0",
      "name": "no_record_feeding_config_sets_the_switch",
      "observed": "0 record-feeding config(s) mention the switch",
      "pass": true
    },
    {
      "expected": "-0.448918151148 (committed drift flag)",
      "name": "committed_record_gate_value_reproduced",
      "observed": "-0.448918151148",
      "pass": true
    },
    {
      "expected": "NO-GO on both paths (the decision is unchanged)",
      "name": "corrected_path_does_not_rescue_the_promotion_decision",
      "observed": "default NO-GO, corrected NO-GO",
      "pass": true
    },
    {
      "expected": "< 0.9 (the corrected window is worse)",
      "name": "corrected_path_does_not_clear_the_rolling_gate",
      "observed": "corrected trailing 63d Sharpe -0.515807",
      "pass": true
    },
    {
      "expected": "< 0.95",
      "name": "corrected_path_does_not_clear_the_psr_gate",
      "observed": "corrected PSR 0.623929",
      "pass": true
    },
    {
      "expected": "the artefact disappears when the estimate is lagged",
      "name": "published_numerical_artefact_fold_is_absent_on_the_corrected_path",
      "observed": "fold 12: default -21.829879, corrected 0.000000",
      "pass": true
    },
    {
      "expected": "the 8 documented values of research/run_cycle7.py::DOCUMENTED on the 2026-10-09 vintage (mismatching: none)",
      "name": "published_test_period_baseline_reproduced",
      "observed": "Sharpe 1.417752, max DD -0.077940, trades 1196",
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
  "cycle": "926",
  "data_source": "committed parquet cache in data/raw/ and the committed paper-trading state (fetcher never called)",
  "decision": {
    "re_derivation_plan": [
      "0. The seven research scripts that still inline the same-session estimate (run_cycle5.py, run_cycle13.py, run_cycle15.py, run_cycle15_c4_corrected.py, run_cycle18.py, run_cycle19.py, month_end_candidate_reaudit.py) must route through the shared src/evaluation/risk.py::realized_vol_scale and accept the same default-off switch, so that a future adoption cannot be partial: one implementation, not two.",
      "1. src/simulation/engine.py: keep the switch default-off until the live record is restarted, then set lag_vol_estimate: true in the (new) simulation config for records started from that point on; never rewrite a committed record.",
      "2. research/experiments/tsmomentum_regime_filter_wf_001.md: publish a labelled successor record (new file) with the corrected 48-fold table; do not overwrite the published one.",
      "3. The SMA-window plateau table of the same published record: re-derive on the corrected path in the same successor record.",
      "4. data/processed/paper_trading_state.yaml: keep the committed 450-session record as published; if a corrected record is started, publish it as a new state file with its own drift flags and gate table.",
      "5. research/reports/paper_trading_validation_002.md, go_no_go_evaluation_002.md and deployment_dossier_001.md: add dated addenda with the corrected gate values; do not rewrite the published values.",
      "6. research/reports/opportunity_shortlist.md and the README cycle log: re-state the incumbent's score with the corrected statistics only after the successor record exists.",
      "7. A corrected live record must be started fresh, not appended to the committed one: a record that mixes the two paths measures neither. The track_record_length gate needs 126 sessions, and the corrected path's own 2018-2026 backtest reference is 1.335983, so the unchanged PSR reference 1.4178 is a stricter bar than that record's own backtest."
    ],
    "reason": "The same-session estimate is a point-in-time error in the live path, so a new live record must not be produced with it; but the published backtest artefacts are frozen, are quoted by many committed files, and the correction lowers every record-level statistic of the incumbent while leaving the promotion decision NO-GO, so adopting it everywhere would invalidate published evidence for no decision-relevant gain.",
    "recommendation": "adopt_only_for_new_live_paper_trading_records"
  },
  "incumbent_verdict": "Credible Candidate (unchanged); promotion decision NO-GO (unchanged)",
  "overall": "PASS",
  "read_only": {
    "committed_artifacts_unchanged": true,
    "config_unchanged": true,
    "data_unchanged": true
  },
  "record": {
    "corrected": {
      "canonical_sharpe": 1.6357048500763227,
      "max_drawdown": -0.051056745657613756,
      "n_sessions": 450,
      "psr_ci_lower": 0.4254386381069959,
      "psr_ci_upper": 3.1200499506702983,
      "psr_empirical": 0.676,
      "psr_gate_passes": false,
      "psr_normal": 0.6239288012257087,
      "psr_sharpe_se": 0.6899747138191692,
      "psr_target": 1.4178,
      "return_sum": 0.2881624374604081,
      "rolling_gate_passes": false,
      "rolling_gate_value": -0.5158072079113799,
      "trailing_63d_sharpe": -0.5158072079113799
    },
    "gate_threshold_psr": 0.95,
    "gate_threshold_rolling": 0.9,
    "production_gates_corrected": {
      "decision": "NO-GO",
      "failed_gates": [
        "rolling_63d_sharpe",
        "psr"
      ],
      "gates": {
        "full_period_sharpe": 1.6357048500763227,
        "max_drawdown": -0.051056745657613756,
        "psr": 0.6239288012257087,
        "regime_flips": 6.0,
        "rolling_63d_max_dd": -0.039641816292728116,
        "rolling_63d_sharpe": -0.5158072079113799,
        "track_record_length": 450.0
      },
      "psr_normal": 0.6239288012257087
    },
    "production_gates_published": {
      "decision": "NO-GO",
      "failed_gates": [
        "rolling_63d_sharpe",
        "psr"
      ],
      "gates": {
        "full_period_sharpe": 1.7710837711005303,
        "max_drawdown": -0.04985740111232129,
        "psr": 0.6956061412869707,
        "regime_flips": 6.0,
        "rolling_63d_max_dd": -0.038564371456788704,
        "rolling_63d_sharpe": -0.4489181511478863,
        "track_record_length": 450.0
      },
      "psr_normal": 0.6956061412869707
    },
    "psr_settings": {
      "block_size": 22,
      "n_bootstrap": 1000,
      "seed": 20240101,
      "target": 1.4178
    },
    "published": {
      "canonical_sharpe": 1.7710837711005303,
      "max_drawdown": -0.04985740111232129,
      "n_sessions": 450,
      "psr_ci_lower": 0.5722123240010532,
      "psr_ci_upper": 3.262801596197271,
      "psr_empirical": 0.742,
      "psr_gate_passes": false,
      "psr_normal": 0.6956061412869707,
      "psr_sharpe_se": 0.690270698276111,
      "psr_target": 1.4178,
      "return_sum": 0.3032746228175681,
      "rolling_gate_passes": false,
      "rolling_gate_value": -0.4489181511478863,
      "trailing_63d_sharpe": -0.4489181511478863
    },
    "test_period_2018_2026": {
      "corrected": {
        "annualized_return": 0.13976706592411392,
        "annualized_turnover": 13.353378156681666,
        "annualized_volatility": 0.08964716344234774,
        "avg_daily_turnover": 0.05298959585984788,
        "avg_exposure": 0.6507370457157997,
        "max_drawdown": -0.07954307246238446,
        "profit_factor": 1.3320204824743451,
        "sharpe_ratio": 1.335982772072162,
        "sortino_ratio": 1.6067002178588543,
        "total_return": 2.141527800254236,
        "trade_count": 1194
      },
      "published": {
        "annualized_return": 0.14464798483485786,
        "annualized_turnover": 13.32063122779988,
        "annualized_volatility": 0.08791945818978678,
        "avg_daily_turnover": 0.052859647729364606,
        "avg_exposure": 0.6506084793501165,
        "max_drawdown": -0.07793990324215139,
        "profit_factor": 1.3471760928654277,
        "sharpe_ratio": 1.4177519675540684,
        "sortino_ratio": 1.7476749946939096,
        "total_return": 2.261215856568716,
        "trade_count": 1196
      },
      "published_reference": {
        "annualized_return": 0.1446,
        "annualized_turnover": 13.32,
        "annualized_volatility": 0.0879,
        "max_drawdown": -0.0779,
        "profit_factor": 1.35,
        "sharpe_ratio": 1.4178,
        "sortino_ratio": 1.7477,
        "trade_count": 1196
      },
      "vintage_end": "2026-10-09"
    }
  },
  "sharpe_convention": "arithmetic_annualized_rf0",
  "switch": {
    "config_files_setting_the_switch": [],
    "default": false,
    "entry_points": [
      "src/evaluation/risk.py::realized_vol_scale",
      "src/evaluation/risk.py::volatility_target_overlay",
      "src/evaluation/risk.py::combined_risk_overlay",
      "src/evaluation/risk.py::run_risk_overlays",
      "src/evaluation/risk.py::run_combined_risk_overlays",
      "src/simulation/engine.py::SimulationConfig.lag_vol_estimate",
      "src/simulation/engine.py::_target_weights",
      "src/simulation/paper_trading.py::PaperTradingConfig.from_paper_config_yaml",
      "research/run_cycle6.py::_apply_overlay",
      "research/run_cycle6.py::_eval_candidate",
      "research/run_cycle6.py::_eval_candidate_period",
      "research/run_cycle6.py::run_walkforward"
    ],
    "name": "lag_vol_estimate",
    "semantics": "When True the realised-volatility estimate for session t is computed from sessions up to and including t-1 only (no same-session feedback). When False (the default) the trailing 63-session window includes session t, which is the committed behaviour."
  },
  "verdict": "**1. The defect is real, quantified and now correctable, but it is not a cause of the gate failure and it does not rescue anything.** The same-session volatility estimate (session *t*'s own return moves session *t*'s exposure) is present in the published research path, in the shared simulation / live paper-trading path and in both overlay helpers of `src/evaluation/risk.py`. With the estimate lagged one session the committed record's canonical Sharpe moves from 1.771084 to 1.635705, its trailing 63-session Sharpe from -0.448918 to -0.515807 and its PSR against the fixed backtest baseline 1.4178 from 0.695606 to 0.623929. The corrected path is **worse on every record-level statistic** and the promotion decision stays **NO-GO** (failed gates: rolling_63d_sharpe, psr).\n\n**2. The corrected 48-fold walk-forward mean looks better only because a numerical artefact disappears.** On the default path the published mean OOS Sharpe is 0.947307 and it contains one pathological fold (fold 12, -21.829879: 242 of 244 flat sessions, so the backtest-scale estimator divides a near-zero numerator by a near-zero dispersion, Cycle 925 section 5). Excluding that fold the default path's mean is 1.431928. On the corrected path the same segment is entirely flat, so the estimator returns 0.000000 instead of a pathology, the mean over all 48 folds is 1.318605, and the strictest comparable statistic - both paths with fold 12 excluded - is **lower** on the corrected path (1.346660 vs 1.431928); excluding each path's own worst fold it is also lower (1.357135 vs 1.431928). The corrected path is not a recovery, and the higher headline mean must never be quoted without the fold-level table.\n\n**3. The default path is unchanged, bit-for-bit.** The opt-in switch (`lag_vol_estimate`, default off) is available in all three code paths; every default-path comparison in this report is a max |diff| of exactly 0.0 against a frozen copy of the pre-change implementation (research path, simulation path and both risk-overlay helpers). No gate, threshold, universe, cost model, Sharpe convention, parameter, hypothesis or drift flag was changed, the published walk-forward record and the committed paper-trading state were **not** overwritten, and `data/` and `config/` are byte-identical before and after the run.\n\n**4. Decision recommendation: adopt only for new live paper-trading records.** The defect is a genuine point-in-time error in the **live** path (the exposure for session *t* is set with information that is only fully observable after session *t*'s close, at the price the trade is executed at), so a **new** live record must not be produced with it. But the published backtest artefacts are frozen, are quoted by 66 committed files, and the correction **lowers** every record-level statistic of the only credible candidate in the repository while leaving the decision NO-GO: adopting it everywhere would invalidate a large body of published evidence in exchange for no decision-relevant gain. The published record therefore stays as it is, and a clearly labelled successor record is the right vehicle for the corrected backtest (plan in section 7, not executed here). Two consequences must be stated. (i) A corrected live record is measured on a different path from the published backtest baseline 1.4178, so its PSR comparison against that unchanged reference is **conservative**: the corrected path's own 2018-2026 test-period Sharpe is 1.335983 against the published 1.417752. (ii) A corrected live record must be **started fresh** rather than appended to the committed one, because a record that mixes the two paths measures neither; the `track_record_length` gate needs 126 sessions, so the promotion evidence would restart from zero while the committed record stays published and NO-GO.\n\n**5. The incumbent's published verdict is unchanged.** It remains a **Credible Candidate** by its published verdict and **NO-GO** for promotion, live deployment remains unsupported, and this cycle publishes a measurement and a plan - not an edge, not a recovery and not a promotion.",
  "walk_forward": {
    "corrected": {
      "artefact_fold": 12,
      "artefact_fold_detail": {
        "fold": 12,
        "mean_daily_return": 0.0,
        "n_flat_sessions": 244,
        "n_sessions": 244,
        "std_daily_return": 0.0,
        "test_end": "2009-01-07",
        "test_start": "2008-01-22"
      },
      "artefact_fold_test_end": "2009-01-07",
      "artefact_fold_test_sharpe": 0.0,
      "artefact_fold_test_start": "2008-01-22",
      "max_test_sharpe": 3.9121052879675915,
      "mean_test_sharpe": 1.31860460818871,
      "mean_test_sharpe_excl_artefact_fold": 1.3466600253842143,
      "mean_test_sharpe_excl_worst_fold": 1.3571347667023979,
      "median_test_sharpe": 1.2320602755074876,
      "min_test_sharpe": -0.49231284195462954,
      "n_folds": 48,
      "pct_positive_sharpe": 0.9166666666666666,
      "std_test_sharpe": 0.9405384733674299,
      "total_test_trades": 6002,
      "worst_fold": 13,
      "worst_fold_detail": {
        "fold": 13,
        "mean_daily_return": 1.2717979624484224e-05,
        "n_flat_sessions": 222,
        "n_sessions": 244,
        "std_daily_return": 0.002228208328370255,
        "test_end": "2009-07-02",
        "test_start": "2008-07-16"
      },
      "worst_fold_test_end": "2009-07-02",
      "worst_fold_test_sharpe": -0.49231284195462954,
      "worst_fold_test_start": "2008-07-16"
    },
    "corrected_folds": [
      {
        "fold": 1,
        "test_ann_return": 0.2347059770429174,
        "test_end": "2003-09-16",
        "test_max_dd": -0.03186555223445697,
        "test_sharpe": 2.456028816211574,
        "test_sharpe_canonical": 2.4562033624674955,
        "test_start": "2002-09-30",
        "test_trades": 93,
        "train_end": "2002-08-29",
        "train_sharpe": 1.1658375841610158,
        "train_start": "1993-01-01"
      },
      {
        "fold": 2,
        "test_ann_return": 0.2968860284203525,
        "test_end": "2004-03-10",
        "test_max_dd": -0.034885900772203216,
        "test_sharpe": 2.4934896416002834,
        "test_sharpe_canonical": 2.397587774873691,
        "test_start": "2003-03-25",
        "test_trades": 214,
        "train_end": "2003-02-21",
        "train_sharpe": 1.1595065512445548,
        "train_start": "1993-06-28"
      },
      {
        "fold": 3,
        "test_ann_return": 0.04789849560841075,
        "test_end": "2004-09-02",
        "test_max_dd": -0.08000172224192748,
        "test_sharpe": 0.2923493605643617,
        "test_sharpe_canonical": 0.5378570489242535,
        "test_start": "2003-09-17",
        "test_trades": 211,
        "train_end": "2003-08-18",
        "train_sharpe": 1.330237915398471,
        "train_start": "1993-12-21"
      },
      {
        "fold": 4,
        "test_ann_return": 0.14119597134249795,
        "test_end": "2005-02-25",
        "test_max_dd": -0.07723150897345421,
        "test_sharpe": 1.230816913742744,
        "test_sharpe_canonical": 1.3907178736211494,
        "test_start": "2004-03-11",
        "test_trades": 154,
        "train_end": "2004-02-10",
        "train_sharpe": 1.4680685415847141,
        "train_start": "1994-06-15"
      },
      {
        "fold": 5,
        "test_ann_return": 0.205693730734416,
        "test_end": "2005-08-22",
        "test_max_dd": -0.06161224358382411,
        "test_sharpe": 1.8871178381073754,
        "test_sharpe_canonical": 1.9506802952458318,
        "test_start": "2004-09-03",
        "test_trades": 147,
        "train_end": "2004-08-04",
        "train_sharpe": 1.3523276106396926,
        "train_start": "1994-12-08"
      },
      {
        "fold": 6,
        "test_ann_return": 0.24060338734260078,
        "test_end": "2006-02-14",
        "test_max_dd": -0.06161224358382422,
        "test_sharpe": 2.138125603162835,
        "test_sharpe_canonical": 2.1417635160057977,
        "test_start": "2005-02-28",
        "test_trades": 146,
        "train_end": "2005-01-27",
        "train_sharpe": 1.2556718467149848,
        "train_start": "1995-06-02"
      },
      {
        "fold": 7,
        "test_ann_return": 0.26340768825927796,
        "test_end": "2006-08-09",
        "test_max_dd": -0.0711698519492352,
        "test_sharpe": 2.301415641062975,
        "test_sharpe_canonical": 2.264216856324843,
        "test_start": "2005-08-23",
        "test_trades": 162,
        "train_end": "2005-07-22",
        "train_sharpe": 1.2166481370530002,
        "train_start": "1995-11-27"
      },
      {
        "fold": 8,
        "test_ann_return": 0.20239909097584707,
        "test_end": "2007-02-01",
        "test_max_dd": -0.07116985194923542,
        "test_sharpe": 1.8429086316387178,
        "test_sharpe_canonical": 1.9122619448223472,
        "test_start": "2006-02-15",
        "test_trades": 207,
        "train_end": "2006-01-16",
        "train_sharpe": 1.3133105609841675,
        "train_start": "1996-05-21"
      },
      {
        "fold": 9,
        "test_ann_return": 0.1374500214886949,
        "test_end": "2007-07-27",
        "test_max_dd": -0.06325602430851773,
        "test_sharpe": 1.0550212576448028,
        "test_sharpe_canonical": 1.2129768197100708,
        "test_start": "2006-08-10",
        "test_trades": 230,
        "train_end": "2006-07-11",
        "train_sharpe": 1.2361495557344737,
        "train_start": "1996-11-13"
      },
      {
        "fold": 10,
        "test_ann_return": 0.209465559209844,
        "test_end": "2008-01-21",
        "test_max_dd": -0.06325602430851796,
        "test_sharpe": 1.7761410607964703,
        "test_sharpe_canonical": 1.836953789363126,
        "test_start": "2007-02-02",
        "test_trades": 198,
        "train_end": "2007-01-03",
        "train_sharpe": 1.303156915568635,
        "train_start": "1997-05-08"
      },
      {
        "fold": 11,
        "test_ann_return": 0.19094939600177296,
        "test_end": "2008-07-15",
        "test_max_dd": -0.017329370535518973,
        "test_sharpe": 2.726488399017649,
        "test_sharpe_canonical": 2.819232691777685,
        "test_start": "2007-07-30",
        "test_trades": 76,
        "train_end": "2007-06-28",
        "train_sharpe": 1.2943816721024657,
        "train_start": "1997-10-31"
      },
      {
        "fold": 12,
        "test_ann_return": 0.0,
        "test_end": "2009-01-07",
        "test_max_dd": 0.0,
        "test_sharpe": 0.0,
        "test_sharpe_canonical": 0.0,
        "test_start": "2008-01-22",
        "test_trades": 0,
        "train_end": "2007-12-21",
        "train_sharpe": 1.3343014057299072,
        "train_start": "1998-04-27"
      },
      {
        "fold": 13,
        "test_ann_return": 0.0025860526116672222,
        "test_end": "2009-07-02",
        "test_max_dd": -0.028677407434000157,
        "test_sharpe": -0.49231284195462954,
        "test_sharpe_canonical": 0.09060717753492013,
        "test_start": "2008-07-16",
        "test_trades": 8,
        "train_end": "2008-06-16",
        "train_sharpe": 1.3747679826462227,
        "train_start": "1998-10-20"
      },
      {
        "fold": 14,
        "test_ann_return": 0.168480616727801,
        "test_end": "2009-12-25",
        "test_max_dd": -0.0459895872096755,
        "test_sharpe": 1.6146965664138158,
        "test_sharpe_canonical": 1.7395374538474675,
        "test_start": "2009-01-08",
        "test_trades": 113,
        "train_end": "2008-12-09",
        "train_sharpe": 1.218973457325439,
        "train_start": "1999-04-14"
      },
      {
        "fold": 15,
        "test_ann_return": 0.1880257113905892,
        "test_end": "2010-06-21",
        "test_max_dd": -0.06127659044562317,
        "test_sharpe": 1.46658003292995,
        "test_sharpe_canonical": 1.5613610896870926,
        "test_start": "2009-07-03",
        "test_trades": 211,
        "train_end": "2009-06-03",
        "train_sharpe": 1.2800658510101557,
        "train_start": "1999-10-07"
      },
      {
        "fold": 16,
        "test_ann_return": 0.123177814533866,
        "test_end": "2010-12-14",
        "test_max_dd": -0.061276590445623724,
        "test_sharpe": 1.0275568658650256,
        "test_sharpe_canonical": 1.2070897178380384,
        "test_start": "2009-12-28",
        "test_trades": 149,
        "train_end": "2009-11-26",
        "train_sharpe": 1.3642049054534091,
        "train_start": "2000-03-31"
      },
      {
        "fold": 17,
        "test_ann_return": 0.11813733533564608,
        "test_end": "2011-06-08",
        "test_max_dd": -0.04991559134986523,
        "test_sharpe": 1.0023163450029784,
        "test_sharpe_canonical": 1.1895270589299416,
        "test_start": "2010-06-22",
        "test_trades": 163,
        "train_end": "2010-05-21",
        "train_sharpe": 1.248538295628831,
        "train_start": "2000-09-25"
      },
      {
        "fold": 18,
        "test_ann_return": 0.03369563420501409,
        "test_end": "2011-12-01",
        "test_max_dd": -0.058803440677336005,
        "test_sharpe": 0.1630739921528695,
        "test_sharpe_canonical": 0.4365410797143491,
        "test_start": "2010-12-15",
        "test_trades": 162,
        "train_end": "2010-11-15",
        "train_sharpe": 1.336726312244332,
        "train_start": "2001-03-20"
      },
      {
        "fold": 19,
        "test_ann_return": 0.07924367986008085,
        "test_end": "2012-05-25",
        "test_max_dd": -0.04259998747586802,
        "test_sharpe": 0.9177649933568012,
        "test_sharpe_canonical": 1.213728070107293,
        "test_start": "2011-06-09",
        "test_trades": 50,
        "train_end": "2011-05-10",
        "train_sharpe": 1.3989785870072378,
        "train_start": "2001-09-12"
      },
      {
        "fold": 20,
        "test_ann_return": 0.12328240311395633,
        "test_end": "2012-11-19",
        "test_max_dd": -0.047830962563369495,
        "test_sharpe": 1.233303637272231,
        "test_sharpe_canonical": 1.4302295209094298,
        "test_start": "2011-12-02",
        "test_trades": 24,
        "train_end": "2011-11-02",
        "train_sharpe": 1.3094877173935016,
        "train_start": "2002-03-07"
      },
      {
        "fold": 21,
        "test_ann_return": 0.23563586029614747,
        "test_end": "2013-05-14",
        "test_max_dd": -0.04783096256337005,
        "test_sharpe": 2.1508651161814454,
        "test_sharpe_canonical": 2.1612828795117918,
        "test_start": "2012-05-28",
        "test_trades": 130,
        "train_end": "2012-04-26",
        "train_sharpe": 1.4163118178544478,
        "train_start": "2002-08-30"
      },
      {
        "fold": 22,
        "test_ann_return": 0.23146928206081152,
        "test_end": "2013-11-06",
        "test_max_dd": -0.059540761603600556,
        "test_sharpe": 2.0717144367993523,
        "test_sharpe_canonical": 2.0914740399291007,
        "test_start": "2012-11-20",
        "test_trades": 237,
        "train_end": "2012-10-19",
        "train_sharpe": 1.4045126787196003,
        "train_start": "2003-02-24"
      },
      {
        "fold": 23,
        "test_ann_return": 0.09442721616248995,
        "test_end": "2014-05-01",
        "test_max_dd": -0.05954076160360011,
        "test_sharpe": 0.7246971695704805,
        "test_sharpe_canonical": 0.9299891273803887,
        "test_start": "2013-05-15",
        "test_trades": 236,
        "train_end": "2013-04-15",
        "train_sharpe": 1.326655905941277,
        "train_start": "2003-08-19"
      },
      {
        "fold": 24,
        "test_ann_return": 0.06258205908175718,
        "test_end": "2014-10-24",
        "test_max_dd": -0.05896719278560947,
        "test_sharpe": 0.4321683358391797,
        "test_sharpe_canonical": 0.6653271161521523,
        "test_start": "2013-11-07",
        "test_trades": 184,
        "train_end": "2013-10-08",
        "train_sharpe": 1.257733860478315,
        "train_start": "2004-02-11"
      },
      {
        "fold": 25,
        "test_ann_return": 0.12811808827101934,
        "test_end": "2015-04-20",
        "test_max_dd": -0.04102880669252784,
        "test_sharpe": 1.1820714593735548,
        "test_sharpe_canonical": 1.363901720643945,
        "test_start": "2014-05-02",
        "test_trades": 102,
        "train_end": "2014-04-02",
        "train_sharpe": 1.4284776794149503,
        "train_start": "2004-08-05"
      },
      {
        "fold": 26,
        "test_ann_return": 0.09265505214527736,
        "test_end": "2015-10-13",
        "test_max_dd": -0.04203852386214868,
        "test_sharpe": 0.9048897269621834,
        "test_sharpe_canonical": 1.143787929713124,
        "test_start": "2014-10-27",
        "test_trades": 35,
        "train_end": "2014-09-25",
        "train_sharpe": 1.3188510842523886,
        "train_start": "2005-01-28"
      },
      {
        "fold": 27,
        "test_ann_return": 0.0376710748586373,
        "test_end": "2016-04-06",
        "test_max_dd": -0.039912359506039774,
        "test_sharpe": 0.2791575413387473,
        "test_sharpe_canonical": 0.615665329311792,
        "test_start": "2015-04-21",
        "test_trades": 18,
        "train_end": "2015-03-20",
        "train_sharpe": 1.3238132120637056,
        "train_start": "2005-07-25"
      },
      {
        "fold": 28,
        "test_ann_return": 0.1099010890454648,
        "test_end": "2016-09-29",
        "test_max_dd": -0.034187786134353804,
        "test_sharpe": 1.345349582023667,
        "test_sharpe_canonical": 1.593934184105767,
        "test_start": "2015-10-14",
        "test_trades": 28,
        "train_end": "2015-09-14",
        "train_sharpe": 1.1152908804582202,
        "train_start": "2006-01-17"
      },
      {
        "fold": 29,
        "test_ann_return": 0.044210603423026074,
        "test_end": "2017-03-24",
        "test_max_dd": -0.09930830523225076,
        "test_sharpe": 0.2974225801297888,
        "test_sharpe_canonical": 0.5720780644704432,
        "test_start": "2016-04-07",
        "test_trades": 31,
        "train_end": "2016-03-08",
        "train_sharpe": 1.1179880530777757,
        "train_start": "2006-07-12"
      },
      {
        "fold": 30,
        "test_ann_return": 0.07749507227492591,
        "test_end": "2017-09-18",
        "test_max_dd": -0.08650196470325744,
        "test_sharpe": 0.6258229233492778,
        "test_sharpe_canonical": 0.8583957009233236,
        "test_start": "2016-09-30",
        "test_trades": 62,
        "train_end": "2016-08-31",
        "train_sharpe": 1.0986814204572017,
        "train_start": "2007-01-04"
      },
      {
        "fold": 31,
        "test_ann_return": 0.17767585581165135,
        "test_end": "2018-03-13",
        "test_max_dd": -0.09630845770448349,
        "test_sharpe": 1.486022921746613,
        "test_sharpe_canonical": 1.5949627384765672,
        "test_start": "2017-03-27",
        "test_trades": 75,
        "train_end": "2017-02-23",
        "train_sharpe": 1.0405758934374079,
        "train_start": "2007-06-29"
      },
      {
        "fold": 32,
        "test_ann_return": 0.11733515552722817,
        "test_end": "2018-09-05",
        "test_max_dd": -0.09630845770448349,
        "test_sharpe": 0.9597698606533395,
        "test_sharpe_canonical": 1.1449956595115003,
        "test_start": "2017-09-19",
        "test_trades": 148,
        "train_end": "2017-08-18",
        "train_sharpe": 0.9041024479433185,
        "train_start": "2007-12-24"
      },
      {
        "fold": 33,
        "test_ann_return": 0.041722066110288614,
        "test_end": "2019-02-28",
        "test_max_dd": -0.06143247772982807,
        "test_sharpe": 0.27168323743163253,
        "test_sharpe_canonical": 0.5511026978730981,
        "test_start": "2018-03-14",
        "test_trades": 131,
        "train_end": "2018-02-12",
        "train_sharpe": 0.9627031437633111,
        "train_start": "2008-06-17"
      },
      {
        "fold": 34,
        "test_ann_return": 0.10918868497763978,
        "test_end": "2019-08-23",
        "test_max_dd": -0.05912876041784676,
        "test_sharpe": 1.1208756657505121,
        "test_sharpe_canonical": 1.34223784439709,
        "test_start": "2018-09-06",
        "test_trades": 28,
        "train_end": "2018-08-07",
        "train_sharpe": 1.024519034175852,
        "train_start": "2008-12-10"
      },
      {
        "fold": 35,
        "test_ann_return": 0.2507648494811565,
        "test_end": "2020-02-17",
        "test_max_dd": -0.03707907709313607,
        "test_sharpe": 3.252075026352224,
        "test_sharpe_canonical": 3.190023719554733,
        "test_start": "2019-03-01",
        "test_trades": 26,
        "train_end": "2019-01-30",
        "train_sharpe": 0.9918903803333313,
        "train_start": "2009-06-04"
      },
      {
        "fold": 36,
        "test_ann_return": 0.3062388503284017,
        "test_end": "2020-08-11",
        "test_max_dd": -0.03916526988162272,
        "test_sharpe": 3.9121052879675915,
        "test_sharpe_canonical": 3.6896116995686974,
        "test_start": "2019-08-26",
        "test_trades": 24,
        "train_end": "2019-07-25",
        "train_sharpe": 0.9344870369067846,
        "train_start": "2009-11-27"
      },
      {
        "fold": 37,
        "test_ann_return": 0.24014509902192782,
        "test_end": "2021-02-03",
        "test_max_dd": -0.061051348834939456,
        "test_sharpe": 2.2820780238647953,
        "test_sharpe_canonical": 2.2801686457892565,
        "test_start": "2020-02-18",
        "test_trades": 123,
        "train_end": "2020-01-17",
        "train_sharpe": 1.1138927592614876,
        "train_start": "2010-05-24"
      },
      {
        "fold": 38,
        "test_ann_return": 0.093809673341257,
        "test_end": "2021-07-29",
        "test_max_dd": -0.06105134883493979,
        "test_sharpe": 0.6925199656670963,
        "test_sharpe_canonical": 0.8946175470932551,
        "test_start": "2020-08-12",
        "test_trades": 232,
        "train_end": "2020-07-13",
        "train_sharpe": 1.1938644943646652,
        "train_start": "2010-11-16"
      },
      {
        "fold": 39,
        "test_ann_return": 0.0031303706575014356,
        "test_end": "2022-01-21",
        "test_max_dd": -0.06494144482205988,
        "test_sharpe": -0.15584372358516463,
        "test_sharpe_canonical": 0.08287480593546127,
        "test_start": "2021-02-04",
        "test_trades": 243,
        "train_end": "2021-01-05",
        "train_sharpe": 1.193506236240225,
        "train_start": "2011-05-11"
      },
      {
        "fold": 40,
        "test_ann_return": 0.007087287946543341,
        "test_end": "2022-07-18",
        "test_max_dd": -0.06494144482206055,
        "test_sharpe": -0.15235627640672267,
        "test_sharpe_canonical": 0.1256149249337182,
        "test_start": "2021-07-30",
        "test_trades": 148,
        "train_end": "2021-06-30",
        "train_sharpe": 1.2484257157404777,
        "train_start": "2011-11-03"
      },
      {
        "fold": 41,
        "test_ann_return": 0.03152929311456898,
        "test_end": "2023-01-10",
        "test_max_dd": -0.01499653314371674,
        "test_sharpe": 0.34300724020432016,
        "test_sharpe_canonical": 0.940347814322834,
        "test_start": "2022-01-24",
        "test_trades": 29,
        "train_end": "2021-12-23",
        "train_sharpe": 1.1212244435071574,
        "train_start": "2012-04-27"
      },
      {
        "fold": 42,
        "test_ann_return": 0.10841307912567899,
        "test_end": "2023-07-05",
        "test_max_dd": -0.0496547092085442,
        "test_sharpe": 1.2642890867305596,
        "test_sharpe_canonical": 1.5069847115697452,
        "test_start": "2022-07-19",
        "test_trades": 33,
        "train_end": "2022-06-17",
        "train_sharpe": 1.0972602658686066,
        "train_start": "2012-10-22"
      },
      {
        "fold": 43,
        "test_ann_return": 0.20016145852411338,
        "test_end": "2023-12-28",
        "test_max_dd": -0.07954307246238457,
        "test_sharpe": 1.8189533953160475,
        "test_sharpe_canonical": 1.8920926129732059,
        "test_start": "2023-01-11",
        "test_trades": 119,
        "train_end": "2022-12-12",
        "train_sharpe": 1.0126993584460122,
        "train_start": "2013-04-16"
      },
      {
        "fold": 44,
        "test_ann_return": 0.20042577059640854,
        "test_end": "2024-06-21",
        "test_max_dd": -0.0795430724623849,
        "test_sharpe": 1.7769847414844067,
        "test_sharpe_canonical": 1.8503457428299712,
        "test_start": "2023-07-06",
        "test_trades": 184,
        "train_end": "2023-06-06",
        "train_sharpe": 1.059051875847262,
        "train_start": "2013-10-09"
      },
      {
        "fold": 45,
        "test_ann_return": 0.2013127217568691,
        "test_end": "2024-12-16",
        "test_max_dd": -0.06796256758837937,
        "test_sharpe": 1.7457955485324042,
        "test_sharpe_canonical": 1.8184280806939754,
        "test_start": "2023-12-29",
        "test_trades": 219,
        "train_end": "2023-11-29",
        "train_sharpe": 1.00393041811503,
        "train_start": "2014-04-03"
      },
      {
        "fold": 46,
        "test_ann_return": 0.11450024524034697,
        "test_end": "2025-06-10",
        "test_max_dd": -0.0679625675883796,
        "test_sharpe": 0.9806412509072754,
        "test_sharpe_canonical": 1.1732980779087885,
        "test_start": "2024-06-24",
        "test_trades": 186,
        "train_end": "2024-05-23",
        "train_sharpe": 1.1312390269915915,
        "train_start": "2014-09-26"
      },
      {
        "fold": 47,
        "test_ann_return": 0.19517814677372503,
        "test_end": "2025-12-03",
        "test_max_dd": -0.051056745657613645,
        "test_sharpe": 1.8339476762888707,
        "test_sharpe_canonical": 1.9148981135133643,
        "test_start": "2024-12-17",
        "test_trades": 114,
        "train_end": "2024-11-15",
        "train_sharpe": 1.0778812967473725,
        "train_start": "2015-03-23"
      },
      {
        "fold": 48,
        "test_ann_return": 0.30948541123585227,
        "test_end": "2026-05-28",
        "test_max_dd": -0.04450479546838515,
        "test_sharpe": 2.713430637995761,
        "test_sharpe_canonical": 2.5819251412769257,
        "test_start": "2025-06-11",
        "test_trades": 159,
        "train_end": "2025-05-12",
        "train_sharpe": 1.103578010762002,
        "train_start": "2015-09-15"
      }
    ],
    "published": {
      "artefact_fold": 12,
      "artefact_fold_detail": {
        "fold": 12,
        "mean_daily_return": -4.962781666339485e-06,
        "n_flat_sessions": 242,
        "n_sessions": 244,
        "std_daily_return": 6.132163741108965e-05,
        "test_end": "2009-01-07",
        "test_start": "2008-01-22"
      },
      "artefact_fold_test_end": "2009-01-07",
      "artefact_fold_test_sharpe": -21.829879416796786,
      "artefact_fold_test_start": "2008-01-22",
      "max_test_sharpe": 3.9121052879675915,
      "mean_test_sharpe": 0.9473074720246092,
      "mean_test_sharpe_excl_artefact_fold": 1.431928469659107,
      "mean_test_sharpe_excl_worst_fold": 1.431928469659107,
      "median_test_sharpe": 1.29329878363231,
      "min_test_sharpe": -21.829879416796786,
      "n_folds": 48,
      "pct_positive_sharpe": 0.9166666666666666,
      "std_test_sharpe": 3.4797702418403893,
      "total_test_trades": 6013,
      "worst_fold": 12,
      "worst_fold_detail": {
        "fold": 12,
        "mean_daily_return": -4.962781666339485e-06,
        "n_flat_sessions": 242,
        "n_sessions": 244,
        "std_daily_return": 6.132163741108965e-05,
        "test_end": "2009-01-07",
        "test_start": "2008-01-22"
      },
      "worst_fold_test_end": "2009-01-07",
      "worst_fold_test_sharpe": -21.829879416796786,
      "worst_fold_test_start": "2008-01-22"
    },
    "published_folds": [
      {
        "fold": 1,
        "test_ann_return": 0.2376477486419304,
        "test_end": "2003-09-16",
        "test_max_dd": -0.030663328891376795,
        "test_sharpe": 2.554957343861941,
        "test_sharpe_canonical": 2.5462896555619716,
        "test_start": "2002-09-30",
        "test_trades": 94,
        "train_end": "2002-08-29",
        "train_sharpe": 1.2279634518441336,
        "train_start": "1993-01-01"
      },
      {
        "fold": 2,
        "test_ann_return": 0.30094714999850347,
        "test_end": "2004-03-10",
        "test_max_dd": -0.034646576000514906,
        "test_sharpe": 2.582051440567476,
        "test_sharpe_canonical": 2.473353898707039,
        "test_start": "2003-03-25",
        "test_trades": 215,
        "train_end": "2003-02-21",
        "train_sharpe": 1.2213240196570518,
        "train_start": "1993-06-28"
      },
      {
        "fold": 3,
        "test_ann_return": 0.04855931391588175,
        "test_end": "2004-09-02",
        "test_max_dd": -0.0796932859468743,
        "test_sharpe": 0.30274767243282663,
        "test_sharpe_canonical": 0.5496867064796653,
        "test_start": "2003-09-17",
        "test_trades": 211,
        "train_end": "2003-08-18",
        "train_sharpe": 1.3993052662260737,
        "train_start": "1993-12-21"
      },
      {
        "fold": 4,
        "test_ann_return": 0.14380394968973986,
        "test_end": "2005-02-25",
        "test_max_dd": -0.07607654608655523,
        "test_sharpe": 1.2699867020172544,
        "test_sharpe_canonical": 1.4271842215188322,
        "test_start": "2004-03-11",
        "test_trades": 154,
        "train_end": "2004-02-10",
        "train_sharpe": 1.5440703257733894,
        "train_start": "1994-06-15"
      },
      {
        "fold": 5,
        "test_ann_return": 0.2101684286299157,
        "test_end": "2005-08-22",
        "test_max_dd": -0.06013536651786566,
        "test_sharpe": 1.9493967137143615,
        "test_sharpe_canonical": 2.0047864502238606,
        "test_start": "2004-09-03",
        "test_trades": 146,
        "train_end": "2004-08-04",
        "train_sharpe": 1.4240136216530885,
        "train_start": "1994-12-08"
      },
      {
        "fold": 6,
        "test_ann_return": 0.24266149027572004,
        "test_end": "2006-02-14",
        "test_max_dd": -0.06013536651786566,
        "test_sharpe": 2.184895834814226,
        "test_sharpe_canonical": 2.1833935979536854,
        "test_start": "2005-02-28",
        "test_trades": 146,
        "train_end": "2005-01-27",
        "train_sharpe": 1.3278535556250024,
        "train_start": "1995-06-02"
      },
      {
        "fold": 7,
        "test_ann_return": 0.2625037213001782,
        "test_end": "2006-08-09",
        "test_max_dd": -0.06914882906909847,
        "test_sharpe": 2.3382234952228322,
        "test_sharpe_canonical": 2.300047269359534,
        "test_start": "2005-08-23",
        "test_trades": 163,
        "train_end": "2005-07-22",
        "train_sharpe": 1.2887808024245055,
        "train_start": "1995-11-27"
      },
      {
        "fold": 8,
        "test_ann_return": 0.20347048361261577,
        "test_end": "2007-02-01",
        "test_max_dd": -0.0691488290690988,
        "test_sharpe": 1.8911657288561508,
        "test_sharpe_canonical": 1.9581022491717013,
        "test_start": "2006-02-15",
        "test_trades": 207,
        "train_end": "2006-01-16",
        "train_sharpe": 1.3808067444757361,
        "train_start": "1996-05-21"
      },
      {
        "fold": 9,
        "test_ann_return": 0.15802025957072852,
        "test_end": "2007-07-27",
        "test_max_dd": -0.05115685317802399,
        "test_sharpe": 1.3166108652473656,
        "test_sharpe_canonical": 1.452316828617102,
        "test_start": "2006-08-10",
        "test_trades": 230,
        "train_end": "2006-07-11",
        "train_sharpe": 1.3005489517755242,
        "train_start": "1996-11-13"
      },
      {
        "fold": 10,
        "test_ann_return": 0.22751692328549655,
        "test_end": "2008-01-21",
        "test_max_dd": -0.05115685317802421,
        "test_sharpe": 2.081502248810079,
        "test_sharpe_canonical": 2.1068165950623907,
        "test_start": "2007-02-02",
        "test_trades": 198,
        "train_end": "2007-01-03",
        "train_sharpe": 1.3681773900538474,
        "train_start": "1997-05-08"
      },
      {
        "fold": 11,
        "test_ann_return": 0.18816098072809817,
        "test_end": "2008-07-15",
        "test_max_dd": -0.016672932819318587,
        "test_sharpe": 2.7409393118032823,
        "test_sharpe_canonical": 2.841582883589101,
        "test_start": "2007-07-30",
        "test_trades": 78,
        "train_end": "2007-06-28",
        "train_sharpe": 1.367133602091332,
        "train_start": "1997-10-31"
      },
      {
        "fold": 12,
        "test_ann_return": -0.0012503139197203028,
        "test_end": "2009-01-07",
        "test_max_dd": -0.001210645450968828,
        "test_sharpe": -21.829879416796786,
        "test_sharpe_canonical": -1.2847295005078068,
        "test_start": "2008-01-22",
        "test_trades": 2,
        "train_end": "2007-12-21",
        "train_sharpe": 1.408750969779352,
        "train_start": "1998-04-27"
      },
      {
        "fold": 13,
        "test_ann_return": 0.010358952184071457,
        "test_end": "2009-07-02",
        "test_max_dd": -0.028677407434000157,
        "test_sharpe": -0.2665263717842321,
        "test_sharpe_canonical": 0.30289212694810447,
        "test_start": "2008-07-16",
        "test_trades": 8,
        "train_end": "2008-06-16",
        "train_sharpe": 1.4459384481741144,
        "train_start": "1998-10-20"
      },
      {
        "fold": 14,
        "test_ann_return": 0.1798868045551152,
        "test_end": "2009-12-25",
        "test_max_dd": -0.04455892802721595,
        "test_sharpe": 1.766952939611926,
        "test_sharpe_canonical": 1.8737070090903962,
        "test_start": "2009-01-08",
        "test_trades": 114,
        "train_end": "2008-12-09",
        "train_sharpe": 1.2815756520529757,
        "train_start": "1999-04-14"
      },
      {
        "fold": 15,
        "test_ann_return": 0.1893496048056018,
        "test_end": "2010-06-21",
        "test_max_dd": -0.05845897354583074,
        "test_sharpe": 1.524240869787849,
        "test_sharpe_canonical": 1.6166032273462736,
        "test_start": "2009-07-03",
        "test_trades": 212,
        "train_end": "2009-06-03",
        "train_sharpe": 1.3579922084492122,
        "train_start": "1999-10-07"
      },
      {
        "fold": 16,
        "test_ann_return": 0.12399313128154388,
        "test_end": "2010-12-14",
        "test_max_dd": -0.058458973545830295,
        "test_sharpe": 1.0670791750849684,
        "test_sharpe_canonical": 1.2481738430690315,
        "test_start": "2009-12-28",
        "test_trades": 150,
        "train_end": "2009-11-26",
        "train_sharpe": 1.4469375346610183,
        "train_start": "2000-03-31"
      },
      {
        "fold": 17,
        "test_ann_return": 0.12550680619365795,
        "test_end": "2011-06-08",
        "test_max_dd": -0.04837369532033353,
        "test_sharpe": 1.0959979317769908,
        "test_sharpe_canonical": 1.2764605029462512,
        "test_start": "2010-06-22",
        "test_trades": 164,
        "train_end": "2010-05-21",
        "train_sharpe": 1.3349195836085468,
        "train_start": "2000-09-25"
      },
      {
        "fold": 18,
        "test_ann_return": 0.04000735359578855,
        "test_end": "2011-12-01",
        "test_max_dd": -0.056276047293041365,
        "test_sharpe": 0.24257925704586458,
        "test_sharpe_canonical": 0.516804291450329,
        "test_start": "2010-12-15",
        "test_trades": 162,
        "train_end": "2010-11-15",
        "train_sharpe": 1.4236750399243714,
        "train_start": "2001-03-20"
      },
      {
        "fold": 19,
        "test_ann_return": 0.08045949987028544,
        "test_end": "2012-05-25",
        "test_max_dd": -0.04259998747586713,
        "test_sharpe": 0.9429345486345174,
        "test_sharpe_canonical": 1.239066620433899,
        "test_start": "2011-06-09",
        "test_trades": 50,
        "train_end": "2011-05-10",
        "train_sharpe": 1.4900388497909631,
        "train_start": "2001-09-12"
      },
      {
        "fold": 20,
        "test_ann_return": 0.12251367328369644,
        "test_end": "2012-11-19",
        "test_max_dd": -0.047830962563369495,
        "test_sharpe": 1.2266564177629347,
        "test_sharpe_canonical": 1.424823745025369,
        "test_start": "2011-12-02",
        "test_trades": 24,
        "train_end": "2011-11-02",
        "train_sharpe": 1.3917363136685,
        "train_start": "2002-03-07"
      },
      {
        "fold": 21,
        "test_ann_return": 0.23686267965922148,
        "test_end": "2013-05-14",
        "test_max_dd": -0.04783096256337005,
        "test_sharpe": 2.206317379155769,
        "test_sharpe_canonical": 2.2125874707065027,
        "test_start": "2012-05-28",
        "test_trades": 131,
        "train_end": "2012-04-26",
        "train_sharpe": 1.5006807615998008,
        "train_start": "2002-08-30"
      },
      {
        "fold": 22,
        "test_ann_return": 0.23562742089650301,
        "test_end": "2013-11-06",
        "test_max_dd": -0.05738998583156685,
        "test_sharpe": 2.1734324648501686,
        "test_sharpe_canonical": 2.1829516096713686,
        "test_start": "2012-11-20",
        "test_trades": 238,
        "train_end": "2012-10-19",
        "train_sharpe": 1.4859679957466458,
        "train_start": "2003-02-24"
      },
      {
        "fold": 23,
        "test_ann_return": 0.10130056393265607,
        "test_end": "2014-05-01",
        "test_max_dd": -0.05738998583156685,
        "test_sharpe": 0.8107437857855019,
        "test_sharpe_canonical": 1.0124449391805923,
        "test_start": "2013-05-15",
        "test_trades": 236,
        "train_end": "2013-04-15",
        "train_sharpe": 1.4046143770201083,
        "train_start": "2003-08-19"
      },
      {
        "fold": 24,
        "test_ann_return": 0.06688119721467167,
        "test_end": "2014-10-24",
        "test_max_dd": -0.055822625043241425,
        "test_sharpe": 0.4830070939940177,
        "test_sharpe_canonical": 0.7155206545957572,
        "test_start": "2013-11-07",
        "test_trades": 184,
        "train_end": "2013-10-08",
        "train_sharpe": 1.3381406814895558,
        "train_start": "2004-02-11"
      },
      {
        "fold": 25,
        "test_ann_return": 0.12682151609439463,
        "test_end": "2015-04-20",
        "test_max_dd": -0.04136091095118488,
        "test_sharpe": 1.1701768634693603,
        "test_sharpe_canonical": 1.3537847973741637,
        "test_start": "2014-05-02",
        "test_trades": 102,
        "train_end": "2014-04-02",
        "train_sharpe": 1.5173941532049358,
        "train_start": "2004-08-05"
      },
      {
        "fold": 26,
        "test_ann_return": 0.09196473639188407,
        "test_end": "2015-10-13",
        "test_max_dd": -0.04205310246631744,
        "test_sharpe": 0.8976428595555964,
        "test_sharpe_canonical": 1.1375065786195537,
        "test_start": "2014-10-27",
        "test_trades": 35,
        "train_end": "2014-09-25",
        "train_sharpe": 1.4012779393841517,
        "train_start": "2005-01-28"
      },
      {
        "fold": 27,
        "test_ann_return": 0.0376710748586373,
        "test_end": "2016-04-06",
        "test_max_dd": -0.039912359506039774,
        "test_sharpe": 0.2791575413387473,
        "test_sharpe_canonical": 0.615665329311792,
        "test_start": "2015-04-21",
        "test_trades": 18,
        "train_end": "2015-03-20",
        "train_sharpe": 1.4038559632732708,
        "train_start": "2005-07-25"
      },
      {
        "fold": 28,
        "test_ann_return": 0.1099010890454648,
        "test_end": "2016-09-29",
        "test_max_dd": -0.034187786134353804,
        "test_sharpe": 1.345349582023667,
        "test_sharpe_canonical": 1.593934184105767,
        "test_start": "2015-10-14",
        "test_trades": 28,
        "train_end": "2015-09-14",
        "train_sharpe": 1.1924018146540654,
        "train_start": "2006-01-17"
      },
      {
        "fold": 29,
        "test_ann_return": 0.04416191764059829,
        "test_end": "2017-03-24",
        "test_max_dd": -0.09934896639748347,
        "test_sharpe": 0.29685553055420993,
        "test_sharpe_canonical": 0.5715565326724592,
        "test_start": "2016-04-07",
        "test_trades": 29,
        "train_end": "2016-03-08",
        "train_sharpe": 1.19454076585112,
        "train_start": "2006-07-12"
      },
      {
        "fold": 30,
        "test_ann_return": 0.07797678067254865,
        "test_end": "2017-09-18",
        "test_max_dd": -0.0865432040027524,
        "test_sharpe": 0.6331745793088774,
        "test_sharpe_canonical": 0.8658386856694635,
        "test_start": "2016-09-30",
        "test_trades": 60,
        "train_end": "2016-08-31",
        "train_sharpe": 1.1733893097399966,
        "train_start": "2007-01-04"
      },
      {
        "fold": 31,
        "test_ann_return": 0.19058612790369245,
        "test_end": "2018-03-13",
        "test_max_dd": -0.08666119876873024,
        "test_sharpe": 1.67638167680865,
        "test_sharpe_canonical": 1.7657714026375597,
        "test_start": "2017-03-27",
        "test_trades": 75,
        "train_end": "2017-02-23",
        "train_sharpe": 1.0888713372579566,
        "train_start": "2007-06-29"
      },
      {
        "fold": 32,
        "test_ann_return": 0.13034856000643624,
        "test_end": "2018-09-05",
        "test_max_dd": -0.08666119876873035,
        "test_sharpe": 1.137310395687428,
        "test_sharpe_canonical": 1.311592579711584,
        "test_start": "2017-09-19",
        "test_trades": 148,
        "train_end": "2017-08-18",
        "train_sharpe": 0.9463856437444401,
        "train_start": "2007-12-24"
      },
      {
        "fold": 33,
        "test_ann_return": 0.039472774857814974,
        "test_end": "2019-02-28",
        "test_max_dd": -0.06143247772982807,
        "test_sharpe": 0.24718947185832646,
        "test_sharpe_canonical": 0.5307313914254013,
        "test_start": "2018-03-14",
        "test_trades": 130,
        "train_end": "2018-02-12",
        "train_sharpe": 1.0242046314639115,
        "train_start": "2008-06-17"
      },
      {
        "fold": 34,
        "test_ann_return": 0.10550886044213681,
        "test_end": "2019-08-23",
        "test_max_dd": -0.05912876041784676,
        "test_sharpe": 1.0883359067575717,
        "test_sharpe_canonical": 1.3160590591907242,
        "test_start": "2018-09-06",
        "test_trades": 28,
        "train_end": "2018-08-07",
        "train_sharpe": 1.0865880972169413,
        "train_start": "2008-12-10"
      },
      {
        "fold": 35,
        "test_ann_return": 0.2507648494811565,
        "test_end": "2020-02-17",
        "test_max_dd": -0.03707907709313607,
        "test_sharpe": 3.252075026352224,
        "test_sharpe_canonical": 3.190023719554733,
        "test_start": "2019-03-01",
        "test_trades": 26,
        "train_end": "2019-01-30",
        "train_sharpe": 1.039860669648358,
        "train_start": "2009-06-04"
      },
      {
        "fold": 36,
        "test_ann_return": 0.3062388503284017,
        "test_end": "2020-08-11",
        "test_max_dd": -0.03916526988162272,
        "test_sharpe": 3.9121052879675915,
        "test_sharpe_canonical": 3.6896116995686974,
        "test_start": "2019-08-26",
        "test_trades": 24,
        "train_end": "2019-07-25",
        "train_sharpe": 0.980137509736173,
        "train_start": "2009-11-27"
      },
      {
        "fold": 37,
        "test_ann_return": 0.24455516266448196,
        "test_end": "2021-02-03",
        "test_max_dd": -0.05737581276154191,
        "test_sharpe": 2.3629158330846916,
        "test_sharpe_canonical": 2.3505046675433587,
        "test_start": "2020-02-18",
        "test_trades": 124,
        "train_end": "2020-01-17",
        "train_sharpe": 1.1592647490930292,
        "train_start": "2010-05-24"
      },
      {
        "fold": 38,
        "test_ann_return": 0.10230564579347545,
        "test_end": "2021-07-29",
        "test_max_dd": -0.057375812761542466,
        "test_sharpe": 0.7952411969062717,
        "test_sharpe_canonical": 0.9929171427171172,
        "test_start": "2020-08-12",
        "test_trades": 233,
        "train_end": "2020-07-13",
        "train_sharpe": 1.2404296932975856,
        "train_start": "2010-11-16"
      },
      {
        "fold": 39,
        "test_ann_return": 0.011215008818299843,
        "test_end": "2022-01-21",
        "test_max_dd": -0.06324205466798849,
        "test_sharpe": -0.08358271006476463,
        "test_sharpe_canonical": 0.15852684230016514,
        "test_start": "2021-02-04",
        "test_trades": 243,
        "train_end": "2021-01-05",
        "train_sharpe": 1.2415200531342212,
        "train_start": "2011-05-11"
      },
      {
        "fold": 40,
        "test_ann_return": 0.011128203969249295,
        "test_end": "2022-07-18",
        "test_max_dd": -0.06324205466798782,
        "test_sharpe": -0.10732991321229177,
        "test_sharpe_canonical": 0.1751153791361648,
        "test_start": "2021-07-30",
        "test_trades": 148,
        "train_end": "2021-06-30",
        "train_sharpe": 1.2987273115038214,
        "train_start": "2011-11-03"
      },
      {
        "fold": 41,
        "test_ann_return": 0.05558728826307191,
        "test_end": "2023-01-10",
        "test_max_dd": -0.014533910576322917,
        "test_sharpe": 0.8946927114221876,
        "test_sharpe_canonical": 1.3799207150944197,
        "test_start": "2022-01-24",
        "test_trades": 29,
        "train_end": "2021-12-23",
        "train_sharpe": 1.1736537258095172,
        "train_start": "2012-04-27"
      },
      {
        "fold": 42,
        "test_ann_return": 0.13407946859976905,
        "test_end": "2023-07-05",
        "test_max_dd": -0.049654709208544756,
        "test_sharpe": 1.5583667409783086,
        "test_sharpe_canonical": 1.7555942817851862,
        "test_start": "2022-07-19",
        "test_trades": 32,
        "train_end": "2022-06-17",
        "train_sharpe": 1.1516924367432786,
        "train_start": "2012-10-22"
      },
      {
        "fold": 43,
        "test_ann_return": 0.2002503938626765,
        "test_end": "2023-12-28",
        "test_max_dd": -0.07793990324215128,
        "test_sharpe": 1.8332409273747643,
        "test_sharpe_canonical": 1.9060465393026864,
        "test_start": "2023-01-11",
        "test_trades": 118,
        "train_end": "2022-12-12",
        "train_sharpe": 1.090448418493581,
        "train_start": "2013-04-16"
      },
      {
        "fold": 44,
        "test_ann_return": 0.2022204171983275,
        "test_end": "2024-06-21",
        "test_max_dd": -0.07793990324215094,
        "test_sharpe": 1.81856488947759,
        "test_sharpe_canonical": 1.888572580072733,
        "test_start": "2023-07-06",
        "test_trades": 185,
        "train_end": "2023-06-06",
        "train_sharpe": 1.1321906009905789,
        "train_start": "2013-10-09"
      },
      {
        "fold": 45,
        "test_ann_return": 0.20729793433723254,
        "test_end": "2024-12-16",
        "test_max_dd": -0.06462135007497705,
        "test_sharpe": 1.8342182200072057,
        "test_sharpe_canonical": 1.8964216181154532,
        "test_start": "2023-12-29",
        "test_trades": 220,
        "train_end": "2023-11-29",
        "train_sharpe": 1.073121241583694,
        "train_start": "2014-04-03"
      },
      {
        "fold": 46,
        "test_ann_return": 0.12490239669762193,
        "test_end": "2025-06-10",
        "test_max_dd": -0.06462135007497694,
        "test_sharpe": 1.1148099216076683,
        "test_sharpe_canonical": 1.2980143119148375,
        "test_start": "2024-06-24",
        "test_trades": 186,
        "train_end": "2024-05-23",
        "train_sharpe": 1.2036487751206402,
        "train_start": "2014-09-26"
      },
      {
        "fold": 47,
        "test_ann_return": 0.20334324434421824,
        "test_end": "2025-12-03",
        "test_max_dd": -0.049857401112320954,
        "test_sharpe": 1.9609278869742752,
        "test_sharpe_canonical": 2.02710364685011,
        "test_start": "2024-12-17",
        "test_trades": 115,
        "train_end": "2024-11-15",
        "train_sharpe": 1.1557021608851996,
        "train_start": "2015-03-23"
      },
      {
        "fold": 48,
        "test_ann_return": 0.3197431491772065,
        "test_end": "2026-05-28",
        "test_max_dd": -0.038241314668189696,
        "test_sharpe": 2.8969247986858013,
        "test_sharpe_canonical": 2.734388052684735,
        "test_start": "2025-06-11",
        "test_trades": 160,
        "train_end": "2025-05-12",
        "train_sharpe": 1.190343042350607,
        "train_start": "2015-09-15"
      }
    ]
  }
}
```
