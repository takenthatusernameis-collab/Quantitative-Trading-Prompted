# Erratum 001 -- `reversal_001` evaluation (Cycle 935)

**Published:** 2026-10-21 (UTC), after the Cycle-935 commit `1612851` ("Cycle 935:
evaluate the frozen reversal_001 candidate - Rejected/Failed").
**Type:** wording/figure corrections in the Cycle-934 and Cycle-935 published records.
**Effect on the verdict:** **none** -- see the last section. No measured value,
no threshold, no gate, no cost model and no frozen input changed.

## Why this erratum exists

A post-commit audit of the published Cycle-935 numbers found two places where the
**narrative** text of a published record does not match the **measured** value the
same record's tool computes, plus one arithmetic slip in the hand-written README.
The published records are **immutable**: they are not regenerated in place, and the
tools that produced them (`research/reversal_001_evaluation.py`,
`research/candidate_shortlist_934.py`) are left **byte-identical to commit
`1612851`**. This erratum is the correction of record.

Every "as measured" figure below was recomputed from the frozen evaluator itself
(`research.reversal_001_evaluation.py`, `build_payload()`), not restated by hand.

## The discrepancies, side by side

| # | Where (as published in `1612851`) | As published | As measured (frozen evaluator) | Nature |
|---|---|---|---|---|
| 1 | `research/experiments/candidate_shortlist_934.md`, section "8. Correction (published by Cycle 935)" (and the same sentence in the generator `research/candidate_shortlist_934.py`) | "the correction moves the cost hurdle from 2.0047% to **3.5%** of the measured cross-sectional dispersion per rebalance" | the corrected hurdle is **0.042843 = 4.2843%** of the measured dispersion | wrong figure |
| 2 | `research/experiments/reversal_001_evaluation.md`, section "The pre-registered cost hurdle" (and the same sentence in the generator `research/reversal_001_evaluation.py`) | "the measured capture fraction is -1.259560, which is of the *opposite sign* and roughly **29** times the magnitude of **either** hurdle" | 29.4x the **recomputed** hurdle (0.042843) and 62.8x the **pre-registered** hurdle (0.020047) -- "either hurdle" is imprecise, the single number 29 applies to the recomputed hurdle only | imprecise wording (the number 29 itself is correct for the recomputed hurdle) |
| 3 | `README.md`, Cycle-935 (step 2 of 2) bullet | "walk-forward mean OOS Sharpe -0.004016 (median 0.145992, **std 0.383187**)" | the walk-forward **standard deviation of the 36 fold Sharpes (ddof=1) is 0.752318** (ddof=0: 0.741795) | wrong figure |

## The arithmetic behind the corrected figures

| Quantity | Value | Source |
|---|---|---|
| Realized turnover | 100.766355 units/yr | measured from the out-of-sample weight changes |
| Realized cost drag (3.0 bp/unit) | 3.022991%/yr | measured turnover x the committed cost model |
| Median cross-sectional dispersion per rebalance | 1.399674% | measured over the out-of-sample rebalances |
| Out-of-sample rebalances per year | 50.4112 | 899 observations over 4,494 out-of-sample sessions |
| Measured gross scale per year | 70.5593% | dispersion x rebalances per year |
| **Corrected cost hurdle** | **0.042843 (4.2843%)** | realized drag / measured gross scale |
| Pre-registered cost hurdle | 0.020047 (2.0047%) | frozen in `config/reversal_candidate_001.yaml` |
| Measured median capture fraction | -1.259560 | measured over the 899 out-of-sample rebalances |
| Capture / corrected hurdle | 29.4x (opposite sign) | - |
| Capture / pre-registered hurdle | 62.8x (opposite sign) | - |
| WF std of the 36 fold Sharpes (ddof=1) | 0.752318 | measured |

## Why the verdict does not change

The verdict is driven by the six **frozen** falsification conditions, and the
corrections touch only the *narrative* around two of them:

- condition **(iv)** (median capture fraction >= the pre-registered hurdle) is
  evaluated against the **frozen** hurdle 0.020047. The measured capture fraction
  is **-1.259560**, which is below **both** the frozen hurdle (0.020047) and the
  recomputed one (0.042843), so the condition fires either way;
- conditions **(i)**, **(iii)** and **(vi)** (WF mean OOS Sharpe, post-2009
  excess, mirror test) do not depend on the hurdle at all;
- conditions **(ii)** and **(v)** did not fire and still do not fire.

The published verdict therefore remains **Rejected/Failed (a pre-registered
falsification condition fired)**, with conditions **i, iii, iv, vi** fired, and
`reversal_001` remains closed, unpromoted, with no variant opened.

## What was done

1. `research/reversal_001_evaluation.py`, `research/candidate_shortlist_934.py`
   and their four generated records are left **byte-identical to commit
   `1612851`** (verified with `git diff 1612851 -- <paths>`, empty).
2. The two wrong figures in the **hand-written** `README.md` are corrected in
   place, because the README is a hand-authored cycle summary rather than a
   generated frozen output, and it must state the measured values. It also
   points at this erratum.
3. `tests/test_reversal_001_erratum_001.py` pins this erratum: it asserts that
   the published tools and records are byte-identical to `1612851` (skipped if
   the git history is unavailable), that the erratum states both the published
   and the measured figures side by side, and that the measured figures still
   agree with the frozen evaluator's own payload.

## Reproduction

```bash
python research/reversal_001_evaluation.py
python -m pytest -q tests/test_reversal_001_erratum_001.py
git diff 1612851 -- research/reversal_001_evaluation.py research/candidate_shortlist_934.py
```
