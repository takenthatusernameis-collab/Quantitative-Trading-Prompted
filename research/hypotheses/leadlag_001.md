# Hypothesis: Futures-to-ETF Delayed Price Discovery (leadlag_001)

## Version History

- v001 (leadlag_001, 2026-10-21): Initial pre-registered hypothesis for
  Cycle 939 (evaluation Cycle 939). Parent cycle: Cycle 934 evidence-based
  candidate shortlist (`leadlag_001`, **16/35**, rank 4 of 4; behind
  `reversal_001` 28/35 rank 1, `pairs_001` 25/35 rank 2 and
  `liquidity_001` 24/35 rank 3). Source of every pre-registered value:
  `research/experiments/candidate_shortlist_934.md` (tool
  `research/candidate_shortlist_934.py`, OVERALL: PASS). Code revision at
  freeze: 429e7f5. **Pre-registered BEFORE any leadlag_001 backtest
  execution.** No leadlag_001 backtest exists in this repository at the time
  of this freeze.

---

## Mechanism Description

The futures market is deeper and is quoted with a settlement convention that
differs from the ETF's closing auction; information that reaches the futures
close is only partly incorporated into the ETF close, so part of the futures
move is realised in the ETF on the next session.

The pre-registered test isolates the first-order effect in its **weakest,
testable form**: for each of five pre-registered futures-to-ETF pairs, take
the **sign** of the futures contract's trailing 5-session return as the
signal for the ETF leg; long the ETF leg when the signal is positive and
hold **cash** otherwise; rebalance every 5th session; the signal formed at
`t` is effective at `t+1` (one-session lag). The five pairs are the five
components of **one** configuration; no pair, horizon, lookback or weight was
searched.

This mechanism family is **distinct from every closed line in this
repository**:

* the momentum family (incumbent `tsmomentum_spytrend_001`, `csmomentum_001`,
  `sectorrotation_001` / `sectorrotation_002`) uses time-series or
  cross-sectional momentum; this candidate uses a **cross-instrument lead**,
  not the sign of the traded asset's own return;
* `reversal_001` (Rejected/Failed, Cycle 935) is short-horizon reversal on
  the nine-sector ETF panel; this candidate trades futures/ETF pairs on a
  2015-2026 panel;
* `pairs_001` (Rejected/Failed, Cycle 936) is market-neutral pairs trading on
  the same nine-sector panel; this candidate is long-only and directional;
* `liquidity_001` (Rejected/Failed, Cycle 938) is an illiquidity tilt on the
  same nine-sector panel;
* `futuresbasis_001` (Blocked by data) and `futuresbasis_002`
  (Rejected/Failed) traded the **roll/carry** of the same futures complex;
  this candidate trades the **next-session lead** of the futures close into
  the ETF leg, which is a different mechanism and a different construction;
* `riskparity_001` (Rejected), `calendar_effects_001` (Rejected/Failed),
  `overnight_capture_001` (Rejected/Failed), `macroregime_001`
  (Rejected/Failed), `mom121_microcap_001` (Blocked by data),
  `cryptofunding_001` (Exploratory signal, not promoted) are not touched by
  this candidate.

The shortlist's published weakness is carried into the evaluation plan
unchanged: the futures/ETF panel is only 11.8 years long, the two calendars
differ, `CL-F` carries a non-positive close inside the sample and the roll
prices are unobservable. The candidate scored **1/5** on data quality for
exactly those reasons, and this evaluation is expected to test whether the
mechanism can be measured at all on the committed cache.

---

## Expected direction and magnitude (Pre-Specified Prior)

The prior is conservative and consistent with the Cycle 934 shortlist score
(c) Expected net return after costs = **2/5** (the *minimum* of the measured
cost hurdle **4/5** and a declared gross prior of **2/5**). **No gross
magnitude has been measured in this repository**, so no return is asserted.

| Metric | Prior (this hypothesis) | Note |
|--------|--------------------------|------|
| Gross direction | positive relative to **cash** (the rule is long-only) | the futures close leads the ETF close |
| Gross magnitude | **not measured**; the pre-registered requirement is quantitative and below | the cost hurdle is the only magnitude claim, and it is a *requirement*, not a forecast |
| Net walk-forward mean OOS Sharpe | >= 0.9 (promotion gate) | gate fixed by AGENTS.md / `config/promotion_gates.yaml`; the prior probability of clearing it is **LOW** |
| Maximum drawdown (test) | < 25% | the book is long a single commodity/rate factor at a time |
| Annualized turnover | ~52 units/yr (one book rotation per weekly rebalance) -> 1.5600%/yr drag at 3 bp/unit | the **realized** turnover is measured by the evaluation |

**The pre-registered cost hurdle (measured in Cycle 934).** The shortlist
published a measured gross scale of **30.1518%/yr** (the median annualised
volatility of the traded ETF legs) and a cost hurdle of **5.1738%** of that
gross scale. The annual cost drag at the Cycle-934 turnover convention is
**1.5600%/yr**. The rule must therefore capture at least **5.1738%** of the
measured gross scale to break even. The **realized** turnover and drag are
**measured** by the evaluation, not assumed; the 52 units/yr figure is the
committed one-book-rotation-per-rebalance convention and is quoted as a
**proxy**.

---

## Holding horizon

5 trading sessions (one week). The signal is formed on the close of session
`t` and the positions are effective from session `t+1` (one-session lag).
The portfolio is rebalanced every 5th session of the panel (52 rebalances per
year).

---

## Asset universe

Ten instruments in two roles:

* **Futures legs (signal only, never traded)**: **CL-F** (WTI crude oil front
  month), **GC-F** (COMEX gold front month), **NG-F** (Henry Hub natural gas
  front month), **ZB-F** (US Treasury bond front month).
* **ETF legs (the traded book)**: **USO** (WTI crude oil), **BNO** (Brent
  crude oil), **UNG** (natural gas), **GSG** (broad commodity), **GLD**
  (gold), **TLT** (20+ year US Treasury).
* **The five pre-registered pairs**: `CL-F/USO`, `CL-F/BNO`, `GC-F/GLD`,
  `NG-F/UNG`, `ZB-F/TLT`. `GSG` is in the universe (Cycle 934) and in no
  pair; it is kept in the panel definition so that the sample is exactly the
  Cycle-934 complete panel.

The panel is the **complete cross-section** of the ten instruments: the
sessions on which *every* instrument carries a price. Measured at freeze from
the committed cache: the union calendar of the ten instruments holds **6,098**
sessions (TLT from 2002-07-30) and the complete cross-section holds
**2,960** sessions, **2015-01-02 .. 2026-10-15**; the two calendars therefore
differ and **51.46%** of the union calendar is not covered by the panel. The
panel gives **592** non-overlapping 5-session holding-horizon observations and
**2.96** effective independent bets (correlation eigenvalues of the traded
legs' 5-session returns).

---

## Features and data sources

| Feature | Definition | Source |
|---------|------------|--------|
| Lead-lag signal | sign of the futures leg's trailing 5-session total return (`Close[t]/Close[t-5]-1` on the futures' own cached calendar) | `data/raw/{CL-F,GC-F,NG-F,ZB-F}.parquet`, column `Close` |
| Traded leg return | the ETF leg's session-to-session total return on the panel calendar | `data/raw/{USO,BNO,UNG,GSG,GLD,TLT}.parquet`, column `Close` |
| Roll detection | the committed volume-signature detector (`research/futures_roll_visibility.py`) applied to the futures legs' `Volume` column | `data/raw/{CL-F,GC-F,NG-F,ZB-F}.parquet`, column `Volume` |
| Data-integrity screen | non-positive closes in the required series | same files |

Data source: the committed parquet cache only. **The fetcher is never called.**
No external data, no fundamental data, no intraday data, no roll prices.

**The signal is point-in-time.** The trailing 5-session return at session `t`
uses closes up to and including `t` only, and the weights formed at `t`
become effective at `t+1`.

---

## Entry / exit rules

1. On every rebalance session `t` (every 5th session of the panel, anchored
   on the panel's first session), compute for each of the five pairs the
   signal = sign of that pair's futures leg's trailing 5-session return.
2. If the signal is positive, the pair holds **its ETF leg at 1/5 of the
   book (0.2)**; if the signal is zero or negative, the pair holds **cash**
   (0.0). The five pairs are equally weighted, so the book's gross exposure
   never exceeds **1.0** and there is no leverage, no short leg and no
   borrow.
3. The weights formed at `t` are effective from `t+1` (one-session lag) and
   are held until the next rebalance.
4. Exit an ETF leg when its signal is zero or negative at a rebalance; no
   intra-horizon trading.
5. **Unusable signal (data quality, not a trading rule).** A futures signal
   at session `t` is **unusable** when the trailing 5-session futures window
   `[t-5, t]` contains (a) a **detected roll date** -- the first session of
   the new front month, where the spliced front-month price jumps and the
   roll price is unobservable -- or (b) a **non-positive close**. An unusable
   signal leaves the pair in **cash** from the next session on. This is a
   data-cleaning rule, not a lookahead: the pair simply does not trade on a
   signal the cache cannot supply, and the ex-post nature of the roll
   detection is disclosed below.

---

## Benchmark

**Cash** (the rule is a directional tilt on the ETF leg only). The
repository's 2.00% annual risk-free rate is the cash hurdle and is reported
alongside the net excess over a zero-return cash benchmark.

---

## Known confounders

1. **Unobservable roll price.** The cached front-month futures series is a
   continuous spliced series whose roll price is unobservable: the return
   series is contaminated at every roll event, so the roll-affected signal
   sessions are excluded. The roll **dates** are detectable (Cycle 884) from
   the volume signature; the roll **prices** are not observable in any source
   in scope.
2. **The roll detection is ex-post.** The committed detector classifies a
   session using up to eight forward sessions and four subsequent volume
   ratios, so the roll dates can be used to clean a backtest but are **not** a
   tradable point-in-time signal; a live rule would have to detect the roll
   with the same lag. The cleaned result is therefore an upper bound on what
   a live implementation could achieve.
3. **CL-F carries a non-positive close inside the sample.** The front month
   went negative in 2020: `CL-F` closes at **-37.63** on **2020-04-20**, one
   integrity defect row in a required series. Any return computation that
   spans it is broken, so the affected signal sessions are excluded.
4. **Different trading calendars.** The futures and the ETF legs have
   different calendars, so the paired panel is complete only on the sessions
   both markets opened: 2,960 of the 6,098 union-calendar sessions.
5. **The daily bar cannot establish the intraday ordering.** The mechanism
   depends on the futures settlement preceding the ETF close, and a daily bar
   cannot show that; only the weaker next-session form is testable.
6. **The five pairs are not independent bets.** The four futures are four
   different factor exposures (oil, gas, gold, rates) and two of the five
   pairs share the same futures leg, so the measured effective-bet count is
   **2.96**, not five. The Deflated Sharpe Ratio is therefore computed over a
   declared trial count of **5**.
7. **Statistical power.** With 11.8 years of data and the committed
   10-year train window, the walk-forward produces only **3** out-of-sample
   folds whose test windows overlap; the pooled out-of-sample span is about
   two years. This is a real limitation of the design on this panel and it is
   disclosed here rather than worked around by changing the design.
8. **Short-horizon arbitrage.** A one-session lead of a futures close into an
   ETF close is a well-known, heavily arbitraged effect at the daily horizon
   the cache can measure; the declared gross prior is 2/5 for that reason.
9. **Embedded fees and tracking.** The ETF legs' expense ratios and
   index-tracking differences are embedded in the observed (adjusted) prices
   and are not modelled separately.

---

## Falsification condition (pre-registered)

The hypothesis is **falsified** if ANY of the following hold on the
chronological out-of-sample walk-forward (10-year train, 12-month test,
6-month step, 21-day purge, 21-day embargo, one-session signal lag, 3 bp per
unit of weight change, cash benchmark, five pre-registered pairs):

1. the walk-forward mean OOS Sharpe (net, canonical convention) is **< 0.9**;
2. the **net excess over cash** has a moving-block bootstrap 95% CI that
   **includes zero**, or the Deflated Sharpe Ratio over the declared trial
   count of **5** is **<= 0** (the CI must exclude zero *after* the
   deflation for the five pairs tested);
3. the excess **disappears once the detected roll windows are excluded** --
   i.e. the net excess over cash is positive on the panel *with* the
   roll-affected signal sessions and is **<= 0** on the cleaned panel
   (the pre-registered primary panel), which would show the effect is a roll
   artefact;
4. the excess is **carried by the CL-F window** -- i.e. the net excess over
   cash of the book is positive but the net excess of the book **without the
   two CL-F pairs** (`CL-F/USO`, `CL-F/BNO`) is **<= 0**, which would make the
   sample unusable because of the non-positive close.

Promotion requires **all** of (1)-(4) to pass **and** the standard AGENTS.md
multiple-testing controls (positive-fold rate >= 0.5, pooled out-of-sample
trades > 100, DSR > 0). Failing any condition downgrades the candidate to
**Rejected/Failed**; no result obtained after this freeze may change a
threshold, a gate, the universe, the cost model or the Sharpe convention.

---

## Cost model assumptions

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Slippage | 2.0 bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Round trip | **3.0 bp per unit of weight change** | derived |
| Risk-free rate | 2.00% annual | `config/settings.yaml` via `src.backtest.engine.get_risk_free_rate()` |
| Borrow / short-side cost | **none** (the rule is long-only: no short leg) | n/a |
| Roll price / roll cost | **absent from the repository's cost model** | disclosed gap: the cached front-month series exposes the roll date but not the roll price |
| Market impact, bid-ask spread, latency, margin | **absent from the repository's cost model** | disclosed gap |

Costs are charged on the absolute weight change, exactly as
`src/backtest/engine.py` does for every committed artifact. The realized
turnover is **measured** in the evaluation, not assumed.

---

## Evaluation design (pre-registered)

* **Sample**: the complete cross-section of the ten instruments, 2,960
  sessions, 2015-01-02 .. 2026-10-15. No sample selection is performed after
  the fact; the panel is the Cycle-934 panel.
* **Walk-forward**: 10-year rolling train, 12-month test, 6-month step,
  21-day purge, 21-day embargo (the repository's committed design, from
  `src/evaluation/walkforward.py`). The rule has **no fitted parameter**, so
  the train window changes nothing; the design is the out-of-sample
  protocol, and on this panel it yields 3 overlapping test folds.
* **Trials**: **5** (the five pre-registered pairs, deflated through the
  Deflated Sharpe Ratio). No parameter search and no variant is
  pre-registered here.
* **Reported**: walk-forward mean/median/std OOS Sharpe, positive-fold rate,
  pooled out-of-sample trades, the net excess over cash with its
  moving-block bootstrap 95% CI (seed 20240101, 2,000 draws, 22-session
  blocks), the Deflated Sharpe Ratio over the declared trial count of 5, the
  realized turnover and cost drag against the 1.5600%/yr proxy, the
  per-pair attribution, the roll-window exclusion result, the CL-F
  non-positive close detection, and the four falsification conditions with
  their observed values.
* **Benchmark**: cash (net excess = net return).

## Reproduction

```bash
python research/leadlag_001_evaluation.py
python -m pytest -q tests/test_leadlag_001_evaluation.py
```
