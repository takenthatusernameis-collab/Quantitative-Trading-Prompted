# Like-for-like mechanism comparison on the point-in-time-complete window

**Cycle 931 — measurement of three mechanisms on one window, under one walk-forward design and one cost model.**

## Status

- **Decision label: Exploratory signal** — at least one mechanism's excess over 1/N is statistically supported, but no mechanism clears the 0.9 walk-forward gate on the point-in-time-complete window.
- The label applies to the **incremental-value comparison only**. The incumbent's published verdict is unchanged (a Credible Candidate by its published verdict and NO-GO for promotion) and `riskparity_001` remains **rejected**.
- Window: **2006-02-15 .. 2026-05-28** (41 walk-forward folds, the point-in-time-complete folds of the published design).
- Cost model: 1.0 bp commission + 2.0 bp slippage = **3.0 bp per unit of weight change**, applied identically to all three paths.
- Universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM.

## 1. What was compared and why it was not comparable before

Cycle 929 measured the incumbent's point-in-time universe membership: the published 48-fold walk-forward mixes **7 folds measured on an incomplete cross-section** with **41 measured on the complete one**. Cycle 930 evaluated `riskparity_001` on its own 22-fold design. The three numbers therefore came from three different windows and could not be compared:

| Path | Where it was measured | Walk-forward mean OOS Sharpe |
|---|---|---|
| Incumbent, published record | 48 folds, membership-heterogeneous | 0.947307 |
| Incumbent, complete subsample | the 41 complete published folds | 0.787522 |
| `riskparity_001` (rejected) | its own 22 folds | 0.778089 |
| 1/N equal weight | its own 22 folds | 0.773084 |

This cycle re-measures **all three paths on the same 41 folds** with the same cost model. No candidate is proposed, no parameter is searched and no committed artefact is modified.

## 2. The window and the design

| Item | Value |
|---|---|
| Design | the published one: 10-year rolling train, 12-month test, 6-month step, 21-day purge, 21-day embargo |
| Published folds | 48 |
| Point-in-time-complete folds (measured) | 41 |
| Membership-incomplete folds (excluded) | 7 |
| Measured window | 2006-02-15 .. 2026-05-28 |
| Excluded folds | 1, 2, 3, 4, 5, 6, 7 |

A fold is *point-in-time complete* when all seven members carry a valid momentum (226-session lookback skipping 21) on **every** session of its test window. The 41 measured folds are folds 8..48 of the published design; the seven excluded folds are the ones before the last member (GLD) has a valid momentum.

## 3. The three paths on the same folds

| Path | WF mean OOS Sharpe (backtest) | WF mean OOS Sharpe (canonical) | Median fold | Worst fold | Positive folds | Pooled OOS trades | Window Sharpe (backtest) |
|---|---|---|---|---|---|---|---|---|
| Incumbent `tsmomentum_spytrend_001` | 0.787524 | 1.443935 | 1.170177 | -21.829879 | 0.902439 | 4884 | 1.314633 |
| `riskparity_001` baseline (L = 63, cap = 0.30) | 0.642829 | 0.813226 | 0.761863 | -1.522262 | 0.780488 | 474 | 0.465593 |
| 1/N equal weight (7 ETFs) | 0.603562 | 0.764690 | 0.770649 | -1.421259 | 0.756098 | 0 | 0.391867 |

The *window Sharpe* is a single Sharpe over the union of the 41 test windows; the *walk-forward mean* is the mean of the per-fold Sharpes. The two are not interchangeable and are never compared with each other.

### 3.1 The pre-registered gates on the one window

| Path | Gate 1: WF mean OOS Sharpe >= 0.9 | Gate 2: positive folds >= 0.5 | Gate 3: pooled OOS trades > 100 | All gates |
|---|---|---|---|---|
| Incumbent `tsmomentum_spytrend_001` | 0.787524 >= 0.900000 -> FAIL | 0.902439 >= 0.500000 -> PASS | 4884.000000 > 100.000000 -> PASS | FAIL |
| `riskparity_001` baseline (L = 63, cap = 0.30) | 0.642829 >= 0.900000 -> FAIL | 0.780488 >= 0.500000 -> PASS | 474.000000 > 100.000000 -> PASS | FAIL |
| 1/N equal weight (7 ETFs) | 0.603562 >= 0.900000 -> FAIL | 0.756098 >= 0.500000 -> PASS | 0.000000 > 100.000000 -> FAIL | FAIL |

Gate 3 is a *strategy* gate (a live book must trade). The 1/N benchmark holds constant weights, so it books no trade inside the measured folds and fails gate 3 by construction; that is a property of the benchmark, not a result.

## 4. Incremental value over 1/N

The excess is the **paired per-fold difference** of the walk-forward Sharpe against 1/N on the same fold, so the equity beta a long-only seven-asset book earns anyway cancels. The CI is a moving-block bootstrap over the 41 fold-level differences (block 5, seed 20240101, draw counts 2000, 1000 — the seed and the draw counts of Cycle 929 and Cycle 930).

| Path | Excess over 1/N (same folds) | 95% CI (2000 draws) | 95% CI (1000 draws) | Canonical-scale excess | Correlation with 1/N |
|---|---|---|---|---|---|
| Incumbent `tsmomentum_spytrend_001` | 0.183963 | [-0.906068, 0.839629] | [-0.915213, 0.836081] | 0.679245 | 0.572272 |
| `riskparity_001` baseline (L = 63, cap = 0.30) | 0.039267 | [0.006458, 0.079121] | [0.005774, 0.077745] | 0.048537 | 0.988127 |

Correlation between the two mechanisms' pooled out-of-sample returns: 0.615710.

## 5. The per-fold table

| Fold | Test window | Incumbent Sharpe | `riskparity_001` Sharpe | 1/N Sharpe | Incumbent excess |
|---|---|---|---|---|---|
| 8 | 2006-02-15 .. 2007-02-01 | 1.891166 | 0.897270 | 0.952281 | 0.938884 |
| 9 | 2006-08-10 .. 2007-07-27 | 1.316611 | 1.331914 | 1.384333 | -0.067722 |
| 10 | 2007-02-02 .. 2008-01-21 | 2.081502 | 0.285352 | 0.190607 | 1.890895 |
| 11 | 2007-07-30 .. 2008-07-15 | 2.740939 | -0.141028 | -0.193201 | 2.934140 |
| 12 | 2008-01-22 .. 2009-01-07 | -21.829879 | -0.684195 | -0.726202 | -21.103678 |
| 13 | 2008-07-16 .. 2009-07-02 | -0.266526 | -0.391449 | -0.464759 | 0.198232 |
| 14 | 2009-01-08 .. 2009-12-25 | 1.766953 | 1.314210 | 1.274604 | 0.492349 |
| 15 | 2009-07-03 .. 2010-06-21 | 1.524241 | 1.564962 | 1.466019 | 0.058222 |
| 16 | 2009-12-28 .. 2010-12-14 | 1.067079 | 1.108746 | 0.899242 | 0.167837 |
| 17 | 2010-06-22 .. 2011-06-08 | 1.095998 | 1.492304 | 1.256543 | -0.160545 |
| 18 | 2010-12-15 .. 2011-12-01 | 0.242579 | 0.336886 | 0.120351 | 0.122229 |
| 19 | 2011-06-09 .. 2012-05-25 | 0.942935 | 0.055677 | -0.069593 | 1.012528 |
| 20 | 2011-12-02 .. 2012-11-19 | 1.226656 | 0.445680 | 0.477550 | 0.749107 |
| 21 | 2012-05-28 .. 2013-05-14 | 2.206317 | 1.197620 | 1.282417 | 0.923900 |
| 22 | 2012-11-20 .. 2013-11-06 | 2.173432 | 0.816447 | 0.801045 | 1.372387 |
| 23 | 2013-05-15 .. 2014-05-01 | 0.810744 | 0.536750 | 0.369629 | 0.441115 |
| 24 | 2013-11-07 .. 2014-10-24 | 0.483007 | 0.443794 | 0.321712 | 0.161295 |
| 25 | 2014-05-02 .. 2015-04-20 | 1.170177 | 0.844901 | 0.748748 | 0.421428 |
| 26 | 2014-10-27 .. 2015-10-13 | 0.897643 | -0.144129 | -0.240017 | 1.137660 |
| 27 | 2015-04-21 .. 2016-04-06 | 0.279158 | -0.673495 | -0.672055 | 0.951213 |
| 28 | 2015-10-14 .. 2016-09-29 | 1.345350 | 0.675498 | 0.623616 | 0.721733 |
| 29 | 2016-04-07 .. 2017-03-24 | 0.296856 | 1.093415 | 1.062014 | -0.765158 |
| 30 | 2016-09-30 .. 2017-09-18 | 0.633175 | 1.543610 | 1.520896 | -0.887721 |
| 31 | 2017-03-27 .. 2018-03-13 | 1.676382 | 1.726317 | 1.740541 | -0.064160 |
| 32 | 2017-09-19 .. 2018-09-05 | 1.137310 | 0.260431 | 0.298686 | 0.838625 |
| 33 | 2018-03-14 .. 2019-02-28 | 0.247189 | -0.560665 | -0.426689 | 0.673878 |
| 34 | 2018-09-06 .. 2019-08-23 | 1.088336 | 0.157943 | 0.045145 | 1.043191 |
| 35 | 2019-03-01 .. 2020-02-17 | 3.252075 | 2.162742 | 1.887360 | 1.364715 |
| 36 | 2019-08-26 .. 2020-08-11 | 3.912105 | 0.844472 | 0.831146 | 3.080959 |
| 37 | 2020-02-18 .. 2021-02-03 | 2.362916 | 0.761863 | 0.838403 | 1.524513 |
| 38 | 2020-08-12 .. 2021-07-29 | 0.795241 | 1.360544 | 1.467381 | -0.672140 |
| 39 | 2021-02-04 .. 2022-01-21 | -0.083583 | -0.077441 | -0.141864 | 0.058281 |
| 40 | 2021-07-30 .. 2022-07-18 | -0.107330 | -1.522262 | -1.421259 | 1.313929 |
| 41 | 2022-01-24 .. 2023-01-10 | 0.894693 | -0.868927 | -0.811798 | 1.706491 |
| 42 | 2022-07-19 .. 2023-07-05 | 1.558367 | 0.573063 | 0.557607 | 1.000759 |
| 43 | 2023-01-11 .. 2023-12-28 | 1.833241 | 1.089896 | 1.113580 | 0.719661 |
| 44 | 2023-07-06 .. 2024-06-21 | 1.818565 | 1.189931 | 1.023244 | 0.795320 |
| 45 | 2023-12-29 .. 2024-12-16 | 1.834218 | 1.308668 | 1.226409 | 0.607810 |
| 46 | 2024-06-24 .. 2025-06-10 | 1.114810 | 0.722728 | 0.770649 | 0.344161 |
| 47 | 2024-12-17 .. 2025-12-03 | 1.960928 | 1.199444 | 1.262695 | 0.698233 |
| 48 | 2025-06-11 .. 2026-05-28 | 2.896925 | 2.076500 | 2.099011 | 0.797914 |

## 6. Which published statistic survives the homogeneous window

| Published statistic | Where it comes from | On the homogeneous window |
|---|---|---|
| 0.947307 (incumbent walk-forward headline) | the published 48-fold record, membership-heterogeneous | **does not survive**: the same path on the 41 complete folds is 0.787522 (published convention) / 0.787524 (recomputed at full precision), below the 0.9 gate |
| 0.4716 (1/N reference) | the Cycle-7 benchmark record: a **single** 1/N Sharpe over the incumbent's 2018-01-01..2026-10-09 test window at 0 bp cost | **not a walk-forward statistic**, so it cannot survive or fail a walk-forward comparison; the like-for-like 1/N reference for the headline is the 1/N walk-forward mean on the same folds, 0.603562, and the 1/N window Sharpe on the homogeneous window is 0.391867 |

**Implication for the incumbent's published verdict: none.** The verdict stays a Credible Candidate by its published verdict and NO-GO for promotion (it failed the `rolling_63d_sharpe` and `psr` gates in the committed record). This cycle does not change, and does not re-open, that verdict: it measures the *incremental value over equal weight* of two mechanisms on one homogeneous window, and it states the result. The published headline (0.947307) is a membership-heterogeneous statistic and the published 1/N reference (0.4716) is a different statistic on a different window; the pair was never like-for-like and is not used as one here.

## 7. The reproduction anchors

| Anchor | Required | Observed | Outcome |
|---|---|---|---|
| Published 48-fold walk-forward | 48 folds, mean 0.947307, positive 0.916667, 6013 pooled trades | 48 folds, mean 0.947307, positive 0.916667, 6013 pooled trades | PASS |
| Per-fold Sharpes vs the published table | <= 5e-05 (the published table carries four decimals) | max |Δ| = 4.958e-05 | PASS |
| Cycle-929 complete-cross-section figure | 0.787522 ± 1e-06 | 0.787522 (|Δ| = 4.878e-08) | PASS |
| Cycle-930 `riskparity_001` baseline on its own design | 0.778089 | 0.778089 | PASS |

The Cycle-929 figure is the mean of the **published** per-fold Sharpes of the 41 complete folds; the full-precision recomputation is 0.787524 (|Δ| = 2.377e-06 against the published figure). The difference is the four-decimal rounding of the published fold table (max per-fold |Δ| = 4.958e-05) — the same residual Cycle 929 documented for the phase decomposition — and it changes no gate outcome: both values are below the 0.9 threshold.

## 8. What this does and does not change

- **Nothing published changed.** The published record, the published gates, the published protocol, the committed shortlist and every committed candidate artefact are byte-identical after the run; the fetcher was never called and `data/` and `config/` are byte-identical.
- **No new candidate and no new edge is claimed.** The cycle measures two already-published mechanisms against a benchmark on one window; it proposes nothing and re-tunes nothing.
- **The incumbent's verdict is unchanged** (Credible Candidate by its published verdict, NO-GO for promotion) and `riskparity_001` remains rejected.
- **The comparison is an association, not a mechanism.** The 41 folds overlap (a 12-month test window on a 6-month step), so the pooled out-of-sample trade count is not 41 independent samples; the bootstrap CI is a moving-block interval on that serial structure, not an independent-sample interval.

## 9. Reproduction

```bash
python research/mechanism_comparison_001.py
python -m pytest -q tests/test_mechanism_comparison_001.py
python -m pytest -q tests/test_riskparity_001_evaluation.py
git status --porcelain data/ config/
```

Every number in this report is re-derived by the first command from the committed cache, `config/`, `src/` and the committed published record.
