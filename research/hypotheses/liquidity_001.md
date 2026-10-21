# Hypothesis: Liquidity-Provision Premium (liquidity_001)

## Version History

- v001 (liquidity_001, 2026-10-21): Initial pre-registered hypothesis for
  Cycle 938 (evaluation Cycle 938). Parent cycle: Cycle 934 evidence-based
  candidate shortlist (`liquidity_001`, **24/35**, rank 3 of 4; after
  `reversal_001` 28/35 rank 1, `pairs_001` 25/35 rank 2, ahead of
  `leadlag_001` 16/35). Source of every pre-registered value:
  `research/experiments/candidate_shortlist_934.md` (tool
  `research/candidate_shortlist_934.py`, OVERALL: PASS). Code revision at
  freeze: 5b6421a. **Pre-registered BEFORE any liquidity_001 backtest execution.** No
  liquidity_001 backtest exists in this repository at the time of this freeze.

---

## Mechanism Description

Assets whose price moves more per unit of traded volume earn a premium, because
the liquidity provider is compensated for the risk of adverse selection; the
premium is realised as the illiquid asset's price drifts back toward its
fundamental value. The pre-registered test isolates the first-order effect:
score each sector ETF by the Amihud measure |21-session return| / dollar volume
over the trailing 21 sessions; hold the most illiquid quintile (2 of 9) at equal
weight, cash otherwise, rebalance monthly (every ~21 sessions) with the signal
formed at `t` effective at `t+1`.

This mechanism is **distinct from every closed line in this repository**:

* the momentum family (incumbent `tsmomentum_spytrend_001`, `csmomentum_001`,
  `sectorrotation_001` / `sectorrotation_002`) uses time-series or cross-sectional
  momentum; this candidate uses an illiquidity-based ranking, not return momentum;
* `reversal_001` (Rejected/Failed, Cycle 935) is short-horizon reversal on the
  same nine-sector panel; this candidate uses a 21-session horizon and an
  illiquidity measure, not trailing returns;
* `pairs_001` (Rejected/Failed, Cycle 936) is market-neutral pairs trading; this
  candidate is long-only and directional;
* `riskparity_001` (Rejected), `calendar_effects_001` (Rejected/Failed),
  `overnight_capture_001` (Rejected/Failed), `macroregime_001` (Rejected/Failed),
  `futuresbasis_001` (Blocked by data), `futuresbasis_002` (Rejected/Failed),
  `mom121_microcap_001` (Blocked by data), `cryptofunding_001` (Exploratory
  signal, not promoted) are not touched by this candidate.

The shortlist's published weakness is carried into the evaluation plan: the
Amihud score is dominated by the volume denominator, so the ranking partly
re-ranks the volume of the ETF wrappers, not the liquidity of the underlying
sector. Volume-based scores are also sensitive to volume spikes that follow
large price moves, which mechanically invert the signal.

---

## Expected direction and magnitude (Pre-Specified Prior)

The prior is conservative and consistent with the Cycle 934 shortlist score
(c) Expected net return after costs = **2/5** (the *minimum* of the measured
cost hurdle 5/5 and a declared gross prior of 2/5). **No gross magnitude has
been measured in this repository**, so no return is asserted.

| Metric | Prior (this hypothesis) | Note |
|--------|--------------------------|------|
| Gross direction | positive relative to the 1/N benchmark of the same nine sectors | long the most illiquid, funded from cash |
| Gross magnitude | **not measured**; the pre-registered requirement is quantitative and below | the cost hurdle is the only magnitude claim, and it is a *requirement*, not a forecast |
| Net walk-forward mean OOS Sharpe | >= 0.9 (promotion gate) | gate fixed by AGENTS.md / `config/promotion_gates.yaml`; the prior probability of clearing it is **LOW** |
| Maximum drawdown (test) | < 25% | the book is long illiquid names, so liquidity shocks could create losses |
| Annualized turnover | ~24 units/yr (one book rotation per monthly rebalance) -> 0.7200%/yr drag at 3 bp/unit | measured by the evaluation |

**The pre-registered cost hurdle (measured in Cycle 934).** The shortlist
published a measured gross scale of **73.4546%/yr** and a cost hurdle of
**0.9802%** of that gross scale per year / per the horizon. The annual cost
drag is **0.7200%/yr**. The rule must therefore capture enough to cover the
0.7200%/yr drag against a 73.4546%/yr gross scale.

---

## Holding horizon

21 trading sessions (one month). The signal is formed on the close of session
`t` and the positions are effective from session `t+1` (one-session lag). The
portfolio is rebalanced monthly (~every 21 sessions).

---

## Asset universe

Nine GICS sector ETFs: **XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY**.

This is the only **membership-stable** cross-section in the repository: all
nine files carry an identical cached history (**6,991 sessions,
1998-12-22 .. 2026-10-08, 0 missing closes, 0 duplicate timestamps, 0
non-positive closes, 0 zero-volume rows**), so the effective cross-section is
constant over the whole sample and there is no survivorship or
membership-growth channel.

---

## Features and data sources

| Feature | Definition | Source |
|---------|------------|--------|
| Amihud illiquidity | \|21-session return\| / dollar volume over the trailing 21 sessions, per sector ETF | `data/raw/{XLB,...,XLY}.parquet`, columns `Close`, `Volume` |
| Cross-sectional ranking | rank by Amihud measure (higher = more illiquid) | same panel |
| Cross-sectional dispersion | standard deviation of Amihud scores at formation date | same panel (used for hurdle check) |

Data source: the committed parquet cache only. **The fetcher is never called.**
No external data, no fundamental data, no intraday data.

---

## Entry / exit rules

1. On every rebalance session `t` (every 21st session of the panel, anchored on
   the panel's first session), score each of the nine ETFs by Amihud measure
   over trailing 21 sessions formed at `t`.
2. Select the **most illiquid quintile**: the two highest-ranked ETFs (2 of 9)
   by illiquidity.
3. Hold the two at equal weight (0.5 each of the gross book); hold **cash**
   (0.0) in the other seven. No leverage, no short leg, no borrow.
4. The weights formed at `t` are effective from `t+1` (one-session lag).
5. Exit an ETF when it leaves the most illiquid quintile at a rebalance; no
   intra-horizon trading.

---

## Benchmark

**1/N equal-weight buy-and-hold of the same nine sector ETFs** over the same
window.

---

## Known confounders

1. **Volume-denominated ranking**: The Amihud score is dominated by the volume
   denominator, so the ranking partly re-ranks the volume of the ETF wrappers,
   not the liquidity of the underlying sector.
2. **Volume spike inversion**: Volume-based scores are sensitive to the volume
   spike that follows a large price move, which mechanically inverts the signal.
3. **ETF volume fragmentation**: ETF volume is venue-fragmented and the cached
   volume is a consolidated daily figure.
4. **Embedded fees**: Sector ETF expense ratios and index-tracking differences
   are embedded in the observed (adjusted) prices and are not modelled separately.
5. **Short-horizon arbitrage**: The illiquidity premium in the most liquid corner
   of the market (large-cap sector ETFs) may be small and heavily arbitraged.
6. **Constituent membership unavailable**: GICS constituent-level membership
   history is not in the repository.

---

## Falsification condition (pre-registered)

The hypothesis is **falsified** if ANY of the following hold on the
chronological out-of-sample walk-forward (10-year train, 12-month test,
6-month step, 21-day purge, 21-day embargo, one-session signal lag, 3 bp per
unit of weight change):

1. the walk-forward mean OOS Sharpe (net, canonical convention) is **< 0.9**;
2. the **benchmark-relative net excess** has a moving-block bootstrap 95% CI
   that **includes zero**;
3. the **measured cross-sectional dispersion of the Amihud score** is too small
   to cover the cost hurdle (mechanism does not reach its own cost hurdle);
4. the benchmark-relative net excess is **not positive** in the post-2009
   sub-sample.

Promotion requires **all** of (1)-(4) to pass and the standard AGENTS.md
multiple-testing controls (Deflated Sharpe Ratio over the declared trial count
of 1, positive-fold rate, pooled trade count, bootstrap CI). Failing any
condition downgrades the candidate to **Rejected/Failed**; no result obtained
after this freeze may change a threshold.

---

## Cost model assumptions

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Slippage | 2.0 bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Round trip | **3.0 bp per unit of weight change** | derived |
| Risk-free rate | 2.00% annual | `config/settings.yaml` via `src.backtest.engine.get_risk_free_rate()` |
| Borrow / short-side cost | **none** (the rule is long-only: no short leg) | n/a |
| Market impact, bid-ask spread, latency, margin | **absent from the repository's cost model** | disclosed gap |

Costs are charged on the absolute weight change on rebalance days, exactly as
`src/backtest/engine.py` does for every committed artifact. The realized
turnover is **measured** in the evaluation, not assumed.

---

## Evaluation design (pre-registered)

* **Sample**: the nine-sector panel, 1998-12-22 .. 2026-10-08 (6,991 sessions). No sample selection is performed after the fact.
* **Walk-forward**: 10-year rolling train, 12-month test, 6-month step, 21-day purge, 21-day embargo.
* **Trials**: **1** (one baseline rule, one configuration, no grid). No parameter search and no variant is pre-registered here.
* **Reported**: walk-forward mean OOS Sharpe on both the backtest and the canonical scale, positive-fold rate, pooled OOS trades, the three promotion gates, the benchmark-relative net excess with its moving-block bootstrap 95% CI (seed 20240101), the measured Amihud score dispersion against the cost hurdle, realized turnover and cost drag, and post-2009 sub-sample check.
* **Benchmark**: 1/N of the same nine sectors over the same folds.

## Reproduction

```bash
python research/liquidity_001_evaluation.py
python -m pytest -q tests/test_liquidity_001_evaluation.py
```
