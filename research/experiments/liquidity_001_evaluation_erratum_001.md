# Erratum 001 -- `liquidity_001` evaluation (Cycle 940)

**Published:** Cycle 940, after the Cycle-938 commit `429e7f5` ("Cycle 938: evaluate
the frozen liquidity_001 candidate - Rejected/Failed").
**Type:** reproducibility defect in a published statistic (a **defect repair of the
generator**, not a re-measurement of the candidate).
**Effect on the verdict:** **none** -- see the last section. No measured value other
than the Deflated Sharpe Ratio line, no threshold, no gate, no cost model, no
universe and no frozen input changed.

## Why this erratum exists

The Cycle-938 record published the Deflated Sharpe Ratio of the liquidity_001
evaluation as `-2.919035`. A Cycle-940 audit found that this number **cannot be
reproduced**: the tool that published it called the bootstrap **without a seed**, so
every execution drew a different moving-block resample and wrote a different number
into the published record and report.

Three consecutive executions of the **unfixed** tool measured:

| Run | Published Deflated Sharpe Ratio |
|---|---|
| Cycle-938 commit (as published) | -2.919035 |
| Cycle-940 audit run 1 | -2.963458 |
| Cycle-940 audit run 2 | -2.954174 |
| Cycle-940 audit run 3 | -2.886135 |

The spread across draws (about 0.08 in DSR units) is the Monte-Carlo error of the
1000-draw, block-22 bootstrap with no seed; the four values above are four draws
from the same distribution.

## Root cause

`research/liquidity_001_evaluation.py` (the Cycle-938 generator) called

```python
compute_dsr(strat_excess.dropna(), n_configs=int(config["total_configs"]))
```

with **no `seed`**, and therefore also with the helper's default draw count
(`n_bootstrap=1000`) instead of the draw count the frozen configuration declares.
`compute_dsr` -> `compute_psr` -> `block_bootstrap_sharpe`
(`src/evaluation/statistics.py`) draws its resamples with
`np.random.default_rng(seed)`; with `seed=None` the generator is seeded from OS
entropy, so the resample -- and every statistic derived from it -- differs on every
run. The frozen configuration `config/liquidity_candidate_001.yaml` had declared
`evaluation.multiple_testing.bootstrap_seed: 20240101` and `n_bootstrap: 2000` all
along; the generator simply did not pass them to this call. Every other candidate
evaluator in the repository does pass a seed (`reversal_001`, `pairs_001` with
`seed=42`; `leadlag_001` with the seed frozen in its own config), and
`liquidity_001` was the only one that did not.

A second, smaller defect in the same line: the code read the probability from
`dsr_res["probability"]`, but `compute_dsr` returns it under `dsr_probability`, so
the published probability was `nan`.

A third, independent reporting defect was found in the same record's cost table: the
**Realized cost drag** line published the fraction of return under a percent label.
The record's own turnover figure is 23.862681 units/yr and the committed cost model is
3.0 bp per unit of weight change, which implies a drag of **0.715880%/yr**; the record
published **0.007159%/yr**, the fraction 0.0071588 with a `%/yr` suffix. The line now
carries 0.715880%/yr. (The sibling records use the percent convention correctly:
`reversal_001` publishes 3.0230%/yr for 100.7664 units/yr, `leadlag_001` publishes
0.7654%/yr for 25.5124 units/yr.)

## The correction

| Item | Before (Cycle 938) | After (Cycle 940) |
|---|---|---|
| DSR call | unseeded, helper-default 1000 draws, block 22 | seeded with the **frozen** `bootstrap_seed` **20240101**, the **frozen** `n_bootstrap` **2000**, block **22** |
| Published DSR | -2.919035 (not reproducible) | **-2.968111** (reproducible) |
| Published probability | `nan` (wrong key) | **0.001498** |
| Seed recorded in the record | not recorded | `seed 20240101, 2000 draws, block 22` |
| Published "Realized cost drag" | 0.007159%/yr (a **fraction** under a percent label) | **0.715880%/yr** |
| Verdict | Rejected/Failed (conditions i, iv) | **Rejected/Failed (conditions i, iv)** |

* **No new number is introduced.** The seed (20240101) and the draw count (2000) are
  the values the frozen configuration already declared under
  `evaluation.multiple_testing`; the block length (22) is the shared helper's
  default and the repository's committed monthly block length. The frozen
  configuration file itself is **unchanged** (`config/` is byte-identical).
* **The generator is repaired, not only the record.** Unlike the Cycle-935
  `reversal_001` erratum -- where only narrative text was wrong and the generator
  was left byte-identical -- the defect here is *in the generator's output*: an
  unseeded publisher rewrites its own published artifact on every run. Leaving the
  generator unfixed would mean the next execution of
  `python research/liquidity_001_evaluation.py` (the repository's own test suite
  runs it) silently replaces the published Deflated Sharpe Ratio with a different
  number again. The generator is therefore corrected, and the two published
  artifacts are regenerated from it.
* The corrected line is also printed to stdout (`DSR|...|SEED|...|DRAWS|...|BLOCK|...`),
  so that the repository's existing "two runs are byte-identical" test now covers
  the Deflated Sharpe Ratio instead of only the gate statistics.

## Reproducibility after the correction

Two consecutive executions of the corrected tool:

| Run | DSR | Probability | Verdict |
|---|---|---|---|
| 1 | -2.968111 | 0.001498 | Rejected/Failed (i, iv) |
| 2 | -2.968111 | 0.001498 | Rejected/Failed (i, iv) |

The regenerated `research/experiments/liquidity_001_evaluation.md` and
`research/reports/liquidity_001_evaluation.md` differ from the Cycle-938 versions
**only** in the Deflated Sharpe Ratio line and in the correction note that points
at this erratum; every other published number, the fold table, the bootstrap
confidence interval, the cost drag and the falsification table are unchanged.

## Why the verdict does not change

The verdict of `liquidity_001` is driven by the four **frozen** falsification
conditions, and the Deflated Sharpe Ratio is a **reported statistic only** -- it is
not one of them:

* condition **(i)** (walk-forward mean OOS Sharpe >= 0.9) is fired by the measured
  -0.649990 and does not read the DSR;
* condition **(ii)** (benchmark-relative net excess bootstrap 95% CI excludes zero)
  is decided by the seeded moving-block CI on the fold excess Sharpes
  ([-2.113215, -0.859968]), which was already seeded and is unchanged;
* condition **(iii)** (measured cross-sectional dispersion of the Amihud score) and
  condition **(iv)** (post-2009 benchmark-relative excess > 0) do not read the DSR.

The published verdict therefore remains **Rejected/Failed** with conditions **i** and
**iv** fired, and the candidate keeps its committed status: retired as written, not
promoted, not simulated, not paper-traded, no variant opened.

## A separate, still-open limitation (not corrected here)

The `liquidity_001` Deflated Sharpe Ratio is computed on the **full-sample**
strategy-excess series (1998-12-22 .. 2026-10-08), whereas the sibling candidate
evaluators (`reversal_001`, `pairs_001`, `leadlag_001`) compute theirs on the
**pooled out-of-sample** net returns. A full-sample DSR is optimistic (it includes
the in-sample train period). This is a methodological difference, not the
reproducibility defect corrected here, and it is **not** a verdict driver for this
candidate, so the published value is **not** changed by this erratum. The
sample-alignment of the Deflated Sharpe Ratio across the candidate evaluators is
flagged for the next cycle's audit.

## Reproduction

```bash
python research/liquidity_001_evaluation.py
python -m pytest -q tests/test_liquidity_001_evaluation.py
python research/bootstrap_seed_audit.py
git status --porcelain data/
git diff --name-only HEAD -- config/settings.yaml
```
