# Report: bootstrap seed audit (bootstrap_seed_audit)

**Cycle 940.** Read-only, deterministic audit of every bootstrap call site in `research/` and `src/`. The tool parses the repository with `ast`; it reads no market data, calls no fetcher and writes nothing unless `--write` is given. This document contains no timestamp: two consecutive runs are byte-identical.

## What a missing seed costs

`compute_dsr`, `compute_psr` and `block_bootstrap_sharpe` draw their resamples with `np.random.default_rng(seed)`. With `seed=None` the generator is seeded from OS entropy, so a different resample -- and every statistic derived from it -- is produced on every execution. A tool that publishes such a statistic into a committed record therefore rewrites that record with a different number on its next run. That is exactly what happened to the Cycle-938 `liquidity_001` record; the correction of record is `research/experiments/liquidity_001_evaluation_erratum_001.md`.

## Result

| Quantity | Value |
|---|---|
| Bootstrap call sites scanned | 55 |
| Seeded call sites | 51 |
| Unseeded call sites | 4 |
| Candidate evaluators audited | 5 |
| Candidate evaluators with an unseeded call | 0 |

## Checks

| Check | Outcome | Detail |
|---|---|---|
| `repository_parses` | PASS | every python file under research/ and src/ parses |
| `candidate_evaluators_seed_every_bootstrap` | PASS | no unseeded bootstrap call in a candidate evaluator |
| `bootstrap_call_sites_found` | PASS | 55 bootstrap call sites scanned |

## Every bootstrap call site

| Call site | Function | Seed | Seed expression |
|---|---|---|---|
| `research/common_inception_sample_audit.py:199` | `compute_psr` | seeded | `PSR_SEED` |
| `research/csmomentum_plateau_gate_eval.py:680` | `compute_dsr` | seeded | `SEED` |
| `research/csmomentum_plateau_gate_eval.py:687` | `compute_dsr` | seeded | `SEED` |
| `research/csmomentum_plateau_gate_eval.py:694` | `compute_psr` | seeded | `SEED` |
| `research/csmomentum_plateau_gate_eval.py:697` | `compute_psr` | seeded | `SEED` |
| `research/leadlag_001_evaluation.py:462` | `compute_dsr` | seeded | `int(config['dsr_seed'])` |
| `research/liquidity_001_evaluation.py:370` | `compute_dsr` | seeded | `int(config['bootstrap_seed'])` |
| `research/overnight_capture_backtest.py:295` | `compute_dsr` | seeded | `SEED` |
| `research/overnight_capture_backtest.py:297` | `compute_psr` | seeded | `SEED` |
| `research/overnight_capture_backtest.py:299` | `block_bootstrap_sharpe` | seeded | `SEED` |
| `research/pairs_001_evaluation.py:544` | `compute_dsr` | seeded | `42` |
| `research/promotion_feasibility_backtest.py:145` | `compute_psr` | seeded | `20240101` |
| `research/promotion_feasibility_backtest.py:240` | `compute_psr` | seeded | `20240101` |
| `research/psr_continuation_horizon.py:41` | `compute_psr` | seeded | `PSR_SEED` |
| `research/psr_continuation_horizon.py:57` | `compute_psr` | seeded | `PSR_SEED` |
| `research/psr_feasibility.py:51` | `compute_psr` | seeded | `20240101` |
| `research/rebalance_schedule_audit.py:305` | `compute_psr` | seeded | `20240101` |
| `research/rebalance_schedule_audit.py:314` | `compute_psr` | seeded | `20240101` |
| `research/reversal_001_evaluation.py:365` | `compute_dsr` | seeded | `42` |
| `research/riskparity_001_eval.py:566` | `compute_psr` | seeded | `BOOTSTRAP_SEED` |
| `research/riskparity_001_eval.py:568` | `compute_dsr` | seeded | `BOOTSTRAP_SEED` |
| `research/run_cycle13.py:712` | `compute_dsr` | seeded | `SEED` |
| `research/run_cycle13.py:716` | `compute_dsr` | seeded | `SEED` |
| `research/run_cycle13.py:720` | `compute_psr` | seeded | `SEED` |
| `research/run_cycle13.py:724` | `compute_psr` | seeded | `SEED` |
| `research/run_cycle15.py:712` | `compute_dsr` | seeded | `SEED` |
| `research/run_cycle15.py:716` | `compute_dsr` | seeded | `SEED` |
| `research/run_cycle15.py:720` | `compute_psr` | seeded | `SEED` |
| `research/run_cycle15.py:724` | `compute_psr` | seeded | `SEED` |
| `research/run_cycle15_c4_corrected.py:723` | `compute_dsr` | seeded | `SEED` |
| `research/run_cycle15_c4_corrected.py:727` | `compute_dsr` | seeded | `SEED` |
| `research/run_cycle15_c4_corrected.py:731` | `compute_psr` | seeded | `SEED` |
| `research/run_cycle15_c4_corrected.py:735` | `compute_psr` | seeded | `SEED` |
| `research/run_cycle18.py:404` | `compute_dsr` | seeded | `SEED` |
| `research/run_cycle18.py:405` | `compute_psr` | seeded | `SEED` |
| `research/run_cycle18.py:406` | `compute_psr` | seeded | `SEED` |
| `research/run_cycle19.py:768` | `compute_dsr` | seeded | `SEED` |
| `research/run_cycle19.py:772` | `compute_psr` | seeded | `SEED` |
| `research/run_cycle19.py:776` | `compute_psr` | seeded | `SEED` |
| `research/run_cycle19.py:782` | `block_bootstrap_sharpe` | seeded | `SEED` |
| `research/run_cycle3.py:514` | `compute_psr` | **unseeded** | (none) |
| `research/run_cycle3.py:518` | `compute_dsr` | **unseeded** | (none) |
| `research/run_cycle3.py:1508` | `compute_psr` | **unseeded** | (none) |
| `research/run_cycle3.py:1511` | `compute_dsr` | **unseeded** | (none) |
| `research/sectorrotation_long_sample_feasibility.py:533` | `compute_psr` | seeded | `PSR_SEED` |
| `research/sectorrotation_long_sample_feasibility.py:540` | `compute_psr` | seeded | `PSR_SEED` |
| `research/sectorrotation_long_sample_feasibility.py:547` | `compute_psr` | seeded | `PSR_SEED` |
| `research/sectorrotation_long_sample_feasibility.py:554` | `compute_dsr` | seeded | `DSR_SEED` |
| `research/sharpe_convention_audit.py:126` | `block_bootstrap_sharpe` | seeded | `PSR_SEED` |
| `research/trailing_window_attribution.py:289` | `block_bootstrap_sharpe` | seeded | `PSR_SEED` |
| `research/tsmomentum_same_session_vol_correction.py:410` | `compute_psr` | seeded | `PSR_SEED` |
| `research/tsmomentum_sma175_promotion_gate_eval.py:202` | `compute_psr` | seeded | `PSR_SEED` |
| `src/evaluation/statistics.py:110` | `block_bootstrap_sharpe` | seeded | `seed` |
| `src/evaluation/statistics.py:153` | `compute_psr` | seeded | `seed` |
| `src/simulation/evaluation.py:513` | `compute_psr` | seeded | `go_no_go_config.psr_seed` |

## Unseeded call sites (findings)

| Call site | Function | Seed | Seed expression |
|---|---|---|---|
| `research/run_cycle3.py:514` | `compute_psr` | **unseeded** | (none) |
| `research/run_cycle3.py:518` | `compute_dsr` | **unseeded** | (none) |
| `research/run_cycle3.py:1508` | `compute_psr` | **unseeded** | (none) |
| `research/run_cycle3.py:1511` | `compute_dsr` | **unseeded** | (none) |

These call sites are **not** repaired by this audit. They belong to historical cycle scripts whose published records are immutable; the audit records their status so that the next cycle can decide whether to re-state them. The candidate evaluators, whose output is regenerated into committed records on every test run, are all seeded.

## Reproduction

```bash
python research/bootstrap_seed_audit.py
python research/bootstrap_seed_audit.py --write
python -m pytest -q tests/test_bootstrap_seed_audit.py
```
