# Experiment: `pairs_001` evaluation (pairs_001_evaluation)

**Cycle 936.** Execution of the **frozen** pre-registration
(`research/hypotheses/pairs_001.md` + `config/pairs_candidate_001.yaml`, freeze commit
**fe17260**). The frozen values are re-asserted by the tool before the run; a
post-freeze edit of the config fails closed. No threshold, gate, cost model, universe or
Sharpe convention was changed after the result was known; nothing under `data/` or
`config/` was written; the fetcher was never called; no other candidate was executed,
re-tuned or re-ranked.

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
| 1 | 2008-09-17 | 2009-09-03 | 244 | 0.261516 | 0.066108 | 0.261516 | 97 |
| 2 | 2009-03-12 | 2010-02-26 | 243 | -1.070847 | -1.282899 | -1.070847 | 97 |
| 3 | 2009-09-04 | 2010-08-23 | 243 | -4.514317 | -4.301167 | -4.514317 | 96 |
| 4 | 2010-03-01 | 2011-02-15 | 245 | -6.260876 | -5.580462 | -6.260876 | 97 |
| 5 | 2010-08-24 | 2011-08-10 | 244 | -5.744202 | -5.314012 | -5.744202 | 98 |
| 6 | 2011-02-16 | 2012-02-02 | 243 | -2.958713 | -3.003016 | -2.958713 | 96 |
| 7 | 2011-08-11 | 2012-07-27 | 243 | -2.876394 | -2.956996 | -2.876394 | 97 |
| 8 | 2012-02-03 | 2013-01-18 | 241 | -5.822682 | -5.486781 | -5.822682 | 96 |
| 9 | 2012-07-30 | 2013-07-16 | 241 | -6.055767 | -5.606576 | -6.055767 | 96 |
| 10 | 2013-01-22 | 2014-01-08 | 244 | -4.495706 | -4.229645 | -4.495706 | 95 |
| 11 | 2013-07-17 | 2014-07-03 | 244 | -4.800803 | -4.429071 | -4.800803 | 95 |
| 12 | 2014-01-09 | 2014-12-26 | 244 | -6.144111 | -5.426593 | -6.144111 | 98 |
| 13 | 2014-07-07 | 2015-06-22 | 243 | -3.810001 | -3.547507 | -3.810001 | 96 |
| 14 | 2014-12-29 | 2015-12-15 | 244 | -2.797636 | -2.737644 | -2.797636 | 98 |
| 15 | 2015-06-23 | 2016-06-08 | 243 | -2.350287 | -2.478956 | -2.350287 | 98 |
| 16 | 2015-12-16 | 2016-12-01 | 243 | -2.093125 | -2.276382 | -2.093125 | 94 |
| 17 | 2016-06-09 | 2017-05-26 | 244 | -3.227137 | -3.289160 | -3.227137 | 95 |
| 18 | 2016-12-02 | 2017-11-20 | 244 | -4.736939 | -4.836270 | -4.736939 | 97 |
| 19 | 2017-05-30 | 2018-05-15 | 243 | -4.856397 | -4.486118 | -4.856397 | 96 |
| 20 | 2017-11-21 | 2018-11-07 | 243 | -3.829704 | -3.620330 | -3.829704 | 94 |
| 21 | 2018-05-16 | 2019-05-02 | 242 | -3.009410 | -2.906538 | -3.009410 | 93 |
| 22 | 2018-11-08 | 2019-10-25 | 242 | -3.551818 | -3.375604 | -3.551818 | 96 |
| 23 | 2019-05-03 | 2020-04-20 | 243 | -2.879776 | -2.745865 | -2.879776 | 96 |
| 24 | 2019-10-28 | 2020-10-13 | 243 | -3.626955 | -3.093512 | -3.626955 | 98 |
| 25 | 2020-04-21 | 2021-04-07 | 243 | -1.779813 | -1.760119 | -1.779813 | 98 |
| 26 | 2020-10-14 | 2021-09-30 | 243 | -0.377145 | -0.589309 | -0.377145 | 92 |
| 27 | 2021-04-08 | 2022-03-25 | 245 | -2.170259 | -2.153904 | -2.170259 | 94 |
| 28 | 2021-10-01 | 2022-09-19 | 243 | -3.141842 | -2.780950 | -3.141842 | 97 |
| 29 | 2022-03-28 | 2023-03-14 | 242 | -3.325074 | -2.972502 | -3.325074 | 96 |
| 30 | 2022-09-20 | 2023-09-06 | 242 | -3.512729 | -3.006494 | -3.512729 | 96 |
| 31 | 2023-03-15 | 2024-02-29 | 242 | -3.820591 | -3.294773 | -3.820591 | 95 |
| 32 | 2023-09-07 | 2024-08-23 | 243 | -2.065968 | -2.159821 | -2.065968 | 93 |
| 33 | 2024-03-01 | 2025-02-14 | 241 | -1.677175 | -1.852730 | -1.677175 | 94 |
| 34 | 2024-08-26 | 2025-08-12 | 241 | -3.395498 | -3.285614 | -3.395498 | 96 |
| 35 | 2025-02-18 | 2026-02-04 | 243 | -3.319556 | -3.112881 | -3.319556 | 96 |
| 36 | 2025-08-13 | 2026-07-30 | 242 | -1.853381 | -1.857042 | -1.853381 | 97 |

### Gate statistics

| Statistic | Value | Gate | Outcome |
|---|---|---|---|
| Walk-forward mean OOS Sharpe (canonical) | -3.380309 | >= 0.9 | FAIL |
| Walk-forward median OOS Sharpe | -3.322315 | - | - |
| Walk-forward std of OOS Sharpe | 1.571789 | - | - |
| Positive-fold rate | 0.0278 | >= 0.5 | FAIL |
| Pooled OOS trades | 3453 | > 100 | PASS |
| Net excess over cash (mean fold Sharpe difference) | -3.380309 | - | - |
| Excess 95% CI (moving block, 2000 draws, block 4, seed 20240101) | [-4.101434, -2.881548] | excludes zero | PASS |
| Deflated Sharpe Ratio (N = 1) | -8.538808 (probability 0.000000) | z > 0 | FAIL |
| Out-of-sample sessions | 4494 | - | - |
| Absolute out-of-sample Sharpe | -2.637485 | - | - |
| Absolute out-of-sample annualised return | -25.8137% | - | - |

### Per-pair attribution (out of sample)

| Pair | Net excess annualized | Sharpe | Trades |
|---|---|---|---|
| XLP/XLU | -0.032524 | -1.261827 | 893 |
| XLF/XLK | -0.040877 | -1.000159 | 950 |
| XLE/XLB | -0.047784 | -1.373462 | 980 |
| XLI/XLB | -0.042787 | -2.152719 | 952 |
| XLV/XLY | -0.046602 | -1.521623 | 935 |
| XLK/XLU | -0.047563 | -1.337530 | 1088 |

### Cost model and the implied hurdle

| Quantity | Value |
|---|---|
| Gross scale (frozen, shortlist Cycle 934) | 69.6626%/yr |
| Realized turnover | 294.6168 units/yr (shortlist proxy: 52 units/yr, a lower bound) |
| Realized turnover cost drag | 0.0029%/yr |
| Realized borrow drag (25 bp x short notional per active pair per rebalance) | 20.3271%/yr |
| Realized total cost drag | 20.3300%/yr |
| Gross excess (before borrow) annualized | -5.4866% |
| Net excess after borrow annualized | -25.8137% |

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
| i | walk-forward mean OOS Sharpe (net, canonical) >= 0.9 | -3.380308782997972 | 0.9 | **FIRED** |
| ii | net excess over cash bootstrap 95% CI excludes zero | [-4.101434, -2.881548] | excludes zero | not fired |
| iii | cointegration of every pair holds on all training windows | any pair failed | no pair fails | **FIRED** |
| iv | net excess survives the pre-registered borrow cost | -0.2581371841606682 | > 0 | **FIRED** |

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
