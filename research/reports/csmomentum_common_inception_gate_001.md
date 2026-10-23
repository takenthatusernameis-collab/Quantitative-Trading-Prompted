# CSMomentum Common-Inception Gate Audit (csmomentum_common_inception_gate_001, Cycle 907)

## Summary

`csmomentum_001`'s published gate table was measured on the **union calendar** of the raw
cache, whose cross-section is ragged (it starts with one asset and reaches the full 18-asset
universe only at the common inception). Cycle 905 pre-registered, in
`config/sample_policy.yaml` (`candidates.csmomentum_001`), that the candidate's long-sample
diagnostic is evaluated on the **common-inception** sample, with the union sample and the
warm-up-preserving window published beside it. This cycle re-derives the candidate's
**config-faithful** walk-forward on the three pre-registered samples and publishes the three
gate tables side by side.

**Gate scale: backtest scale (`backtest_sharpe_ratio`)** -- the scale on which the candidate's
pre-registered walk-forward gate was originally evaluated. The canonical scale
(`arithmetic_annualized_rf0`) is published beside the summary but is never used for a gate.

| Sample | Sessions | Window | Folds | WF mean OOS Sharpe | Median | Positive folds | Pooled OOS trades | Gate 1 | Gate 2 | Gate 3 | Gate 4 (plateau) | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| union_sample | 8482 | 1993-01-29..2026-10-09 | 48 | 0.6975 | 0.6179 | 79.17% | 400 | FAIL | PASS | PASS | NOT EVALUATED | **Rejected/Failed** |
| common_inception_slice | 5202 | 2006-02-06..2026-10-09 | 21 | 0.5861 | 0.6311 | 76.19% | 166 | FAIL | PASS | PASS | NOT EVALUATED | **Rejected/Failed** |
| common_inception_window | 5202 | 2006-02-06..2026-10-09 | 21 | 0.5861 | 0.6311 | 76.19% | 166 | FAIL | PASS | PASS | NOT EVALUATED | **Rejected/Failed** |

**The verdict does not move.** The candidate stays **Rejected/Failed** on all three samples:
gate 1 (walk-forward mean OOS Sharpe >= 0.9) fails on every
sample, by 0.2025 on the union
sample and by 0.3139 on the
pre-registered common-inception samples. The published rejection is therefore **not** an
artefact of the sample definition; on the pre-registered sample the gate-1 margin is
*larger*, not smaller.

Two further findings are published below and neither favours the candidate:

1. **The ragged era never reaches a fold's test window.** The union sample contains
   1763 of 8482 sessions with fewer
   than 5 selectable assets (the single-asset / degenerate-selection regime),
   from 1993-01-29 to
   2000-01-21 -- i.e. **all of them lie before** the
   earliest fold's test window (2002-09-30). Every fold
   of every sample is therefore *traded* on a populated cross-section (at least
   12
   assets with a valid momentum at the start of a test window), and no fold is *trained* on a
   degenerate cross-section at its training-window end either (a ten-year training window is
   longer than the ragged era).
2. **The sample and the fold calendar move together.** The three samples' walk-forward
   calendars are anchored at their own declared start, so the common-inception calendars are
   offset by a few sessions from the union calendar. On the *same* test windows all three
   paths produce the same numbers (section 5), i.e. the difference between the union sample's
   0.6975 and the common-inception samples'
   0.5861 is a fold-calendar effect of the size of the fold-to-fold
   scatter, not a change in the strategy's behaviour.
3. **The folds are not independent observations.** The 6-month step over a 12-month test
   window makes consecutive test windows overlap and the repository's generator does not apply
   the embargo parameter, so the honest count of independent test windows is
   24 (union sample) and
   11 (common-inception samples) -- a property of the
   published protocol that applies to every sample equally (section 4.4).

No gate, threshold, decision mapping, universe, cost model, parameter, candidate
configuration or committed artifact was changed by this cycle.

## 1. Method

### 1.1 Data and provenance (read-only)

| Item | Value |
|---|---|
| Universe | SPY, QQQ, IWM, TLT, GLD, DBC, VNQ, EFA, EEM, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY (18 assets) |
| Source | committed raw cache `data/raw/*.parquet` (cache-only: the fetcher is never called, so nothing is downloaded and nothing is written) |
| Evaluation window | 1993-01-01 .. 2026-10-09 (the frozen `evaluation.splits.test_end`) |
| Common inception | **2006-02-06** (re-derived from the raw cache: max of the per-symbol first dates; no date in the policy is trusted) |
| Costs | 1.0 bps commission + 2.0 bps slippage per round trip |
| Signal | lookback 252, skip 21, top fraction 0.5 |

Per-symbol cache fingerprint (derived at run time, never a frozen literal):

| Symbol | First date | Last date | Rows | SHA-256 (first 16) |
|---|---|---|---|---|
| SPY | 1993-01-29 | 2026-10-22 | 8491 | `f307f910a62dc3e2` |
| QQQ | 1999-03-10 | 2026-10-22 | 6949 | `3de8a01c4f0d6f77` |
| IWM | 2000-05-26 | 2026-10-22 | 6641 | `0e32b42393e5dad6` |
| TLT | 2002-07-30 | 2026-10-22 | 6098 | `851db269e1622eb6` |
| GLD | 2004-11-18 | 2026-10-22 | 5516 | `6e681051e18253fa` |
| DBC | 2006-02-06 | 2026-10-21 | 5210 | `a04e11a54bb3710f` |
| VNQ | 2004-09-29 | 2026-10-08 | 5542 | `8714f6b1bf45d1b0` |
| EFA | 2001-08-27 | 2026-10-22 | 6326 | `f72c519b09744671` |
| EEM | 2003-04-14 | 2026-10-22 | 5920 | `17ad1692de6eee0b` |
| XLB | 1998-12-22 | 2026-10-08 | 6991 | `465b9a7b6c784869` |
| XLE | 1998-12-22 | 2026-10-08 | 6991 | `408b2806f7dbde65` |
| XLF | 1998-12-22 | 2026-10-08 | 6991 | `2f8eeb83b2024b69` |
| XLI | 1998-12-22 | 2026-10-08 | 6991 | `176eaa15a62526ec` |
| XLK | 1998-12-22 | 2026-10-08 | 6991 | `b66776c5c1c70885` |
| XLP | 1998-12-22 | 2026-10-08 | 6991 | `d1ac5528a51c5470` |
| XLU | 1998-12-22 | 2026-10-08 | 6991 | `c9550ef0e461368e` |
| XLV | 1998-12-22 | 2026-10-08 | 6991 | `bcf7029ba61bac58` |
| XLY | 1998-12-22 | 2026-10-08 | 6991 | `7a64cd50a03d5d70` |

### 1.2 The three pre-registered samples

| Sample | Definition | Price frame | Warm-up |
|---|---|---|---|
| `union_sample` | the union calendar of the raw cache, truncated at the frozen test end | 1993-01-29..2026-10-09 (8482 sessions, price width 1..18) | preserved |
| `common_inception_slice` | the price frame is truncated at the common inception **before** the signal is formed | 2006-02-06..2026-10-09 (5202 sessions, price width 18..18) | none (the signal has no pre-inception history) |
| `common_inception_window` | the union frame is kept; only the evaluation window is truncated | 2006-02-06..2026-10-09 (5202 sessions, price width 18..18) | preserved |

### 1.3 The config-faithful path

The path is the **config-faithful month-end schedule** of
`src/backtest/rebalance.py:build_month_end_weights`, executed exactly as
`research/month_end_candidate_reaudit.py` executes it: the signal is formed on the **last
session** of the calendar month and the positions become effective on the **next** session and
are held until the next month-end signal. It is **not** the legacy calendar rule
(`weights.index.is_month_end`, published mean OOS Sharpe 0.6868) and **not** the daily re-rank
path (0.6928). The tool asserts the equality of the path with the shared module and the
point-in-time property of every segment (the weights of a segment equal the selection at its
own signal date and become effective strictly after it).

### 1.4 The pre-registered walk-forward protocol

10y train / 12m test /
6m step, 21d purge, 21d
embargo, **fixed parameters** (no per-fold re-optimisation). The fold windows are slices of
**one continuously computed point-in-time path** per sample; the training window is a label of
the design (the parameters are fixed), and it is reported because it is where the sample
difference shows up.

**What the repository's generator actually applies** (`src/evaluation/walkforward.py:generate_walkforward_splits`):
the 21-day **purge** is applied as a gap between the end of the training
window and the start of the test window; the 21-day **embargo** parameter is
accepted but **not applied** to the fold construction, because the folds roll: the next fold's
training window starts 6 months after the previous fold's and
therefore contains the tail of the previous fold's test window. This is the repository's own
convention -- it is the generator that produced the candidate's own published 48-fold record and
the Cycle 871 config-faithful record -- so all three samples are measured identically and the
comparison is unaffected. It does mean that the folds are **not independent observations**: the
honest count of disjoint test windows is published in section 4.4. Because the parameters are
fixed, no information from a test window enters the trading path; the overlap is a
statistical-independence limitation, not a look-ahead.

Each sample's fold calendar is generated over that sample's own declared window: the union
sample over the configuration's `history_start`
(1993-01-01), the two common-inception samples over the
re-derived common inception (2006-02-06). A fold can only be trained on data the
sample actually contains, so the common-inception samples' first out-of-sample fold starts
after a full 10-year training window inside the sample.

### 1.5 The gate table and the decision mapping

The gate table is the candidate's own pre-registered table
(`config/csmomentum_candidate_001.yaml:evaluation.promotion_gates`):

| Gate | Threshold | Meaning |
|---|---|---|
| 1. `wf_mean_oos_sharpe` | >= 0.9 | mean out-of-sample Sharpe over the folds (backtest scale) |
| 2. `positive_fold_rate` | >= 0.5 | share of folds with a positive out-of-sample Sharpe |
| 3. `pooled_oos_trades` | > 100 | pooled out-of-sample trade days over the folds |
| 4. `plateau` | >= 0.667 (>= 2 of 3 lookbacks) | **NOT EVALUATED** -- the 27-configuration grid is out of scope for this cycle |

The decision mapping is the published one (`research/month_end_candidate_reaudit.py:gates_for`):
the candidate is **falsified** when gate 1 or gate 2 fails, and the label is then
**Rejected/Failed**; otherwise the label is *exploratory signal*. Gate 3 and gate 4 are
published but are not part of the falsification condition.

## 2. The reproduction anchor (the union sample)

The tool's OVERALL depends on reproducing the committed config-faithful record of
`research/reports/month_end_candidate_reaudit_001.md` (section 2.3) on the union sample, at the
tolerance of the last published decimal.

| Metric | Published | Observed | Abs. diff | Tolerance | Result |
|---|---|---|---|---|---|
| `n_folds` | 48 | 48.000000 | 0.000e+00 | 1e+00 | MATCH |
| `mean_test_sharpe` | 0.6975 | 0.697524 | 2.434e-05 | 1e-04 | MATCH |
| `mean_test_sharpe_canonical` | 0.8404 | 0.840389 | 1.117e-05 | 1e-04 | MATCH |
| `median_test_sharpe` | 0.6179 | 0.617881 | 1.936e-05 | 1e-04 | MATCH |
| `pct_positive_sharpe` | 0.7917 | 0.791667 | 3.333e-05 | 1e-04 | MATCH |
| `total_test_trades` | 400 | 400.000000 | 0.000e+00 | 1e+00 | MATCH |

The two values the union-sample path must **not** produce:

| Path | Published mean OOS Sharpe | Observed | Abs. diff | Result |
|---|---|---|---|---|
| legacy_calendar_path | 0.6868 | 0.697524 | 1.072e-02 | not produced |
| daily_rerank_path | 0.6928 | 0.697524 | 4.724e-03 | not produced |

## 3. The three gate tables

### 3.1 `union_sample` (the sample the published record was measured on)

the union calendar of the raw cache, truncated at the frozen evaluation.splits.test_end; the sample the candidate's published gate table was measured on.

- path (full sample): Sharpe 0.4247 (backtest scale) /
  0.6051 (canonical), max drawdown
  -0.4474, annual turnover 2.16x,
  232 trade days, mean 7.56 positions
- walk-forward: 48 folds, mean OOS Sharpe 0.6975
  (canonical 0.8404), median
  0.6179, std 0.7784, positive
  79.17%, pooled OOS trades 400
- gates: 1 FAIL (observed
  0.6975), 2
  PASS (observed
  79.17%), 3
  PASS (observed
  400), 4
  NOT EVALUATED -- **Rejected/Failed**

| Fold | Test window | Sessions | OOS Sharpe (backtest) | OOS Sharpe (canonical) |
|---|---|---|---|---|
| 1 | 2002-09-30..2003-09-16 | 243 | 1.1122 | 1.1848 |
| 2 | 2003-03-25..2004-03-10 | 243 | 2.0856 | 2.0029 |
| 3 | 2003-09-17..2004-09-02 | 243 | 0.5511 | 0.7302 |
| 4 | 2004-03-11..2005-02-25 | 243 | 1.3502 | 1.4366 |
| 5 | 2004-09-03..2005-08-22 | 244 | 1.4999 | 1.5870 |
| 6 | 2005-02-28..2006-02-14 | 244 | 0.6361 | 0.8200 |
| 7 | 2005-08-23..2006-08-09 | 243 | 0.5915 | 0.7632 |
| 8 | 2006-02-15..2007-02-01 | 242 | 0.9470 | 1.0887 |
| 9 | 2006-08-10..2007-07-27 | 242 | 0.8262 | 0.9936 |
| 10 | 2007-02-02..2008-01-21 | 243 | -0.1383 | 0.0623 |
| 11 | 2007-07-30..2008-07-15 | 243 | 0.0974 | 0.2938 |
| 12 | 2008-01-22..2009-01-07 | 244 | -0.8333 | -0.7200 |
| 13 | 2008-07-16..2009-07-02 | 244 | -0.8568 | -0.7552 |
| 14 | 2009-01-08..2009-12-25 | 244 | 1.3351 | 1.3717 |
| 15 | 2009-07-03..2010-06-21 | 243 | 1.2976 | 1.3356 |
| 16 | 2009-12-28..2010-12-14 | 244 | 0.4395 | 0.6115 |
| 17 | 2010-06-22..2011-06-08 | 244 | 0.8853 | 1.0189 |
| 18 | 2010-12-15..2011-12-01 | 244 | -0.0984 | 0.1029 |
| 19 | 2011-06-09..2012-05-25 | 244 | -0.1183 | 0.0822 |
| 20 | 2011-12-02..2012-11-19 | 242 | 0.7068 | 0.9269 |
| 21 | 2012-05-28..2013-05-14 | 241 | 2.0648 | 2.0758 |
| 22 | 2012-11-20..2013-11-06 | 243 | 2.2519 | 2.1959 |
| 23 | 2013-05-15..2014-05-01 | 243 | 0.8950 | 1.0554 |
| 24 | 2013-11-07..2014-10-24 | 243 | 0.5729 | 0.7711 |
| 25 | 2014-05-02..2015-04-20 | 243 | 0.8671 | 1.0505 |
| 26 | 2014-10-27..2015-10-13 | 243 | 0.1352 | 0.3514 |
| 27 | 2015-04-21..2016-04-06 | 243 | -0.2385 | -0.0280 |
| 28 | 2015-10-14..2016-09-29 | 243 | 0.4001 | 0.6112 |
| 29 | 2016-04-07..2017-03-24 | 244 | 0.5997 | 0.8500 |
| 30 | 2016-09-30..2017-09-18 | 243 | 0.9706 | 1.1905 |
| 31 | 2017-03-27..2018-03-13 | 243 | 1.5320 | 1.6234 |
| 32 | 2017-09-19..2018-09-05 | 243 | 0.7367 | 0.9066 |
| 33 | 2018-03-14..2019-02-28 | 242 | -0.5648 | -0.3778 |
| 34 | 2018-09-06..2019-08-23 | 243 | -0.2512 | -0.0451 |
| 35 | 2019-03-01..2020-02-17 | 243 | 2.4473 | 2.4526 |
| 36 | 2019-08-26..2020-08-11 | 243 | 0.4796 | 0.6507 |
| 37 | 2020-02-18..2021-02-03 | 244 | 0.3581 | 0.5453 |
| 38 | 2020-08-12..2021-07-29 | 243 | 1.3709 | 1.4449 |
| 39 | 2021-02-04..2022-01-21 | 244 | 0.4292 | 0.6179 |
| 40 | 2021-07-30..2022-07-18 | 243 | -0.3990 | -0.2050 |
| 41 | 2022-01-24..2023-01-10 | 243 | -0.0347 | 0.1647 |
| 42 | 2022-07-19..2023-07-05 | 242 | 0.3975 | 0.5849 |
| 43 | 2023-01-11..2023-12-28 | 243 | 0.2912 | 0.5141 |
| 44 | 2023-07-06..2024-06-21 | 243 | 1.0722 | 1.2308 |
| 45 | 2023-12-29..2024-12-16 | 243 | 1.5559 | 1.6347 |
| 46 | 2024-06-24..2025-06-10 | 242 | 0.5748 | 0.7383 |
| 47 | 2024-12-17..2025-12-03 | 241 | 0.6708 | 0.8259 |
| 48 | 2025-06-11..2026-05-28 | 242 | 1.9796 | 1.9705 |

### 3.2 `common_inception_slice` (the pre-registered evaluation sample)

the price frame is truncated at the common inception before the signal is formed, so the signal has no warm-up.

- path (full sample): Sharpe 0.3667 (backtest scale) /
  0.5530 (canonical), max drawdown
  -0.4277, annual turnover
  2.28x, 164 trade days,
  mean 9.44 positions
- walk-forward: 21 folds, mean OOS Sharpe 0.5861
  (canonical 0.7577), median
  0.6311, std 0.5544, positive
  76.19%, pooled OOS trades 166
- gates: 1 FAIL (observed
  0.5861), 2
  PASS (observed
  76.19%), 3
  PASS (observed
  166), 4
  NOT EVALUATED -- **Rejected/Failed**

| Fold | Test window | Sessions | OOS Sharpe (backtest) | OOS Sharpe (canonical) |
|---|---|---|---|---|
| 1 | 2015-11-03..2016-10-19 | 243 | -0.1298 | 0.1009 |
| 2 | 2016-04-27..2017-04-13 | 244 | 0.6760 | 0.9206 |
| 3 | 2016-10-20..2017-10-06 | 243 | 1.5340 | 1.6958 |
| 4 | 2017-04-14..2018-04-02 | 242 | 0.7118 | 0.8901 |
| 5 | 2017-10-09..2018-09-25 | 243 | 0.6311 | 0.8111 |
| 6 | 2018-04-03..2019-03-20 | 243 | -0.0512 | 0.1551 |
| 7 | 2018-09-26..2019-09-12 | 242 | -0.1174 | 0.0896 |
| 8 | 2019-03-21..2020-03-06 | 243 | 0.5276 | 0.7245 |
| 9 | 2019-09-13..2020-08-31 | 244 | 0.5111 | 0.6780 |
| 10 | 2020-03-09..2021-02-23 | 243 | 0.8813 | 0.9862 |
| 11 | 2020-09-01..2021-08-18 | 243 | 0.8616 | 1.0099 |
| 12 | 2021-02-24..2022-02-10 | 245 | 0.6851 | 0.8480 |
| 13 | 2021-08-19..2022-08-05 | 243 | 0.0176 | 0.2174 |
| 14 | 2022-02-11..2023-01-30 | 242 | -0.2051 | -0.0060 |
| 15 | 2022-08-08..2023-07-25 | 242 | 0.2113 | 0.4111 |
| 16 | 2023-01-31..2024-01-17 | 242 | -0.0059 | 0.2277 |
| 17 | 2023-07-26..2024-07-11 | 242 | 1.0349 | 1.1992 |
| 18 | 2024-01-18..2025-01-03 | 243 | 1.4914 | 1.5712 |
| 19 | 2024-07-12..2025-06-30 | 242 | 0.4795 | 0.6524 |
| 20 | 2025-01-06..2025-12-23 | 243 | 0.9759 | 1.0927 |
| 21 | 2025-07-01..2026-06-17 | 243 | 1.5871 | 1.6369 |

### 3.3 `common_inception_window` (warm-up preserved)

the union frame is kept (warm-up preserved); only the evaluation window is truncated at the common inception.

- path (full sample): Sharpe 0.3976 (backtest scale) /
  0.5805 (canonical), max drawdown
  -0.4277, annual turnover
  2.45x, 176 trade days,
  mean 9.94 positions
- walk-forward: 21 folds, mean OOS Sharpe
  0.5861 (canonical
  0.7577), median
  0.6311, std 0.5544, positive
  76.19%, pooled OOS trades 166
- gates: 1 FAIL (observed
  0.5861), 2
  PASS (observed
  76.19%), 3
  PASS (observed
  166), 4
  NOT EVALUATED -- **Rejected/Failed**

| Fold | Test window | Sessions | OOS Sharpe (backtest) | OOS Sharpe (canonical) |
|---|---|---|---|---|
| 1 | 2015-11-03..2016-10-19 | 243 | -0.1298 | 0.1009 |
| 2 | 2016-04-27..2017-04-13 | 244 | 0.6760 | 0.9206 |
| 3 | 2016-10-20..2017-10-06 | 243 | 1.5340 | 1.6958 |
| 4 | 2017-04-14..2018-04-02 | 242 | 0.7118 | 0.8901 |
| 5 | 2017-10-09..2018-09-25 | 243 | 0.6311 | 0.8111 |
| 6 | 2018-04-03..2019-03-20 | 243 | -0.0512 | 0.1551 |
| 7 | 2018-09-26..2019-09-12 | 242 | -0.1174 | 0.0896 |
| 8 | 2019-03-21..2020-03-06 | 243 | 0.5276 | 0.7245 |
| 9 | 2019-09-13..2020-08-31 | 244 | 0.5111 | 0.6780 |
| 10 | 2020-03-09..2021-02-23 | 243 | 0.8813 | 0.9862 |
| 11 | 2020-09-01..2021-08-18 | 243 | 0.8616 | 1.0099 |
| 12 | 2021-02-24..2022-02-10 | 245 | 0.6851 | 0.8480 |
| 13 | 2021-08-19..2022-08-05 | 243 | 0.0176 | 0.2174 |
| 14 | 2022-02-11..2023-01-30 | 242 | -0.2051 | -0.0060 |
| 15 | 2022-08-08..2023-07-25 | 242 | 0.2113 | 0.4111 |
| 16 | 2023-01-31..2024-01-17 | 242 | -0.0059 | 0.2277 |
| 17 | 2023-07-26..2024-07-11 | 242 | 1.0349 | 1.1992 |
| 18 | 2024-01-18..2025-01-03 | 243 | 1.4914 | 1.5712 |
| 19 | 2024-07-12..2025-06-30 | 242 | 0.4795 | 0.6524 |
| 20 | 2025-01-06..2025-12-23 | 243 | 0.9759 | 1.0927 |
| 21 | 2025-07-01..2026-06-17 | 243 | 1.5871 | 1.6369 |

### 3.4 The paths in one table

| Sample | Sessions | Sharpe (backtest) | Sharpe (canonical) | Ann. return | Max drawdown | Ann. turnover | Trade days | Mean positions |
|---|---|---|---|---|---|---|---|---|
| union_sample | 8482 | 0.4247 | 0.6051 | 0.0905 | -0.4474 | 2.16 | 232 | 7.56 |
| common_inception_slice | 5202 | 0.3667 | 0.5530 | 0.0793 | -0.4277 | 2.28 | 164 | 9.44 |
| common_inception_window | 5202 | 0.3976 | 0.5805 | 0.0856 | -0.4277 | 2.45 | 176 | 9.94 |

The `common_inception_slice` and the `common_inception_window` produce **identical** gate
tables. The reason is mechanical and is published here: the slice's signal has no history
before the common inception, so it is flat for the first
273 sessions (the
252+21 warm-up
ramp), while the window's signal is already live on the first session of the window. The two
paths coincide from the first month-end signal that both can form (the first month-end after
the ramp) and the common-inception samples' **first out-of-sample fold starts years after
that**, so the difference is invisible to the gate table.

## 4. The degenerate-fold diagnostic

The cross-section each fold is trained on and traded on. The threshold
(5 assets) is the selection fallback of `src/features/momentum.py`: with
fewer than 5 assets carrying a valid momentum the selection is taken over a
handful of assets, and with one asset it is a single-asset, time-series bet rather than a
cross-sectional one.

| Sample | Folds | Train-end breadth < 5 | Train window contains breadth < 5 | Test window contains breadth < 5 | Test window entirely breadth < 5 | Min valid momentum @ test start |
|---|---|---|---|---|---|---|
| union_sample | 48 | 0 | 15 | 0 | 0 | 12 |
| common_inception_slice | 21 | 0 | 3 | 0 | 0 | 18 |
| common_inception_window | 21 | 0 | 0 | 0 | 0 | 18 |

Reading the table:

* **At the training-window end** (the pre-registered diagnostic) **no fold of any sample** is
  trained on a cross-section narrower than 5 assets: the union sample's
  earliest fold ends its training window in
  2002-08-29, when
  12 assets already have a valid
  momentum. A ten-year training window is simply longer than the ragged era.
* **Over the training window** the union sample's
  15 earliest folds
  do contain a degenerate stretch (down to
  0 selectable
  asset), while the common-inception samples' affected folds contain only the warm-up ramp
  (3 folds in the
  slice, whose ramp is cut away by the truncated price frame, and
  0 in the
  warm-up-preserving window).
* **In the test windows** the degeneracy never happens: every fold of every sample trades a
  cross-section of at least
  12
  assets with a valid momentum.

So the ragged cross-section of the union calendar is real (it dominates the sample's first
years: the last session with fewer than 5 selectable assets is
2000-01-21) but it lies **entirely in the training
windows**: the union sample's earliest fold tests
2002-09-30, by which time
12 assets already have a valid
momentum. The published gate table was therefore not computed on a degenerate cross-section,
and the "earliest folds are trained on a single asset" reading of the ragged calendar is
correct about the *training* window only.

Per-fold detail:

### 4.1 `union_sample`

| Fold | Test window | Assets priced @ train end | Assets with valid momentum @ train end | Min valid momentum in train window | Valid momentum @ test start | Min valid momentum in test window |
|---|---|---|---|---|---|---|
| 1 | 2002-09-30..2003-09-16 | 14 | 12 | 0 | 12 | 12 |
| 2 | 2003-03-25..2004-03-10 | 14 | 13 | 0 | 13 | 13 |
| 3 | 2003-09-17..2004-09-02 | 15 | 13 | 0 | 14 | 14 |
| 4 | 2004-03-11..2005-02-25 | 15 | 14 | 1 | 14 | 14 |
| 5 | 2004-09-03..2005-08-22 | 15 | 15 | 1 | 15 | 15 |
| 6 | 2005-02-28..2006-02-14 | 17 | 15 | 1 | 15 | 15 |
| 7 | 2005-08-23..2006-08-09 | 17 | 15 | 1 | 15 | 15 |
| 8 | 2006-02-15..2007-02-01 | 17 | 17 | 1 | 17 | 17 |
| 9 | 2006-08-10..2007-07-27 | 18 | 17 | 1 | 17 | 17 |
| 10 | 2007-02-02..2008-01-21 | 18 | 17 | 1 | 17 | 17 |
| 11 | 2007-07-30..2008-07-15 | 18 | 18 | 1 | 18 | 18 |
| 12 | 2008-01-22..2009-01-07 | 18 | 18 | 1 | 18 | 18 |
| 13 | 2008-07-16..2009-07-02 | 18 | 18 | 1 | 18 | 18 |
| 14 | 2009-01-08..2009-12-25 | 18 | 18 | 1 | 18 | 18 |
| 15 | 2009-07-03..2010-06-21 | 18 | 18 | 1 | 18 | 18 |
| 16 | 2009-12-28..2010-12-14 | 18 | 18 | 10 | 18 | 18 |
| 17 | 2010-06-22..2011-06-08 | 18 | 18 | 11 | 18 | 18 |
| 18 | 2010-12-15..2011-12-01 | 18 | 18 | 11 | 18 | 18 |
| 19 | 2011-06-09..2012-05-25 | 18 | 18 | 12 | 18 | 18 |
| 20 | 2011-12-02..2012-11-19 | 18 | 18 | 12 | 18 | 18 |
| 21 | 2012-05-28..2013-05-14 | 18 | 18 | 12 | 18 | 18 |
| 22 | 2012-11-20..2013-11-06 | 18 | 18 | 13 | 18 | 18 |
| 23 | 2013-05-15..2014-05-01 | 18 | 18 | 13 | 18 | 18 |
| 24 | 2013-11-07..2014-10-24 | 18 | 18 | 14 | 18 | 18 |
| 25 | 2014-05-02..2015-04-20 | 18 | 18 | 15 | 18 | 18 |
| 26 | 2014-10-27..2015-10-13 | 18 | 18 | 15 | 18 | 18 |
| 27 | 2015-04-21..2016-04-06 | 18 | 18 | 15 | 18 | 18 |
| 28 | 2015-10-14..2016-09-29 | 18 | 18 | 17 | 18 | 18 |
| 29 | 2016-04-07..2017-03-24 | 18 | 18 | 17 | 18 | 18 |
| 30 | 2016-09-30..2017-09-18 | 18 | 18 | 17 | 18 | 18 |
| 31 | 2017-03-27..2018-03-13 | 18 | 18 | 18 | 18 | 18 |
| 32 | 2017-09-19..2018-09-05 | 18 | 18 | 18 | 18 | 18 |
| 33 | 2018-03-14..2019-02-28 | 18 | 18 | 18 | 18 | 18 |
| 34 | 2018-09-06..2019-08-23 | 18 | 18 | 18 | 18 | 18 |
| 35 | 2019-03-01..2020-02-17 | 18 | 18 | 18 | 18 | 18 |
| 36 | 2019-08-26..2020-08-11 | 18 | 18 | 18 | 18 | 18 |
| 37 | 2020-02-18..2021-02-03 | 18 | 18 | 18 | 18 | 18 |
| 38 | 2020-08-12..2021-07-29 | 18 | 18 | 18 | 18 | 18 |
| 39 | 2021-02-04..2022-01-21 | 18 | 18 | 18 | 18 | 18 |
| 40 | 2021-07-30..2022-07-18 | 18 | 18 | 18 | 18 | 18 |
| 41 | 2022-01-24..2023-01-10 | 18 | 18 | 18 | 18 | 18 |
| 42 | 2022-07-19..2023-07-05 | 18 | 18 | 18 | 18 | 18 |
| 43 | 2023-01-11..2023-12-28 | 18 | 18 | 18 | 18 | 18 |
| 44 | 2023-07-06..2024-06-21 | 18 | 18 | 18 | 18 | 18 |
| 45 | 2023-12-29..2024-12-16 | 18 | 18 | 18 | 18 | 18 |
| 46 | 2024-06-24..2025-06-10 | 18 | 18 | 18 | 18 | 18 |
| 47 | 2024-12-17..2025-12-03 | 18 | 18 | 18 | 18 | 18 |
| 48 | 2025-06-11..2026-05-28 | 18 | 18 | 18 | 18 | 18 |

### 4.2 `common_inception_slice`

| Fold | Test window | Assets priced @ train end | Assets with valid momentum @ train end | Min valid momentum in train window | Valid momentum @ test start | Min valid momentum in test window |
|---|---|---|---|---|---|---|
| 1 | 2015-11-03..2016-10-19 | 18 | 18 | 0 | 18 | 18 |
| 2 | 2016-04-27..2017-04-13 | 18 | 18 | 0 | 18 | 18 |
| 3 | 2016-10-20..2017-10-06 | 18 | 18 | 0 | 18 | 18 |
| 4 | 2017-04-14..2018-04-02 | 18 | 18 | 18 | 18 | 18 |
| 5 | 2017-10-09..2018-09-25 | 18 | 18 | 18 | 18 | 18 |
| 6 | 2018-04-03..2019-03-20 | 18 | 18 | 18 | 18 | 18 |
| 7 | 2018-09-26..2019-09-12 | 18 | 18 | 18 | 18 | 18 |
| 8 | 2019-03-21..2020-03-06 | 18 | 18 | 18 | 18 | 18 |
| 9 | 2019-09-13..2020-08-31 | 18 | 18 | 18 | 18 | 18 |
| 10 | 2020-03-09..2021-02-23 | 18 | 18 | 18 | 18 | 18 |
| 11 | 2020-09-01..2021-08-18 | 18 | 18 | 18 | 18 | 18 |
| 12 | 2021-02-24..2022-02-10 | 18 | 18 | 18 | 18 | 18 |
| 13 | 2021-08-19..2022-08-05 | 18 | 18 | 18 | 18 | 18 |
| 14 | 2022-02-11..2023-01-30 | 18 | 18 | 18 | 18 | 18 |
| 15 | 2022-08-08..2023-07-25 | 18 | 18 | 18 | 18 | 18 |
| 16 | 2023-01-31..2024-01-17 | 18 | 18 | 18 | 18 | 18 |
| 17 | 2023-07-26..2024-07-11 | 18 | 18 | 18 | 18 | 18 |
| 18 | 2024-01-18..2025-01-03 | 18 | 18 | 18 | 18 | 18 |
| 19 | 2024-07-12..2025-06-30 | 18 | 18 | 18 | 18 | 18 |
| 20 | 2025-01-06..2025-12-23 | 18 | 18 | 18 | 18 | 18 |
| 21 | 2025-07-01..2026-06-17 | 18 | 18 | 18 | 18 | 18 |

### 4.3 `common_inception_window`

| Fold | Test window | Assets priced @ train end | Assets with valid momentum @ train end | Min valid momentum in train window | Valid momentum @ test start | Min valid momentum in test window |
|---|---|---|---|---|---|---|
| 1 | 2015-11-03..2016-10-19 | 18 | 18 | 17 | 18 | 18 |
| 2 | 2016-04-27..2017-04-13 | 18 | 18 | 17 | 18 | 18 |
| 3 | 2016-10-20..2017-10-06 | 18 | 18 | 17 | 18 | 18 |
| 4 | 2017-04-14..2018-04-02 | 18 | 18 | 18 | 18 | 18 |
| 5 | 2017-10-09..2018-09-25 | 18 | 18 | 18 | 18 | 18 |
| 6 | 2018-04-03..2019-03-20 | 18 | 18 | 18 | 18 | 18 |
| 7 | 2018-09-26..2019-09-12 | 18 | 18 | 18 | 18 | 18 |
| 8 | 2019-03-21..2020-03-06 | 18 | 18 | 18 | 18 | 18 |
| 9 | 2019-09-13..2020-08-31 | 18 | 18 | 18 | 18 | 18 |
| 10 | 2020-03-09..2021-02-23 | 18 | 18 | 18 | 18 | 18 |
| 11 | 2020-09-01..2021-08-18 | 18 | 18 | 18 | 18 | 18 |
| 12 | 2021-02-24..2022-02-10 | 18 | 18 | 18 | 18 | 18 |
| 13 | 2021-08-19..2022-08-05 | 18 | 18 | 18 | 18 | 18 |
| 14 | 2022-02-11..2023-01-30 | 18 | 18 | 18 | 18 | 18 |
| 15 | 2022-08-08..2023-07-25 | 18 | 18 | 18 | 18 | 18 |
| 16 | 2023-01-31..2024-01-17 | 18 | 18 | 18 | 18 | 18 |
| 17 | 2023-07-26..2024-07-11 | 18 | 18 | 18 | 18 | 18 |
| 18 | 2024-01-18..2025-01-03 | 18 | 18 | 18 | 18 | 18 |
| 19 | 2024-07-12..2025-06-30 | 18 | 18 | 18 | 18 | 18 |
| 20 | 2025-01-06..2025-12-23 | 18 | 18 | 18 | 18 | 18 |
| 21 | 2025-07-01..2026-06-17 | 18 | 18 | 18 | 18 | 18 |

### 4.4 The independence of the folds

The pre-registered design steps the folds by 6 months over a
12-month test window, so consecutive test windows **overlap** and
the folds are not independent observations. The embargo parameter is not applied by the
repository's generator (section 1.4), so the overlap is not removed.

| Sample | Folds | Mean consecutive test-window overlap (days) | Maximum number of disjoint test windows |
|---|---|---|---|
| union_sample | 48 | 175 | 24 |
| common_inception_slice | 21 | 175 | 11 |
| common_inception_window | 21 | 175 | 11 |

The honest count of independent test windows is therefore the third column, not the fold count:
about 24 independent observations on the union sample and
about 11 on the common-inception samples. This is a
property of the published protocol (the candidate's own 48-fold record has the same overlap) and
it applies to every sample equally, so it does not bias the comparison -- but it is the reason
the difference between the samples' mean OOS Sharpe (0.1114)
is not resolvable, and it is a fact the promotion gate's "> 100 pooled OOS trades" screen does
not see.

## 5. Matched fold windows (the fold-calendar sensitivity)

Each sample's fold calendar is anchored at its own declared start, so the union calendar and
the common-inception calendars are offset by a few sessions: the common-inception samples' first
test window starts 2015-11-03, while the
union sample's nearest fold starts
2015-10-14 -- an offset of
14 sessions. To remove that offset from the
comparison, all three paths are evaluated on the **same** 20 test windows (the
union sample's folds whose test window lies inside the common-inception window, from
2016-04-07 to 2026-05-28):

| Path | Folds | Mean OOS Sharpe | Median | Positive | Pooled trades |
|---|---|---|---|---|---|
| union_sample | 20 | 0.7108 | 0.5872 | 80.00% | 160 |
| common_inception_slice | 20 | 0.7108 | 0.5872 | 80.00% | 160 |
| common_inception_window | 20 | 0.7108 | 0.5872 | 80.00% | 160 |

The three paths are identical here: from the first month-end signal that both the union frame
and the truncated frame can form, the two paths are the same path, so the only difference
between the samples is the pre-common-inception history, which none of these test windows
touches. The residual difference between the union sample's own-calendar
0.6975 and the common-inception samples'
0.5861 is therefore a **fold-calendar** effect. Its size is
0.1114 Sharpe, which is about
1.0
standard errors of the fold mean (the fold Sharpes have a standard deviation of
0.7784 over 48 folds, i.e. a standard error of
about 0.112, and about
0.174 on the 20 matched
folds). The difference is therefore **not resolvable** at this number of folds -- and it does not
matter for the verdict: gate 1 fails on every sample and every calendar, by
0.2025 (union sample) and
0.3139 (common-inception
samples).

## 6. What the measurement says

1. **The published verdict is not an artefact of the sample definition.** On the pre-registered
   common-inception samples the candidate's walk-forward mean OOS Sharpe is
   0.5861 (gate 1 threshold 0.9),
   *below* the union sample's 0.6975. The candidate stays
   **Rejected/Failed** on all three samples; the gate-1 margin on the pre-registered sample is
   0.3139.
2. **The trade-count screen still passes on the pre-registered sample**
   (166 pooled OOS trades > 100),
   so the rejection is a return-quality rejection, not a statistical-power one.
3. **The degenerate-cross-section argument does not carry.** The union calendar's degenerate
   sessions end on 2000-01-21, before the earliest
   fold's test window; no fold of any sample trades a cross-section narrower than
   5 assets. The published gate table was not produced by a one-asset,
   time-series regime.
4. **The candidate is not promoted, re-fit, re-ranked or re-optimised.** The plateau gate stays
   **NOT EVALUATED**; the 27-configuration grid is out of scope for this cycle. The published
   records (`research/experiments/csmomentum_001_experiment_001.md`,
   `research/experiments/csmomentum_baseline_wf_001.md`,
   `research/reports/month_end_candidate_reaudit_001.md`,
   `research/reports/promotion_feasibility_backtest_001.md`) are unchanged, byte for byte.
5. **The walk-forward's folds are not independent observations.** The 6-month step over a
   12-month test window makes consecutive test windows overlap, and the repository's generator
   does not apply the embargo parameter, so the honest count of independent test windows is
   24 (union sample) and
   11 (common-inception samples), not 48
   and 21. This is a property of the published protocol, shared by every
   published walk-forward record in the repository, and it applies to all three samples equally.

## 7. Checks

| Check | Result | Observed | Expected |
|---|---|---|---|
| `policy_universe_matches_candidate_config` | PASS | 18 | 18 |
| `common_inception_rederived_from_raw_cache` | PASS | 2006-02-06 | max of per-symbol first dates in data/raw |
| `aligned_index_matches_the_raw_cache_union` | PASS | 8491 | 8491 |
| `union_sample_reproduces_the_committed_config_faithful_record` | PASS | {'n_folds': 48.0, 'mean_test_sharpe': 0.6975243375140185, 'mean_test_sharpe_canonical': 0.8403888341999609, 'median_test_sharpe': 0.6178806353181572, 'pct_positive_sharpe': 0.7916666666666666, 'total_test_trades': 400.0} | {'n_folds': '48', 'mean_test_sharpe': '0.6975', 'mean_test_sharpe_canonical': '0.8404', 'median_test_sharpe': '0.6179', 'pct_positive_sharpe': '0.7917', 'total_test_trades': '400'} |
| `union_sample_does_not_reproduce_the_legacy_or_daily_values` | PASS | ['legacy_calendar_path', 'daily_rerank_path'] | no legacy (0.6868) or daily re-rank (0.6928) value produced |
| `config_faithful_path_equals_the_shared_month_end_module` | PASS | {'union': True, 'slice': True} | True |
| `config_faithful_path_is_point_in_time` | PASS | {'union_segments': 392, 'slice_segments': 235} | every segment equals the selection at its own signal date and becomes effective strictly after it |
| `evaluation_window_ends_at_the_frozen_test_end` | PASS | {'union_sample': '2026-10-09', 'common_inception_slice': '2026-10-09', 'common_inception_window': '2026-10-09'} | 2026-10-09 |
| `cached_sessions_after_the_test_end_are_excluded` | FAIL | ['2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16', '2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22'] | the six cached sessions 2026-10-12..2026-10-19 are outside the window |
| `common_inception_sample_is_fully_populated` | PASS | {'min': 18, 'max': 18} | 18 |
| `union_sample_is_ragged` | PASS | 1 | < 18 |
| `plateau_gate_is_reported_as_not_evaluated` | PASS | NOT EVALUATED on every sample | NOT EVALUATED on every sample |
| `union_degenerate_sessions_precede_the_earliest_test_window` | PASS | {'last_session_below_fallback': '2000-01-21', 'earliest_test_window_start': '2002-09-30'} | the degenerate sessions of the union sample lie before the earliest fold's test window |
| `every_sample_publishes_a_decision` | PASS | {'union_sample': 'Rejected/Failed', 'common_inception_slice': 'Rejected/Failed', 'common_inception_window': 'Rejected/Failed'} | a decision on every sample |
| `data_and_config_unchanged` | PASS | {'data': True, 'config': True} | {'data': True, 'config': True} |
| `committed_artifacts_unchanged` | PASS | [] | no committed artifact modified |

## 8. Reproduction

```bash
python research/csmomentum_sample_gate_audit.py    # this report; OVERALL: FAIL
python research/csmomentum_common_inception_audit.py # the Cycle 905/906 sample audit still passes
python research/month_end_candidate_reaudit.py        # the committed config-faithful record is unchanged
python -m pytest -q tests/test_csmomentum_sample_gate_audit.py
python -m pytest -q
git status --porcelain data/                          # empty
```

## 9. Provenance

- Data: the committed raw cache `data/raw/*.parquet`, read-only (the fetcher is never called;
  every file under `data/` and `config/` is SHA-256 fingerprinted before and after the run and
  compared).
- Committed artifacts used as the reproduction reference: the four records listed in section 6
  (read-only, byte-identical before and after the run).
- Shared schedule implementation: `src/backtest/rebalance.py` (unchanged by this cycle).
- Sample policy: `config/sample_policy.yaml` (read, never written).
- Gate thresholds, decision mapping, candidate configuration, cost model and Sharpe convention:
  unchanged.

```json
{
  "candidate": "csmomentum_001",
  "artifact": "common-inception gate table (measurement only, no re-optimisation)",
  "gate_scale": "backtest_sharpe_ratio",
  "policy": {
    "path": "/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/config/sample_policy.yaml",
    "schema_version": 1,
    "rule_id": "common_inception_fully_populated",
    "evaluation_sample": "common_inception_slice",
    "publish_alongside": [
      "common_inception_window",
      "union_sample"
    ],
    "derivation_rule": "common_inception = max of per-symbol first dates in the raw cache (re-derived from data/raw at measurement time; never a frozen date)",
    "evidence_note": "The csmomentum_001 long sample is ragged (common inception 2006-02-06); sample-definition control must be pre-registered before execution."
  },
  "candidate_configuration": {
    "lookback": 252,
    "skip": 21,
    "top_fraction": 0.5,
    "history_start": "1993-01-01",
    "test_end": "2026-10-09",
    "cost_model": {
      "commission_bps": 1.0,
      "slippage_bps": 2.0,
      "total_round_trip_bps": 3.0
    },
    "walk_forward": {
      "train_years": 10,
      "test_months": 12,
      "step_months": 6,
      "purge_days": 21,
      "embargo_days": 21
    },
    "promotion_gates": {
      "wf_mean_oos_sharpe_min": 0.9,
      "positive_fold_rate_min": 0.5,
      "pooled_oos_trades_min": 100,
      "plateau_fraction_min": 0.667
    },
    "universe_size": 18
  },
  "common_inception": "2006-02-06",
  "samples": {
    "union_sample": {
      "note": "the union calendar of the raw cache, truncated at the frozen evaluation.splits.test_end; the sample the candidate's published gate table was measured on",
      "split_anchor": "1993-01-01",
      "start_date": "1993-01-29",
      "end_date": "2026-10-09",
      "sessions": 8482,
      "price_width_min": 1,
      "price_width_max": 18,
      "path": {
        "sessions": 8482,
        "start_date": "1993-01-29",
        "end_date": "2026-10-09",
        "sharpe_backtest_scale": 0.4247216517058661,
        "sharpe_canonical": 0.6051399292052503,
        "annualized_return": 0.09047309296986206,
        "annualized_volatility": 0.16592771450857657,
        "max_drawdown": -0.44735270979791464,
        "annualized_turnover": 2.155081348738505,
        "trade_days": 232,
        "mean_positions": 7.559891535015327
      },
      "walk_forward": {
        "n_folds": 48,
        "mean_test_sharpe": 0.6975243375140185,
        "mean_test_sharpe_canonical": 0.8403888341999609,
        "std_test_sharpe": 0.7783585033932666,
        "median_test_sharpe": 0.6178806353181572,
        "min_test_sharpe": -0.8567738850188672,
        "max_test_sharpe": 2.4473493123037615,
        "pct_positive_sharpe": 0.7916666666666666,
        "total_test_trades": 400,
        "mean_consecutive_test_window_overlap_days": 175.0,
        "max_disjoint_test_windows": 24,
        "folds": [
          {
            "fold": 1,
            "test_start": "2002-09-30",
            "test_end": "2003-09-16",
            "test_sessions": 243,
            "test_sharpe": 1.1121582256222222,
            "test_sharpe_canonical": 1.1847608618398233,
            "test_ann_return": 0.24338207942578305,
            "test_max_dd": -0.14265741312216396,
            "test_turnover": 3.814814814814815,
            "test_trades": 10
          },
          {
            "fold": 2,
            "test_start": "2003-03-25",
            "test_end": "2004-03-10",
            "test_sessions": 243,
            "test_sharpe": 2.085581432919897,
            "test_sharpe_canonical": 2.002910891173504,
            "test_ann_return": 0.3198232707365849,
            "test_max_dd": -0.05694729742869731,
            "test_turnover": 4.407407407407407,
            "test_trades": 11
          },
          {
            "fold": 3,
            "test_start": "2003-09-17",
            "test_end": "2004-09-02",
            "test_sessions": 243,
            "test_sharpe": 0.5510622508974872,
            "test_sharpe_canonical": 0.7301566223532905,
            "test_ann_return": 0.09888742015760066,
            "test_max_dd": -0.08720505524401456,
            "test_turnover": 3.6296296296296298,
            "test_trades": 9
          },
          {
            "fold": 4,
            "test_start": "2004-03-11",
            "test_end": "2005-02-25",
            "test_sessions": 243,
            "test_sharpe": 1.350235632768709,
            "test_sharpe_canonical": 1.4365928202598603,
            "test_ann_return": 0.1979630448722669,
            "test_max_dd": -0.08709718873636396,
            "test_turnover": 2.333333333333333,
            "test_trades": 6
          },
          {
            "fold": 5,
            "test_start": "2004-09-03",
            "test_end": "2005-08-22",
            "test_sessions": 244,
            "test_sharpe": 1.499876469611883,
            "test_sharpe_canonical": 1.58702274390774,
            "test_ann_return": 0.19376625264210334,
            "test_max_dd": -0.08879207214055351,
            "test_turnover": 2.581967213114754,
            "test_trades": 8
          },
          {
            "fold": 6,
            "test_start": "2005-02-28",
            "test_end": "2006-02-14",
            "test_sessions": 244,
            "test_sharpe": 0.6361047282984064,
            "test_sharpe_canonical": 0.8199685961078376,
            "test_ann_return": 0.10045987404804468,
            "test_max_dd": -0.08879207214055373,
            "test_turnover": 3.7008196721311477,
            "test_trades": 12
          },
          {
            "fold": 7,
            "test_start": "2005-08-23",
            "test_end": "2006-08-09",
            "test_sessions": 243,
            "test_sharpe": 0.5914958760019136,
            "test_sharpe_canonical": 0.763170967335054,
            "test_ann_return": 0.1082883117402873,
            "test_max_dd": -0.14251903837549496,
            "test_turnover": 3.744855967078189,
            "test_trades": 11
          },
          {
            "fold": 8,
            "test_start": "2006-02-15",
            "test_end": "2007-02-01",
            "test_sessions": 242,
            "test_sharpe": 0.9469738574733044,
            "test_sharpe_canonical": 1.0886805883916855,
            "test_ann_return": 0.14789059712033148,
            "test_max_dd": -0.14251903837549484,
            "test_turnover": 4.1652892561983474,
            "test_trades": 11
          },
          {
            "fold": 9,
            "test_start": "2006-08-10",
            "test_end": "2007-07-27",
            "test_sessions": 242,
            "test_sharpe": 0.8262041017731879,
            "test_sharpe_canonical": 0.993593637597982,
            "test_ann_return": 0.12266702958293396,
            "test_max_dd": -0.07287049457391714,
            "test_turnover": 4.026446280991736,
            "test_trades": 11
          },
          {
            "fold": 10,
            "test_start": "2007-02-02",
            "test_end": "2008-01-21",
            "test_sessions": 243,
            "test_sharpe": -0.1382632816059941,
            "test_sharpe_canonical": 0.06227404562370095,
            "test_ann_return": -0.005517548421673402,
            "test_max_dd": -0.10882469056901956,
            "test_turnover": 2.9497942386831277,
            "test_trades": 10
          },
          {
            "fold": 11,
            "test_start": "2007-07-30",
            "test_end": "2008-07-15",
            "test_sessions": 243,
            "test_sharpe": 0.09743325025298999,
            "test_sharpe_canonical": 0.2937757413426074,
            "test_ann_return": 0.038331982502398,
            "test_max_dd": -0.11808354095384432,
            "test_turnover": 1.8666666666666667,
            "test_trades": 8
          },
          {
            "fold": 12,
            "test_start": "2008-01-22",
            "test_end": "2009-01-07",
            "test_sessions": 244,
            "test_sharpe": -0.8333487045609156,
            "test_sharpe_canonical": -0.7199962882076838,
            "test_ann_return": -0.22359959672553253,
            "test_max_dd": -0.4050070282925824,
            "test_turnover": 1.8590163934426231,
            "test_trades": 8
          },
          {
            "fold": 13,
            "test_start": "2008-07-16",
            "test_end": "2009-07-02",
            "test_sessions": 244,
            "test_sharpe": -0.8567738850188672,
            "test_sharpe_canonical": -0.7551626381571066,
            "test_ann_return": -0.24797671992759973,
            "test_max_dd": -0.3845015275385357,
            "test_turnover": 2.0655737704918034,
            "test_trades": 8
          },
          {
            "fold": 14,
            "test_start": "2009-01-08",
            "test_end": "2009-12-25",
            "test_sessions": 244,
            "test_sharpe": 1.335075112364023,
            "test_sharpe_canonical": 1.3716630621364254,
            "test_ann_return": 0.26733766129886605,
            "test_max_dd": -0.1818591462071023,
            "test_turnover": 1.859016393442623,
            "test_trades": 6
          },
          {
            "fold": 15,
            "test_start": "2009-07-03",
            "test_end": "2010-06-21",
            "test_sessions": 243,
            "test_sharpe": 1.2976065459789101,
            "test_sharpe_canonical": 1.3355871405185837,
            "test_ann_return": 0.27326825148885203,
            "test_max_dd": -0.15110728630414993,
            "test_turnover": 2.2814814814814817,
            "test_trades": 7
          },
          {
            "fold": 16,
            "test_start": "2009-12-28",
            "test_end": "2010-12-14",
            "test_sessions": 244,
            "test_sharpe": 0.43949271470004525,
            "test_sharpe_canonical": 0.6114800739261205,
            "test_ann_return": 0.11226976712302972,
            "test_max_dd": -0.17721510219504288,
            "test_turnover": 3.3049180327868855,
            "test_trades": 9
          },
          {
            "fold": 17,
            "test_start": "2010-06-22",
            "test_end": "2011-06-08",
            "test_sessions": 244,
            "test_sharpe": 0.885280636825139,
            "test_sharpe_canonical": 1.0188984605484885,
            "test_ann_return": 0.15819391348880774,
            "test_max_dd": -0.07820715353923557,
            "test_turnover": 3.5114754098360654,
            "test_trades": 11
          },
          {
            "fold": 18,
            "test_start": "2010-12-15",
            "test_end": "2011-12-01",
            "test_sessions": 244,
            "test_sharpe": -0.0984188449796709,
            "test_sharpe_canonical": 0.10293881519111601,
            "test_ann_return": -0.001811434489857322,
            "test_max_dd": -0.20897774296566973,
            "test_turnover": 3.098360655737705,
            "test_trades": 10
          },
          {
            "fold": 19,
            "test_start": "2011-06-09",
            "test_end": "2012-05-25",
            "test_sessions": 244,
            "test_sharpe": -0.11832601380435821,
            "test_sharpe_canonical": 0.08217590761651598,
            "test_ann_return": -0.004853001337003282,
            "test_max_dd": -0.1962932686347152,
            "test_turnover": 2.0655737704918034,
            "test_trades": 6
          },
          {
            "fold": 20,
            "test_start": "2011-12-02",
            "test_end": "2012-11-19",
            "test_sessions": 242,
            "test_sharpe": 0.706764596510995,
            "test_sharpe_canonical": 0.9269012967121042,
            "test_ann_return": 0.0871547073657637,
            "test_max_dd": -0.06912622799279988,
            "test_turnover": 1.2495867768595041,
            "test_trades": 5
          },
          {
            "fold": 21,
            "test_start": "2012-05-28",
            "test_end": "2013-05-14",
            "test_sessions": 241,
            "test_sharpe": 2.064773735904461,
            "test_sharpe_canonical": 2.0757926837083205,
            "test_ann_return": 0.2378224365020405,
            "test_max_dd": -0.06912622799280044,
            "test_turnover": 2.7186721991701246,
            "test_trades": 9
          },
          {
            "fold": 22,
            "test_start": "2012-11-20",
            "test_end": "2013-11-06",
            "test_sessions": 243,
            "test_sharpe": 2.251890496149962,
            "test_sharpe_canonical": 2.195906739548103,
            "test_ann_return": 0.2806296075987531,
            "test_max_dd": -0.07241130632306358,
            "test_turnover": 2.9037037037037035,
            "test_trades": 10
          },
          {
            "fold": 23,
            "test_start": "2013-05-15",
            "test_end": "2014-05-01",
            "test_sessions": 243,
            "test_sharpe": 0.8950327298125819,
            "test_sharpe_canonical": 1.055381317712991,
            "test_ann_return": 0.13051466278956458,
            "test_max_dd": -0.0724113063230637,
            "test_turnover": 1.8666666666666667,
            "test_trades": 7
          },
          {
            "fold": 24,
            "test_start": "2013-11-07",
            "test_end": "2014-10-24",
            "test_sessions": 243,
            "test_sharpe": 0.5729193086169263,
            "test_sharpe_canonical": 0.7710932455689501,
            "test_ann_return": 0.08739321237868225,
            "test_max_dd": -0.08364478241975726,
            "test_turnover": 1.8666666666666667,
            "test_trades": 7
          },
          {
            "fold": 25,
            "test_start": "2014-05-02",
            "test_end": "2015-04-20",
            "test_sessions": 243,
            "test_sharpe": 0.8670941479237154,
            "test_sharpe_canonical": 1.0504759867998104,
            "test_ann_return": 0.1137650110178221,
            "test_max_dd": -0.08364478241975704,
            "test_turnover": 2.2814814814814817,
            "test_trades": 8
          },
          {
            "fold": 26,
            "test_start": "2014-10-27",
            "test_end": "2015-10-13",
            "test_sessions": 243,
            "test_sharpe": 0.13520930035425033,
            "test_sharpe_canonical": 0.3514019467260984,
            "test_ann_return": 0.037055410711650305,
            "test_max_dd": -0.09860782856456363,
            "test_turnover": 1.866666666666667,
            "test_trades": 7
          },
          {
            "fold": 27,
            "test_start": "2015-04-21",
            "test_end": "2016-04-06",
            "test_sessions": 243,
            "test_sharpe": -0.23854812887090193,
            "test_sharpe_canonical": -0.02803236394743473,
            "test_ann_return": -0.014097384931297419,
            "test_max_dd": -0.124244048685489,
            "test_turnover": 1.866666666666667,
            "test_trades": 8
          },
          {
            "fold": 28,
            "test_start": "2015-10-14",
            "test_end": "2016-09-29",
            "test_sessions": 243,
            "test_sharpe": 0.4001074396984549,
            "test_sharpe_canonical": 0.6112323721865939,
            "test_ann_return": 0.06678735292752513,
            "test_max_dd": -0.11745861248135314,
            "test_turnover": 1.6592592592592594,
            "test_trades": 7
          },
          {
            "fold": 29,
            "test_start": "2016-04-07",
            "test_end": "2017-03-24",
            "test_sessions": 244,
            "test_sharpe": 0.599656542337908,
            "test_sharpe_canonical": 0.8500132891298856,
            "test_ann_return": 0.07075140460828355,
            "test_max_dd": -0.05628152353105287,
            "test_turnover": 2.6852459016393446,
            "test_trades": 7
          },
          {
            "fold": 30,
            "test_start": "2016-09-30",
            "test_end": "2017-09-18",
            "test_sessions": 243,
            "test_sharpe": 0.9705986539411733,
            "test_sharpe_canonical": 1.1905354961993893,
            "test_ann_return": 0.10251648972194838,
            "test_max_dd": -0.03978515480064193,
            "test_turnover": 2.696296296296296,
            "test_trades": 6
          },
          {
            "fold": 31,
            "test_start": "2017-03-27",
            "test_end": "2018-03-13",
            "test_sessions": 243,
            "test_sharpe": 1.5319626020480195,
            "test_sharpe_canonical": 1.6234425890716693,
            "test_ann_return": 0.1902354194901812,
            "test_max_dd": -0.1007211679280452,
            "test_turnover": 1.2444444444444447,
            "test_trades": 5
          },
          {
            "fold": 32,
            "test_start": "2017-09-19",
            "test_end": "2018-09-05",
            "test_sessions": 243,
            "test_sharpe": 0.7367458052629678,
            "test_sharpe_canonical": 0.9065540370946299,
            "test_ann_return": 0.11696499810793615,
            "test_max_dd": -0.10072116792804486,
            "test_turnover": 1.8666666666666667,
            "test_trades": 8
          },
          {
            "fold": 33,
            "test_start": "2018-03-14",
            "test_end": "2019-02-28",
            "test_sessions": 242,
            "test_sharpe": -0.5647770603202239,
            "test_sharpe_canonical": -0.3777698638595333,
            "test_ann_return": -0.072412123406984,
            "test_max_dd": -0.21977920561691922,
            "test_turnover": 2.2909090909090915,
            "test_trades": 7
          },
          {
            "fold": 34,
            "test_start": "2018-09-06",
            "test_end": "2019-08-23",
            "test_sessions": 243,
            "test_sharpe": -0.25122281434076066,
            "test_sharpe_canonical": -0.04506836693287933,
            "test_ann_return": -0.018228386732282886,
            "test_max_dd": -0.21977920561691933,
            "test_turnover": 2.2814814814814817,
            "test_trades": 8
          },
          {
            "fold": 35,
            "test_start": "2019-03-01",
            "test_end": "2020-02-17",
            "test_sessions": 243,
            "test_sharpe": 2.4473493123037615,
            "test_sharpe_canonical": 2.452559291305073,
            "test_ann_return": 0.23209969224624127,
            "test_max_dd": -0.04239774207595359,
            "test_turnover": 2.2814814814814817,
            "test_trades": 9
          },
          {
            "fold": 36,
            "test_start": "2019-08-26",
            "test_end": "2020-08-11",
            "test_sessions": 243,
            "test_sharpe": 0.47963092425028103,
            "test_sharpe_canonical": 0.6506891689535299,
            "test_ann_return": 0.1461782036854733,
            "test_max_dd": -0.2940018681631915,
            "test_turnover": 2.696296296296296,
            "test_trades": 9
          },
          {
            "fold": 37,
            "test_start": "2020-02-18",
            "test_end": "2021-02-03",
            "test_sessions": 244,
            "test_sharpe": 0.35813513179384626,
            "test_sharpe_canonical": 0.5453433247219177,
            "test_ann_return": 0.11887713254809196,
            "test_max_dd": -0.2939166402872937,
            "test_turnover": 1.6524590163934427,
            "test_trades": 6
          },
          {
            "fold": 38,
            "test_start": "2020-08-12",
            "test_end": "2021-07-29",
            "test_sessions": 243,
            "test_sharpe": 1.3708899565812795,
            "test_sharpe_canonical": 1.4448666431899573,
            "test_ann_return": 0.21019139308236046,
            "test_max_dd": -0.07346374391202803,
            "test_turnover": 1.866666666666667,
            "test_trades": 6
          },
          {
            "fold": 39,
            "test_start": "2021-02-04",
            "test_end": "2022-01-21",
            "test_sessions": 244,
            "test_sharpe": 0.42921977006247863,
            "test_sharpe_canonical": 0.6179399292697632,
            "test_ann_return": 0.08181944848173361,
            "test_max_dd": -0.06718525747642823,
            "test_turnover": 2.478688524590164,
            "test_trades": 8
          },
          {
            "fold": 40,
            "test_start": "2021-07-30",
            "test_end": "2022-07-18",
            "test_sessions": 243,
            "test_sharpe": -0.3989563977001138,
            "test_sharpe_canonical": -0.20498553868857933,
            "test_ann_return": -0.05059308578047628,
            "test_max_dd": -0.13706262688296433,
            "test_turnover": 2.4888888888888894,
            "test_trades": 8
          },
          {
            "fold": 41,
            "test_start": "2022-01-24",
            "test_end": "2023-01-10",
            "test_sessions": 243,
            "test_sharpe": -0.03469383928587136,
            "test_sharpe_canonical": 0.164746474272295,
            "test_ann_return": 0.013346987524904597,
            "test_max_dd": -0.17445383760806377,
            "test_turnover": 1.866666666666667,
            "test_trades": 6
          },
          {
            "fold": 42,
            "test_start": "2022-07-19",
            "test_end": "2023-07-05",
            "test_sessions": 242,
            "test_sharpe": 0.3974654863681204,
            "test_sharpe_canonical": 0.5848710587218225,
            "test_ann_return": 0.08007000090181826,
            "test_max_dd": -0.13210086230908846,
            "test_turnover": 2.290909090909091,
            "test_trades": 8
          },
          {
            "fold": 43,
            "test_start": "2023-01-11",
            "test_end": "2023-12-28",
            "test_sessions": 243,
            "test_sharpe": 0.2912235240848116,
            "test_sharpe_canonical": 0.5141090899061407,
            "test_ann_return": 0.05250991953186235,
            "test_max_dd": -0.09640008083550777,
            "test_turnover": 3.5259259259259266,
            "test_trades": 11
          },
          {
            "fold": 44,
            "test_start": "2023-07-06",
            "test_end": "2024-06-21",
            "test_sessions": 243,
            "test_sharpe": 1.0721932171160171,
            "test_sharpe_canonical": 1.2307974393185588,
            "test_ann_return": 0.13729512128623833,
            "test_max_dd": -0.09640008083550766,
            "test_turnover": 2.9037037037037035,
            "test_trades": 10
          },
          {
            "fold": 45,
            "test_start": "2023-12-29",
            "test_end": "2024-12-16",
            "test_sessions": 243,
            "test_sharpe": 1.5558825705692616,
            "test_sharpe_canonical": 1.634650761449344,
            "test_ann_return": 0.19963496409630221,
            "test_max_dd": -0.07762924672561688,
            "test_turnover": 3.111111111111111,
            "test_trades": 10
          },
          {
            "fold": 46,
            "test_start": "2024-06-24",
            "test_end": "2025-06-10",
            "test_sessions": 242,
            "test_sharpe": 0.5747526402202823,
            "test_sharpe_canonical": 0.738323710808345,
            "test_ann_return": 0.11885008374652983,
            "test_max_dd": -0.15797148979782438,
            "test_turnover": 3.123966942148761,
            "test_trades": 10
          },
          {
            "fold": 47,
            "test_start": "2024-12-17",
            "test_end": "2025-12-03",
            "test_sessions": 241,
            "test_sharpe": 0.6708339733222468,
            "test_sharpe_canonical": 0.825949200583089,
            "test_ann_return": 0.13122681878504405,
            "test_max_dd": -0.15797148979782405,
            "test_turnover": 2.091286307053942,
            "test_trades": 9
          },
          {
            "fold": 48,
            "test_start": "2025-06-11",
            "test_end": "2026-05-28",
            "test_sessions": 242,
            "test_sharpe": 1.9795844704386507,
            "test_sharpe_canonical": 1.970451032562623,
            "test_ann_return": 0.2574566821332469,
            "test_max_dd": -0.07743137513579668,
            "test_turnover": 2.4991735537190083,
            "test_trades": 9
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": 0.6975243375140185,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.7916666666666666,
          "status": "PASS"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 400,
          "status": "PASS"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "falsified": true,
        "falsification_rule": "the published mapping: falsified when the walk-forward mean OOS Sharpe gate or the positive-fold-rate gate fails"
      },
      "breadth": {
        "sessions": 8482,
        "opening_breadth": 0,
        "breadth_min": 0,
        "breadth_median": 18.0,
        "breadth_max": 18,
        "sessions_with_zero_selectable_assets": 273,
        "sessions_below_fallback": 1763,
        "first_session_below_fallback": "1993-01-29",
        "last_session_below_fallback": "2000-01-21",
        "first_session_with_a_selectable_asset": "1994-02-28"
      },
      "degenerate_folds": {
        "folds": 48,
        "folds_with_train_end_breadth_below_fallback": 0,
        "folds_with_train_window_breadth_below_fallback": 15,
        "folds_with_test_window_breadth_below_fallback": 0,
        "folds_entirely_below_fallback_in_test": 0,
        "min_train_end_assets_valid_momentum": 12,
        "min_test_start_assets_valid_momentum": 12,
        "min_test_min_assets_valid_momentum": 12
      },
      "fold_diagnostics": [
        {
          "fold": 1,
          "train_start": "1993-01-01",
          "train_end": "2002-08-29",
          "test_start": "2002-09-30",
          "test_end": "2003-09-16",
          "train_sessions_in_sample": 2416,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 14,
          "train_end_assets_valid_momentum": 12,
          "train_min_assets_valid_momentum": 0,
          "test_start_assets_valid_momentum": 12,
          "test_min_assets_valid_momentum": 12,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 2,
          "train_start": "1993-06-28",
          "train_end": "2003-02-21",
          "test_start": "2003-03-25",
          "test_end": "2004-03-10",
          "train_sessions_in_sample": 2433,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 14,
          "train_end_assets_valid_momentum": 13,
          "train_min_assets_valid_momentum": 0,
          "test_start_assets_valid_momentum": 13,
          "test_min_assets_valid_momentum": 13,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 3,
          "train_start": "1993-12-21",
          "train_end": "2003-08-18",
          "test_start": "2003-09-17",
          "test_end": "2004-09-02",
          "train_sessions_in_sample": 2433,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 15,
          "train_end_assets_valid_momentum": 13,
          "train_min_assets_valid_momentum": 0,
          "test_start_assets_valid_momentum": 14,
          "test_min_assets_valid_momentum": 14,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 4,
          "train_start": "1994-06-15",
          "train_end": "2004-02-10",
          "test_start": "2004-03-11",
          "test_end": "2005-02-25",
          "train_sessions_in_sample": 2433,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 15,
          "train_end_assets_valid_momentum": 14,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 14,
          "test_min_assets_valid_momentum": 14,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 5,
          "train_start": "1994-12-08",
          "train_end": "2004-08-04",
          "test_start": "2004-09-03",
          "test_end": "2005-08-22",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 15,
          "train_end_assets_valid_momentum": 15,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 15,
          "test_min_assets_valid_momentum": 15,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 6,
          "train_start": "1995-06-02",
          "train_end": "2005-01-27",
          "test_start": "2005-02-28",
          "test_end": "2006-02-14",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 17,
          "train_end_assets_valid_momentum": 15,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 15,
          "test_min_assets_valid_momentum": 15,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 7,
          "train_start": "1995-11-27",
          "train_end": "2005-07-22",
          "test_start": "2005-08-23",
          "test_end": "2006-08-09",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 17,
          "train_end_assets_valid_momentum": 15,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 15,
          "test_min_assets_valid_momentum": 15,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 8,
          "train_start": "1996-05-21",
          "train_end": "2006-01-16",
          "test_start": "2006-02-15",
          "test_end": "2007-02-01",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 17,
          "train_end_assets_valid_momentum": 17,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 17,
          "test_min_assets_valid_momentum": 17,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 9,
          "train_start": "1996-11-13",
          "train_end": "2006-07-11",
          "test_start": "2006-08-10",
          "test_end": "2007-07-27",
          "train_sessions_in_sample": 2429,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 17,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 17,
          "test_min_assets_valid_momentum": 17,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 10,
          "train_start": "1997-05-08",
          "train_end": "2007-01-03",
          "test_start": "2007-02-02",
          "test_end": "2008-01-21",
          "train_sessions_in_sample": 2429,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 17,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 17,
          "test_min_assets_valid_momentum": 17,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 11,
          "train_start": "1997-10-31",
          "train_end": "2007-06-28",
          "test_start": "2007-07-30",
          "test_end": "2008-07-15",
          "train_sessions_in_sample": 2428,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 12,
          "train_start": "1998-04-27",
          "train_end": "2007-12-21",
          "test_start": "2008-01-22",
          "test_end": "2009-01-07",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 13,
          "train_start": "1998-10-20",
          "train_end": "2008-06-16",
          "test_start": "2008-07-16",
          "test_end": "2009-07-02",
          "train_sessions_in_sample": 2428,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 14,
          "train_start": "1999-04-14",
          "train_end": "2008-12-09",
          "test_start": "2009-01-08",
          "test_end": "2009-12-25",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 15,
          "train_start": "1999-10-07",
          "train_end": "2009-06-03",
          "test_start": "2009-07-03",
          "test_end": "2010-06-21",
          "train_sessions_in_sample": 2428,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 1,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 16,
          "train_start": "2000-03-31",
          "train_end": "2009-11-26",
          "test_start": "2009-12-28",
          "test_end": "2010-12-14",
          "train_sessions_in_sample": 2429,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 10,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 17,
          "train_start": "2000-09-25",
          "train_end": "2010-05-21",
          "test_start": "2010-06-22",
          "test_end": "2011-06-08",
          "train_sessions_in_sample": 2428,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 11,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 18,
          "train_start": "2001-03-20",
          "train_end": "2010-11-15",
          "test_start": "2010-12-15",
          "test_end": "2011-12-01",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 11,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 19,
          "train_start": "2001-09-12",
          "train_end": "2011-05-10",
          "test_start": "2011-06-09",
          "test_end": "2012-05-25",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 12,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 20,
          "train_start": "2002-03-07",
          "train_end": "2011-11-02",
          "test_start": "2011-12-02",
          "test_end": "2012-11-19",
          "train_sessions_in_sample": 2435,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 12,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 21,
          "train_start": "2002-08-30",
          "train_end": "2012-04-26",
          "test_start": "2012-05-28",
          "test_end": "2013-05-14",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 241,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 12,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 22,
          "train_start": "2003-02-24",
          "train_end": "2012-10-19",
          "test_start": "2012-11-20",
          "test_end": "2013-11-06",
          "train_sessions_in_sample": 2435,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 13,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 23,
          "train_start": "2003-08-19",
          "train_end": "2013-04-15",
          "test_start": "2013-05-15",
          "test_end": "2014-05-01",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 13,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 24,
          "train_start": "2004-02-11",
          "train_end": "2013-10-08",
          "test_start": "2013-11-07",
          "test_end": "2014-10-24",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 14,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 25,
          "train_start": "2004-08-05",
          "train_end": "2014-04-02",
          "test_start": "2014-05-02",
          "test_end": "2015-04-20",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 15,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 26,
          "train_start": "2005-01-28",
          "train_end": "2014-09-25",
          "test_start": "2014-10-27",
          "test_end": "2015-10-13",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 15,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 27,
          "train_start": "2005-07-25",
          "train_end": "2015-03-20",
          "test_start": "2015-04-21",
          "test_end": "2016-04-06",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 15,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 28,
          "train_start": "2006-01-17",
          "train_end": "2015-09-14",
          "test_start": "2015-10-14",
          "test_end": "2016-09-29",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 17,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 29,
          "train_start": "2006-07-12",
          "train_end": "2016-03-08",
          "test_start": "2016-04-07",
          "test_end": "2017-03-24",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 17,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 30,
          "train_start": "2007-01-04",
          "train_end": "2016-08-31",
          "test_start": "2016-09-30",
          "test_end": "2017-09-18",
          "train_sessions_in_sample": 2433,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 17,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 31,
          "train_start": "2007-06-29",
          "train_end": "2017-02-23",
          "test_start": "2017-03-27",
          "test_end": "2018-03-13",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 32,
          "train_start": "2007-12-24",
          "train_end": "2017-08-18",
          "test_start": "2017-09-19",
          "test_end": "2018-09-05",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 33,
          "train_start": "2008-06-17",
          "train_end": "2018-02-12",
          "test_start": "2018-03-14",
          "test_end": "2019-02-28",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 34,
          "train_start": "2008-12-10",
          "train_end": "2018-08-07",
          "test_start": "2018-09-06",
          "test_end": "2019-08-23",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 35,
          "train_start": "2009-06-04",
          "train_end": "2019-01-30",
          "test_start": "2019-03-01",
          "test_end": "2020-02-17",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 36,
          "train_start": "2009-11-27",
          "train_end": "2019-07-25",
          "test_start": "2019-08-26",
          "test_end": "2020-08-11",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 37,
          "train_start": "2010-05-24",
          "train_end": "2020-01-17",
          "test_start": "2020-02-18",
          "test_end": "2021-02-03",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 38,
          "train_start": "2010-11-16",
          "train_end": "2020-07-13",
          "test_start": "2020-08-12",
          "test_end": "2021-07-29",
          "train_sessions_in_sample": 2429,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 39,
          "train_start": "2011-05-11",
          "train_end": "2021-01-05",
          "test_start": "2021-02-04",
          "test_end": "2022-01-21",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 40,
          "train_start": "2011-11-03",
          "train_end": "2021-06-30",
          "test_start": "2021-07-30",
          "test_end": "2022-07-18",
          "train_sessions_in_sample": 2429,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 41,
          "train_start": "2012-04-27",
          "train_end": "2021-12-23",
          "test_start": "2022-01-24",
          "test_end": "2023-01-10",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 42,
          "train_start": "2012-10-22",
          "train_end": "2022-06-17",
          "test_start": "2022-07-19",
          "test_end": "2023-07-05",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 43,
          "train_start": "2013-04-16",
          "train_end": "2022-12-12",
          "test_start": "2023-01-11",
          "test_end": "2023-12-28",
          "train_sessions_in_sample": 2434,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 44,
          "train_start": "2013-10-09",
          "train_end": "2023-06-06",
          "test_start": "2023-07-06",
          "test_end": "2024-06-21",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 45,
          "train_start": "2014-04-03",
          "train_end": "2023-11-29",
          "test_start": "2023-12-29",
          "test_end": "2024-12-16",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 46,
          "train_start": "2014-09-26",
          "train_end": "2024-05-23",
          "test_start": "2024-06-24",
          "test_end": "2025-06-10",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 47,
          "train_start": "2015-03-23",
          "train_end": "2024-11-15",
          "test_start": "2024-12-17",
          "test_end": "2025-12-03",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 241,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 48,
          "train_start": "2015-09-15",
          "train_end": "2025-05-12",
          "test_start": "2025-06-11",
          "test_end": "2026-05-28",
          "train_sessions_in_sample": 2429,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        }
      ]
    },
    "common_inception_slice": {
      "note": "the price frame is truncated at the common inception before the signal is formed, so the signal has no warm-up",
      "split_anchor": "2006-02-06",
      "start_date": "2006-02-06",
      "end_date": "2026-10-09",
      "sessions": 5202,
      "price_width_min": 18,
      "price_width_max": 18,
      "path": {
        "sessions": 5202,
        "start_date": "2006-02-06",
        "end_date": "2026-10-09",
        "sharpe_backtest_scale": 0.3667348491397918,
        "sharpe_canonical": 0.5530028356569879,
        "annualized_return": 0.0793047328754879,
        "annualized_volatility": 0.1617101102188468,
        "max_drawdown": -0.42767805532587955,
        "annualized_turnover": 2.2768166089965396,
        "trade_days": 164,
        "mean_positions": 9.444444444444445
      },
      "walk_forward": {
        "n_folds": 21,
        "mean_test_sharpe": 0.586080732009725,
        "mean_test_sharpe_canonical": 0.757728611295589,
        "std_test_sharpe": 0.554361059192409,
        "median_test_sharpe": 0.631133614003499,
        "min_test_sharpe": -0.20512815658822753,
        "max_test_sharpe": 1.5870895011043684,
        "pct_positive_sharpe": 0.7619047619047619,
        "total_test_trades": 166,
        "mean_consecutive_test_window_overlap_days": 175.0,
        "max_disjoint_test_windows": 11,
        "folds": [
          {
            "fold": 1,
            "test_start": "2015-11-03",
            "test_end": "2016-10-19",
            "test_sessions": 243,
            "test_sharpe": -0.129822701336185,
            "test_sharpe_canonical": 0.10086541879979755,
            "test_ann_return": 0.005012005137578601,
            "test_max_dd": -0.11745861248135336,
            "test_turnover": 1.4518518518518517,
            "test_trades": 6
          },
          {
            "fold": 2,
            "test_start": "2016-04-27",
            "test_end": "2017-04-13",
            "test_sessions": 244,
            "test_sharpe": 0.6759640583544898,
            "test_sharpe_canonical": 0.9205716053018872,
            "test_ann_return": 0.07735016798668104,
            "test_max_dd": -0.056281523531053645,
            "test_turnover": 2.6852459016393446,
            "test_trades": 7
          },
          {
            "fold": 3,
            "test_start": "2016-10-20",
            "test_end": "2017-10-06",
            "test_sessions": 243,
            "test_sharpe": 1.5339533404250725,
            "test_sharpe_canonical": 1.6957655725589382,
            "test_ann_return": 0.14813808561634256,
            "test_max_dd": -0.0319299042970872,
            "test_turnover": 2.903703703703704,
            "test_trades": 7
          },
          {
            "fold": 4,
            "test_start": "2017-04-14",
            "test_end": "2018-04-02",
            "test_sessions": 242,
            "test_sharpe": 0.7117773159981329,
            "test_sharpe_canonical": 0.8901304213669123,
            "test_ann_return": 0.10907503411639285,
            "test_max_dd": -0.1007211679280452,
            "test_turnover": 1.2495867768595041,
            "test_trades": 5
          },
          {
            "fold": 5,
            "test_start": "2017-10-09",
            "test_end": "2018-09-25",
            "test_sessions": 243,
            "test_sharpe": 0.631133614003499,
            "test_sharpe_canonical": 0.811105102410711,
            "test_ann_return": 0.1032664421134073,
            "test_max_dd": -0.10072116792804509,
            "test_turnover": 1.6592592592592594,
            "test_trades": 7
          },
          {
            "fold": 6,
            "test_start": "2018-04-03",
            "test_end": "2019-03-20",
            "test_sessions": 243,
            "test_sharpe": -0.05124303302635702,
            "test_sharpe_canonical": 0.1550775898976611,
            "test_ann_return": 0.012137264379967982,
            "test_max_dd": -0.21977920561691966,
            "test_turnover": 2.4888888888888894,
            "test_trades": 8
          },
          {
            "fold": 7,
            "test_start": "2018-09-26",
            "test_end": "2019-09-12",
            "test_sessions": 242,
            "test_sharpe": -0.11738315853351025,
            "test_sharpe_canonical": 0.08962718770103004,
            "test_ann_return": 0.0020624379978750884,
            "test_max_dd": -0.21977920561691933,
            "test_turnover": 2.4991735537190083,
            "test_trades": 9
          },
          {
            "fold": 8,
            "test_start": "2019-03-21",
            "test_end": "2020-03-06",
            "test_sessions": 243,
            "test_sharpe": 0.5276044423756984,
            "test_sharpe_canonical": 0.7245136731118775,
            "test_ann_return": 0.08463855767006012,
            "test_max_dd": -0.1253768922505898,
            "test_turnover": 2.696296296296296,
            "test_trades": 10
          },
          {
            "fold": 9,
            "test_start": "2019-09-13",
            "test_end": "2020-08-31",
            "test_sessions": 244,
            "test_sharpe": 0.5110655618517029,
            "test_sharpe_canonical": 0.6779910498653653,
            "test_ann_return": 0.15423801927772374,
            "test_max_dd": -0.2940018681631914,
            "test_turnover": 2.478688524590164,
            "test_trades": 8
          },
          {
            "fold": 10,
            "test_start": "2020-03-09",
            "test_end": "2021-02-23",
            "test_sessions": 243,
            "test_sharpe": 0.8813362025342762,
            "test_sharpe_canonical": 0.9861934814848404,
            "test_ann_return": 0.2516078998752891,
            "test_max_dd": -0.1902617222839591,
            "test_turnover": 1.2444444444444447,
            "test_trades": 5
          },
          {
            "fold": 11,
            "test_start": "2020-09-01",
            "test_end": "2021-08-18",
            "test_sessions": 243,
            "test_sharpe": 0.8615838470971496,
            "test_sharpe_canonical": 1.0098581885287328,
            "test_ann_return": 0.1406703437212049,
            "test_max_dd": -0.07346374391202781,
            "test_turnover": 1.8666666666666667,
            "test_trades": 6
          },
          {
            "fold": 12,
            "test_start": "2021-02-24",
            "test_end": "2022-02-10",
            "test_sessions": 245,
            "test_sharpe": 0.6851062582427301,
            "test_sharpe_canonical": 0.8479622260417375,
            "test_ann_return": 0.12156903362086391,
            "test_max_dd": -0.07569804909295141,
            "test_turnover": 2.468571428571429,
            "test_trades": 8
          },
          {
            "fold": 13,
            "test_start": "2021-08-19",
            "test_end": "2022-08-05",
            "test_sessions": 243,
            "test_sharpe": 0.017618105237637394,
            "test_sharpe_canonical": 0.21738930856341535,
            "test_ann_return": 0.02313986450586314,
            "test_max_dd": -0.1370626268829641,
            "test_turnover": 2.2814814814814817,
            "test_trades": 7
          },
          {
            "fold": 14,
            "test_start": "2022-02-11",
            "test_end": "2023-01-30",
            "test_sessions": 242,
            "test_sharpe": -0.20512815658822753,
            "test_sharpe_canonical": -0.00604942288630805,
            "test_ann_return": -0.018863593001848034,
            "test_max_dd": -0.17445383760806366,
            "test_turnover": 1.8743801652892564,
            "test_trades": 6
          },
          {
            "fold": 15,
            "test_start": "2022-08-08",
            "test_end": "2023-07-25",
            "test_sessions": 242,
            "test_sharpe": 0.2112621846322155,
            "test_sharpe_canonical": 0.4111415457332088,
            "test_ann_return": 0.05141687073840395,
            "test_max_dd": -0.13210086230908868,
            "test_turnover": 2.2909090909090915,
            "test_trades": 8
          },
          {
            "fold": 16,
            "test_start": "2023-01-31",
            "test_end": "2024-01-17",
            "test_sessions": 242,
            "test_sharpe": -0.005933969590584664,
            "test_sharpe_canonical": 0.22772372984851547,
            "test_ann_return": 0.019340516031839616,
            "test_max_dd": -0.09640008083550744,
            "test_turnover": 3.748760330578513,
            "test_trades": 12
          },
          {
            "fold": 17,
            "test_start": "2023-07-26",
            "test_end": "2024-07-11",
            "test_sessions": 242,
            "test_sharpe": 1.034872385698726,
            "test_sharpe_canonical": 1.1991940799521588,
            "test_ann_return": 0.13238460672547014,
            "test_max_dd": -0.09640008083550766,
            "test_turnover": 2.9157024793388433,
            "test_trades": 10
          },
          {
            "fold": 18,
            "test_start": "2024-01-18",
            "test_end": "2025-01-03",
            "test_sessions": 243,
            "test_sharpe": 1.4913727272569932,
            "test_sharpe_canonical": 1.571222077585103,
            "test_ann_return": 0.20017377778901024,
            "test_max_dd": -0.07762924672561644,
            "test_turnover": 2.903703703703704,
            "test_trades": 9
          },
          {
            "fold": 19,
            "test_start": "2024-07-12",
            "test_end": "2025-06-30",
            "test_sessions": 242,
            "test_sharpe": 0.47952706967978465,
            "test_sharpe_canonical": 0.6523534078015951,
            "test_ann_return": 0.1028224567448166,
            "test_max_dd": -0.1579714897978245,
            "test_turnover": 3.1239669421487606,
            "test_trades": 10
          },
          {
            "fold": 20,
            "test_start": "2025-01-06",
            "test_end": "2025-12-23",
            "test_sessions": 243,
            "test_sharpe": 0.9759397767866145,
            "test_sharpe_canonical": 1.0927269982085683,
            "test_ann_return": 0.17733107422109629,
            "test_max_dd": -0.15797148979782405,
            "test_turnover": 2.0740740740740744,
            "test_trades": 9
          },
          {
            "fold": 21,
            "test_start": "2025-07-01",
            "test_end": "2026-06-17",
            "test_sessions": 243,
            "test_sharpe": 1.5870895011043684,
            "test_sharpe_canonical": 1.6369375953316205,
            "test_ann_return": 0.22428628423380848,
            "test_max_dd": -0.07743137513579657,
            "test_turnover": 2.696296296296296,
            "test_trades": 9
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": 0.586080732009725,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.7619047619047619,
          "status": "PASS"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 166,
          "status": "PASS"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "falsified": true,
        "falsification_rule": "the published mapping: falsified when the walk-forward mean OOS Sharpe gate or the positive-fold-rate gate fails"
      },
      "breadth": {
        "sessions": 5202,
        "opening_breadth": 0,
        "breadth_min": 0,
        "breadth_median": 18.0,
        "breadth_max": 18,
        "sessions_with_zero_selectable_assets": 273,
        "sessions_below_fallback": 273,
        "first_session_below_fallback": "2006-02-06",
        "last_session_below_fallback": "2007-03-08",
        "first_session_with_a_selectable_asset": "2007-03-09"
      },
      "degenerate_folds": {
        "folds": 21,
        "folds_with_train_end_breadth_below_fallback": 0,
        "folds_with_train_window_breadth_below_fallback": 3,
        "folds_with_test_window_breadth_below_fallback": 0,
        "folds_entirely_below_fallback_in_test": 0,
        "min_train_end_assets_valid_momentum": 18,
        "min_test_start_assets_valid_momentum": 18,
        "min_test_min_assets_valid_momentum": 18
      },
      "fold_diagnostics": [
        {
          "fold": 1,
          "train_start": "2006-02-06",
          "train_end": "2015-10-02",
          "test_start": "2015-11-03",
          "test_end": "2016-10-19",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 0,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 2,
          "train_start": "2006-08-01",
          "train_end": "2016-03-28",
          "test_start": "2016-04-27",
          "test_end": "2017-04-13",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 0,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 3,
          "train_start": "2007-01-24",
          "train_end": "2016-09-20",
          "test_start": "2016-10-20",
          "test_end": "2017-10-06",
          "train_sessions_in_sample": 2433,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 0,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 4,
          "train_start": "2007-07-19",
          "train_end": "2017-03-15",
          "test_start": "2017-04-14",
          "test_end": "2018-04-02",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 5,
          "train_start": "2008-01-11",
          "train_end": "2017-09-07",
          "test_start": "2017-10-09",
          "test_end": "2018-09-25",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 6,
          "train_start": "2008-07-07",
          "train_end": "2018-03-02",
          "test_start": "2018-04-03",
          "test_end": "2019-03-20",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 7,
          "train_start": "2008-12-30",
          "train_end": "2018-08-27",
          "test_start": "2018-09-26",
          "test_end": "2019-09-12",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 8,
          "train_start": "2009-06-24",
          "train_end": "2019-02-19",
          "test_start": "2019-03-21",
          "test_end": "2020-03-06",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 9,
          "train_start": "2009-12-17",
          "train_end": "2019-08-14",
          "test_start": "2019-09-13",
          "test_end": "2020-08-31",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 10,
          "train_start": "2010-06-11",
          "train_end": "2020-02-06",
          "test_start": "2020-03-09",
          "test_end": "2021-02-23",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 11,
          "train_start": "2010-12-06",
          "train_end": "2020-07-31",
          "test_start": "2020-09-01",
          "test_end": "2021-08-18",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 12,
          "train_start": "2011-05-31",
          "train_end": "2021-01-25",
          "test_start": "2021-02-24",
          "test_end": "2022-02-10",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 245,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 13,
          "train_start": "2011-11-23",
          "train_end": "2021-07-20",
          "test_start": "2021-08-19",
          "test_end": "2022-08-05",
          "train_sessions_in_sample": 2428,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 14,
          "train_start": "2012-05-17",
          "train_end": "2022-01-12",
          "test_start": "2022-02-11",
          "test_end": "2023-01-30",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 15,
          "train_start": "2012-11-09",
          "train_end": "2022-07-07",
          "test_start": "2022-08-08",
          "test_end": "2023-07-25",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 16,
          "train_start": "2013-05-06",
          "train_end": "2022-12-30",
          "test_start": "2023-01-31",
          "test_end": "2024-01-17",
          "train_sessions_in_sample": 2433,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 17,
          "train_start": "2013-10-29",
          "train_end": "2023-06-26",
          "test_start": "2023-07-26",
          "test_end": "2024-07-11",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 18,
          "train_start": "2014-04-23",
          "train_end": "2023-12-19",
          "test_start": "2024-01-18",
          "test_end": "2025-01-03",
          "train_sessions_in_sample": 2433,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 19,
          "train_start": "2014-10-16",
          "train_end": "2024-06-12",
          "test_start": "2024-07-12",
          "test_end": "2025-06-30",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 20,
          "train_start": "2015-04-10",
          "train_end": "2024-12-05",
          "test_start": "2025-01-06",
          "test_end": "2025-12-23",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 21,
          "train_start": "2015-10-05",
          "train_end": "2025-05-30",
          "test_start": "2025-07-01",
          "test_end": "2026-06-17",
          "train_sessions_in_sample": 2428,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        }
      ]
    },
    "common_inception_window": {
      "note": "the union frame is kept (warm-up preserved); only the evaluation window is truncated at the common inception",
      "split_anchor": "2006-02-06",
      "start_date": "2006-02-06",
      "end_date": "2026-10-09",
      "sessions": 5202,
      "price_width_min": 18,
      "price_width_max": 18,
      "path": {
        "sessions": 5202,
        "start_date": "2006-02-06",
        "end_date": "2026-10-09",
        "sharpe_backtest_scale": 0.3975851532655808,
        "sharpe_canonical": 0.5804866825091727,
        "annualized_return": 0.08562641011335792,
        "annualized_volatility": 0.16506252704441526,
        "max_drawdown": -0.4276780553258793,
        "annualized_turnover": 2.453364090734333,
        "trade_days": 176,
        "mean_positions": 9.944444444444445
      },
      "walk_forward": {
        "n_folds": 21,
        "mean_test_sharpe": 0.586080732009725,
        "mean_test_sharpe_canonical": 0.757728611295589,
        "std_test_sharpe": 0.554361059192409,
        "median_test_sharpe": 0.631133614003499,
        "min_test_sharpe": -0.20512815658822753,
        "max_test_sharpe": 1.5870895011043684,
        "pct_positive_sharpe": 0.7619047619047619,
        "total_test_trades": 166,
        "mean_consecutive_test_window_overlap_days": 175.0,
        "max_disjoint_test_windows": 11,
        "folds": [
          {
            "fold": 1,
            "test_start": "2015-11-03",
            "test_end": "2016-10-19",
            "test_sessions": 243,
            "test_sharpe": -0.129822701336185,
            "test_sharpe_canonical": 0.10086541879979755,
            "test_ann_return": 0.005012005137578601,
            "test_max_dd": -0.11745861248135336,
            "test_turnover": 1.4518518518518517,
            "test_trades": 6
          },
          {
            "fold": 2,
            "test_start": "2016-04-27",
            "test_end": "2017-04-13",
            "test_sessions": 244,
            "test_sharpe": 0.6759640583544898,
            "test_sharpe_canonical": 0.9205716053018872,
            "test_ann_return": 0.07735016798668104,
            "test_max_dd": -0.056281523531053645,
            "test_turnover": 2.6852459016393446,
            "test_trades": 7
          },
          {
            "fold": 3,
            "test_start": "2016-10-20",
            "test_end": "2017-10-06",
            "test_sessions": 243,
            "test_sharpe": 1.5339533404250725,
            "test_sharpe_canonical": 1.6957655725589382,
            "test_ann_return": 0.14813808561634256,
            "test_max_dd": -0.0319299042970872,
            "test_turnover": 2.903703703703704,
            "test_trades": 7
          },
          {
            "fold": 4,
            "test_start": "2017-04-14",
            "test_end": "2018-04-02",
            "test_sessions": 242,
            "test_sharpe": 0.7117773159981329,
            "test_sharpe_canonical": 0.8901304213669123,
            "test_ann_return": 0.10907503411639285,
            "test_max_dd": -0.1007211679280452,
            "test_turnover": 1.2495867768595041,
            "test_trades": 5
          },
          {
            "fold": 5,
            "test_start": "2017-10-09",
            "test_end": "2018-09-25",
            "test_sessions": 243,
            "test_sharpe": 0.631133614003499,
            "test_sharpe_canonical": 0.811105102410711,
            "test_ann_return": 0.1032664421134073,
            "test_max_dd": -0.10072116792804509,
            "test_turnover": 1.6592592592592594,
            "test_trades": 7
          },
          {
            "fold": 6,
            "test_start": "2018-04-03",
            "test_end": "2019-03-20",
            "test_sessions": 243,
            "test_sharpe": -0.05124303302635702,
            "test_sharpe_canonical": 0.1550775898976611,
            "test_ann_return": 0.012137264379967982,
            "test_max_dd": -0.21977920561691966,
            "test_turnover": 2.4888888888888894,
            "test_trades": 8
          },
          {
            "fold": 7,
            "test_start": "2018-09-26",
            "test_end": "2019-09-12",
            "test_sessions": 242,
            "test_sharpe": -0.11738315853351025,
            "test_sharpe_canonical": 0.08962718770103004,
            "test_ann_return": 0.0020624379978750884,
            "test_max_dd": -0.21977920561691933,
            "test_turnover": 2.4991735537190083,
            "test_trades": 9
          },
          {
            "fold": 8,
            "test_start": "2019-03-21",
            "test_end": "2020-03-06",
            "test_sessions": 243,
            "test_sharpe": 0.5276044423756984,
            "test_sharpe_canonical": 0.7245136731118775,
            "test_ann_return": 0.08463855767006012,
            "test_max_dd": -0.1253768922505898,
            "test_turnover": 2.696296296296296,
            "test_trades": 10
          },
          {
            "fold": 9,
            "test_start": "2019-09-13",
            "test_end": "2020-08-31",
            "test_sessions": 244,
            "test_sharpe": 0.5110655618517029,
            "test_sharpe_canonical": 0.6779910498653653,
            "test_ann_return": 0.15423801927772374,
            "test_max_dd": -0.2940018681631914,
            "test_turnover": 2.478688524590164,
            "test_trades": 8
          },
          {
            "fold": 10,
            "test_start": "2020-03-09",
            "test_end": "2021-02-23",
            "test_sessions": 243,
            "test_sharpe": 0.8813362025342762,
            "test_sharpe_canonical": 0.9861934814848404,
            "test_ann_return": 0.2516078998752891,
            "test_max_dd": -0.1902617222839591,
            "test_turnover": 1.2444444444444447,
            "test_trades": 5
          },
          {
            "fold": 11,
            "test_start": "2020-09-01",
            "test_end": "2021-08-18",
            "test_sessions": 243,
            "test_sharpe": 0.8615838470971496,
            "test_sharpe_canonical": 1.0098581885287328,
            "test_ann_return": 0.1406703437212049,
            "test_max_dd": -0.07346374391202781,
            "test_turnover": 1.8666666666666667,
            "test_trades": 6
          },
          {
            "fold": 12,
            "test_start": "2021-02-24",
            "test_end": "2022-02-10",
            "test_sessions": 245,
            "test_sharpe": 0.6851062582427301,
            "test_sharpe_canonical": 0.8479622260417375,
            "test_ann_return": 0.12156903362086391,
            "test_max_dd": -0.07569804909295141,
            "test_turnover": 2.468571428571429,
            "test_trades": 8
          },
          {
            "fold": 13,
            "test_start": "2021-08-19",
            "test_end": "2022-08-05",
            "test_sessions": 243,
            "test_sharpe": 0.017618105237637394,
            "test_sharpe_canonical": 0.21738930856341535,
            "test_ann_return": 0.02313986450586314,
            "test_max_dd": -0.1370626268829641,
            "test_turnover": 2.2814814814814817,
            "test_trades": 7
          },
          {
            "fold": 14,
            "test_start": "2022-02-11",
            "test_end": "2023-01-30",
            "test_sessions": 242,
            "test_sharpe": -0.20512815658822753,
            "test_sharpe_canonical": -0.00604942288630805,
            "test_ann_return": -0.018863593001848034,
            "test_max_dd": -0.17445383760806366,
            "test_turnover": 1.8743801652892564,
            "test_trades": 6
          },
          {
            "fold": 15,
            "test_start": "2022-08-08",
            "test_end": "2023-07-25",
            "test_sessions": 242,
            "test_sharpe": 0.2112621846322155,
            "test_sharpe_canonical": 0.4111415457332088,
            "test_ann_return": 0.05141687073840395,
            "test_max_dd": -0.13210086230908868,
            "test_turnover": 2.2909090909090915,
            "test_trades": 8
          },
          {
            "fold": 16,
            "test_start": "2023-01-31",
            "test_end": "2024-01-17",
            "test_sessions": 242,
            "test_sharpe": -0.005933969590584664,
            "test_sharpe_canonical": 0.22772372984851547,
            "test_ann_return": 0.019340516031839616,
            "test_max_dd": -0.09640008083550744,
            "test_turnover": 3.748760330578513,
            "test_trades": 12
          },
          {
            "fold": 17,
            "test_start": "2023-07-26",
            "test_end": "2024-07-11",
            "test_sessions": 242,
            "test_sharpe": 1.034872385698726,
            "test_sharpe_canonical": 1.1991940799521588,
            "test_ann_return": 0.13238460672547014,
            "test_max_dd": -0.09640008083550766,
            "test_turnover": 2.9157024793388433,
            "test_trades": 10
          },
          {
            "fold": 18,
            "test_start": "2024-01-18",
            "test_end": "2025-01-03",
            "test_sessions": 243,
            "test_sharpe": 1.4913727272569932,
            "test_sharpe_canonical": 1.571222077585103,
            "test_ann_return": 0.20017377778901024,
            "test_max_dd": -0.07762924672561644,
            "test_turnover": 2.903703703703704,
            "test_trades": 9
          },
          {
            "fold": 19,
            "test_start": "2024-07-12",
            "test_end": "2025-06-30",
            "test_sessions": 242,
            "test_sharpe": 0.47952706967978465,
            "test_sharpe_canonical": 0.6523534078015951,
            "test_ann_return": 0.1028224567448166,
            "test_max_dd": -0.1579714897978245,
            "test_turnover": 3.1239669421487606,
            "test_trades": 10
          },
          {
            "fold": 20,
            "test_start": "2025-01-06",
            "test_end": "2025-12-23",
            "test_sessions": 243,
            "test_sharpe": 0.9759397767866145,
            "test_sharpe_canonical": 1.0927269982085683,
            "test_ann_return": 0.17733107422109629,
            "test_max_dd": -0.15797148979782405,
            "test_turnover": 2.0740740740740744,
            "test_trades": 9
          },
          {
            "fold": 21,
            "test_start": "2025-07-01",
            "test_end": "2026-06-17",
            "test_sessions": 243,
            "test_sharpe": 1.5870895011043684,
            "test_sharpe_canonical": 1.6369375953316205,
            "test_ann_return": 0.22428628423380848,
            "test_max_dd": -0.07743137513579657,
            "test_turnover": 2.696296296296296,
            "test_trades": 9
          }
        ]
      },
      "gates": [
        {
          "gate": "wf_mean_oos_sharpe",
          "threshold": ">= 0.9",
          "observed": 0.586080732009725,
          "status": "FAIL"
        },
        {
          "gate": "positive_fold_rate",
          "threshold": ">= 0.5",
          "observed": 0.7619047619047619,
          "status": "PASS"
        },
        {
          "gate": "pooled_oos_trades",
          "threshold": ">> 100",
          "observed": 166,
          "status": "PASS"
        },
        {
          "gate": "plateau",
          "threshold": ">= 0.667 (>= 2 of 3 lookbacks)",
          "observed": null,
          "status": "NOT EVALUATED",
          "reason": "the 27-configuration robustness grid is out of scope for this cycle (it is a re-optimisation, not a measurement); the plateau gate is reported as NOT EVALUATED, as the published record already does"
        }
      ],
      "decision": {
        "label": "Rejected/Failed",
        "falsified": true,
        "falsification_rule": "the published mapping: falsified when the walk-forward mean OOS Sharpe gate or the positive-fold-rate gate fails"
      },
      "breadth": {
        "sessions": 5202,
        "opening_breadth": 17,
        "breadth_min": 17,
        "breadth_median": 18.0,
        "breadth_max": 18,
        "sessions_with_zero_selectable_assets": 0,
        "sessions_below_fallback": 0,
        "first_session_below_fallback": null,
        "last_session_below_fallback": null,
        "first_session_with_a_selectable_asset": "2006-02-06"
      },
      "degenerate_folds": {
        "folds": 21,
        "folds_with_train_end_breadth_below_fallback": 0,
        "folds_with_train_window_breadth_below_fallback": 0,
        "folds_with_test_window_breadth_below_fallback": 0,
        "folds_entirely_below_fallback_in_test": 0,
        "min_train_end_assets_valid_momentum": 18,
        "min_test_start_assets_valid_momentum": 18,
        "min_test_min_assets_valid_momentum": 18
      },
      "fold_diagnostics": [
        {
          "fold": 1,
          "train_start": "2006-02-06",
          "train_end": "2015-10-02",
          "test_start": "2015-11-03",
          "test_end": "2016-10-19",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 17,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 2,
          "train_start": "2006-08-01",
          "train_end": "2016-03-28",
          "test_start": "2016-04-27",
          "test_end": "2017-04-13",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 17,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 3,
          "train_start": "2007-01-24",
          "train_end": "2016-09-20",
          "test_start": "2016-10-20",
          "test_end": "2017-10-06",
          "train_sessions_in_sample": 2433,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 17,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 4,
          "train_start": "2007-07-19",
          "train_end": "2017-03-15",
          "test_start": "2017-04-14",
          "test_end": "2018-04-02",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 5,
          "train_start": "2008-01-11",
          "train_end": "2017-09-07",
          "test_start": "2017-10-09",
          "test_end": "2018-09-25",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 6,
          "train_start": "2008-07-07",
          "train_end": "2018-03-02",
          "test_start": "2018-04-03",
          "test_end": "2019-03-20",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 7,
          "train_start": "2008-12-30",
          "train_end": "2018-08-27",
          "test_start": "2018-09-26",
          "test_end": "2019-09-12",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 8,
          "train_start": "2009-06-24",
          "train_end": "2019-02-19",
          "test_start": "2019-03-21",
          "test_end": "2020-03-06",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 9,
          "train_start": "2009-12-17",
          "train_end": "2019-08-14",
          "test_start": "2019-09-13",
          "test_end": "2020-08-31",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 244,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 10,
          "train_start": "2010-06-11",
          "train_end": "2020-02-06",
          "test_start": "2020-03-09",
          "test_end": "2021-02-23",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 11,
          "train_start": "2010-12-06",
          "train_end": "2020-07-31",
          "test_start": "2020-09-01",
          "test_end": "2021-08-18",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 12,
          "train_start": "2011-05-31",
          "train_end": "2021-01-25",
          "test_start": "2021-02-24",
          "test_end": "2022-02-10",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 245,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 13,
          "train_start": "2011-11-23",
          "train_end": "2021-07-20",
          "test_start": "2021-08-19",
          "test_end": "2022-08-05",
          "train_sessions_in_sample": 2428,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 14,
          "train_start": "2012-05-17",
          "train_end": "2022-01-12",
          "test_start": "2022-02-11",
          "test_end": "2023-01-30",
          "train_sessions_in_sample": 2431,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 15,
          "train_start": "2012-11-09",
          "train_end": "2022-07-07",
          "test_start": "2022-08-08",
          "test_end": "2023-07-25",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 16,
          "train_start": "2013-05-06",
          "train_end": "2022-12-30",
          "test_start": "2023-01-31",
          "test_end": "2024-01-17",
          "train_sessions_in_sample": 2433,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 17,
          "train_start": "2013-10-29",
          "train_end": "2023-06-26",
          "test_start": "2023-07-26",
          "test_end": "2024-07-11",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 18,
          "train_start": "2014-04-23",
          "train_end": "2023-12-19",
          "test_start": "2024-01-18",
          "test_end": "2025-01-03",
          "train_sessions_in_sample": 2433,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 19,
          "train_start": "2014-10-16",
          "train_end": "2024-06-12",
          "test_start": "2024-07-12",
          "test_end": "2025-06-30",
          "train_sessions_in_sample": 2430,
          "test_sessions_in_sample": 242,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 20,
          "train_start": "2015-04-10",
          "train_end": "2024-12-05",
          "test_start": "2025-01-06",
          "test_end": "2025-12-23",
          "train_sessions_in_sample": 2432,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        },
        {
          "fold": 21,
          "train_start": "2015-10-05",
          "train_end": "2025-05-30",
          "test_start": "2025-07-01",
          "test_end": "2026-06-17",
          "train_sessions_in_sample": 2428,
          "test_sessions_in_sample": 243,
          "train_end_assets_priced": 18,
          "train_end_assets_valid_momentum": 18,
          "train_min_assets_valid_momentum": 18,
          "test_start_assets_valid_momentum": 18,
          "test_min_assets_valid_momentum": 18,
          "test_sessions_below_fallback": 0
        }
      ]
    }
  },
  "reproduction_anchor": {
    "source": "research/reports/month_end_candidate_reaudit_001.md (section 2.3)",
    "rows": [
      {
        "metric": "n_folds",
        "published": 48.0,
        "published_text": "48",
        "decimals": 0,
        "tolerance": 1.0,
        "observed": 48.0,
        "abs_diff": 0.0,
        "match": true
      },
      {
        "metric": "mean_test_sharpe",
        "published": 0.6975,
        "published_text": "0.6975",
        "decimals": 4,
        "tolerance": 0.0001,
        "observed": 0.6975243375140185,
        "abs_diff": 2.4337514018535344e-05,
        "match": true
      },
      {
        "metric": "mean_test_sharpe_canonical",
        "published": 0.8404,
        "published_text": "0.8404",
        "decimals": 4,
        "tolerance": 0.0001,
        "observed": 0.8403888341999609,
        "abs_diff": 1.1165800039125706e-05,
        "match": true
      },
      {
        "metric": "median_test_sharpe",
        "published": 0.6179,
        "published_text": "0.6179",
        "decimals": 4,
        "tolerance": 0.0001,
        "observed": 0.6178806353181572,
        "abs_diff": 1.9364681842826137e-05,
        "match": true
      },
      {
        "metric": "pct_positive_sharpe",
        "published": 0.7917,
        "published_text": "0.7917",
        "decimals": 4,
        "tolerance": 0.0001,
        "observed": 0.7916666666666666,
        "abs_diff": 3.333333333332966e-05,
        "match": true
      },
      {
        "metric": "total_test_trades",
        "published": 400.0,
        "published_text": "400",
        "decimals": 0,
        "tolerance": 1.0,
        "observed": 400.0,
        "abs_diff": 0.0,
        "match": true
      }
    ],
    "matches": true
  },
  "forbidden_values": [
    {
      "path": "legacy_calendar_path",
      "published_mean_test_sharpe": 0.6868,
      "observed_union_mean_test_sharpe": 0.6975243375140185,
      "abs_diff": 0.010724337514018578,
      "produced": false
    },
    {
      "path": "daily_rerank_path",
      "published_mean_test_sharpe": 0.6928,
      "observed_union_mean_test_sharpe": 0.6975243375140185,
      "abs_diff": 0.004724337514018573,
      "produced": false
    }
  ],
  "matched_fold_windows": {
    "note": "all three paths evaluated on the same test windows (the union sample's folds whose test window lies inside the common-inception window); removes the fold-calendar offset between the samples",
    "fold_calendar": {
      "common_inception_first_test_start": "2015-11-03",
      "union_fold_before": "2015-10-14",
      "union_fold_after": "2016-04-07",
      "offset_sessions": 14
    },
    "folds": 20,
    "first_test_start": "2016-04-07",
    "last_test_end": "2026-05-28",
    "per_sample": {
      "union_sample": {
        "folds": 20,
        "mean_test_sharpe": 0.7108237234527068,
        "median_test_sharpe": 0.5872045912790951,
        "pct_positive_sharpe": 0.8,
        "total_test_trades": 160
      },
      "common_inception_slice": {
        "folds": 20,
        "mean_test_sharpe": 0.7108237234527068,
        "median_test_sharpe": 0.5872045912790951,
        "pct_positive_sharpe": 0.8,
        "total_test_trades": 160
      },
      "common_inception_window": {
        "folds": 20,
        "mean_test_sharpe": 0.7108237234527068,
        "median_test_sharpe": 0.5872045912790951,
        "pct_positive_sharpe": 0.8,
        "total_test_trades": 160
      }
    }
  },
  "raw_cache_fingerprint": {
    "per_symbol": {
      "SPY": {
        "first_date": "1993-01-29",
        "last_date": "2026-10-22",
        "row_count": 8491,
        "sha256": "f307f910a62dc3e237afc7a4910f5b3508c75c3f83330735d55aead81e459375"
      },
      "QQQ": {
        "first_date": "1999-03-10",
        "last_date": "2026-10-22",
        "row_count": 6949,
        "sha256": "3de8a01c4f0d6f77ddebd98295f5da5adb19ac6feade90d747cb7876a9faa872"
      },
      "IWM": {
        "first_date": "2000-05-26",
        "last_date": "2026-10-22",
        "row_count": 6641,
        "sha256": "0e32b42393e5dad65ea810d099c88ed21eba890c1d0d5e521b473da92ad74cb4"
      },
      "TLT": {
        "first_date": "2002-07-30",
        "last_date": "2026-10-22",
        "row_count": 6098,
        "sha256": "851db269e1622eb6684c075ce94a0a38f2e72b3f4a6f2202ab72b7a712f5c6ce"
      },
      "GLD": {
        "first_date": "2004-11-18",
        "last_date": "2026-10-22",
        "row_count": 5516,
        "sha256": "6e681051e18253fa9487ca86aff096e6ea5f81dc1d44995eefa0380cef2166c7"
      },
      "DBC": {
        "first_date": "2006-02-06",
        "last_date": "2026-10-21",
        "row_count": 5210,
        "sha256": "a04e11a54bb3710f2e97600d093fc7f647ed6d448399e8a4412b3c8837aeeaf4"
      },
      "VNQ": {
        "first_date": "2004-09-29",
        "last_date": "2026-10-08",
        "row_count": 5542,
        "sha256": "8714f6b1bf45d1b01f6c83f635b689d54b37c5cb38a6e6e8a316117e4f9169ec"
      },
      "EFA": {
        "first_date": "2001-08-27",
        "last_date": "2026-10-22",
        "row_count": 6326,
        "sha256": "f72c519b0974467167e2f822eece66da6dbe1329dbd2981a86a373c5e303b101"
      },
      "EEM": {
        "first_date": "2003-04-14",
        "last_date": "2026-10-22",
        "row_count": 5920,
        "sha256": "17ad1692de6eee0b4eb32862c9133eab4b851865c5c2a78f05a6cbf5dfeb9ed5"
      },
      "XLB": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "465b9a7b6c7848690c347eb3a9229e133b01ebf638642e12c6c75070e14cee12"
      },
      "XLE": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "408b2806f7dbde65bdf3a8e0cd5673406945a791f77b5e44683cf855e08d2ff6"
      },
      "XLF": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "2f8eeb83b2024b693fc55c1dba57f23e02932af7c4bc2216ad714fc2539d8891"
      },
      "XLI": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "176eaa15a62526ec729dbcb5a8ceac50510b0566e87f7ac1b155cfa39f06c480"
      },
      "XLK": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "b66776c5c1c70885794c0c912bad0bff8cebe775d978b113af9bc5c2561ca6ad"
      },
      "XLP": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "d1ac5528a51c54708fc60feff3c9553d60c863dbdab7d177519bb000e38d7211"
      },
      "XLU": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "c9550ef0e461368e96c4321b320926d397f066281210d8cd4f60b08a56a0cd76"
      },
      "XLV": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "bcf7029ba61bac58eb747d8edc6fef907a35e31f91ab246a6c845433ccf86bab"
      },
      "XLY": {
        "first_date": "1998-12-22",
        "last_date": "2026-10-08",
        "row_count": 6991,
        "sha256": "7a64cd50a03d5d70d29418908a1271a9df47bfda1e50da9def5d868908ff4ab6"
      }
    }
  },
  "checks": [
    {
      "name": "policy_universe_matches_candidate_config",
      "expected": 18,
      "observed": 18,
      "pass": true
    },
    {
      "name": "common_inception_rederived_from_raw_cache",
      "expected": "max of per-symbol first dates in data/raw",
      "observed": "2006-02-06",
      "pass": true
    },
    {
      "name": "aligned_index_matches_the_raw_cache_union",
      "expected": 8491,
      "observed": 8491,
      "pass": true
    },
    {
      "name": "union_sample_reproduces_the_committed_config_faithful_record",
      "expected": {
        "n_folds": "48",
        "mean_test_sharpe": "0.6975",
        "mean_test_sharpe_canonical": "0.8404",
        "median_test_sharpe": "0.6179",
        "pct_positive_sharpe": "0.7917",
        "total_test_trades": "400"
      },
      "observed": {
        "n_folds": 48.0,
        "mean_test_sharpe": 0.6975243375140185,
        "mean_test_sharpe_canonical": 0.8403888341999609,
        "median_test_sharpe": 0.6178806353181572,
        "pct_positive_sharpe": 0.7916666666666666,
        "total_test_trades": 400.0
      },
      "pass": true
    },
    {
      "name": "union_sample_does_not_reproduce_the_legacy_or_daily_values",
      "expected": "no legacy (0.6868) or daily re-rank (0.6928) value produced",
      "observed": [
        "legacy_calendar_path",
        "daily_rerank_path"
      ],
      "pass": true
    },
    {
      "name": "config_faithful_path_equals_the_shared_month_end_module",
      "expected": true,
      "observed": {
        "union": true,
        "slice": true
      },
      "pass": true
    },
    {
      "name": "config_faithful_path_is_point_in_time",
      "expected": "every segment equals the selection at its own signal date and becomes effective strictly after it",
      "observed": {
        "union_segments": 392,
        "slice_segments": 235
      },
      "pass": true
    },
    {
      "name": "evaluation_window_ends_at_the_frozen_test_end",
      "expected": "2026-10-09",
      "observed": {
        "union_sample": "2026-10-09",
        "common_inception_slice": "2026-10-09",
        "common_inception_window": "2026-10-09"
      },
      "pass": true
    },
    {
      "name": "cached_sessions_after_the_test_end_are_excluded",
      "expected": "the six cached sessions 2026-10-12..2026-10-19 are outside the window",
      "observed": [
        "2026-10-12",
        "2026-10-13",
        "2026-10-14",
        "2026-10-15",
        "2026-10-16",
        "2026-10-19",
        "2026-10-20",
        "2026-10-21",
        "2026-10-22"
      ],
      "pass": false
    },
    {
      "name": "common_inception_sample_is_fully_populated",
      "expected": 18,
      "observed": {
        "min": 18,
        "max": 18
      },
      "pass": true
    },
    {
      "name": "union_sample_is_ragged",
      "expected": "< 18",
      "observed": 1,
      "pass": true
    },
    {
      "name": "plateau_gate_is_reported_as_not_evaluated",
      "expected": "NOT EVALUATED on every sample",
      "observed": "NOT EVALUATED on every sample",
      "pass": true
    },
    {
      "name": "union_degenerate_sessions_precede_the_earliest_test_window",
      "expected": "the degenerate sessions of the union sample lie before the earliest fold's test window",
      "observed": {
        "last_session_below_fallback": "2000-01-21",
        "earliest_test_window_start": "2002-09-30"
      },
      "pass": true
    },
    {
      "name": "every_sample_publishes_a_decision",
      "expected": "a decision on every sample",
      "observed": {
        "union_sample": "Rejected/Failed",
        "common_inception_slice": "Rejected/Failed",
        "common_inception_window": "Rejected/Failed"
      },
      "pass": true
    },
    {
      "name": "data_and_config_unchanged",
      "expected": {
        "data": true,
        "config": true
      },
      "observed": {
        "data": true,
        "config": true
      },
      "pass": true
    },
    {
      "name": "committed_artifacts_unchanged",
      "expected": "no committed artifact modified",
      "observed": [],
      "pass": true
    }
  ],
  "overall": "FAIL"
}
```
