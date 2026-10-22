# Hypothesis: Commodity-Complex Absolute Time-Series Momentum (`commoditytrend_001`)

## Version History

- v001 (`commoditytrend_001`, 2026-10-22): Initial pre-registered hypothesis
  for Cycle 947 (evaluation: the next cycle, after the data gate is
  satisfied). Parent cycle: Cycle 947 evidence-based market-opportunity
  search (`research/experiments/market_opportunity_search_001.md`, tool
  `research/market_opportunity_search_001.py`, OVERALL: PASS). Source of
  every pre-registered value: that search's committed report and the
  committed cache; no new number is fitted to satisfy this freeze. Code
  revision at freeze: current working tree. **Pre-registered BEFORE any
  backtest of this candidate is executed** -- no `commoditytrend_001`
  backtest exists in this repository at the time of this freeze.

**Status at the freeze: Blocked by data/infrastructure.** The pre-registered
data gate (section "Data gate") is **not** satisfied by the committed cache.
This is a *block*, not a rejection: no trading verdict is published for this
candidate, and it is neither promoted, nor simulated, nor paper-traded.

---

## Mechanism Description

A commodity that has risen over the past year tends to keep rising over the
following months, and a commodity that has fallen over the past year tends to
keep falling. The mechanism is a **trend premium that is paid by the
market's own risk-bearing**: in a commodity complex, prices are set by
inventory-constrained producers, hedgers and speculators whose positions
build slowly, so a price that has been trending continues to trend while the
positioning that produced it is unwound. Time-series momentum in commodity
futures is the best-documented member of the trend family, and it is the
only *carry-like* mechanism in this repository that is neither closed nor
blocked on data.

The pre-registered test isolates the first-order effect and adds nothing:
**each instrument's own trailing 252-session return (skipping the most
recent 21 sessions) decides whether that instrument is held; the held
instruments are equal-weighted; the book is flat in cash when none is held.**
There is no ranking against other instruments (this is *absolute*,
not cross-sectional), no volatility target, no drawdown control, no trend
filter on the market, and no regime gate.

This mechanism is **distinct from every closed line in this repository**:

- it is not the incumbent `tsmomentum_spytrend_001` (cross-sectional
  momentum over seven equity ETFs with a SPY trend filter, a volatility
  target and a drawdown cut; the universe here is a commodity complex and
  the construction is absolute rather than relative);
- it is not `csmomentum_001` / `sectorrotation_001` / `sectorrotation_002`
  (cross-sectional momentum over equity ETFs -- rejected);
- it is not `reversal_001` (short-horizon cross-sectional reversal --
  rejected);
- it is not `futuresbasis_001` / `futuresbasis_002` (the futures roll
  yield, which is a *carry* mechanism and is blocked/rejected on the roll
  prices being unobservable);
- it is not `cryptofunding_001` (the crypto funding carry).

**The overlap that is disclosed rather than hidden:** the mechanism family
(time-series momentum) is shared with the incumbent. The *exposure* is new
(the commodity complex is the only market segment in this repository that
has never been traded as a book) and the *construction* is new (absolute,
long-only, cash when out, no overlays). The family overlap is a
multiple-testing risk and is accounted for in the declared trial count
below.

## Expected direction and magnitude (pre-specified prior)

- **Direction (pre-registered):** positive. The held assets are expected to
  earn more than the equal-weighted buy-and-hold benchmark over the sample,
  because the rule is out of the instruments whose trends are negative.
- **Magnitude (pre-registered prior, a DECLARED PRIOR and not a
  measurement):** the gross capture fraction is expected to be of the order
  of 1-3% of the benchmark's annualised dispersion per rebalance, against a
  measured cost hurdle of the order of 0.2% of the same dispersion for a
  monthly rule on this universe. The prior is deliberately modest: the
  *published* feasibility screen of the same rule on the only universe the
  committed cache can evaluate (see "Published prior evidence") has a
  **negative** benchmark-relative excess.
- **What would falsify the prior:** a benchmark-relative net excess whose
  moving-block bootstrap 95% CI includes zero (falsification condition 2
  below), or a walk-forward mean OOS Sharpe below 0.9 (condition 1).

## Holding horizon

- Signal: trailing **252-session** total return, skipping the most recent
  **21** sessions (a 12-1 momentum signal with a one-month skip).
- Rebalance: **monthly**, on the last session of each calendar month, with a
  **one-session** signal lag (the signal is formed at the month-end session
  `t` and the weights are effective from session `t+1`).
- Holding period: the intended holding period of each position is one month
  or longer; the minimum is 21 sessions, which is why the declared (and
  unmeasurable) spread component is not expected to be decisive.

## Asset universe

| Instrument | Exposure | Cached history at the freeze |
|---|---|---|
| `DBC` | broad commodity complex | 2006-02-06 .. 2026-10-08, 5,201 sessions |
| `BNO` | crude oil | 2015-01-02 .. 2026-10-15, 2,964 sessions |
| `UNG` | natural gas | 2015-01-02 .. 2026-10-15, 2,964 sessions |
| `GLD` | gold | 2004-11-18 .. 2026-10-19, 5,513 sessions |

- The **common inception** of the four is **2015-01-02** and the common end
  is **2026-10-15**; 0 NaN closes, 0 duplicate timestamps and 0 non-positive
  closes in all four files.
- `GSG` and `USO` are **excluded** as near-duplicates of `DBC` and `BNO`
  (two overlapping exposures of the same complex would not diversify the
  book, and the search's declared rule for a candidate universe is
  "non-redundant exposures").
- The front-month futures series (`CL-F`, `GC-F`, `NG-F`) are **excluded**
  because their roll prices are unobservable (`futuresbasis_001`, **Blocked by
  data/infrastructure**), which contaminates every signal computed on them
  at every roll (`leadlag_001`).
- **Declared prior (not measurable from the cache):** `DBC`'s index holds a
  gold sleeve, so the book's gold exposure is not independent of `GLD`. The
  overlap is disclosed, not corrected, and the evaluation must publish the
  per-instrument attribution beside the portfolio result.

## Features and data sources

- **Only** the committed parquet cache under `data/raw/`: the `Close` column
  of `DBC`, `BNO`, `UNG` and `GLD`. No network call, no fetcher invocation,
  no alternative source, no fundamental or macro series.
- Derived features: `signal(t) = Close[t-21] / Close[t-252] - 1`, evaluated
  at the month-end session `t` only. No value of `t+1` or later enters the
  signal.
- The month-end session is the last session of the calendar month in the
  instrument's own session calendar, i.e. the repository's shared
  month-end rebalance schedule (`src/backtest/rebalance.py`).

## Entry / exit rules

- At each month-end session `t`, an instrument is **held** if and only if
  its signal is strictly positive.
- The held instruments are **equal-weighted** at `1/N_held` each; the
  remaining weight is cash.
- If no instrument has a positive signal the book is **100% cash**. The
  book is **never short**: there is no short leg, no borrow and no margin.
- The weights formed at `t` become effective at `t+1` and are held until
  the next month-end signal.
- No position exists before the first valid signal (252 + 21 sessions of
  warm-up), and positions are never back-filled.
- **One rule, one universe, no grid, no parameter sweep, no variant.** The
  declared trial count is 3 (section "Multiple testing").

## Benchmark

- **1/N buy-and-hold of the same four instruments** over the same sessions,
  charged the same cost model (its entry cost is 1.0 unit of weight change
  at 3.0 bp/unit).
- The benchmark is the right one for this rule because the rule's whole
  claim is that *timing* a commodity complex beats *holding* it. A cash
  benchmark would flatter a long-only rule that is never short, and the
  equal-weighted buy-and-hold of the same universe removes the composition
  effect.
- The benchmark holds the same instruments, so it absorbs the **average**
  embedded roll term; it does **not** absorb its time variation, which is
  a disclosed confound.

## Known confounders

1. **The embedded roll yield of the commodity ETFs** (not observable from
   the cache). Each instrument is a rolling futures-index fund whose
   realised return contains a time-varying roll term. It is not corrected
   for. A trend rule that is systematically in cash during contango would
   show a roll-driven excess that is not a trend premium.
2. **The embedded fund expense ratios** (not in the cache; declared as a
   0.40-0.85 %/yr band). The net figures are reported on the primary
   3.0 bp/unit model and on the band, and the verdict is reported on both.
3. **Family overlap with the incumbent.** The mechanism family
   (time-series momentum) is the incumbent's; the exposure and the
   construction are not. The declared trial count accounts for it.
4. **The published prior is negative.** The same rule on the only universe
   the committed cache can evaluate has a **-0.5304 %/yr** benchmark-relative
   net excess and a net Sharpe of 0.4041 against the benchmark's 0.4580;
   neither of its single-asset decompositions has an excess either
   (`DBC` -0.4626 %/yr, `GLD` -1.9110 %/yr). This is published in full and
   it is the reason the candidate's prior is weak.
5. **The diversification cannot be supplied by the committed cache.** Time-
   series momentum needs a diversified cross-section; the cache offers only
   two long-history commodity ETFs, whose exposures overlap. The data gate
   exists to obtain that cross-section, and the evaluation must publish the
   two-asset screen's numbers beside its own.
6. **Momentum crashes.** Trend strategies have documented crash regimes
   (a sharp reversal in the crowded trend). The post-2010 sub-period
   condition (falsification condition 5) exists to detect a crash-driven
   result.
7. **The commodity complex is not equity-market-like.** The instruments are
   roll-based, their volume is reported with roll spikes, and their price
   series contain the roll gaps, so a volatility estimate computed on them
   is contaminated at every roll.
8. **The four instruments are not independent** (see the declared prior in
   "Asset universe" and confounders 1 and 5).
9. **The sample regime.** The panel's history is dominated by the 2011-2016
   energy collapse and the 2020-2022 commodity bull; a commodity rule
   evaluated over it is evaluated over very few independent commodity
   regimes.

## Data gate (pre-registered, measured at the freeze, currently FAILED)

- The frozen walk-forward design (10y train / 12m test / 6m step, 21-day
  purge and embargo) needs `2520 + 252 + (folds-1)*126` business days for
  `folds` folds. **Ten folds** -- the minimum at which the positive-fold
  gate resolves below 0.1, the walk-forward mean has a standard error of
  the order of 0.2, and the >100 pooled-trade gate is reachable
  (10 folds x 12 months x 4 assets) -- needs **3,906 business days**, i.e.
  a common inception **on or before 2011-10-20**.
- **Measured at the freeze:** the cached common inception is 2015-01-02,
  which supports **three** folds. The gate therefore **FAILS** by a factor
  of 3.3 and the candidate's status is **Blocked by data/infrastructure**.
- **The evidence that the gate is satisfiable** (and it is a declared
  prior, not a measurement): four of the six cached commodity ETFs and all
  four cached futures series share the *identical* first session
  **2015-01-02**. Eight independent instruments do not incept on the same
  day, so that common start is a **fetch window**, not instrument history.
  The upstream history of the four commodity ETFs is declared to reach back
  to 2010-2011, which would put the common inception before 2011-10-20 and
  give 10-14 folds. **The next cycle must measure this** (a fetch into a
  scratch directory; the committed cache is not to be rewritten in the same
  step) before any evaluation is run.
- If the gate cannot be satisfied, the candidate is **blocked**, the
  condition fires, and **no trading verdict is published**.

## Falsification condition (pre-registered)

The candidate is **falsified** if **any** of the following fires; the
**data gate** is a block and not a rejection:

1. `wf_mean_oos_sharpe` -- the walk-forward mean out-of-sample Sharpe is
   below **0.9**.
2. `benchmark_relative_excess_ci` -- the benchmark-relative **net** excess
   has a moving-block bootstrap 95% CI that **includes zero** (block 4,
   2,000 draws, seed 20240101).
3. `gross_capture_below_cost_hurdle` -- the measured gross capture fraction
   (median over the out-of-sample rebalances) is below the measured cost
   hurdle (3.0 bp per unit of weight change over the measured dispersion).
4. `fold_or_trade_gate` -- the positive-fold rate is below 0.5 **or** the
   pooled out-of-sample trades are at most 100.
5. `no_post_2010_excess` -- there is no positive benchmark-relative excess
   in the post-2010 sub-period.
6. `expense_ratio_band` -- the verdict holds only after the declared
   embedded-expense-ratio band (0.40-0.85 %/yr) is deducted. A pass that
   survives only the primary cost model is reported as a **conditional
   pass**, not a pass.
7. `data_gate` -- the cached common-inception panel supports fewer than ten
   folds of the frozen design. **This blocks the candidate** (reported as
   "Blocked by data/infrastructure"); it is not a rejection and it publishes
   no trading verdict.

A falsified candidate is labelled **Rejected/Failed**, is not promoted, not
simulated and not paper-traded, and its configuration is retired as
written (no variant is opened). A candidate that clears every condition
above is labelled **Exploratory signal**; promotion is a separate decision
that this hypothesis does not make.

## Cost model assumptions

- **Primary (the repository's committed model, read from
  `src/backtest/engine.py`):** 1.0 bp commission + 2.0 bp slippage =
  **3.0 bp per unit of weight change**, at a **2.00%** annual risk-free
  rate. The cost is charged on the realised absolute weight change, exactly
  as `src/backtest/engine.py` does it.
- **Declared BLOCKED (not in the model, not measurable from the cache):**
  - **quoted bid-ask spread** -- the cache carries no quoted spread. The
    rule's minimum holding period is 21 sessions, so the spread is not
    expected to be decisive, but this cannot be verified from the cache.
  - **market impact** -- not modelled and not measurable from the cache.
  - **latency** -- not modelled; the signal is a month-end close-to-close
    quantity, so the latency exposure is one session.
  - **embedded roll yield** -- the commodity ETFs are rolling futures-index
    funds; the roll term is not observable from the cache and is not
    corrected for.
  - **embedded fund expense ratios** -- not in the cache; declared as a
    0.40-0.85 %/yr band and reported beside the primary net figure.
- **Not applicable:** borrow (long-only, no short leg) and margin (no
  leverage, no futures).
- **Turnover expectation:** a monthly rule that replaces its whole book
  every rebalance pays at most 24 units of weight change per year, i.e. at
  most **0.72 %/yr** at 3.0 bp/unit; the realised turnover of the rule on
  the committed panel must be published.

## Multiple testing

- The headline configuration is **one** rule: no grid, no parameter sweep,
  no variant.
- The Deflated Sharpe Ratio of the evaluation must nevertheless use a
  **declared trial count of 3**, because the pre-registration's own prior
  evidence contains three published rule measurements (the two-asset rule
  and its two single-asset decompositions). Bootstrap seed **20240101**,
  2,000 draws, block 4.

## Evaluation design (pre-registered)

- Walk-forward: **10y train / 12m test / 6m step, 21-day purge, 21-day
  embargo**, on the repository's own `src/evaluation/walkforward.py`
  (identical to the incumbent's `WF_*` constants).
- Parameters are **fixed across folds**; nothing is re-optimised per fold.
- Gates: walk-forward mean OOS Sharpe >= 0.9, positive-fold rate >= 0.5,
  pooled OOS trades > 100, plus the benchmark-relative excess CI, the gross
  capture hurdle, the post-2010 sub-period and the expense-ratio band.
- The evaluation must publish, beside its own numbers: the realised
  turnover and cost drag, the per-instrument attribution, the two-asset
  screen's numbers, the expense-ratio-adjusted figures, and the data gate's
  measurement.
- The evaluation must **not** change the rule, the universe, the benchmark,
  the cost model, the gates or the Sharpe convention after the result is
  known.

## Published prior evidence (measured before this freeze)

A pre-declared, in-sample, full-sample **feasibility screen** of the same
rule was run on the only universe the committed cache can evaluate with
enough folds: `{DBC, GLD}` over 2006-02-06 .. 2026-10-08 (21 folds). It is
a feasibility screen and **not** an evaluation: it produces no fold
statistics and no gate table, and it is published in full in
`research/reports/market_opportunity_search_001.md` (section 4).

| Quantity | Value |
|---|---|
| Net benchmark-relative excess | **-0.5304 %/yr** (gross -0.4620 %/yr) |
| Rule net Sharpe | 0.4041 (gross 0.4083) |
| Benchmark net Sharpe (1/N buy-and-hold) | 0.4580 |
| Realised cost drag | 0.0683 %/yr (2.2773 units/yr) |
| Sessions with a weight change | 45 in 5,201 sessions |
| Single-asset excess, `DBC` | -0.4626 %/yr (net Sharpe 0.2069) |
| Single-asset excess, `GLD` | -1.9110 %/yr (net Sharpe 0.5887) |

**The screen's result is negative and it is published as such.** The
candidate is pre-registered with a **weak prior** and a **data gate**, so
that the next cycle's work is bounded and unbiased. It is not a strong
claim, and it is not a promotion.

## Reproduction

```bash
python research/market_opportunity_search_001.py
python -m pytest -q tests/test_market_opportunity_search_001.py
git status --porcelain data/ config/
```

The frozen configuration is `config/commoditytrend_001.yaml`. The evaluation
must publish the hash of that file with its result.
