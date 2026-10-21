# Hypothesis: Cross-Sectional Short-Horizon Reversal (reversal_001)

## Version History

- v001 (reversal_001, 2026-10-21): Initial pre-registered hypothesis for
  Cycle 935 (evaluation Cycle 935/936). Parent cycle: Cycle 934
  evidence-based candidate shortlist (`reversal_001`, **28/35**, rank 1 of 4;
  next best `pairs_001` 25/35, `liquidity_001` 24/35, `leadlag_001` 16/35).
  Source of every pre-registered value: `research/experiments/candidate_shortlist_934.md`
  (tool `research/candidate_shortlist_934.py`, OVERALL: PASS). Code revision at
  freeze: 5b6421a. **Pre-registered BEFORE any backtest execution.** No
  reversal backtest exists in this repository at the time of this freeze.

---

## Mechanism Description

An asset that has fallen over the past week tends to revert over the
following weeks. The move is driven by non-informational,
liquidity-demanding order flow; the seller who provides liquidity is
compensated by the subsequent reversal, and short-sale and rebalancing
constraints make temporary price pressure persistent.

The pre-registered test isolates the first-order effect: rank the nine GICS
sector ETFs by their trailing 5-session total return, hold the **bottom
quintile** (2 of 9) at equal weight, hold cash otherwise, and rebalance every
5 sessions with a one-session signal lag.

This mechanism is **distinct from every closed line in this repository**:

* the momentum family (incumbent `tsmomentum_spytrend_001`, `csmomentum_001`)
  uses a 226+21-session horizon and the *opposite* sign; this candidate uses a
  5-session horizon and the opposite sign;
* `sectorrotation_001` / `sectorrotation_002` rank the *same nine sector
  ETFs* by a 12-month score and are **Rejected/Failed**; this candidate ranks
  the same panel by a 5-session score, which is the **mirror** of that
  rejected signal (see the mandatory mirror test below);
* `riskparity_001` (Rejected), `calendar_effects_001` (Rejected/Failed),
  `overnight_capture_001` (Rejected/Failed), `macroregime_001` (Rejected/Failed),
  `futuresbasis_001` (Blocked by data), `futuresbasis_002` (Rejected/Failed),
  `mom121_microcap_001` (Blocked by data), `cryptofunding_001` (Exploratory
  signal, not promoted) are not touched by this candidate.

The shortlist's published weakness is carried into the evaluation plan: the
nine-sector panel is **not** new to this repository, so a reversal result on it
could be the arithmetic mirror of a rejected momentum result rather than a new
edge. The **mirror test** below exists to make that visible.

---

## Expected direction and magnitude (Pre-Specified Prior)

The prior is conservative and consistent with the Cycle 934 shortlist score
(c) Expected net return after costs = **3/5** (the *minimum* of the measured
cost hurdle 5/5 and a declared gross prior of 3/5). **No gross magnitude has
been measured in this repository**, so no return is asserted.

| Metric | Prior (this hypothesis) | Note |
|--------|--------------------------|------|
| Gross direction | positive relative to the 1/N benchmark of the same nine sectors | long the laggards, funded from cash |
| Gross magnitude | **not measured**; the pre-registered requirement is quantitative and below | the capture-fraction hurdle is the only magnitude claim, and it is a *requirement*, not a forecast |
| Net walk-forward mean OOS Sharpe | >= 0.9 (promotion gate) | gate fixed by AGENTS.md / `config/promotion_gates.yaml`; the prior probability of clearing it is **LOW** |
| Maximum drawdown (test) | < 25% | the book is long the recent losers, so a sharp rally in the winners is a direct loss |
| Annualized turnover | ~52 units/yr (one book rotation per weekly rebalance) -> 1.5600%/yr drag at 3 bp/unit | the committed one-book-rotation-per-rebalance convention; the measured panel (6,991 sessions over 27.79 years, 251.4 sessions/yr) implies ~50.3 actual rebalances/yr, so the estimate is an upper bound |

**The pre-registered cost hurdle (measured in Cycle 934).** The median
cross-sectional dispersion of the 5-session return across the nine sector ETFs
is **1.4965%** per rebalance, i.e. **77.8181%/yr** of scale. The annual cost
drag is **1.5600%/yr**. The rule must therefore capture at least

    3 bp / 1.4965%  =  2.0047%

of the cross-sectional dispersion per rebalance to break even at the
repository's cost model. This number is the cycle's only magnitude claim.

---

## Holding horizon

5 trading sessions (one week). The signal is formed on the close of session
`t` and the positions are effective from session `t+1` (one-session lag). The
portfolio is rebalanced every 5 sessions.

---

## Asset universe

Nine GICS sector ETFs: **XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY**.

This is the only **membership-stable** cross-section in the repository: all
nine files carry an identical cached history (**6,991 sessions,
1998-12-22 .. 2026-10-08, 0 missing closes, 0 duplicate timestamps, 0
non-positive closes, 0 zero-volume rows**), so the effective cross-section is
constant over the whole sample and there is no survivorship or
membership-growth channel. The panel ends 2026-10-08, eight sessions behind
the rest of the committed cache.

---

## Features and data sources

| Feature | Definition | Source |
|---------|------------|--------|
| Signal score | trailing 5-session total return (Close[t] / Close[t-5] - 1) per sector ETF | `data/raw/{XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY}.parquet`, column `Close` |
| Cross-sectional dispersion | standard deviation, across the nine, of the 5-session return at the formation date | same panel (used for the capture fraction and the hurdle) |

Data source: the committed parquet cache only. **The fetcher is never called.**
No external data, no fundamental data, no constituent (GICS) membership data,
no intraday data.

---

## Entry / exit rules

1. On every rebalance session `t` (every 5th session of the panel, anchored on
   the panel's first session), rank the nine ETFs by the trailing 5-session
   return formed at `t`.
2. Select the **bottom quintile**: the two lowest-ranked ETFs (2 of 9).
3. Hold the two at equal weight (0.5 each of the gross book); hold **cash**
   (0.0) in the other seven. No leverage, no short leg, no borrow.
4. The weights formed at `t` are effective from `t+1` (one-session lag).
5. Exit an ETF when it leaves the bottom quintile at a rebalance; no
   intra-horizon trading.

---

## Benchmark

**1/N equal-weight buy-and-hold of the same nine sector ETFs** over the same
window -- the benchmark the committed cross-sectional candidates use. The
decision statistic is the **benchmark-relative** result, because the rule is a
short-beta tilt against 1/N in a risk-on market.

Secondary references (read-only, not decision statistics): the incumbent
`tsmomentum_spytrend_001` on its own seven-asset universe, and the
**mirror** of the rejected `sectorrotation_001` / `sectorrotation_002` signal
on this same nine-sector panel.

---

## Known confounders

1. **Momentum-crash risk**: the book is long the laggards, so a sharp rally in
   the recent winners is a direct loss.
2. **Short-beta tilt**: all nine ETFs are US equity sectors; the rule is a
   short-beta tilt against the 1/N benchmark in a risk-on market, so the
   benchmark-relative result, not the absolute return, is the relevant
   statistic.
3. **Panel lag**: the sector panel ends 2026-10-08, eight sessions behind the
   rest of the committed cache.
4. **Constituent membership unavailable**: GICS constituent-level membership
   history is not in the repository, so the sector ETFs' underlying
   composition over the sample cannot be reconstructed.
5. **Embedded fees**: ETF expense ratios and index-tracking differences are
   embedded in the observed (adjusted) prices and are not modelled separately.
6. **Turnover convention**: the one-book-rotation-per-rebalance estimate
   follows the repository's committed cost-screen convention and is an upper
   bound; a partial rotation turns over less. The evaluation must measure the
   realized turnover rather than assume it.
7. **Mirror-image confound**: the same nine-sector panel was traded by two
   rejected momentum candidates. A positive reversal result is not
   automatically a new edge (the mandatory mirror test).
8. **Effect decay**: short-horizon reversal is heavily arbitraged in liquid
   ETFs and its published magnitude has decayed; the declared gross prior is
   3/5, not higher.

---

## Falsification condition (pre-registered)

The hypothesis is **falsified** if ANY of the following hold on the
chronological out-of-sample walk-forward (10-year train, 12-month test,
6-month step, 21-day purge, 21-day embargo, one-session signal lag, 3 bp per
unit of weight change):

1. the walk-forward mean OOS Sharpe (net, canonical convention) is **< 0.9**;
2. the **benchmark-relative net excess** has a moving-block bootstrap 95% CI
   that **includes zero**;
3. the benchmark-relative net excess is **not positive** in the post-2009
   sub-sample (era stability);
4. the **measured gross capture fraction** falls below the pre-registered cost
   hurdle of **2.0047%** of the cross-sectional dispersion per rebalance (the
   mechanism does not reach its own cost hurdle) -- capture fraction at a
   rebalance is
   `[mean(bottom quintile 5-session return) - mean(all nine)] / std(all nine)`
   at the formation date, and the test statistic is its median over the
   out-of-sample rebalances;
5. the **positive-fold rate < 0.5** or the **pooled OOS trades <= 100**;
6. the **mirror test** shows the result is not distinguishable from the
   arithmetic mirror of the rejected sector-momentum signal: the candidate's
   benchmark-relative net excess must not be explained by the *negative* of
   the rejected `sectorrotation_002` signal's excess on the same panel (the
   correlation of the two excess series and the sign of the mirror
   difference are reported, and a mirror-explained result is **not** a new
   edge).

Promotion requires **all** of: (1)-(5) pass, (6) not fired, and the standard
AGENTS.md multiple-testing controls (Deflated Sharpe Ratio over the declared
trial count of 1, positive-fold rate, pooled trade count, bootstrap CI).
Failing any condition downgrades the candidate to **Rejected/Failed**; no
result obtained after this freeze may change a threshold.

---

## Cost model assumptions

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Slippage | 2.0 bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Round trip | **3.0 bp per unit of weight change** | derived |
| Risk-free rate | 2.00% annual | `config/settings.yaml` via `src.backtest.engine.get_risk_free_rate()` |
| Borrow / short-side cost | **none** (the rule is long-only: no short leg) | n/a |
| Market impact, bid-ask spread, latency, margin | **absent from the repository's cost model** | disclosed gap; bounded by the committed Cycle-913 break-even audit |

Costs are charged on the absolute weight change on rebalance days, exactly as
`src/backtest/engine.py` does for every committed artifact. The realized
turnover is **measured** in the evaluation, not assumed.

---

## Evaluation design (pre-registered)

* **Sample**: the nine-sector panel, 1998-12-22 .. 2026-10-08 (6,991
  sessions). No sample selection is performed after the fact.
* **Walk-forward**: 10-year rolling train, 12-month test, 6-month step,
  21-day purge, 21-day embargo -- the repository's committed design.
* **Trials**: **1** (one baseline rule, one configuration, no grid). No
  parameter search and no variant is pre-registered here.
* **Reported**: walk-forward mean OOS Sharpe on both the backtest and the
  canonical scale, positive-fold rate, pooled OOS trades, the three promotion
  gates, the benchmark-relative net excess with its moving-block bootstrap 95%
  CI (seed 20240101, the seed of Cycles 929/930), the median gross capture
  fraction against the 2.0047% hurdle, the realized turnover and cost drag,
  and the mirror test against the rejected sector-momentum signal.
* **Benchmark**: 1/N of the same nine sectors over the same folds.

## Reproduction

The evaluation tool does not exist yet at the time of this freeze; it is
written in the evaluation cycle and must read this file and
`config/reversal_candidate_001.yaml` as the frozen specification. The
pre-registration commit hash is published with the result record.

```bash
python -m pytest -q tests/test_reversal_001_evaluation.py
```
