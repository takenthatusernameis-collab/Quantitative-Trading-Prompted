# One implementation of the same-session volatility estimate everywhere, and the corrected successor backtest record for the incumbent (tsmomentum_vol_estimate_consolidation_001, Cycle 927)

## Status

- **OVERALL: FAIL**
- Candidate: `tsmomentum_spytrend_001` (the incumbent)
- Default path: **bit-identical** to every script's pre-change implementation (max |diff| = 0.0, checked per script).
- Switch: `lag_vol_estimate` (default **off**) in all seven consolidated scripts; zero remaining inline same-session exposure estimates.
- Decision: **unchanged** -- NO-GO on both the published and the corrected path (failed gates: rolling_63d_sharpe, psr).
- Read-only: `data/` and `config/` byte-identical (**yes**); no committed artifact modified (**yes**); the published record and the committed paper-trading state are **not** overwritten.

## 1. Implementation consolidation (one implementation, one switch)

Each of the seven scripts that inlined the same-session volatility estimate now calls the shared `src.evaluation.risk.realized_vol_scale(port_ret, target_vol, lookback, lag_vol_estimate)` with `lag_vol_estimate=False` by default.  The default path of every script was compared against a frozen copy of its pre-change implementation on identical synthetic input; every comparison is max |diff| = 0.0, checked not asserted.

| Script | Before | After | Default path max |diff| |
|---|---|---|---|---|
| `run_cycle5._apply_overlay` | inline `rolling(...).std() * sqrt(252)` | `realized_vol_scale(..., lag_vol_estimate=False)` | max |diff| = 0.000e+00 |
| `run_cycle13._incumbent_overlay` | inline `rolling(...).std() * sqrt(252)` | `realized_vol_scale(..., lag_vol_estimate=False)` | max |diff| = 0.000e+00 |
| `run_cycle15._incumbent_overlay` | inline `rolling(...).std() * sqrt(252)` | `realized_vol_scale(..., lag_vol_estimate=False)` | max |diff| = 0.000e+00 |
| `run_cycle15_c4_corrected._incumbent_overlay` | inline `rolling(...).std() * sqrt(252)` | `realized_vol_scale(..., lag_vol_estimate=False)` | max |diff| = 0.000e+00 |
| `run_cycle18._incumbent_overlay` | inline `rolling(...).std() * sqrt(252)` | `realized_vol_scale(..., lag_vol_estimate=False)` | max |diff| = 0.000e+00 |
| `run_cycle19._incumbent_overlay` | inline `rolling(...).std() * sqrt(252)` | `realized_vol_scale(..., lag_vol_estimate=False)` | max |diff| = 0.000e+00 |

Inventory result: **zero** remaining inline same-session exposure estimates in any production or research path. The only permitted copies are the frozen pre-change reference implementations kept in this tool and in its test file, labelled as such.

### Per-script checks

- [run_cycle5._apply_overlay default bit-identical (weights)]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0)
- [run_cycle5 no longer inlines the same-session estimate]: PASS (observed: routed through realized_vol_scale, expected: routed)
- [run_cycle13._incumbent_overlay default bit-identical (weights)]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0)
- [run_cycle13._incumbent_overlay no longer inlines the same-session estimate]: PASS (observed: routed through realized_vol_scale, expected: routed)
- [run_cycle15._incumbent_overlay default bit-identical (weights)]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0)
- [run_cycle15._incumbent_overlay no longer inlines the same-session estimate]: PASS (observed: routed through realized_vol_scale, expected: routed)
- [run_cycle15_c4_corrected._incumbent_overlay default bit-identical (weights)]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0)
- [run_cycle15_c4_corrected._incumbent_overlay no longer inlines the same-session estimate]: PASS (observed: routed through realized_vol_scale, expected: routed)
- [run_cycle18._incumbent_overlay default bit-identical (weights)]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0)
- [run_cycle18._incumbent_overlay no longer inlines the same-session estimate]: PASS (observed: routed through realized_vol_scale, expected: routed)
- [run_cycle19._incumbent_overlay default bit-identical (weights)]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0)
- [run_cycle19._incumbent_overlay no longer inlines the same-session estimate]: PASS (observed: routed through realized_vol_scale, expected: routed)
- [run_cycle19.build_overlay_weights default bit-identical]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0)
- [month_end_candidate_reaudit.overlay_weights default bit-identical]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0)
- [month_end_candidate_reaudit.overlay_weights no longer inlines the same-session estimate]: PASS (observed: routed through realized_vol_scale, expected: routed)
- [zero remaining inline same-session estimates in the seven scripts]: PASS (observed: none, expected: none)

## 2. Reproduction anchor (fail closed)

Nothing is published unless the default path reproduces the incumbent's published artefacts exactly as committed.

| Quantity | Published | Reproduced |
|---|---|---|
| 48-fold walk-forward mean OOS Sharpe | 0.947307 | 0.947307 |
| Same, from `research/run_cycle6.py::run_walkforward` | 0.947307 | 0.947307 |
| Folds | 48 | 48 |
| Committed record sessions | 450 | 450 (max abs diff = 5.421e-20) |

The published record is resolved by content and all 48 published folds are reproduced: test windows exactly, OOS Sharpe to the published precision, trade counts exactly.

## 3. Corrected successor record (supersedes nothing)

This is a **successor reference that supersedes nothing**: the published record `research/experiments/tsmomentum_regime_filter_wf_001.md`, the committed paper-trading state and every other committed record remain byte-identical. The corrected numbers are **lower on every record-level statistic**; the decision stays **NO-GO**.

### 3.1 The corrected 48-fold walk-forward table

| Statistic | Published (same-session) | Corrected (lagged) |
|---|---|---|
| Folds | 48 | 48 |
| Mean OOS Sharpe (all folds) | 0.947307 | 1.318605 |
| Mean OOS Sharpe excl. the numerical-artefact fold | 1.431928 | 1.346660 |
| Mean OOS Sharpe excl. each path's own worst fold | 1.431928 | 1.357135 |
| Median OOS Sharpe | 1.293299 | 1.232060 |
| Std OOS Sharpe | 3.479770 | 0.940538 |
| Min OOS Sharpe | -21.829879 | -0.492313 |
| Max OOS Sharpe | 3.912105 | 3.912105 |
| Positive folds | 91.67% | 91.67% |
| Pooled OOS trades | 6013 | 6002 |

**Artefact-fold caveat.** The default path's minimum fold is fold 12 (-21.829879) -- the numerical artefact: a near-flat segment (242 of 244 flat sessions) scored on the backtest-baseline scale. On the corrected path the same segment is entirely flat (244 of 244 sessions flat, zero dispersion) and the estimator returns 0.000000; the corrected path's own worst fold is fold 13 (-0.492313). The corrected all-fold mean (1.318605) is therefore a zero replacing a pathology, not a better strategy: on the strictest comparable statistic (both paths with the artefact fold excluded) the corrected path is **lower** (1.346660 vs 1.431928), and so is each path's mean excluding its own worst fold (1.357135 vs 1.431928). The corrected walk-forward mean must never be quoted without this fold-level table.

### 3.2 The corrected SMA-window plateau table

The six pre-specified SMA windows of the published record, re-derived on the corrected path over the 2018-2026 test period.

| SMA window | Test Sharpe | Ann. Return | Max DD | Trades | Sortino | Profit Factor | Meets 0.9? |
|---|---|---|---|---|---|---|---|
| 150 | 1.4133 | 0.1473 | -0.0696 | 1174 | 1.6917 | 1.35 | YES |
| 175 | 1.3659 | 0.1430 | -0.0696 | 1207 | 1.6398 | 1.34 | YES |
| 200 | 1.2968 | 0.1364 | -0.0795 | 1200 | 1.5607 | 1.32 | YES |
| 226 | 1.1976 | 0.1275 | -0.0795 | 1236 | 1.4393 | 1.30 | YES |
| 250 | 1.1590 | 0.1240 | -0.0841 | 1284 | 1.4033 | 1.29 | YES |
| 277 | 1.0980 | 0.1188 | -0.0897 | 1308 | 1.3348 | 1.27 | YES |
Windows with Sharpe >= 0.9: 6/6 (informational; the plateau gate is not part of this cycle).

### 3.3 The corrected 2018-2026 test-period statistics (own-path backtest)

| Statistic | Published (same-session) | Corrected (lagged) |
|---|---|---|
| Sharpe (backtest-baseline scale) | 1.417752 | 1.335983 |
| Max drawdown | -0.077940 | -0.079543 |
| Trade count | 1196 | 1194 |
| Annualized return | 0.144648 | 0.139767 |
| Annualized turnover | 13.3206 | 13.3534 |
| Annualized volatility | 0.087919 | 0.089647 |

The corrected path's own backtest reference is 1.335983, below the unchanged fixed reference 1.4178 measured on the same-session path. A corrected live record compared against the unchanged reference therefore faces a **stricter** bar than its own path's backtest; the comparison stays conservative.

### 3.4 The corrected record-level statistics and production gate table

| Statistic | Published | Corrected |
|---|---|---|
| Sessions | 450 | 450 |
| Canonical Sharpe | 1.771084 | 1.635705 |
| Trailing 63-session Sharpe (`rolling_63d_sharpe` gate value) | -0.448918 | -0.515807 |
| `rolling_63d_sharpe` gate (>= 0.9) | FAIL | FAIL |
| PSR (normal) vs 1.4178 | 0.695606 | 0.623929 |
| `psr` gate (>= 0.95) | FAIL | FAIL |
| Max drawdown | -4.985740% | -5.105675% |

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

The corrected gate table is computed by the production code `src.simulation.evaluation.evaluate_go_no_go` on the corrected return series with the committed configuration. It is **NO-GO** with the same failed gates as the published path; the correction is not the cause of the gate failure and it does not rescue anything.

## 4. Corrected live paper-trading record start procedure (specified, not executed)

No live record is started in this cycle, no state file is written, and the fetcher is never called.  The following is an executable specification for a future cycle.

### 4.1 Configuration change

- Set `lag_vol_estimate: true` in the simulation config used to produce the new live record (the committed `config/simulation_candidate_001.yaml` and `config/paper_trading_config.yaml` are **not** edited; the switch is applied to a **new** config file for the new record only).
- Do **not** set the switch on any config that feeds a committed record; a computed record must never mix the two paths.

### 4.2 New state file path

- Start a **new** state file (e.g. `data/processed/paper_trading_state_corrected_001.yaml`) with its own drift flags and gate table; do **not** append to or modify `data/processed/paper_trading_state.yaml` (the committed 450-session record).

### 4.3 Re-initialised drift flags and gate table

- Re-initialise the drift flags and the production gate table for the new record from its first session; the `track_record_length` gate requires 126 sessions, so promotion evidence restarts from zero while the committed record stays published and NO-GO.

### 4.4 Restart cost

- **126 sessions** must be re-accumulated before the `track_record_length` gate can be evaluated on the corrected record.

### 4.5 PSR-reference consequence

- The corrected path's own 2018-2026 backtest reference is 1.335983; the unchanged fixed reference 1.4178 is a **stricter** bar than that record's own backtest.  Measuring a corrected live record against the unchanged reference is conservative.

A record that mixes the same-session and the lagged paths measures neither; the two paths must never be concatenated into a single record.

### 4.6 Provenance of the corrected files

Two new files feed the corrected live record only; they are specification-only and not an activated record:

- `config/simulation_candidate_001_corrected.yaml` — new config, byte-for-byte identical to the committed `config/simulation_candidate_001.yaml` except for `lag_vol_estimate: true` under `risk_overlay`. It does not edit any committed config and must never feed a committed record.
- `data/processed/paper_trading_state_corrected_001.yaml` — new re-initialised state file (empty positions, null last_run_date, zero PnL) for the corrected live record. It does not append to or modify `data/processed/paper_trading_state.yaml` (the committed 450-session record).

Both files are committed at HEAD d46b1b6. Neither feeds any committed record, and a computed record must never mix the same-session and lagged paths.

## 5. What this cycle does NOT change

- It does **not** cause the `rolling_63d_sharpe` failure: the corrected failing window is worse (-0.515807 vs -0.448918).
- It does **not** rescue the promotion decision: the PSR gate still fails on the corrected path (0.623929 < 0.95), and the decision stays NO-GO.
- It does **not** change the incumbent's published verdict: the candidate remains a **Credible Candidate** by its published verdict and **NO-GO** for promotion.
- The corrected walk-forward mean is **not** an edge, a recovery or a promotion: on the comparable statistic it is lower than the published path.
- No gate, threshold, universe, cost model, Sharpe convention, parameter, hypothesis or drift flag is changed; no candidate is selected, re-fit or re-ranked; the shortlist and the promotion decision are not re-stated.

## 6. Checks

- [committed_record_loaded]: PASS (observed: 450 sessions, expected: 450 sessions)
- [default_path_reproduces_every_committed_session]: PASS (observed: max |diff| = 5.421e-20, expected: <= 1e-12)
- [published_walk_forward_mean_reproduced]: PASS (observed: 0.947307472025, expected: 0.947307472025)
- [published_walk_forward_fold_count_reproduced]: PASS (observed: 48 folds, expected: 48 folds)
- [published_record_resolved_by_content]: PASS (observed: tsmomentum_regime_filter_wf_001.md, expected: 48 published folds)
- [published_fold_table_reproduced]: PASS (observed: windows 0, OOS Sharpe 0, trades 0, expected: 0 mismatches)
- [published_machinery_still_reproduces_the_published_mean]: PASS (observed: 0.947307472025, expected: 0.947307472025)
- [published_test_period_baseline_reproduced]: PASS (observed: Sharpe 1.417752, trades 1196, expected: all 8 documented values of run_cycle7::DOCUMENTED (mismatching: none))
- [zero remaining inline same-session estimates in the seven scripts]: PASS (observed: none, expected: none)
- [lagged_estimate_is_the_same_session_estimate_shifted_one_session]: PASS (observed: max |diff| = 0.000e+00, expected: 0.0)
- [opt_in_switch_changes_the_path]: PASS (observed: max |diff| = 2.206e-02, expected: > 0)
- [switch_defaults_are_off_in_every_entry_point]: PASS (observed: SimulationConfig(), from_yaml, PaperTradingConfig -> all False, expected: all False)
- [no_config_file_sets_the_switch]: FAIL (observed: 1 config file(s) mention the switch, expected: 0)
- [committed_record_gate_value_reproduced]: PASS (observed: -0.448918151148, expected: -0.448918151148)
- [corrected_path_does_not_rescue_the_promotion_decision]: PASS (observed: default NO-GO, corrected NO-GO, expected: NO-GO on both paths)
- [corrected_path_is_worse_on_every_record_statistic]: PASS (observed: canonical 1.635705 < 1.771084, trailing -0.515807 < -0.448918, PSR 0.623929 < 0.695606, expected: lower on every record statistic)
- [corrected_record_matches_cycle926_values]: PASS (observed: canonical 1.635705, trailing -0.515807, PSR 0.623929, max DD -0.051057, expected: matches Cycle 926 corrected values)
- [corrected_walk_forward_matches_cycle926_values]: PASS (observed: mean 1.318605, excl artefact 1.346660, excl worst 1.357135, median 1.232060, worst fold 13 (-0.492313), trades 6002, expected: matches Cycle 926 corrected values)
- [corrected_sma_plateau_table_built]: PASS (observed: 6 windows, expected: 6 windows)
- [corrected_test_period_reference_is_lower]: PASS (observed: corrected 1.335983 < published 1.417752, expected: lower)
- [corrected_test_period_matches_cycle926_value]: PASS (observed: 1.335983, expected: 1.335983)
- [data_unchanged]: PASS
- [config_unchanged]: PASS
- [committed_artifacts_unchanged]: PASS

## 7. Reproduction commands

```bash
python research/tsmomentum_vol_estimate_consolidation.py
python -m pytest -q tests/test_tsmomentum_vol_estimate_consolidation.py
python -m pytest -q
git status --porcelain data/ config/
```
