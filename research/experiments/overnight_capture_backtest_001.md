# Experiment 001 - Overnight-Session Capture Candidate (`overnight_capture_001`)

## Hypothesis reference

`research/hypotheses/overnight_capture_001.md` (pre-registered in Cycle 880
before any backtest was executed; erratum disclosed post-execution in the same
file - the erratum corrects an arithmetic error in the stated cost drag and
changes no threshold, gate or configuration).

## Data used

| Item | Value |
|------|-------|
| Source | committed cache `data/raw/{SPY,QQQ,IWM}.parquet` (Yahoo Finance via yfinance, `auto_adjust=False` = raw OHLC, not dividend-adjusted) |
| Universe | SPY, QQQ, IWM (fixed; no in-sample selection) |
| Frequency | daily |
| Date range | 2000-05-26 (IWM inception) -> 2026-10-16 |
| Common calendar | 6,637 sessions |
| Missing data | 0 missing Open, 0 missing Close, 0 duplicate dates, 0 OHLC violations |
| Network | none required by the evaluation script (read-only on the committed cache) |

## Point-in-time treatment

The overnight return of session *t* is `Open_t / Close_{t-1} - 1`: the position
is established at the **previous** close and liquidated at the open, so the
standing rule uses only information available before the open of session *t*.
The exposure mask is the trading calendar itself (no price-derived decision,
no lookahead, no fitted parameter).

## Configuration

`config/overnight_capture_001.yaml` (sha256[:12] = bb44adfbc500):
1/3 equal-weight SPY/QQQ/IWM, held overnight only, flat intraday; turnover 2.0
units per session (sell 1.0 at the open, buy 1.0 at the close) = 504 units of
annual turnover; decision cost 3 bp/unit (1 bp commission + 2 bp slippage from
`config/settings.yaml`); sensitivity rows 5 bp and 10 bp; N = 3.

## Splits

`src/evaluation/walkforward.py: generate_walkforward_splits` with
train = 10.0y, test = 12.0m, step = 6.0m, purge = 21d, embargo = 21d.
**33 folds** (asserted in the script). First fold test 2010-02-22 -> 2011-02-08;
last fold test 2025-08-06 -> 2026-07-23. Per-fold statistic = test-period net
Sharpe; the train window only bounds the fold (no fitted parameter).

## Results (3 bp/unit decision configuration)

| Quantity | Value |
|---|---|
| Gross overnight annualized return (no cost) | +0.0916 |
| Net full-sample annualized return | -0.0616 (cost drag 0.1512/yr) |
| Net full-sample Sharpe (CAGR scale, rf 2%) | -0.6679 |
| Net full-sample canonical Sharpe (arithmetic, rf 0) | -0.4590 |
| Net full-sample max drawdown | -0.8558 |
| WF mean OOS Sharpe (gate statistic) | **-0.599718** |
| WF std / median of fold Sharpes | 0.992454 / -0.802496 |
| Positive fold rate | **15.1515%** (5 of 33) |
| Pooled OOS trades | **8016** |
| Pooled OOS sessions | 8016 |
| Pooled canonical Sharpe | -0.389216 |
| DSR (N = 3) | -2.446673 -> rejected |
| PSR vs the 0.9 gate | 0.000000 |
| Block-bootstrap 95% CI (n=1000, block=22, seed=42) | [-0.788295, 0.034214] |
| Cost row 3 / 5 / 10 bp (WF mean OOS Sharpe) | -0.5997 / -1.5469 / -3.5375 |
| Benchmark: close-to-close equal weight (WF mean OOS Sharpe) | **+0.844696** |
| Benchmark: intraday-only leg (WF mean OOS Sharpe) | -0.957874 |
| Rolling-63 windows below the 0.9 gate (own history) | 69.1979% of 7,954 windows |

Gates/falsification: F1 FAIL, F2 FAIL, F3 PASS, F4 FAIL, F5 FAIL; DSR rejected;
bootstrap CI lower bound <= 0.

## Number of trials

**3** (the three pre-registered cost levels 3 / 5 / 10 bp per unit). No
parameter grid, no post-hoc variants, no data-driven selection.

## Reproduction commands

```
python research/overnight_capture_backtest.py   # exit 0, OVERALL: PASS
python research/go_no_go_evaluation.py           # NO-GO, side_effect_free: True
python -m pytest -q                              # 95 existing + 8 new
git status --porcelain data/ config/             # empty
```

## Decision label

**Rejected/Failed.** The gross overnight premium (+9.16%/yr) is real but is
smaller than the 15.12%/yr cost of the two daily round trips an overnight-only
leg requires, and the candidate loses to passive close-to-close holding of the
identical basket on identical folds (WF mean OOS Sharpe -0.599718 vs
+0.844696). No promotion, no deployment, no change to the incumbent.
