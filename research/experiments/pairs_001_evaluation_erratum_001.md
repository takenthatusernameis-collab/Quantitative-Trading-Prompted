# Erratum 001 -- `pairs_001` evaluation (Cycle 940)

**Published:** Cycle 940, after the Cycle-936/937 commits (`4d8892c`, `d0a0ce1`).
**Type:** (a) a **broken reference** in a published record, (b) a **reporting defect** in a
published cost-drag figure and in the label of a published quantity.
**Effect on the verdict:** **none** -- see the last section. The strategy's return series,
the fold Sharpes, the bootstrap confidence interval, the Deflated Sharpe Ratio and every
pre-registered condition are unchanged.

## Why this erratum exists

The Cycle-936 `pairs_001` record carries a correction notice that ends with

> The superseded figures are published verbatim in
> `research/experiments/pairs_001_evaluation_erratum_001.md`.

**That file did not exist.** `research/experiments/pairs_001_evaluation_erratum_001.md` is
absent from the repository and from the whole git history
(`git log --all -- research/experiments/pairs_001_evaluation_erratum_001.md` is empty): the
Cycle-936 evaluator defect (a weight frame initialised to `0.0` instead of `NaN`, so the
forward fill was a no-op and positions were held one session instead of the frozen five)
was found and fixed **before** the record was committed, so no pre-fix version of the
record ever existed to publish. The notice therefore pointed a reader at a file that
could not be found, and the superseded figures it promised cannot be published verbatim
because they were never published.

While checking the notice, a second and independent defect was found in the same
evaluator: the **reported** realized turnover cost drag.

## Defect 1 -- the reported turnover cost drag applied the cost rate twice

`research/pairs_001_evaluation.py` builds the per-pair **cost** series in
`path_returns_pair`:

```python
weight_changes = weights_a.diff().abs().sum(axis=1).fillna(0.0)
turnover_cost = weight_changes * cost_per_unit     # already a cost, in fraction units
...
net = gross - turnover_cost - borrow
return net, turnover_cost, borrow
```

The strategy's own return series is therefore correct: the 3.0 bp rate is applied **once**.
But the *reported* statistic multiplied the cost series by the rate a second time:

```python
realized_turnover_cost = float((oos_turnover * cost_per_unit).sum() / len(oos_index) * 252.0)
```

`oos_turnover` is the aggregated cost series, so the published drag was 3.0 bp times too
small. The same double application was in the per-pair attribution
(`turnover_cost_annualized`).

The record contradicted itself: it published a turnover of **68.6916 units/yr** with a
cost model of **3.0 bp per unit of weight change**, which implies a drag of
**2.0607%/yr**, next to a published drag of **0.0006%/yr**.

## Defect 2 -- a published quantity was labelled "gross" but was net of the turnover cost

The published row "Gross excess (before borrow) annualized" carried the value
`net_excess_before_borrow_annualized`, which is computed as
`oos_gross - oos_turnover` and is therefore **net of the turnover cost** (6.6497%). The
true gross excess before any cost (8.7862%) was computed by the evaluator but never
published.

## The correction

| Published line | Cycle 936/937 | Cycle 940 | Why |
|---|---|---|---|
| Realized turnover | 68.6916 units/yr | 68.6916 units/yr | unchanged |
| Realized turnover cost drag | 0.0006%/yr | **2.1364%/yr** | the cost rate is now applied once, to the pair-level cost series |
| Realized borrow drag | 20.3271%/yr | 20.3271%/yr | unchanged |
| Realized total cost drag | 20.3277%/yr | **22.4636%/yr** | turnover drag + borrow drag |
| Gross excess (before any cost) annualized | not published | **8.7862%/yr** | the already-computed gross is now published |
| Excess net of the turnover cost, before borrow, annualized | 6.6497% (labelled "Gross excess (before borrow)") | 6.6497% | relabelled; the value is unchanged |
| Net excess after borrow annualized | -13.6774% | **-13.6774%** | unchanged |

The decomposition is now internally consistent:
8.7862% (gross) - 2.1364% (turnover) - 20.3271% (borrow) = -13.6773% (net, rounding).

`research/pairs_001_failure_analysis.py` transcribed the defective drag
(`realized_turnover_cost_drag = 0.000006`) into its own hard-coded cost-breakdown block;
that block and the narrative sentence that quoted it are corrected the same way, and both
failure-analysis artifacts are regenerated.

## Why the verdict does not change

The `pairs_001` verdict is driven by the four **frozen** falsification conditions, and the
reported drag is not one of them:

* condition **(i)** (walk-forward mean OOS Sharpe >= 0.9) is fired by the measured
  -0.829067, which is computed from the net return series -- unchanged;
* condition **(ii)** (net excess over cash bootstrap 95% CI excludes zero) is decided by
  the seeded moving-block CI [-1.219160, -0.467513] -- unchanged;
* condition **(iii)** (cointegration of every pair holds on all training windows) is
  decided by the Engle-Granger tests on the training windows -- unchanged;
* condition **(iv)** (net excess survives the pre-registered borrow cost) is decided by
  the net excess after borrow, -13.6774%/yr -- unchanged.

The published verdict therefore remains **Rejected/Failed** with conditions **i**, **iii**
and **iv** fired. The candidate keeps its committed status: retired as written, not
promoted, not simulated, not paper-traded, no variant opened. The Cycle-937 failure
analysis' conclusion -- cointegration instability plus a gross edge that cannot survive
the pre-registered borrow cost -- is unchanged; only the drag figures it quotes are
corrected.

## Also corrected

The broken reference itself: the notice in
`research/experiments/pairs_001_evaluation.md` and
`research/reports/pairs_001_evaluation.md` now states that the superseded figures were
never published (the Cycle-936 defect was fixed before the record was committed) and
points at this erratum, which exists.

## Reproduction

```bash
python research/pairs_001_evaluation.py
python research/pairs_001_failure_analysis.py
python -m pytest -q tests/test_pairs_001_evaluation.py
python -m pytest -q tests/test_pairs_001_failure_analysis.py
git status --porcelain data/ config/
```
