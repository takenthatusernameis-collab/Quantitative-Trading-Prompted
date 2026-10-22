# Erratum 001 -- `cryptofunding_001` evaluation (Cycle 945)

**Published:** Cycle 945, after the Cycle 944 commit `dd55de5` (the Cycle 944
generator, its two published artifacts and the two tests).
**Type:** implementation defect in the published evaluation (a **defect repair of
the generator**, not a re-measurement of the candidate, and not a change of the
frozen specification).
**Effect on the verdict:** **none** -- see "Why the verdict does not change".
`config/cryptofunding_001.yaml` and the frozen hypothesis are byte-identical; no
threshold, no gate, no cost model, no universe, no split and no trial changed.

## Why this erratum exists

The Cycle 944 record published a **frozen-configuration** evaluation of
`cryptofunding_001` whose report header declared

> Cost model: 5.0 bp/unit

and

> Portfolio net ann (headline): 13.7746%

with the per-rule out-of-sample Sharpes `always_on` 9.209,
`funding_positive_sameday` 1.762, `funding_positive_lagged` 0.977.

Neither of those numbers was produced under the cost model the record declared.

## Root cause

Two separate defects in `research/cryptofunding_001_evaluation.py`, both in the
same two lines that produce the published numbers:

1. **The headline was computed at 0.02 bp/unit with no capital charge.** The
   generator built the headline net series with

   ```python
   net = ev.net_series(portfolio_lagged, ev.CAPITAL_CHARGE_RATES["repo_rf"])
   ```

   `net_series(book, cost_bps)` charges `cost_bps` **basis points** per unit of
   weight change, but `CAPITAL_CHARGE_RATES["repo_rf"]` is the repository's
   **annual capital-charge rate** (`0.02`, i.e. 2%/yr). The annual rate was
   therefore applied as **0.02 basis points per unit of turnover** -- a factor
   250 too small -- and the capital charge it came from was never charged at
   all. The published "net" headline was, to within 0.02 pp/yr, the **gross**
   return of the headline rule's portfolio (+13.7966%/yr gross vs +13.7746%/yr
   published). The frozen configuration's `total_round_trip_bps` (5.0) and
   `capital_charge_annual` (0.02) were read from the config file -- the report
   header printed them -- but never used in the computation.
2. **The gate was evaluated at the module's default cost model.** The generator
   called `ev.evaluate_book(book)` without a cost model, so every book was
   evaluated with `research/eval_cryptofunding.py`'s default flat model
   (`flat_3bp`: 3.0 bp per unit of weight change, no capital charge) instead of
   the frozen configuration's cost model. The published OOS Sharpes are
   therefore the **Cycle 891 flat-3 bp** rows: they are byte-identical to the
   `flat_3bp` rows of the committed prior record
   (`research/experiments/cryptofunding_002_evaluation.md`, "Promotion gates
   ... Under every cost model").

Both defects are of the same class as the corrected `pairs_001` (Cycle 940) and
`liquidity_001` (Cycle 940) defects: a published number that does not follow
from the specification the same record claims to implement.

## The correction

| Item | Cycle 944 (as published) | Cycle 945 (corrected) |
|---|---|---|
| Applied trading cost | 0.02 bp/unit (the annual capital-charge rate, passed into the flat-cost function) | **5.0 bp/unit** (the frozen `total_round_trip_bps`) |
| Applied capital charge | none | **2.00%/yr** on the spot leg (the frozen `capital_charge_annual`) |
| Portfolio net ann (headline, `funding_positive_lagged`) | +13.7746% | **+6.5212%** |
| Portfolio gross ann (no cost) | +13.7966% | +13.7966% (unchanged) |
| Mean per-symbol OOS Sharpe, `always_on` | 9.209 | **3.154** |
| Mean per-symbol OOS Sharpe, `funding_positive_sameday` | 1.762 | **-3.956** |
| Mean per-symbol OOS Sharpe, `funding_positive_lagged` | 0.977 | **-4.378** |
| Pooled OOS independent round trips | 0 / 95 / 95 | 0 / 95 / 95 (unchanged) |
| Promotion gate | FAIL for all three rules | **FAIL for all three rules** |
| Verdict | exploratory signal, not promoted | **exploratory signal, not promoted** |

* **No new number is introduced.** 5.0 bp/unit and 2.00%/yr are the values the
  frozen configuration already declared under `cost_model`; the cost model is
  now **built from the loaded configuration** (`frozen_cost_model(config)`), so
  it cannot drift away from the published one again. The frozen configuration
  file itself is **unchanged** (`config/` is byte-identical).
* **The generator is repaired, not only the record.** The published artifacts
  are regenerated from the repaired generator, and the repository's own test
  suite now regenerates them and compares them byte for byte
  (`test_committed_report_matches_the_generator`), so a future execution cannot
  silently republish a different number.
* **The drag is now decomposed, not asserted.** Under the frozen cost model the
  headline rule's portfolio turns over 96.9597 units/yr, so the fee drag is
  4.847985%/yr and the capital charge on the spot leg (an average 87.93% of
  equity) is 1.758523%/yr, a total of 6.606508%/yr against a gross
  +13.796632%/yr. The corrected headline is the net of that drag.

## The reconciliation with the prior cycles

Every figure the prior cycles published is reproduced by the corrected
generator under its **own** cost model, so the prior record is consistent and
was not touched by this erratum (the reconciled table is regenerated in
`research/reports/cryptofunding_001_evaluation.md`, section "Reconciliation
with the prior cycles"):

| Quantity | Prior record | Reproduced | Cost model |
|---|---|---|---|
| `always_on` full-sample net ann | +12.77%/yr | +12.7694% | flat 3 bp/unit (Cycle 891) |
| `always_on` portfolio OOS Sharpe | 11.14 | 11.144 | flat 3 bp/unit (Cycle 891) |
| `funding_positive_lagged` full-sample net ann | +10.53%/yr | +10.5340% | flat 3 bp/unit (Cycle 891) |
| `funding_positive_lagged` portfolio OOS Sharpe | 1.13 | 1.128 | flat 3 bp/unit (Cycle 891) |
| `always_on` full-sample net ann | +9.22%/yr | +9.2190% | venue taker + slippage + rf (Cycle 892) |
| `always_on` portfolio OOS Sharpe | 1.52 | 1.516 | venue taker + slippage + rf (Cycle 892) |
| `funding_positive_lagged` full-sample net ann | +1.97%/yr | +1.9706% | venue taker + slippage + rf (Cycle 892) |
| `funding_positive_lagged` per-symbol mean OOS Sharpe | -6.46 | -6.459 | venue taker + slippage + rf (Cycle 892) |

The only Cycle 944 figure that survives this erratum unchanged is the **gross**
return of the headline portfolio (+13.7966%/yr), which was never in dispute.

## Reproducibility after the correction

Two consecutive executions of the corrected tool print the same headline and the
same gate rows (the numbers are deterministic: the tool reads committed parquet
files and performs no sampling):

| Run | Headline net ann | `always_on` OOS Sharpe | `funding_positive_lagged` OOS Sharpe | Verdict |
|---|---|---|---|---|
| 1 | +6.521243% | 3.153657 | -4.378373 | exploratory signal, not promoted |
| 2 | +6.521243% | 3.153657 | -4.378373 | exploratory signal, not promoted |

The regenerated `research/reports/cryptofunding_001_evaluation.md` and
`research/experiments/cryptofunding_001_evaluation.md` differ from their
Cycle 944 versions in the cost-model lines, the headline, the per-rule OOS
Sharpes, the new correction and reconciliation sections, and the correction
notice; the gross return, the pooled OOS round trips and the gate outcome are
unchanged.

## Why the verdict does not change

The verdict of `cryptofunding_001` is driven by the repository's **promotion
gates**, which this erratum does not touch:

* the **trade-count criterion** is a property of the *position path*, not of the
  cost model: the pooled out-of-sample independent round trips are 0
  (`always_on`, which opens its position before the out-of-sample window and
  never closes it) and 95 (the two funding-positive rules, 40 on BTC and 55 on
  ETH) against the repository's threshold of **more than 100**. The criterion
  therefore fails under every cost model, as it did in Cycles 891-896;
* the **Sharpe criterion** (net out-of-sample Sharpe >= 0.9) is met only by the
  `always_on` book under the frozen configuration (mean per-symbol OOS Sharpe
  3.154), and it fails for the implementable `funding_positive_lagged` rule
  (-4.378), exactly as it failed under the Cycle 891 flat model and the Cycle
  892 realistic model.

The candidate therefore keeps its committed status: **exploratory signal (not
promoted)**. The correction makes the published record *less* favourable, not
more: the frozen configuration's cost model is materially harsher than the flat
3 bp model the Cycle 944 figures were taken from, and the corrected headline
(+6.52%/yr) sits between the Cycle 891 flat-model headline (+10.53%/yr) and the
Cycle 892 realistic-model headline (+1.97%/yr), as it should for a 5 bp/unit
model with a 2%/yr capital charge.

## Reproduction

```bash
python research/cryptofunding_001_evaluation.py
python -m pytest tests/test_eval_cryptofunding_001.py -q
git status --porcelain data/ config/
```
