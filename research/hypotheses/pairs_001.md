# Hypothesis: Cointegrated-Pairs Relative Value (pairs_001)

## Version History

- v001 (pairs_001, 2026-10-21): Initial pre-registered hypothesis for
  Cycle 936 (evaluation Cycle 936). Parent cycle: Cycle 934 evidence-based
  candidate shortlist (`pairs_001`, **25/35**, rank 2 of 4; selected after
  `reversal_001` 28/35 rank 1, ahead of `liquidity_001` 24/35 and
  `leadlag_001` 16/35). Source of every pre-registered value:
  `research/experiments/candidate_shortlist_934.md` (tool
  `research/candidate_shortlist_934.py`, OVERALL: PASS). Code revision at
  freeze: bf66a64. **Pre-registered BEFORE any pairs backtest execution.** No
  pairs backtest exists in this repository at the time of this freeze.

---

## Mechanism Description

Two securities that share a common driver trade with a temporary dispersion
around their long-run (cointegrated) relationship; the dispersion reverts,
and a market-neutral book (long the cheap leg, short the rich leg) earns the
convergence without the common factor. The pre-registered test isolates the
first-order effect: for each of six pre-registered sector-ETF pairs, z-score
the log price ratio over the trailing 126 sessions and take the contrarian
side when |z| >= 1, dollar-neutral per pair, rebalanced every 5 sessions
with a one-session signal lag.

This mechanism is **distinct from every closed line in this repository**:

* the momentum family (incumbent `tsmomentum_spytrend_001`, `csmomentum_001`,
  `sectorrotation_001` / `sectorrotation_002`) uses time-series or
  cross-sectional momentum and is **Rejected/Failed**; this candidate trades
  the *spread* between two co-moving assets, not the level of any one asset;
* `reversal_001` (Rejected/Failed, Cycle 936) is long-only cross-sectional
  reversal on the same nine-sector panel; this candidate is market-neutral
  and borrows, so it is a different family on the same panel;
* `riskparity_001` (Rejected), `calendar_effects_001` (Rejected/Failed),
  `overnight_capture_001` (Rejected/Failed), `macroregime_001` (Rejected/Failed),
  `futuresbasis_001` (Blocked by data), `futuresbasis_002` (Rejected/Failed),
  `mom121_microcap_001` (Blocked by data), `cryptofunding_001` (Exploratory
  signal, not promoted) are not touched by this candidate.

The shortlist's published weakness is carried into the evaluation plan: the
repository holds **no borrow data at all**, so the short-side borrow cost of
25 bp per unit of short notional per rebalance is a pre-registered
**assumption**, not a measurement; and the six pairs are pre-registered
(they are not selected by a search on the full sample), so pair-selection
multiplicity is bounded by construction.

---

## Expected direction and magnitude (Pre-Specified Prior)

The prior is conservative and consistent with the Cycle 934 shortlist score
(c) Expected net return after costs = **3/5** (the *minimum* of the measured
cost hurdle 5/5 and a declared gross prior of 3/5). **No gross magnitude has
been measured in this repository**, so no return is asserted.

| Metric | Prior (this hypothesis) | Note |
|--------|--------------------------|------|
| Gross direction | positive relative to cash (market-neutral book) | long the cheap leg, short the rich leg of each pair |
| Gross magnitude | **not measured**; the pre-registered requirement is quantitative and below | the borrow-adjusted net excess is the only magnitude claim, and it is a *requirement*, not a forecast |
| Net walk-forward mean OOS Sharpe | >= 0.9 (promotion gate) | gate fixed by AGENTS.md / `config/promotion_gates.yaml`; the prior probability of clearing it is **LOW** |
| Maximum drawdown (test) | < 25% | the book is market-neutral, so drawdown is bounded by spread divergence, not market direction |
| Annualized turnover | ~52 units/yr proxy (one book rotation per weekly rebalance) -> 1.5600%/yr drag at 3 bp/unit | the committed one-book-rotation-per-rebalance convention; the realized turnover is **measured** in the evaluation, not assumed (Cycle 935 showed the 52 units/yr proxy is a lower bound, not an upper bound) |

**The pre-registered cost hurdle (formula, measured in the evaluation).** The
shortlist published a measured gross scale of **69.6626%/yr** (median
|5-session change| of the pairs' log price ratio x 52 rebalances) and a
52-units/yr proxy turnover. Per the Cycle 935 correction, that proxy is a
*lower* bound, not an upper bound, so no hurdle number is frozen from it.
The pre-registration freezes the measured gross scale **69.6626%/yr** itself
and expresses the hurdle as a formula over **measured** quantities:

    hurdle = (realized turnover x 3.0 bp/unit) + (borrow drag: 25 bp x
             short notional per active pair per rebalance)

both divided by the measured gross scale. The realized turnover, the
realized cost drag and the implied hurdle are **measured and reported** in
the evaluation, and the shortlist's 52 units/yr figure is quoted only as the
proxy it is.

---

## Holding horizon

5 trading sessions (one week). The signal is formed on the close of session
`t` and the positions are effective from session `t+1` (one-session lag).
The portfolio is rebalanced every 5 sessions; positions are held 5 sessions
between rebalances. 52 rebalances per year.

---

## Asset universe

Nine GICS sector ETFs: **XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY**.

This is the only **membership-stable** cross-section in the repository: all
nine files carry an identical cached history (**6,991 sessions,
1998-12-22 .. 2026-10-08, 0 missing closes, 0 duplicate timestamps, 0
non-positive closes**), so the effective cross-section is constant over the
whole sample and there is no survivorship or membership-growth channel. The
panel ends 2026-10-08, eight sessions behind the rest of the committed
cache.

---

## Features and data sources

| Feature | Definition | Source |
|---------|------------|--------|
| Log price ratio | log(Close[a]) - log(Close[b]) per pair, session `t` | `data/raw/{symbol}.parquet`, column `Close` |
| Signal score | z-score of the log price ratio over the trailing 126 sessions, formed at `t` | same panel (rolling mean/std, point-in-time) |
| Pair activity | |z| >= 1 at the formation date -> contrarian side; otherwise flat | same panel |
| Cross-sectional dispersion | not used (market-neutral book; benchmark is cash) | n/a |

Data source: the committed parquet cache only. **The fetcher is never called.**
No external data, no fundamental data, no borrow/locate data, no intraday
data.

---

## Entry / exit rules

1. On every rebalance session `t` (every 5th session of the panel, anchored
   on the panel's first session), for each of the six pre-registered pairs
   (XLP/XLU, XLF/XLK, XLE/XLB, XLI/XLB, XLV/XLY, XLK/XLU), compute the
   z-score of the log price ratio over the trailing 126 sessions formed at
   `t`.
2. If `z >= 1`, the spread is rich: **short the numerator leg** `a` and
   **long the denominator leg** `b` (expect convergence: `a` down, `b` up).
   If `z <= -1`, the spread is cheap: **long `a` and short `b`**. If
   `|z| < 1`, the pair is **flat**.
3. Each active pair is **dollar-neutral**: long 0.5 of the cheap leg, short
   0.5 of the rich leg (gross 1.0 per active pair, net 0). An asset's weight
   is the sum of its weights across the pairs in which it is active.
4. The weights formed at `t` are effective from `t+1` (one-session lag) and
   are held until the next rebalance decision (5 sessions).
5. Exit a pair's legs when it leaves the active set at a rebalance
   (`|z| < 1` or the sign flips); no intra-horizon trading.

---

## Benchmark

**Cash** (a market-neutral book earns the risk-free rate on cash collateral;
the benchmark return is 0 excess over cash). The repository's **2.00% annual
risk-free rate** is the hurdle; the canonical Sharpe convention uses a zero
risk-free rate, consistent with every promotion gate in this repository.
The decision statistic is the **net excess over cash** (cash return = 0, so
the net excess equals the candidate's net-of-cost return).

Secondary references (read-only, not decision statistics): the incumbent
`tsmomentum_spytrend_001`, and the six pre-registered pairs' individual
attribution.

---

## Known confounders

1. **Short-sale constraints and recall risk**: the repository has no borrow
   cost or short-availability data at all; the 25 bp per unit of short
   notional per rebalance is a pre-registered **assumption**, not a
   measurement, and the short leg may be unavailable or costly to borrow.
2. **Pair-selection multiplicity**: six pairs are pre-registered, and the
   spread correlations are high, so the six bets are far from independent;
   the pairs are fixed by the config and not selected by a search.
3. **Structural breaks in the long-run relationship**: a pair that stops
   being cointegrated turns a convergence trade into a value trap; the
   pre-registered cointegration test (condition iii) guards against this.
4. **Funding**: the market-neutral construction must be funded and pays the
   repository's 2% risk-free rate, which the canonical Sharpe convention
   (rf 0) does not net.
5. **Panel lag**: the sector panel ends 2026-10-08, eight sessions behind
   the rest of the committed cache.
6. **Embedded fees**: ETF expense ratios and index-tracking differences are
   embedded in the observed (adjusted) prices and are not modelled
   separately.

---

## Falsification condition (pre-registered)

The hypothesis is **falsified** if ANY of the following hold on the
chronological out-of-sample walk-forward (10-year train, 12-month test,
6-month step, 21-day purge, 21-day embargo, one-session signal lag, 3 bp per
unit of weight change on both legs, plus the pre-registered 25 bp per unit
of short notional per rebalance borrow cost):

1. the **walk-forward mean OOS Sharpe** (net of all costs, canonical
   convention) is **< 0.9**;
2. the **net excess over cash** has a moving-block bootstrap 95% CI
   (seed 20240101, block max(2, n_folds // 8)) that **includes zero** (after
   deflating for the six pairs tested);
3. the **cointegration of any pair fails out of sample**: the Engle-Granger
   test (alpha 0.05) on the log price ratio, computed on each fold's
   **training-window data only**, fails (p >= alpha) for any pair in any
   fold;
4. the **net excess does not survive a borrow cost of 25 bp per unit of
   short notional per rebalance**: the annualized net excess after borrow
   is **<= 0**.

Promotion requires **all** of (1)-(4) pass, and the standard AGENTS.md
multiple-testing controls (Deflated Sharpe Ratio over the declared trial
count of 1, positive-fold rate, pooled trade count, bootstrap CI). Failing
any condition downgrades the candidate to **Rejected/Failed**; no result
obtained after this freeze may change a threshold.

---

## Cost model assumptions

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Slippage | 2.0 bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Round trip | **3.0 bp per unit of weight change** (both legs) | derived |
| Short-side borrow | **25.0 bp per unit of short notional per rebalance** (assumption) | pre-registered in `config/pairs_candidate_001.yaml`; **not** in `config/settings.yaml` or any shared cost model |
| Risk-free rate | 2.00% annual (hurdle; canonical Sharpe uses rf 0) | `config/settings.yaml` via `src.backtest.engine.get_risk_free_rate()` |
| Market impact, bid-ask spread, latency, margin | **absent from the repository's cost model** | disclosed gap |

Costs are charged on the absolute weight change on rebalance days (3 bp per
unit), plus the borrow charge on the short notional at each rebalance. The
realized turnover is **measured** in the evaluation, not assumed.

---

## Evaluation design (pre-registered)

* **Sample**: the nine-sector panel, 1998-12-22 .. 2026-10-08 (6,991
  sessions). No sample selection is performed after the fact.
* **Walk-forward**: 10-year rolling train, 12-month test, 6-month step,
  21-day purge, 21-day embargo -- the repository's committed design.
* **Trials**: **1** (one baseline rule, one configuration, no grid). The six
  pairs are pre-registered components of that one configuration; no pair is
  selected by a test on the full sample. No parameter search and no variant
  is pre-registered here.
* **Reported**: walk-forward mean OOS Sharpe on the canonical scale,
  positive-fold rate, pooled OOS trades, the three promotion gates, the net
  excess over cash with its moving-block bootstrap 95% CI (seed 20240101),
  the net excess **after** the pre-registered 25 bp/unit-of-short-notional
  borrow cost, the per-pair attribution and the per-pair out-of-sample
  cointegration test results, the measured realized turnover and cost drag,
  and the implied cost hurdle.
* **Benchmark**: cash (market-neutral book vs cash; 2% hurdle).
* **Declared trial count**: **1**.

## Reproduction

The evaluation tool reads this file and `config/pairs_candidate_001.yaml` as
the frozen specification and fails closed on any post-freeze drift. The
pre-registration commit hash is published with the result record.

```bash
python -m pytest -q tests/test_pairs_001_evaluation.py
```
