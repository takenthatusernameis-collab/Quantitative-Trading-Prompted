# Experiment: `pairs_001` evaluation (pairs_001_evaluation)

**Cycle 936.** Execution of the **frozen** pre-registration
(`research/hypotheses/pairs_001.md` + `config/pairs_candidate_001.yaml`, freeze commit
**fe17260**). The frozen values are re-asserted by the tool before the run; a
post-freeze edit of the config fails closed. No threshold, gate, cost model, universe or
Sharpe convention was changed after the result was known; nothing under `data/` or
`config/` was written; the fetcher was never called; no other candidate was executed,
re-tuned or re-ranked.

**Correction notice (published 2026-10-21).** This record was regenerated after an implementation defect in the evaluator was found and fixed: the weight frame was initialised to `0.0` instead of `NaN`, so the forward fill was a no-op and every position was held for **one** session instead of the frozen **five**, and a pair that left the active set at a rebalance was never exited to flat. The defect was in the **evaluator**, not in the frozen specification: `config/pairs_candidate_001.yaml` and `research/hypotheses/pairs_001.md` are byte-identical to the freeze commit `fe17260`; no frozen value, threshold, gate, cost model, universe or Sharpe convention changed. The superseded figures were never published in this repository (the defect was found and fixed before the record was committed, so no pre-fix version exists in the git history); the correction of record is `research/experiments/pairs_001_evaluation_erratum_001.md`, which publishes the post-fix figures together with the Cycle-940 corrections to the cost-drag lines.

**Correction notice (published by Cycle 940).** A second, independent defect was found in the same evaluator: the *reported* realized turnover cost drag applied the 3.0 bp cost rate to a series that already carried it, so the published drag (0.0006%/yr) understated the drag implied by the record's own turnover figure (68.6916 units/yr x 3.0 bp = 2.0607%/yr) by a factor of the cost rate. The drag is now applied once (2.1364%/yr measured from the pair-level cost series) and the record now publishes the gross excess **before any cost** (8.7862%/yr) next to the excess net of the turnover cost and before borrow (6.6497%/yr), which the previous version labelled "Gross excess (before borrow)". The strategy's return series, the fold Sharpes, the bootstrap CI, the Deflated Sharpe Ratio and the **verdict are unchanged**; only the reported drag lines and their labels changed. See `research/experiments/pairs_001_evaluation_erratum_001.md`.

## Hypothesis reference

`research/hypotheses/pairs_001.md` (frozen at `fe17260`).

## Data used

- **Source**: the committed parquet cache
  `data/raw/{XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY}.parquet` (the fetcher is never called).
- **Date range**: 1998-12-22 .. 2026-10-08
- **Frequency**: daily, session hours
- **Universe**: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY (nine GICS sector ETFs; identical cached
  history, 6991 sessions, no gaps)
- **Point-in-time treatment**: the z-score at session `t` uses only prices up to and
  including `t`; the weights formed at `t` become effective at `t+1` (one-session lag).
  Positions are held 5 sessions between rebalances.

## Configuration (frozen)

| Item | Value |
|---|---|
| Signal | z-score of log(price_a)/price_b over the trailing 126-session window; contrarian side when |z| >= 1.0 |
| Pairs | XLP/XLU, XLF/XLK, XLE/XLB, XLI/XLB, XLV/XLY, XLK/XLU (six pre-registered; components of the one configuration, not a grid) |
| Construction | dollar-neutral per pair: long 0.5 of the cheap leg, short 0.5 of the rich leg; book is market-neutral (net 0) |
| Rebalance | every 5 sessions, anchored on the panel's first session; positions held 5 sessions |
| Signal lag | 1 session |
| Cost model | 1.0 bp commission + 2.0 bp slippage = **3.0 bp per unit of weight change** (both legs), plus pre-registered borrow **25 bp per unit of short notional per rebalance** (assumption; not in `config/settings.yaml`) |
| Risk-free hurdle | 2.00% annual (benchmark is cash); canonical Sharpe uses rf 0 |
| Benchmark | cash (market-neutral book vs cash; net excess = net return) |
| Walk-forward | 10-year train, 12-month test, 6-month step, 21-day purge, 21-day embargo |
| Trials | **1** (one baseline rule, no grid) |
| Cointegration test | Engle-Granger on the log price ratio, alpha 0.05, each fold's training window only |

## Number of trials

**1.** One configuration, one baseline rule. The six pairs are
pre-registered components of that single configuration; no pair was selected by a search
on the full sample. No parameter search.

## Results

### Walk-forward folds (36 folds)

| Fold | Test start | Test end | Sessions | Sharpe (canonical) | Sharpe (backtest) | Excess over cash (Sharpe) | Trades |
|---|---|---|---|---|---|---|---|
| 1 | 2008-09-17 | 2009-09-03 | 244 | 0.008375 | -0.233643 | 0.008375 | 37 |
| 2 | 2009-03-12 | 2010-02-26 | 243 | 0.058170 | -0.141050 | 0.058170 | 36 |
| 3 | 2009-09-04 | 2010-08-23 | 243 | -1.412554 | -1.497443 | -1.412554 | 35 |
| 4 | 2010-03-01 | 2011-02-15 | 245 | -2.890131 | -2.644048 | -2.890131 | 32 |
| 5 | 2010-08-24 | 2011-08-10 | 244 | -2.751527 | -2.601552 | -2.751527 | 35 |
| 6 | 2011-02-16 | 2012-02-02 | 243 | -1.170330 | -1.286265 | -1.170330 | 39 |
| 7 | 2011-08-11 | 2012-07-27 | 243 | -0.270261 | -0.480111 | -0.270261 | 39 |
| 8 | 2012-02-03 | 2013-01-18 | 241 | -0.832936 | -1.057447 | -0.832936 | 35 |
| 9 | 2012-07-30 | 2013-07-16 | 241 | -1.745650 | -1.858121 | -1.745650 | 35 |
| 10 | 2013-01-22 | 2014-01-08 | 244 | -1.889820 | -1.933510 | -1.889820 | 40 |
| 11 | 2013-07-17 | 2014-07-03 | 244 | -1.186887 | -1.323271 | -1.186887 | 42 |
| 12 | 2014-01-09 | 2014-12-26 | 244 | -1.413287 | -1.499111 | -1.413287 | 40 |
| 13 | 2014-07-07 | 2015-06-22 | 243 | -0.835770 | -0.989921 | -0.835770 | 39 |
| 14 | 2014-12-29 | 2015-12-15 | 244 | 0.205462 | 0.001066 | 0.205462 | 43 |
| 15 | 2015-06-23 | 2016-06-08 | 243 | 0.586611 | 0.402094 | 0.586611 | 46 |
| 16 | 2015-12-16 | 2016-12-01 | 243 | -0.281158 | -0.480115 | -0.281158 | 44 |
| 17 | 2016-06-09 | 2017-05-26 | 244 | -1.628800 | -1.685325 | -1.628800 | 37 |
| 18 | 2016-12-02 | 2017-11-20 | 244 | -1.457922 | -1.574132 | -1.457922 | 34 |
| 19 | 2017-05-30 | 2018-05-15 | 243 | -1.636764 | -1.641710 | -1.636764 | 36 |
| 20 | 2017-11-21 | 2018-11-07 | 243 | -0.771504 | -0.919350 | -0.771504 | 40 |
| 21 | 2018-05-16 | 2019-05-02 | 242 | -0.631266 | -0.790189 | -0.631266 | 42 |
| 22 | 2018-11-08 | 2019-10-25 | 242 | -0.652498 | -0.812992 | -0.652498 | 39 |
| 23 | 2019-05-03 | 2020-04-20 | 243 | -0.984274 | -1.049364 | -0.984274 | 41 |
| 24 | 2019-10-28 | 2020-10-13 | 243 | -2.211562 | -1.711751 | -2.211562 | 38 |
| 25 | 2020-04-21 | 2021-04-07 | 243 | -1.270144 | -1.229508 | -1.270144 | 38 |
| 26 | 2020-10-14 | 2021-09-30 | 243 | 0.685299 | 0.522665 | 0.685299 | 43 |
| 27 | 2021-04-08 | 2022-03-25 | 245 | -0.314706 | -0.495489 | -0.314706 | 38 |
| 28 | 2021-10-01 | 2022-09-19 | 243 | -1.204888 | -1.179301 | -1.204888 | 28 |
| 29 | 2022-03-28 | 2023-03-14 | 242 | -1.261136 | -1.247910 | -1.261136 | 31 |
| 30 | 2022-09-20 | 2023-09-06 | 242 | -1.719922 | -1.569557 | -1.719922 | 36 |
| 31 | 2023-03-15 | 2024-02-29 | 242 | -1.297586 | -1.294995 | -1.297586 | 40 |
| 32 | 2023-09-07 | 2024-08-23 | 243 | 1.271531 | 1.203284 | 1.271531 | 42 |
| 33 | 2024-03-01 | 2025-02-14 | 241 | 0.867304 | 0.726886 | 0.867304 | 40 |
| 34 | 2024-08-26 | 2025-08-12 | 241 | -0.346043 | -0.522568 | -0.346043 | 39 |
| 35 | 2025-02-18 | 2026-02-04 | 243 | 0.298810 | 0.102658 | 0.298810 | 39 |
| 36 | 2025-08-13 | 2026-07-30 | 242 | 0.241369 | 0.032220 | 0.241369 | 42 |

### Gate statistics

| Statistic | Value | Gate | Outcome |
|---|---|---|---|
| Walk-forward mean OOS Sharpe (canonical) | -0.829067 | >= 0.9 | FAIL |
| Walk-forward median OOS Sharpe | -0.910022 | - | - |
| Walk-forward std of OOS Sharpe | 0.981866 | - | - |
| Positive-fold rate | 0.2500 | >= 0.5 | FAIL |
| Pooled OOS trades | 1380 | > 100 | PASS |
| Net excess over cash (mean fold Sharpe difference) | -0.829067 | - | - |
| Excess 95% CI (moving block, 2000 draws, block 4, seed 20240101) | [-1.219160, -0.467513] | excludes zero | PASS |
| Deflated Sharpe Ratio (N = 1) | -3.341643 (probability 0.000416) | z > 0 | FAIL |
| Out-of-sample sessions | 4494 | - | - |
| Absolute out-of-sample Sharpe | -0.654744 | - | - |
| Absolute out-of-sample annualised return | -13.6774% | - | - |

### Per-pair attribution (out of sample)

| Pair | Net excess annualized | Sharpe | Trades |
|---|---|---|---|
| XLP/XLU | 0.009094 | 0.179750 | 226 |
| XLF/XLK | -0.026539 | -0.314578 | 205 |
| XLE/XLB | -0.032287 | -0.408004 | 211 |
| XLI/XLB | -0.019626 | -0.451870 | 228 |
| XLV/XLY | -0.028693 | -0.439405 | 201 |
| XLK/XLU | -0.038723 | -0.452537 | 194 |

### Cost model and the implied hurdle

| Quantity | Value |
|---|---|
| Gross scale (frozen, shortlist Cycle 934) | 69.6626%/yr |
| Realized turnover | 68.6916 units/yr (shortlist proxy: 52 units/yr, a lower bound) |
| Realized turnover cost drag | 2.1364%/yr |
| Realized borrow drag (25 bp x short notional per active pair per rebalance) | 20.3271%/yr |
| Realized total cost drag | 22.4636%/yr |
| Gross excess (before any cost) annualized | 8.7862% |
| Excess net of the turnover cost, before borrow, annualized | 6.6497% |
| Net excess after borrow annualized | -13.6774% |

**Turnover-convention disclosure.** The Cycle-934 shortlist's 52 units/yr figure was
published as an upper bound and corrected in Cycle 935 to a lower bound (a rule that
rotates two legs turns over more than one book rotation per rebalance). No hurdle number
is frozen from that proxy; the hurdle is a formula over the measured realized turnover
and the pre-registered borrow cost, and both are measured above.

### Cointegration test (Engle-Granger, alpha 0.05, training-window data only)

| Pair | Train windows | Cointegrated | Min p-value | Max p-value | Outcome |
|---|---|---|---|---|---|
| XLP/XLU | 36 | 14 | 0.001032 | 0.990904 | FAILS a window |
| XLF/XLK | 36 | 4 | 0.000193 | 1.000000 | FAILS a window |
| XLE/XLB | 36 | 1 | 0.022739 | 0.992559 | FAILS a window |
| XLI/XLB | 36 | 7 | 0.002240 | 0.871773 | FAILS a window |
| XLV/XLY | 36 | 11 | 0.000992 | 0.555322 | FAILS a window |
| XLK/XLU | 36 | 10 | 0.001517 | 0.813088 | FAILS a window |

### Era stability

No post-2009 sub-sample condition is pre-registered for pairs_001; the four falsification
conditions above are the complete set.

## Falsification condition (pre-registered) and outcome

| # | Condition | Observed | Requirement | Outcome |
|---|---|---|---|---|
| i | walk-forward mean OOS Sharpe (net, canonical) >= 0.9 | -0.829066502937328 | 0.9 | **FIRED** |
| ii | net excess over cash bootstrap 95% CI excludes zero | [-1.219160, -0.467513] | excludes zero | not fired |
| iii | cointegration of every pair holds on all training windows | any pair failed | no pair fails | **FIRED** |
| iv | net excess survives the pre-registered borrow cost | -0.13677385668139808 | > 0 | **FIRED** |

**Rejected/Failed (a pre-registered falsification condition fired)**

## Decision

The candidate is **falsified**: condition(s) i, iii, iv fired. It is labelled **Rejected/Failed**; it is not promoted, not simulated and not paper-traded, and its configuration is retired as written (no variant is opened).

**No other candidate's verdict changes.** The incumbent `tsmomentum_spytrend_001` stays a
**Credible Candidate** and **NO-GO** for promotion; every closed line keeps its committed
status.

## Reproduction commands

```bash
python research/pairs_001_evaluation.py
python -m pytest -q tests/test_pairs_001_evaluation.py
git status --porcelain data/
git diff --name-only HEAD -- config/settings.yaml
```
