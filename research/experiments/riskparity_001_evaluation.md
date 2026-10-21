# Experiment: riskparity_001_evaluation (Cycle 930)

**Hypothesis reference:** `research/hypotheses/riskparity_001.md`
(pre-registered; this experiment executes its evaluation plan unchanged).

## Data used

- **Source:** committed parquet cache `data/raw/`; the fetcher is never
  called and nothing under `data/` or `config/` is written.
- **Date range:** 2005-11-10 .. 2026-10-19 (the pre-registered point-in-time-complete
  window; the first session on which all seven members carry a valid
  lagged 63-session volatility estimate is measured from the cache).
- **Frequency:** daily (UTC session index).
- **Universe:** SPY, QQQ, IWM, TLT, GLD, EFA, EEM (the incumbent's universe).
- **Point-in-time treatment:** the volatility estimate is lagged (it uses
  the returns up to and including the session *before* the rebalance), the
  book formed on the last session of a month is effective from the next
  session, and no price is forward filled across a member's inception
  inside the evaluation window.

## Configuration

- **Candidate:** `riskparity_001` — long-only inverse-volatility, monthly rebalance, L = 63, per-asset cap 0.30 (baseline).
- **Cost model:** 1.0 bp commission + 2.0 bp slippage = 3.0 bp per unit of weight change; risk-free 2.00%.
- **Walk-forward:** 10y train / 12m test / 6m step, 21d purge, 21d
  embargo, fixed parameters (no per-fold re-optimisation).
- **Splits:** train .. 2015-12-31, validation .. 2020-12-31, test .. end of cache (chronological,
  non-overlapping).

## Results

| Quantity | Value |
|---|---|
| Walk-forward folds | 22 |
| WF mean OOS Sharpe (backtest scale) | 0.778089 |
| WF mean OOS Sharpe (canonical) | 0.914204 |
| Median fold Sharpe | 0.821681 |
| Worst fold Sharpe | -1.805118 |
| Positive-fold rate | 0.863636 |
| Pooled out-of-sample trades | 252 |
| Gate `wf_mean_oos_sharpe` | 0.778089 >= 0.900000 -> FAIL |
| Gate `positive_fold_rate` | 0.863636 >= 0.500000 -> PASS |
| Gate `pooled_oos_trades` | 252.000000 > 100.000000 -> PASS |
| Test-period Sharpe (chronological split) | 0.373945 |
| 1/N benchmark, test window | 0.377583 |
| 1/N benchmark, walk-forward mean OOS Sharpe (same folds) | 0.773084 |
| Excess of the candidate over 1/N (same folds) | 0.005005 |
| SPY buy-and-hold, test window | 0.675278 |
| Correlation with 1/N | 0.991382 |
| Correlation with SPY | 0.884300 |
| Correlation with the incumbent | 0.658742 |
| PSR against 0 | 0.999701 |
| DSR at N = 9 | 2.127308 (probability 0.983303) |
| Edge-erosion cost per unit (WF mean <= 0) | 100.0 bp |
| Decision | **REJECT** |
| Label | Rejected / failed the pre-registered promotion gates |

## Number of trials

**9** — exactly the pre-registered grid (L in {21, 63, 126} x cap in {0.25, 0.30, 0.40}); no configuration was
added, removed or re-selected after the run. The Deflated Sharpe Ratio
is computed at N = 9.

## Reproduction commands

```bash
python research/riskparity_001_eval.py
python -m pytest -q tests/test_riskparity_001_evaluation.py
git status --porcelain data/ config/
```

---

# Cycle 932 — Independent-sample significance of riskparity_001 excess over 1/N (negative result)

**Hypothesis reference:** `research/hypotheses/riskparity_001.md` (same candidate, no re-optimisation).

## Data used

- **Source:** committed parquet cache `data/raw/`; the fetcher is never called.
- **Date range:** 2006-02-15 .. 2026-05-28 (the point-in-time-complete window of Cycle 931).
- **Frequency:** daily (UTC session index).
- **Universe:** SPY, QQQ, IWM, TLT, GLD, EFA, EEM.
- **Point-in-time treatment:** unchanged from Cycle 930 (lagged volatility estimate, effective-from-next-session rebalance, no forward fill).

## Configuration

- **Candidate:** `riskparity_001` (baseline: long-only inverse-volatility, monthly rebalance, L = 63, per-asset cap 0.30).
- **Benchmark:** 1/N on the same universe, same folds, same cost model (3.0 bp per unit).
- **Walk-forward:** same 10y/12m/6m design with 21d purge + embargo; **non-overlapping annual subset** — even folds 8, 10, 12, …, 48 (21 folds, 12-month spacing).

## Results

| Quantity | Value |
|---|---|
| Folds in annual subset | 21 |
| riskparity_001 excess over 1/N | 0.038820 |
| 95% CI (2000 draws, block = 2) | [-0.001639, 0.082736] |
| 95% CI (1000 draws, block = 2) | [-0.000496, 0.081935] |
| Excludes zero | **False** |
| Report | `research/reports/annual_subset_riskparity_vs_oneoverN_932.md` |

**Decision: REJECT (negative result).** The Cycle 931 significance on 41 overlapping folds did not survive non-overlapping sampling. riskparity_001 remains a rejected candidate; its edge over 1/N is not robust.

## Number of trials

**0** — no parameter search, no new candidate, no configuration change. The 21 folds are a subset of the already-evaluated Cycle 931 fold set.

## Reproduction commands

```bash
python research/mechanism_comparison_001.py
python research/annual_subset_riskparity_vs_oneoverN_932.py
git status --porcelain data/ config/
```
