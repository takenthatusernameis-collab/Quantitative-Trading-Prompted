# Experiment: `liquidity_001` evaluation (liquidity_001_evaluation)

**Cycle 938.** Execution of the **frozen** pre-registration (`research/hypotheses/liquidity_001.md` + `config/liquidity_candidate_001.yaml`, freeze commit **5b6421a**). The frozen values are re-asserted by the tool before the run; a post-freeze edit of the config fails closed. No threshold, gate, cost model, universe or Sharpe convention was changed after the result was known; nothing under `data/` or `config/` was written; the fetcher was never called; no other candidate was executed, re-tuned or re-ranked.

**Correction (published by Cycle 940).** Two reporting defects were found in this record. (1) The Deflated Sharpe Ratio line was produced by an **unseeded** moving-block bootstrap and was therefore not reproducible: the published value changed on every run of this tool (three consecutive runs gave -2.963458, -2.954174 and -2.886135). The line is regenerated from the frozen configuration's declared bootstrap seed (20240101) and draw count (2000). (2) The **Realized cost drag** line published the fraction of return under a percent label (0.007159%/yr), while the record's own turnover figure (23.862681 units/yr at 3.0 bp per unit of weight change) implies 0.715880%/yr; the line now carries that value. Every other measured value, every threshold and the **verdict are unchanged**. The corrections are of record in `research/experiments/liquidity_001_evaluation_erratum_001.md`.

## Hypothesis reference
`research/hypotheses/liquidity_001.md` (frozen at `5b6421a`).

## Data used
- **Source**: the committed parquet cache `data/raw/{XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY}.parquet` (the fetcher is never called).
- **Date range**: 1998-12-22 .. 2026-10-08
- **Frequency**: daily, session hours
- **Universe**: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY (nine GICS sector ETFs; identical cached history, 6991 sessions, no gaps)
- **Point-in-time treatment**: the Amihud measure at session `t` uses only prices/volumes up to and including `t`; the weights formed at `t` become effective at `t+1` (one-session lag).

## Configuration (frozen)
| Item | Value |
|---|---|
| Signal | Amihud illiquidity \|21-session return\| / dollar volume, **most illiquid** 2 of 9, equal weight, cash otherwise |
| Rebalance | every 21 sessions (monthly), anchored on the panel's first session |
| Signal lag | 1 session |
| Cost model | 1.0 bp commission + 2.0 bp slippage = **3.0 bp per unit of weight change**, 2.00% annual risk-free |
| Benchmark | 1/N equal-weight buy-and-hold of the same nine ETFs |
| Walk-forward | 10-year train, 12-month test, 6-month step, 21-day purge, 21-day embargo |
| Trials | **1** (one baseline rule, no grid) |

## Results

**Walk-forward folds:** 36

### Gate statistics
| Statistic | Value | Gate | Outcome |
|---|---|---|---|
| Walk-forward mean OOS Sharpe (canonical) | -0.649990 | >= 0.9 | FAIL |
| Walk-forward median OOS Sharpe | -0.640745 | - | - |
| Walk-forward std of OOS Sharpe | 1.144518 | - | - |
| Positive-fold rate | 0.333333 | >= 0.5 | FAIL |
| Pooled OOS trades | 832 | > 100 | PASS |
| Benchmark-relative net excess (mean fold Sharpe difference) | -1.426408 | - | - |
| Excess 95% CI (moving block, 2000 draws, block 4, seed 20240101) | [-2.113215, -0.859968] | excludes zero | PASS |
| Deflated Sharpe Ratio (N = 1) | -2.968111 (probability 0.001498; moving-block bootstrap, 2000 draws, block 22, seed 20240101) | - | - |

### Amihud dispersion and costs
| Quantity | Value |
|---|---|
| Median cross-sectional dispersion of Amihud score | 0.000000 |
| Realized turnover | 23.862681 units/yr |
| Realized cost drag | 0.715880%/yr |
| Post-2009 excess (annualized approx) | -0.125639 |

## Falsification condition (pre-registered) and outcome
| # | Condition | Observed | Requirement | Outcome |
|---|---|---|---|---|
| i | walk-forward mean OOS Sharpe (net, canonical) >= 0.9 | -0.6499904032699622 | 0.9 | **FIRED** |
| ii | benchmark-relative net excess bootstrap 95% CI excludes zero | [-2.113215, -0.859968] | excludes zero | not fired |
| iii | measured cross-sectional dispersion of Amihud score sufficient to cover cost hurdle | 3.2180143291199496e-12 | > 0 | not fired |
| iv | benchmark-relative net excess positive in the post-2009 sub-sample | -0.12563873769605635 | > 0 | **FIRED** |

**Rejected/Failed**

## Decision
The candidate is **falsified**: condition(s) i, iv fired. It is labelled **Rejected/Failed**; it is not promoted, not simulated and not paper-traded, and its configuration is retired as written (no variant is opened).

**No other candidate's verdict changes.** The incumbent `tsmomentum_spytrend_001` stays a **Credible Candidate** and **NO-GO** for promotion; every closed line keeps its committed status.

## Reproduction commands
```bash
python research/liquidity_001_evaluation.py
python -m pytest -q tests/test_liquidity_001_evaluation.py
git status --porcelain data/
git diff --name-only HEAD -- config/settings.yaml
```
