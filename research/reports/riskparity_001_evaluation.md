# Risk-Balanced (Inverse-Volatility) Allocation — `riskparity_001`

**Cycle 930 — pre-registered evaluation of `research/hypotheses/riskparity_001.md`.**

## Status

- **Decision: REJECT** — Rejected / failed the pre-registered promotion gates.
- Pre-registered baseline (L = 63, cap = 0.3): walk-forward mean OOS Sharpe **0.778089** (canonical 0.914204).
- Gate `wf_mean_oos_sharpe`: 0.778089 >= 0.900000 -> **FAIL**.
- Gate `positive_fold_rate`: 0.863636 >= 0.500000 -> **PASS**.
- Gate `pooled_oos_trades`: 252.000000 > 100.000000 -> **PASS**.
- Trials evaluated: **9** (the pre-registered grid; DSR computed at N = 9).
- Evaluation window: 2005-11-10 .. 2026-10-19 (22 walk-forward folds, 10y train / 12m test / 6m step, 21d purge and embargo).

## 1. What was evaluated

A long-only, fully invested, month-end rebalanced inverse-volatility book
over the incumbent's seven-ETF universe. The volatility estimate is
**lagged** (it uses the returns up to and including the session *before*
the rebalance), the book formed on the last session of a month is
effective from the next session, and the cost model is the repository's
committed one: 1.0 bp commission + 2.0 bp slippage = 3.0 bp per unit of weight change.

**The evaluation window is the pre-registered point-in-time-complete one.**
The pre-registration states the rule -- the evaluation starts on the
first session on which all seven members carry a valid *lagged*
volatility estimate -- and gives 2005-11-10 as the date. The rule is
measured at **2005-02-22** from the
committed cache: 2005-11-10 is the incumbent's *momentum* warm-up date
for GLD (226-session lookback skipping 21), not a 63-session volatility
date. The pre-registered date is therefore **later** than the rule
requires, so the window is point-in-time complete strictly from its
first session and every configuration of the grid is measured on a
homogeneous cross-section. The pre-registration is used unchanged; the
discrepancy is measured and reported, not silently corrected.

## 2. Pre-registered grid (9 configurations, no post-hoc change)

| L | cap | WF mean OOS Sharpe | median | canonical mean | positive folds | pooled trades | min fold | gates |
|---|---|---|---|---|---|---|---|---|
| 21 | 0.25 | 0.784390 | 0.847988 | 0.921176 | 0.863636 | 252 | -1.815736 | FAIL |
| 21 | 0.30 | 0.783972 | 0.833841 | 0.921888 | 0.863636 | 252 | -1.813668 | FAIL |
| 21 | 0.40 | 0.783364 | 0.831360 | 0.921356 | 0.863636 | 252 | -1.813668 | FAIL |
| 63 | 0.25 | 0.779549 | 0.830092 | 0.915460 | 0.863636 | 252 | -1.805118 | FAIL |
| 63 | 0.30 | 0.778089 | 0.821681 | 0.914204 | 0.863636 | 252 | -1.805118 | FAIL |
| 63 | 0.40 | 0.778089 | 0.821681 | 0.914204 | 0.863636 | 252 | -1.805118 | FAIL |
| 126 | 0.25 | 0.778202 | 0.763555 | 0.913733 | 0.863636 | 252 | -1.778351 | FAIL |
| 126 | 0.30 | 0.777807 | 0.759278 | 0.913393 | 0.863636 | 252 | -1.778351 | FAIL |
| 126 | 0.40 | 0.777807 | 0.759278 | 0.913393 | 0.863636 | 252 | -1.778351 | FAIL |

Maximum realised weight in the baseline book: 0.300000 (cap 0.30, at most 2 iterations, residual 0.000000).
Rebalances formed: 260; first invested session inside the evaluation window 2005-11-10 (5266 invested sessions).

## 3. The baseline's walk-forward folds

| Fold | Test window | OOS Sharpe | canonical | ann. return | max DD | ann. turnover | trades |
|---|---|---|---|---|---|---|---|
| 1 | 2015-08-07 .. 2016-07-25 | 0.250280 | 0.472613 | 0.048522 | -0.109756 | 0.805 | 11 |
| 2 | 2016-02-01 .. 2017-01-17 | 1.373221 | 1.537679 | 0.142780 | -0.056345 | 0.661 | 11 |
| 3 | 2016-07-26 .. 2017-07-12 | 1.038595 | 1.283952 | 0.097578 | -0.056345 | 0.759 | 12 |
| 4 | 2017-01-18 .. 2018-01-04 | 2.947295 | 3.043913 | 0.190561 | -0.027012 | 0.767 | 12 |
| 5 | 2017-07-13 .. 2018-06-29 | 0.645183 | 0.892313 | 0.074673 | -0.080814 | 0.922 | 11 |
| 6 | 2018-01-05 .. 2018-12-24 | -1.234618 | -1.051876 | -0.108859 | -0.139019 | 1.246 | 11 |
| 7 | 2018-07-02 .. 2019-06-18 | 0.106370 | 0.366263 | 0.029709 | -0.108619 | 1.246 | 11 |
| 8 | 2018-12-25 .. 2019-12-11 | 2.640700 | 2.657352 | 0.223310 | -0.037669 | 1.124 | 12 |
| 9 | 2019-06-19 .. 2020-06-04 | 0.436412 | 0.610925 | 0.104497 | -0.232331 | 1.122 | 12 |
| 10 | 2019-12-12 .. 2020-11-27 | 0.825310 | 0.948397 | 0.190269 | -0.232331 | 1.152 | 11 |
| 11 | 2020-06-05 .. 2021-05-24 | 1.885780 | 1.892087 | 0.249295 | -0.060068 | 0.950 | 11 |
| 12 | 2020-11-30 .. 2021-11-16 | 1.106702 | 1.279057 | 0.130238 | -0.060068 | 1.010 | 12 |
| 13 | 2021-05-25 .. 2022-05-11 | -1.315230 | -1.170692 | -0.134491 | -0.177036 | 1.070 | 12 |
| 14 | 2021-11-17 .. 2022-11-03 | -1.805118 | -1.872048 | -0.266265 | -0.268808 | 0.823 | 12 |
| 15 | 2022-05-12 .. 2023-04-28 | 0.137354 | 0.337140 | 0.041691 | -0.157689 | 0.595 | 11 |
| 16 | 2022-11-04 .. 2023-10-23 | 0.759586 | 0.933191 | 0.114497 | -0.100117 | 0.611 | 11 |
| 17 | 2023-05-01 .. 2024-04-16 | 0.902118 | 1.084800 | 0.115835 | -0.100117 | 0.739 | 11 |
| 18 | 2023-10-24 .. 2024-10-09 | 2.513608 | 2.408423 | 0.302726 | -0.066016 | 0.896 | 12 |
| 19 | 2024-04-17 .. 2025-04-03 | 0.608368 | 0.805892 | 0.090334 | -0.066016 | 0.905 | 12 |
| 20 | 2024-10-10 .. 2025-09-26 | 0.987312 | 1.126741 | 0.150150 | -0.118458 | 1.021 | 11 |
| 21 | 2025-04-04 .. 2026-03-23 | 1.490674 | 1.548211 | 0.220889 | -0.078863 | 1.078 | 11 |
| 22 | 2025-09-29 .. 2026-09-15 | 0.818053 | 0.978162 | 0.128128 | -0.087916 | 1.012 | 12 |

## 4. Chronological splits (baseline)

| Split | Window | Sharpe (backtest scale) | Sharpe (canonical) | ann. return | ann. vol | Sortino | max DD | profit factor | ann. turnover | trade days | exposure |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2005-11-10 .. 2015-12-31 | 0.349464 | 0.546040 | 0.068925 | 0.139999 | 0.482369 | -0.334196 | 1.104 | 0.786 | 121 | 1.000000 |
| validation | 2016-01-04 .. 2020-12-31 | 0.817442 | 0.991936 | 0.117273 | 0.118997 | 0.902551 | -0.232331 | 1.215 | 0.988 | 59 | 1.000000 |
| test | 2021-01-04 .. 2026-10-19 | 0.373945 | 0.576656 | 0.067995 | 0.128347 | 0.556784 | -0.271560 | 1.103 | 0.880 | 69 | 1.000000 |

## 5. Benchmarks and diversification

| Reference | Window | Sharpe (backtest scale) | canonical | ann. return | max DD | ann. turnover |
|---|---|---|---|---|---|---|
| 1/N equal weight (full) | 2005-11-10 .. 2026-10-19 | 0.387201 | 0.574864 | 0.079360 | -0.423520 | 0.000 |
| 1/N equal weight (test) | 2021-01-04 .. 2026-10-19 | 0.377583 | 0.573008 | 0.072401 | -0.279744 | 0.000 |
| SPY buy-and-hold (full) | 2005-11-10 .. 2026-10-19 | 0.372295 | 0.552086 | 0.091358 | -0.564737 | 0.000 |
| SPY buy-and-hold (test) | 2021-01-04 .. 2026-10-19 | 0.675278 | 0.830205 | 0.132393 | -0.253606 | 0.000 |

The two ways of quoting a Sharpe are not interchangeable: the *whole-window*
rows above are a single Sharpe over the whole 21-year window, while the
walk-forward figure is the **mean of the per-fold Sharpes** (each fold is
a 12-month window). Averaging over shorter windows raises the mean
because the annualised volatility of a 12-month slice is smaller than the
volatility of the 21-year path. Both numbers are stated with their
definition, and only like-for-like pairs are compared.
- **1/N on the same walk-forward folds**: mean OOS Sharpe 0.773084 (canonical 0.894553), positive-fold rate 0.863636.
- **Excess of the candidate over 1/N on the same folds**: **0.005005** (backtest scale). This is the
  mechanism's contribution net of the equity beta a long-only seven-asset
  book earns anyway (AGENTS.md, "Known confounders").
- Correlation of the candidate's pooled out-of-sample returns with the 1/N benchmark: **0.991382**.
- Correlation with SPY buy-and-hold: **0.884300**.
- Correlation with the incumbent's path (reference only, a different path and a different window): **0.658742**.

## 6. Statistical validity

- Probabilistic Sharpe Ratio against 0 (block bootstrap, 1000 draws, block 22): PSR(normal) = 0.999701, PSR(empirical) = 1.000000, observed canonical Sharpe 0.748521 (95% CI 0.330754 .. 1.161947).
- Deflated Sharpe Ratio at the declared N = 9: DSR = 2.127308, probability = 0.983303, selection threshold 0.284575 (E[max] = 1.304845).

## 7. Cost sensitivity

- Walk-forward mean OOS Sharpe at 0 bp per unit: 0.780927;
  at the committed 3 bp per unit: **0.778089**; at 10 bp: 0.771467.
- Gate 1 (WF mean OOS Sharpe >= 0.9) flip cost: never flips (already fails at 0 bp).
- Gate 2 (positive-fold rate >= 0.5) flip cost: 100.0 bp per unit.
- Edge-erosion cost (the largest cost at which the walk-forward mean OOS Sharpe is still above zero): **100.0 bp per unit**.

## 8. Robustness (plateau)

| Volatility lookback | mean WF OOS Sharpe over the three caps |
|---|---|
| 21 | 0.783908 |
| 63 | 0.778575 |
| 126 | 0.777939 |

| Cap | mean WF OOS Sharpe over the three lookbacks |
|---|---|
| 0.25 | 0.780713 |
| 0.3 | 0.779956 |
| 0.4 | 0.779753 |

## 9. What this does and does not change

- **Nothing published changed.** The published record, the published
  gates, the published protocol, the committed shortlist and every
  committed candidate artefact are byte-identical after the run; the
  fetcher was never called and `data/` and `config/` are byte-identical.
- **A new candidate was evaluated, not a new edge claimed.** The
  decision and the label are stated above; a candidate that fails the
  pre-registered gates is archived with its evidence.
- **The incumbent's verdict is unchanged.** It remains a Credible
  Candidate by its published verdict and NO-GO for promotion.
- **The comparison is like-for-like on the window, not on the path.**
  The candidate is measured on the point-in-time-complete window; the
  incumbent's published record is measured on its own window, and the
  correlation with it is reported as a diversification reference only.

## 10. Reproduction

```bash
python research/riskparity_001_eval.py
python -m pytest -q tests/test_riskparity_001_evaluation.py
git status --porcelain data/ config/
```

Every number in this report is re-derived by the first command from the
committed cache, `config/` and the committed hypothesis document.
