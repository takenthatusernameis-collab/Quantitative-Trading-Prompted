# Experiment: Parameter-plateau gate evaluation (csmomentum_001, Cycle 922)

## Hypothesis reference

`research/hypotheses/csmomentum_001.md` (v001, pre-registered). Falsification condition: the walk-forward mean OOS Sharpe < 0.9 OR < 50% of folds positive. Gate 4 (parameter plateau: >= 2 of 3 lookbacks within 10% of the baseline test Sharpe) was the only pre-registered gate still reported as NOT EVALUATED; it is evaluated here on the config-faithful month-end path.

## Data used

- Source: committed raw cache `data/raw/*.parquet` (read-only, fetcher never called); universe 18 ETFs; union sample 1993-01-29..2026-10-09 (8482 sessions); common-inception slice 2006-02-06..2026-10-09 (5202 sessions).
- Point-in-time treatment: momentum at t uses prices through t-skip-lookback; the month-end signal becomes effective on the next session (1-day lag); 3.0 bps round-trip cost on the weight changes; walk-forward 10y/12m/6m with fixed parameters.

## Configuration

- Pre-registered baseline: lookback 252, skip 21, top_fraction 0.5 (frozen in `config/csmomentum_candidate_001.yaml`, SHA-256 `296a619f794262d05f2b00f044fbab706b4dbf3429e3ac3302282a66aa67f57f`).
- Pre-registered grid: 18 unique combinations (3 lookbacks x 2 skips x 3 top fractions); pre-registered trial count 27 (disclosed mislabel).
- Trials: 18 configurations, 1 decision subject.
- Code revision: 9d610a9

## Results

| Gate | Threshold | Observed | Result |
|---|---|---|---|
| wf_mean_oos_sharpe | >= 0.9 | 0.6975 | FAIL |
| positive_fold_rate | >= 0.5 | 0.7917 | PASS |
| pooled_oos_trades | > 100 | 400 | PASS |
| plateau | >= 2 of 3 lookbacks | 3 | PASS |

- Plateau gate: 3 of 3 lookbacks within 0.1000 of the baseline test Sharpe 0.4878 -> **PASS**
- Failed gates: wf_mean_oos_sharpe
- Robustness diagnostic: 0 of 18 pre-registered configurations clear gate 1; the baseline's walk-forward mean OOS Sharpe is 0.6975.
- DSR: 0.1248 at N=27, 0.3098 at N=18 (current canonical Sharpe convention); on the estimator of the committed Cycle 13 record: -0.3961 at N=27.
- structural_pass: True

## Anchors and disclosures

- Reproduction anchors: the tool fails closed unless it reproduces the published config-faithful record -- union sample (48 folds, mean OOS Sharpe 0.697524, median 0.617881, 79.17% positive, 400 pooled trades; path Sharpe 0.4247 backtest-scale / 0.6051 canonical, max DD -0.4474, turnover 2.16, 232 trade days, 7.56 mean positions) and the pre-registered common-inception sample (21 folds, 0.586081, 166 pooled trades).
- The plateau measurement is invariant to the sample definition: the test split lies entirely after the warm-up ramp, so the union sample and the common-inception slice measure the same gate (3 of 3 lookbacks within 0.1000).
- Selection breadth (measured, disclosed): the shared selection module holds the assets whose cross-sectional rank is >= max_rank x (1 - top_fraction), so at 18 assets and top_fraction 0.5 it holds 10 of 18 (55.6%) on every test-window session, one asset more than the literal 'top 50%' reading of the hypothesis prose. The rule is identical for the baseline and for every grid configuration, so it does not bias the plateau comparison.
- DSR scale disclosure: the DSR/PSR above use the repository's current canonical Sharpe convention (unified in Cycle 861); the committed Cycle 13 record's DSR (-0.6484) was computed with the pre-Cycle-861 estimator, so the two numbers are not comparable. On the record's own estimator this path's DSR is -0.3961 at N=27 and -0.2111 at N=18.

## Decision

- Decision: **NO-GO**
- Research label: **Rejected/Failed**
The pre-registered falsification condition is met and the candidate stays rejected/failed; the plateau gate is now evaluated and does not change the verdict (it is not part of the falsification condition).

## Reproduction commands

```bash
python research/csmomentum_plateau_gate_eval.py
python -m pytest -q tests/test_csmomentum_plateau_gate_eval.py
```
