# Experiment: `reversal_001` evaluation (reversal_001_evaluation)

**Cycle 935.** Execution of the **frozen** pre-registration
(`research/hypotheses/reversal_001.md` + `config/reversal_candidate_001.yaml`, freeze commit
**a910dd4**). The frozen values are re-asserted by the tool before the run; a
post-freeze edit of the config fails closed. No threshold, gate, cost model, universe or
Sharpe convention was changed after the result was known; nothing under `data/` or
`config/` was written; the fetcher was never called; no other candidate was executed,
re-tuned or re-ranked.

## Hypothesis reference

`research/hypotheses/reversal_001.md` (frozen at `a910dd4`).

## Data used

- **Source**: the committed parquet cache `data/raw/{XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY}.parquet`
  (the fetcher is never called).
- **Date range**: 1998-12-22 .. 2026-10-08
- **Frequency**: daily, session hours
- **Universe**: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY (nine GICS sector ETFs; identical cached
  history, 6991 sessions, no gaps)
- **Point-in-time treatment**: the signal at session `t` uses only prices up to and
  including `t`; the weights formed at `t` become effective at `t+1` (one-session lag).
  The benchmark-relative series is computed on the same sessions as the candidate.

## Configuration (frozen)

| Item | Value |
|---|---|
| Signal | trailing 5-session total return, **bottom** 2 of 9, equal weight, cash otherwise |
| Rebalance | every 5 sessions, anchored on the panel's first session |
| Signal lag | 1 session |
| Cost model | 1.0 bp commission + 2.0 bp slippage = **3.0 bp per unit of weight change**, 2.00% annual risk-free |
| Benchmark | 1/N equal-weight buy-and-hold of the same nine ETFs |
| Walk-forward | 10-year train, 12-month test, 6-month step, 21-day purge, 21-day embargo |
| Trials | **1** (one baseline rule, no grid) |
| Pre-registered cost hurdle | median gross capture fraction >= 0.020047 of the cross-sectional dispersion per rebalance |

## Number of trials

**1.** One configuration, one baseline rule. No parameter search.

## Results

### Walk-forward folds (36 folds)

| Fold | Test start | Test end | Sessions | Sharpe (canonical) | Sharpe (backtest) | Benchmark Sharpe | Excess Sharpe | Trades |
|---|---|---|---|---|---|---|---|---|
| 1 | 2008-09-17 | 2009-09-03 | 244 | 1.115563 | 1.057722 | -0.183803 | 1.299367 | 97 |
| 2 | 2009-03-12 | 2010-02-26 | 243 | 1.129524 | 1.008918 | 2.168899 | -1.039374 | 97 |
| 3 | 2009-09-04 | 2010-08-23 | 243 | -0.718321 | -0.913217 | 0.501568 | -1.219888 | 96 |
| 4 | 2010-03-01 | 2011-02-15 | 245 | 0.453508 | 0.215326 | 1.174647 | -0.721139 | 97 |
| 5 | 2010-08-24 | 2011-08-10 | 244 | -1.235722 | -1.402672 | 0.396243 | -1.631964 | 98 |
| 6 | 2011-02-16 | 2012-02-02 | 243 | -0.347653 | -0.554140 | 0.161723 | -0.509376 | 96 |
| 7 | 2011-08-11 | 2012-07-27 | 243 | 1.515665 | 1.398040 | 1.110653 | 0.405012 | 97 |
| 8 | 2012-02-03 | 2013-01-18 | 241 | 0.216691 | -0.118590 | 0.945694 | -0.729003 | 96 |
| 9 | 2012-07-30 | 2013-07-16 | 241 | 0.269010 | -0.104922 | 1.666058 | -1.397048 | 96 |
| 10 | 2013-01-22 | 2014-01-08 | 244 | 0.192443 | -0.190604 | 1.895484 | -1.703041 | 97 |
| 11 | 2013-07-17 | 2014-07-03 | 244 | 0.621687 | 0.207978 | 1.811271 | -1.189583 | 97 |
| 12 | 2014-01-09 | 2014-12-26 | 244 | 1.152452 | 0.799507 | 1.249696 | -0.097245 | 98 |
| 13 | 2014-07-07 | 2015-06-22 | 243 | -0.447083 | -0.782314 | 0.449181 | -0.896264 | 96 |
| 14 | 2014-12-29 | 2015-12-15 | 244 | -0.197653 | -0.481297 | -0.247818 | 0.050165 | 98 |
| 15 | 2015-06-23 | 2016-06-08 | 243 | 0.199199 | -0.083791 | 0.175297 | 0.023902 | 98 |
| 16 | 2015-12-16 | 2016-12-01 | 243 | -0.218062 | -0.553224 | 0.794878 | -1.012941 | 96 |
| 17 | 2016-06-09 | 2017-05-26 | 244 | 0.163382 | -0.243223 | 1.223063 | -1.059681 | 97 |
| 18 | 2016-12-02 | 2017-11-20 | 244 | 0.433117 | -0.121051 | 2.173875 | -1.740757 | 97 |
| 19 | 2017-05-30 | 2018-05-15 | 243 | 0.030250 | -0.425580 | 0.863809 | -0.833559 | 96 |
| 20 | 2017-11-21 | 2018-11-07 | 243 | 0.403525 | 0.068104 | 0.564530 | -0.161005 | 98 |
| 21 | 2018-05-16 | 2019-05-02 | 242 | -0.904300 | -1.191611 | 0.461985 | -1.366284 | 97 |
| 22 | 2018-11-08 | 2019-10-25 | 242 | -2.320596 | -2.415924 | 0.466801 | -2.787397 | 96 |
| 23 | 2019-05-03 | 2020-04-20 | 243 | 0.128602 | -0.065802 | -0.163473 | 0.292076 | 96 |
| 24 | 2019-10-28 | 2020-10-13 | 243 | 0.677851 | 0.518313 | 0.292854 | 0.384998 | 98 |
| 25 | 2020-04-21 | 2021-04-07 | 243 | 0.389294 | 0.180354 | 2.030031 | -1.640737 | 98 |
| 26 | 2020-10-14 | 2021-09-30 | 243 | -0.576516 | -0.785253 | 1.694831 | -2.271348 | 96 |
| 27 | 2021-04-08 | 2022-03-25 | 245 | -0.417965 | -0.696753 | 1.282720 | -1.700685 | 98 |
| 28 | 2021-10-01 | 2022-09-19 | 243 | 0.256473 | 0.029965 | 0.192730 | 0.063743 | 97 |
| 29 | 2022-03-28 | 2023-03-14 | 242 | -0.654263 | -0.826447 | -0.355821 | -0.298442 | 96 |
| 30 | 2022-09-20 | 2023-09-06 | 242 | -0.032086 | -0.257637 | 0.606948 | -0.639034 | 96 |
| 31 | 2023-03-15 | 2024-02-29 | 242 | 0.168888 | -0.129161 | 1.511709 | -1.342821 | 97 |
| 32 | 2023-09-07 | 2024-08-23 | 243 | -0.493053 | -0.757327 | 1.628931 | -2.121984 | 97 |
| 33 | 2024-03-01 | 2025-02-14 | 241 | 0.634352 | 0.355297 | 1.376367 | -0.742015 | 96 |
| 34 | 2024-08-26 | 2025-08-12 | 241 | 0.018547 | -0.215743 | 0.538826 | -0.520279 | 96 |
| 35 | 2025-02-18 | 2026-02-04 | 243 | -0.936186 | -1.120401 | 0.846542 | -1.782728 | 96 |
| 36 | 2025-08-13 | 2026-07-30 | 242 | -0.815128 | -1.080332 | 1.691591 | -2.506719 | 97 |

### Gate statistics

| Statistic | Value | Gate | Outcome |
|---|---|---|---|
| Walk-forward mean OOS Sharpe (canonical) | -0.004016 | >= 0.9 | FAIL |
| Walk-forward median OOS Sharpe | 0.145992 | - | - |
| Walk-forward std of OOS Sharpe | 0.752318 | - | - |
| Positive-fold rate | 0.5833 | >= 0.5 | PASS |
| Pooled OOS trades | 3485 | > 100 | PASS |
| Benchmark-relative net excess (mean fold Sharpe difference) | -0.920641 | - | - |
| Excess 95% CI (moving block, 2000 draws, block 4, seed 20240101) | [-1.186788, -0.740217] | excludes zero | PASS |
| Deflated Sharpe Ratio (N = 1) | 0.055015 (probability 0.521937) | z > 0 | PASS |
| Out-of-sample sessions | 4494 | - | - |
| Absolute out-of-sample Sharpe (the rule holds cash most of the time) | 0.070196 | - | - |
| Absolute out-of-sample annualised return | 0.8254% | - | - |

### The pre-registered cost hurdle

| Quantity | Value |
|---|---|
| Median gross capture fraction (out-of-sample rebalances) | -1.259560 (-125.9560%) |
| Mean / min / max | -1.242060 / -1.699920 / -0.605004 |
| Capture-fraction observations | 899 |
| Pre-registered hurdle | 0.020047 (2.0047%) |
| **Realized** turnover | 100.7664 units/yr (the pre-registered convention estimated 52) |
| **Realized** cost drag | 3.0230%/yr |
| **Hurdle recomputed on the realized turnover** | 0.042843 (4.2843%) |

**Turnover-convention correction (disclosed).** The pre-registered estimate -- one
book rotation per rebalance, 52 units/yr -- is a *lower* bound for this rule, not the
upper bound the Cycle-934 shortlist stated: the rule rotates two of nine names, so a
typical rebalance changes 1.5-2.0 units of weight. The **realized** turnover is
100.7664 units/yr, i.e. a
3.0230%/yr drag, and the cost hurdle recomputed on
it is 0.042843 of the cross-sectional dispersion per rebalance
instead of 0.020047. **The outcome does not depend on the
correction**: the measured capture fraction is -1.259560, which is of the
*opposite sign* and roughly 29
times the magnitude of either hurdle. This correction is published here rather than
applied silently to the frozen specification.

### The mirror test

The rejected `sectorrotation_001` / `sectorrotation_002` signal (252-day momentum, 21-day
skip, top 50% at month end, one-session lag) is rebuilt from its own frozen config on the
same nine-sector panel and the same folds. The candidate's benchmark-relative excess is
regressed on the **negated** mirror excess; the residual's mean is the part of the
candidate's result that the rejected signal does **not** explain.

| Statistic | Value |
|---|---|
| Correlation(candidate excess, mirror excess) | 0.155479 |
| R^2 of the candidate excess on the negated mirror excess | 0.024174 |
| Slope on the negated mirror excess | -0.412205 |
| Residual mean | -0.000000 |
| Residual mean 95% CI | [-0.000225, 0.000051] |
| Mirror signal's own mean excess | -0.000014 |

### Era stability (post-2009 sub-sample)

| Statistic | Value |
|---|---|
| Benchmark-relative net excess (post-2009 folds) | -0.984070 |
| Folds in the sub-sample | 35 |

## Falsification condition (pre-registered) and outcome

| # | Condition | Observed | Requirement | Outcome |
|---|---|---|---|---|
| i | walk-forward mean OOS Sharpe (net, canonical) >= 0.9 | -0.004015631631475617 | 0.9 | **FIRED** |
| ii | benchmark-relative net excess bootstrap 95% CI excludes zero | [-1.186788, -0.740217] (significantly NEGATIVE) | excludes zero | not fired |
| iii | benchmark-relative net excess positive in the post-2009 sub-sample | -0.9840699659496313 | > 0 | **FIRED** |
| iv | median gross capture fraction >= the pre-registered cost hurdle | -1.259559874976633 | 0.020047 | **FIRED** |
| v | positive-fold rate >= 0.5 and pooled OOS trades > 100 | rate 0.5833, trades 3485 | rate >= 0.5, trades > 100 | not fired |
| vi | the excess is not explained by the negated rejected sector-momentum signal | residual mean -0.000000 CI [-0.000225, 0.000051] | residual CI excludes zero | **FIRED** |

**Rejected/Failed (a pre-registered falsification condition fired)**

## Decision

The candidate is **falsified**: condition(s) i, iii, iv, vi fired. It is labelled **Rejected/Failed**; it is not promoted, not simulated and not paper-traded, and its configuration is retired as written (no variant is opened).

**No other candidate's verdict changes.** The incumbent `tsmomentum_spytrend_001` stays a
**Credible Candidate** and **NO-GO** for promotion; every closed line keeps its committed
status.

## Reproduction commands

```bash
python research/reversal_001_evaluation.py
python -m pytest -q tests/test_reversal_001_evaluation.py
git status --porcelain data/
```
