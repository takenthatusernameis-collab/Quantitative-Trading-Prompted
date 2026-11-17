# Fold Sharpe Degeneracy Audit — tsmomentum_spytrend_001 (Cycle 930)

**Method:** read-only, cache-only measurement of the incumbent's published 48-fold walk-forward. `research/fold_sharpe_degeneracy_audit.py` rebuilds the continuously computed point-in-time path, records each fold's cash / active / non-zero session counts and annualized volatility, flags folds whose Sharpe is not a valid statistic under a pre-registered rule, and re-evaluates promotion gate 1 on the point-in-time-complete subsample with and without those folds. No backtest was re-tuned, no threshold/gate/cost/universe was changed, nothing under `data/` or `config/` was written and the fetcher was never called.

**Determinism:** this document contains no timestamp and no run id; two consecutive generations are byte-identical.

## Summary

- Candidate: `tsmomentum_spytrend_001` (the incumbent).
- Question: is the point-in-time-complete gate-1 FAIL (mean OOS Sharpe 0.787522) a broad performance gap, or the effect of a single degenerate fold?
- Degenerate folds (pre-registered rule): **fold 12**.
- Complete-subsample gate 1 (mean OOS Sharpe >= 0.9): **FAIL** at 0.787522 (41 folds).
- Complete-subsample gate 1 with the degenerate fold(s) removed: **PASS** at 1.352958 (40 folds).
- Read-only: `data/` and `config/` byte-identical before and after the run; no committed artefact modified.
- Leave-one-fold-out: fold 12 is the unique single-fold determinant of the gate-1 flip; dropping any other single fold leaves the mean in [0.7094, 0.8139] (all FAIL).
- The incumbent's overall verdict is unchanged: **NO-GO** (failed gates `rolling_63d_sharpe`, `psr`).

## The degeneracy rule (pre-registered)

A fold's out-of-sample Sharpe is *degenerate* — not a valid performance measurement — when either:

- its annualized return volatility is below **1%** (`ann_vol < 0.01`); or
- it has at most **2** active (non-cash) sessions (`active_days <= 2`).

Rationale: the Sharpe ratio divides the annualized excess return by the annualized volatility. When the denominator is near zero the ratio is dominated by the risk-free numerator and is numerically meaningless; with 2 or fewer active sessions there is no return distribution to summarise. The thresholds are fixed before the measurement and are not tuned to the outcome.

The check is *separation-based*, not floor-distance: it asserts that fold 12 is far below the floor (`ann_vol` 0.000973, ~10x below 0.01) while the next-lowest non-degenerate fold is far above it (`ann_vol` 0.036173, ~3.6x above), a ~37x separation. The rule's outcome is therefore insensitive to the exact threshold anywhere inside that gap (fold 12 has 1 active day; the next-lowest has 22).

## Fold 12 in detail

| Quantity | Value |
|---|---|
| Test window | 2008-01-22 .. 2009-01-07 |
| Sessions | 244 |
| Cash days (gross weight 0) | 243 |
| Active days (gross weight > 0) | 1 |
| Non-zero return days | 2 |
| Annualized return | -0.001250 |
| Annualized volatility | 0.000973 |
| Recomputed Sharpe | -21.829879 |
| Published Sharpe | -21.8299 |

The SPY trend overlay (SPY below its 200-session SMA) held the portfolio in cash for 243 of 244 sessions of the 2008-01-22 .. 2009-01-07 window. The 2 non-zero return days are the only sessions the portfolio was exposed. The -21.83 Sharpe is the annualized excess return divided by a near-zero volatility; it measures the risk-free rate against that denominator, not a strategy loss. The fold's return over the window is a small negative number, not a crash.

## Complete-subsample gate 1 on each side

| Subsample | Folds | Mean OOS Sharpe | 95% CI (moving block) | Gate 1 (>= 0.9) |
|---|---|---|---|---|
| Point-in-time-complete folds (breadth 7/7) | 41 | 0.787522 | [-0.4244, 1.5431] | FAIL |
| Point-in-time-complete folds, degenerate fold(s) removed | 40 | 1.352958 | [1.0358, 1.6602] | PASS |

## Leave-one-fold-out sensitivity (complete subsample, 41 folds)

The Cycle-929 report shows the complete-subsample gate-1 outcome flips when fold 12 is removed. This section measures whether fold 12 is the *unique* single-fold determinant of that flip, or whether dropping any other single fold also lifts the mean above the threshold. The decision-relevant question is whether the gate-1 PASS on the clean subsample is robust to dropping any single *other* fold -- i.e. whether it is fold 12 specifically, not the act of dropping a fold, that carries the result.

| Drop | Dropped Sharpe | Mean OOS Sharpe (40 folds) | Gate 1 (>= 0.9) |
|---|---|---|---|
| fold 12 (artefact) | -21.8299 | 1.352958 | PASS |
| fold 13 (runner-up) | -0.2665 | 0.813872 | FAIL |
| any other single fold (39 folds) | -- | [0.709407, 0.813872] | FAIL |

**Result:** fold 12 is the **unique** single-fold determinant of the complete-subsample gate-1 flip. Dropping it lifts the mean to 1.352958 (PASS); dropping any other single fold leaves the mean in [0.7094, 0.8139] (all FAIL).
 The runner-up drop (fold 13, Sharpe -0.2665) reaches 0.813872 (FAIL).

## What this does and does not change

- **Nothing published changed.** The published record, gates, protocol and every committed candidate artefact are byte-identical; this is a measurement, not a correction.
- **The complete-subsample gate-1 FAIL is attributable to a single degenerate fold (fold 12).** Its Sharpe is not a valid statistic, so the complete subsample does not actually fail gate 1 on comparable evidence.
- **Leave-one-fold-out confirms fold 12 is the unique single-fold determinant.** Dropping fold 12 lifts the mean to 1.352958 (PASS); dropping any other single fold leaves the mean in [0.7094, 0.8139] (all FAIL). The gate-1 PASS on the clean subsample is therefore not an artefact of dropping a fold in general -- it is fold 12 specifically that carries the result.
- **This refines the Cycle-911 thin-trade grouping.** Fold 13 is *not* degenerate: it has 22 active days, `ann_vol` 0.036173 and a Sharpe of -0.267. The artefact is fold 12 alone.
- **The incumbent's verdict is unchanged**: it stays a Credible Candidate by its published verdict and **NO-GO** for promotion (failed gates `rolling_63d_sharpe`, `psr`). This audit adds a measurement-quality axis to a verdict that was already NO-GO.

## Per-fold diagnostics

| Fold | Test window | Sessions | Cash | Active | Non-zero | Ann. vol | Ann. ret | Sharpe | Published Sharpe | Breadth min | Degenerate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2002-09-30 .. 2003-09-16 | 243 | 136 | 107 | 108 | 0.085186 | 0.237648 | 2.555 | 2.5550 | 4 | no |
| 2 | 2003-03-25 .. 2004-03-10 | 243 | 15 | 228 | 229 | 0.108808 | 0.300947 | 2.582 | 2.5821 | 4 | no |
| 3 | 2003-09-17 .. 2004-09-02 | 243 | 33 | 210 | 212 | 0.094334 | 0.048559 | 0.303 | 0.3027 | 5 | no |
| 4 | 2004-03-11 .. 2005-02-25 | 243 | 50 | 193 | 197 | 0.097484 | 0.143804 | 1.270 | 1.2700 | 5 | no |
| 5 | 2004-09-03 .. 2005-08-22 | 244 | 28 | 216 | 222 | 0.097552 | 0.210168 | 1.949 | 1.9494 | 6 | no |
| 6 | 2005-02-28 .. 2006-02-14 | 244 | 29 | 215 | 220 | 0.101909 | 0.242661 | 2.185 | 2.1849 | 6 | no |
| 7 | 2005-08-23 .. 2006-08-09 | 243 | 45 | 198 | 203 | 0.103713 | 0.262504 | 2.338 | 2.3382 | 6 | no |
| 8 | 2006-02-15 .. 2007-02-01 | 242 | 29 | 213 | 218 | 0.097014 | 0.203470 | 1.891 | 1.8912 | 7 | no |
| 9 | 2006-08-10 .. 2007-07-27 | 242 | 2 | 240 | 241 | 0.104830 | 0.158020 | 1.317 | 1.3166 | 7 | no |
| 10 | 2007-02-02 .. 2008-01-21 | 243 | 53 | 190 | 199 | 0.099696 | 0.227517 | 2.082 | 2.0815 | 7 | no |
| 11 | 2007-07-30 .. 2008-07-15 | 243 | 174 | 69 | 79 | 0.061352 | 0.188161 | 2.741 | 2.7409 | 7 | no |
| 12 | 2008-01-22 .. 2009-01-07 | 244 | 243 | 1 | 2 | 0.000973 | -0.001250 | -21.830 | -21.8299 | 7 | yes |
| 13 | 2008-07-16 .. 2009-07-02 | 244 | 222 | 22 | 23 | 0.036173 | 0.010359 | -0.267 | -0.2665 | 7 | no |
| 14 | 2009-01-08 .. 2009-12-25 | 244 | 104 | 140 | 142 | 0.090487 | 0.179887 | 1.767 | 1.7670 | 7 | no |
| 15 | 2009-07-03 .. 2010-06-21 | 243 | 20 | 223 | 226 | 0.111104 | 0.189350 | 1.524 | 1.5242 | 7 | no |
| 16 | 2009-12-28 .. 2010-12-14 | 244 | 66 | 178 | 182 | 0.097456 | 0.123993 | 1.067 | 1.0671 | 7 | no |
| 17 | 2010-06-22 .. 2011-06-08 | 244 | 50 | 194 | 196 | 0.096266 | 0.125507 | 1.096 | 1.0960 | 7 | no |
| 18 | 2010-12-15 .. 2011-12-01 | 244 | 83 | 161 | 164 | 0.082478 | 0.040007 | 0.243 | 0.2426 | 7 | no |
| 19 | 2011-06-09 .. 2012-05-25 | 244 | 99 | 145 | 151 | 0.064118 | 0.080459 | 0.943 | 0.9429 | 7 | no |
| 20 | 2011-12-02 .. 2012-11-19 | 242 | 25 | 217 | 222 | 0.083572 | 0.122514 | 1.227 | 1.2267 | 7 | no |
| 21 | 2012-05-28 .. 2013-05-14 | 241 | 9 | 232 | 234 | 0.098292 | 0.236863 | 2.206 | 2.2063 | 7 | no |
| 22 | 2012-11-20 .. 2013-11-06 | 243 | 0 | 243 | 243 | 0.099211 | 0.235627 | 2.173 | 2.1734 | 7 | no |
| 23 | 2013-05-15 .. 2014-05-01 | 243 | 0 | 243 | 243 | 0.100279 | 0.101301 | 0.811 | 0.8107 | 7 | no |
| 24 | 2013-11-07 .. 2014-10-24 | 243 | 7 | 236 | 237 | 0.097061 | 0.066881 | 0.483 | 0.4830 | 7 | no |
| 25 | 2014-05-02 .. 2015-04-20 | 243 | 7 | 236 | 237 | 0.091287 | 0.126822 | 1.170 | 1.1702 | 7 | no |
| 26 | 2014-10-27 .. 2015-10-13 | 243 | 40 | 203 | 205 | 0.080171 | 0.091965 | 0.898 | 0.8976 | 7 | no |
| 27 | 2015-04-21 .. 2016-04-06 | 243 | 113 | 130 | 137 | 0.063301 | 0.037671 | 0.279 | 0.2792 | 7 | no |
| 28 | 2015-10-14 .. 2016-09-29 | 243 | 74 | 169 | 175 | 0.066824 | 0.109901 | 1.345 | 1.3453 | 7 | no |
| 29 | 2016-04-07 .. 2017-03-24 | 244 | 1 | 243 | 244 | 0.081393 | 0.044162 | 0.297 | 0.2969 | 7 | no |
| 30 | 2016-09-30 .. 2017-09-18 | 243 | 0 | 243 | 243 | 0.091565 | 0.077977 | 0.633 | 0.6332 | 7 | no |
| 31 | 2017-03-27 .. 2018-03-13 | 243 | 0 | 243 | 243 | 0.101759 | 0.190586 | 1.676 | 1.6764 | 7 | no |
| 32 | 2017-09-19 .. 2018-09-05 | 243 | 2 | 241 | 243 | 0.097026 | 0.130349 | 1.137 | 1.1373 | 7 | no |
| 33 | 2018-03-14 .. 2019-02-28 | 242 | 79 | 163 | 169 | 0.078777 | 0.039473 | 0.247 | 0.2472 | 7 | no |
| 34 | 2018-09-06 .. 2019-08-23 | 243 | 80 | 163 | 169 | 0.078568 | 0.105509 | 1.088 | 1.0883 | 7 | no |
| 35 | 2019-03-01 .. 2020-02-17 | 243 | 3 | 240 | 242 | 0.070959 | 0.250765 | 3.252 | 3.2521 | 7 | no |
| 36 | 2019-08-26 .. 2020-08-11 | 243 | 62 | 181 | 186 | 0.073167 | 0.306239 | 3.912 | 3.9121 | 7 | no |
| 37 | 2020-02-18 .. 2021-02-03 | 244 | 62 | 182 | 187 | 0.095033 | 0.244555 | 2.363 | 2.3629 | 7 | no |
| 38 | 2020-08-12 .. 2021-07-29 | 243 | 0 | 243 | 243 | 0.103498 | 0.102306 | 0.795 | 0.7952 | 7 | no |
| 39 | 2021-02-04 .. 2022-01-21 | 244 | 1 | 243 | 244 | 0.105105 | 0.011215 | -0.084 | -0.0836 | 7 | no |
| 40 | 2021-07-30 .. 2022-07-18 | 243 | 100 | 143 | 149 | 0.082659 | 0.011128 | -0.107 | -0.1073 | 7 | no |
| 41 | 2022-01-24 .. 2023-01-10 | 243 | 218 | 25 | 31 | 0.039776 | 0.055587 | 0.895 | 0.8947 | 7 | no |
| 42 | 2022-07-19 .. 2023-07-05 | 242 | 131 | 111 | 116 | 0.073205 | 0.134079 | 1.558 | 1.5584 | 7 | no |
| 43 | 2023-01-11 .. 2023-12-28 | 243 | 20 | 223 | 229 | 0.098323 | 0.200250 | 1.833 | 1.8332 | 7 | no |
| 44 | 2023-07-06 .. 2024-06-21 | 243 | 8 | 235 | 237 | 0.100200 | 0.202220 | 1.819 | 1.8186 | 7 | no |
| 45 | 2023-12-29 .. 2024-12-16 | 243 | 0 | 243 | 243 | 0.102113 | 0.207298 | 1.834 | 1.8342 | 7 | no |
| 46 | 2024-06-24 .. 2025-06-10 | 242 | 42 | 200 | 202 | 0.094099 | 0.124902 | 1.115 | 1.1148 | 7 | no |
| 47 | 2024-12-17 .. 2025-12-03 | 241 | 42 | 199 | 201 | 0.093498 | 0.203343 | 1.961 | 1.9609 | 7 | no |
| 48 | 2025-06-11 .. 2026-05-28 | 242 | 13 | 229 | 230 | 0.103469 | 0.319743 | 2.897 | 2.8969 | 7 | no |

## Reproduction

```bash
python research/fold_sharpe_degeneracy_audit.py
python -m pytest -q tests/test_fold_sharpe_degeneracy_audit.py
git status --porcelain data/ config/
```
