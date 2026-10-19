# Hypothesis: Overnight-Session Capture Candidate (`overnight_capture_001`)

## Version History

- v001 (`overnight_capture_001`, 2026-10-19): initial pre-registered hypothesis for
  Cycle 880. Parent: Cycle 879 (`research/reports/gate_false_negative_rate_001.md`)
  and Cycle 878 (`research/reports/long_sample_overlay_attribution_001.md`).
  Code revision at registration: `639188b`. **Pre-registered BEFORE any backtest
  was executed.**
- v002 (erratum, 2026-10-19, post-execution, disclosure only): the annual cost-drag
  figure stated in v001 (1.51%/yr) was an arithmetic error; the correct figure is
  15.12%/yr (504 units x 3 bp). No threshold, gate, falsification condition or
  configuration was changed. See the "Erratum" section at the end of this file.

---

## Mechanism Description

The repository's own inventory contains exactly one market-session family that
has never been tested as a candidate: the **overnight-session** effect.
Overnight returns (`Open_t / Close_{t-1} - 1`) are systematically larger and
less volatile than intraday returns across the broad US equity ETF universe,
while the intraday leg is near-zero on average (see
`research/experiments/overnight_drift_exploratory_001.md`):

| Asset (full history) | Overnight ann. mean | Overnight Sharpe | Intraday Sharpe |
|---|---|---|---|
| SPY | 8.37% | 0.790 | 0.122 |
| QQQ | 13.40% | 0.939 | -0.004 |
| IWM | 12.14% | 0.916 | -0.123 |

The mechanism is documented and distinct from every candidate in the repository
(retail open-of-session buying, institutional flow timing, delayed price
discovery after the closing auction). Every candidate evaluated so far is a
close-to-close momentum or rotation signal; this candidate's signal is
**deterministic session timing**, not a price-derived signal.

The candidate holds a 1/3 equal-weight basket of SPY/QQQ/IWM from the previous
close to the next open and is flat during the day. The position is established
at the *previous* close and liquidated at the open, so the standing rule
requires no price-based decision and cannot look ahead: the exposure mask is
the trading calendar itself, exactly as in `calendar_effects_001`.

This is a **different family** from `calendar_effects_001` (turn-of-month
windows): that candidate is exposed ~19% of trading days clustered around month
boundaries; this candidate is exposed on **every** trading day, capturing the
full overnight leg, and is flat only during the intraday leg. The turn-of-month
candidate was tested and rejected (WF mean OOS Sharpe -0.0254), so the
calendar/session-timing space is not exhausted, but this cycle tests a
structurally different mechanism.

---

## Expected Direction and Magnitude (pre-specified prior)

| Metric | Prior (this hypothesis) | Note |
|--------|--------------------------|------|
| Gross annualized overnight return of the 1/3 basket | **+8% to +13%** | Prior from `overnight_drift_exploratory_001.md`; **not** a result |
| Net annualized return after ~1.51%/yr cost (3 bp/unit) | **+5% to +10%** | Prior; 504 units of annual turnover (2x gross exposure per session) |
| Net out-of-sample Sharpe (walk-forward) | >= 0.9 (promotion gate) | Gate fixed by AGENTS.md; prior probability of clearing it is MODERATE |
| Maximum drawdown | < 20% | Overnight-only exposure carries overnight gap risk |
| Annualized turnover | ~504x | 2x gross exposure per session (sell at the open, buy back at the close) |

Direction: positive. The overnight leg is expected to dominate the close-to-close
benchmark after costs, otherwise the effect is equity beta, not an edge.

Falsification: if the net walk-forward mean OOS Sharpe < 0.9 OR < 50% of the
walk-forward folds have a positive test Sharpe, the hypothesis is **rejected**
(downgraded to Rejected/Failed). This condition is pre-stated BEFORE any
backtest execution.

---

## Holding Horizon

Exposure is held on **every** trading day during the overnight leg only (the
period from the previous close to the next open). The position is established at
the prior trading day's close and liquidated at the open; no intra-day trading.
The overnight return of session *t* is `Open_t / Close_{t-1} - 1`. The standing
rule requires no price-based decision.

---

## Asset Universe

The three most liquid US equity ETFs (the same choice as
`research/hypotheses/calendar_effects_001.md`):

1. SPY - SPDR S&P 500 ETF
2. QQQ - Invesco QQQ (Nasdaq-100)
3. IWM - iShares Russell 2000

**No in-sample asset selection; no other symbol may enter the candidate.**
Common sample from IWM's inception (2000-05-26) to 2026-10-16.

---

## Data Integrity (pre-registered expectation, verified before execution)

The fetcher calls yfinance with `auto_adjust=False`
(`src/data/yfinance_fetcher.py`), so the cache is expected to store **raw**
(unadjusted) OHLC. This was checked, not assumed, before execution:

| Symbol | Rows | Start | End | NaN Open | NaN Close | Dup dates | OHLC violations |
|--------|------|-------|-----|----------|-----------|-----------|-----------------|
| SPY | 8,487 | 1993-01-29 | 2026-10-16 | 0 | 0 | 0 | 0 |
| QQQ | 6,945 | 1999-03-10 | 2026-10-16 | 0 | 0 | 0 | 0 |
| IWM | 6,637 | 2000-05-26 | 2026-10-16 | 0 | 0 | 0 | 0 |

- **Raw vs. adjusted confirmation**: an independent fresh download
  (`auto_adjust=False` vs `auto_adjust=True`) over 2024-01-01..2024-02-01 shows
  the cached `Close` matches the **raw** series (max abs diff 0.000000 over all
  21 sessions for SPY/QQQ/IWM) and differs from the adjusted series (SPY cached
  472.65 vs adjusted 457.67). The cache is raw. The exploratory diagnostic's
  caveat #5, which asserts the opposite, is therefore wrong for the committed
  cache and is corrected here.
- **Ex-dividend implication for an overnight holder (conservative)**: the
  overnight leg does **not** receive dividends. On an unadjusted price series
  the overnight return on an ex-dividend date is biased *downward* (the open
  drops by roughly the dividend while the prior close does not). Using raw
  prices therefore **conservatively understates** the overnight edge. The
  candidate is evaluated on raw prices as cached; no dividend adjustment is
  applied and none is claimed.
- **Open/Close alignment**: every cached row has a valid Open and Close; 0
  sessions with a missing Open across the universe.
- **Common trading calendar**: 6,637 sessions, 2000-05-26 -> 2026-10-16
  (bounded by IWM inception).

---

## Features and Data Sources

| Feature | Specification | Source |
|---------|---------------|--------|
| Prices | Daily OHLCV | `data/raw/{SPY,QQQ,IWM}.parquet` (Yahoo Finance via yfinance, `auto_adjust=False`, cached) |
| Signal | Deterministic session timing: hold overnight, flat intraday | Computed from the trading calendar; no price signal |
| Weights | Equal-weight 1/3 per asset during the overnight leg; 0 during the day | `research/overnight_capture_backtest.py` |
| Point-in-time | The overnight return of session *t* uses `Open_t` and `Close_{t-1}`; the position is established at the *previous* close, so the rule uses only information available before the open of session *t* | Engine convention: `port_ret[t] = weights[t] * ret[t]` |

### Execution convention (pre-specified)

The overnight leg return of session *t* is `Open_t / Close_{t-1} - 1`. The
position is established at the previous close and liquidated at the open, so the
standing rule requires no price-based decision and cannot look ahead. This is
the same exogenous-calendar rationale as `calendar_effects_001` (no 1-day
shift), but applied to a **daily** rather than a monthly window.

Turnover per session is exactly **2x gross exposure** (sell the basket at the
open, buy it back at the close), so annualized turnover is 504 units and the
cost drag at 3 bp/unit is ~1.51%/yr. This is pre-registered; the
cost-sensitivity row (5 bp and 10 bp per unit) is evaluated but is **not** a
selection grid.

---

## Entry/Exit Rules

1. **Overnight mask (deterministic)**: every trading day is an overnight
   exposure day. The strategy is long 1/3 SPY, 1/3 QQQ, 1/3 IWM from the
   previous close to the next open, and flat during the day.
2. **Execution**: positions change every session - sell at the open, buy back at
   the close. No intra-session trading.
3. **Long-only, no leverage**: gross exposure is always exactly 1.0 during the
   overnight leg and 0.0 during the intraday leg.
4. **Costs applied**: 3 bps per unit of weight change on every session (the
   repository's model: 1 bp commission + 2 bp slippage, `config/settings.yaml`).
5. **Cash return**: 0% during the intraday leg (engine convention).

---

## Benchmark

Two benchmarks, evaluated on the identical date ranges, cost model and
walk-forward folds:

1. **Close-to-close 1/N equal-weight basket** (buy-and-hold the identical
   1/3 SPY/QQQ/IWM basket, close-to-close). This isolates the value of session
   timing vs. passive holding of the identical basket. The overnight leg must
   beat this benchmark **after costs**, otherwise the effect is equity beta, not
   an edge.
2. **Intraday-only leg** (hold the basket from open to close every session).
   Reported as context: the overnight edge is credible only if it exceeds the
   close-to-close benchmark; the intraday leg is the complementary leg of the
   same exact decomposition
   (`Open_t/Close_{t-1} * Close_t/Open_t = Close_t/Close_{t-1}`).

Both benchmarks are evaluated on the **identical walk-forward folds**.

---

## Known Confounders

1. **Equity beta**: the overnight leg of a broad equity basket is dominated by
   the equity risk premium. The falsification condition (net WF Sharpe must
   exceed the same-fold close-to-close benchmark) is the primary guard against
   labeling beta as an edge.
2. **Overnight gap risk**: a basket held overnight is exposed to overnight
   shocks (geopolitical, macro data released outside US hours, ETF after-hours
   flow). Max drawdown is expected to be larger than a close-to-close strategy's.
3. **Flat cost model**: no bid-ask spread model, no market-impact model, no
   latency model. The pre-registered 5 bp and 10 bp rows probe sensitivity to a
   wider spread assumption ("the hidden cost of buying at the open"), but are
   not a selection grid.
4. **Raw-price dividend bias (conservative)**: the overnight leg does not
   receive dividends; raw-price overnight returns are biased downward on
   ex-dividend dates, so the measured edge is a lower bound.
5. **Turnover is mechanically high**: ~504x annual turnover. Capacity and
   operational constraints are real; this candidate is evaluated for statistical
   edge, not capacity.
6. **Multiple-testing risk**: N = 3 (the three cost levels 3/5/10 bp per unit).
   Controlled by the Deflated Sharpe Ratio at N = 3; no parameter grid, no
   post-hoc variants.
7. **Shorter history than the incumbent**: 26.4 years (2000-05-26 start) vs the
   incumbent's 33 years; 33 walk-forward folds vs 48. Adequate but lower power.
8. **Constant breadth**: universe breadth is 3 for the full history (no
   point-in-time breadth growth); the basket is concentrated in large-cap US
   equity beta and overlaps the incumbent's equity exposure.
9. **No risk overlay in baseline**: per AGENTS.md, the baseline has NO
   volatility targeting, drawdown control, or regime filter.
10. **Weekend/holiday composition**: the Friday-close -> Monday-open overnight
    return spans 3 calendar days; holiday periods span longer. Not separately
    modeled.
11. **Gate-statistic dispersion (Cycle 879)**: the rolling-63 gate statistic is
    noisy - it fails in 39.16% of the incumbent's own rolling-63 windows. Any
    rolling statistic quoted for this candidate must be reported next to its
    own dispersion, so an ordinary drawdown is not read as a structural break.

---

## Falsification Condition

The candidate is **Rejected/Failed** if ANY of the following hold on the
pre-registered walk-forward evaluation (33 folds, fixed parameters, 10yr train /
12m test / 6m step, 21-day purge & embargo):

1. **Walk-forward mean OOS Sharpe < 0.9** (primary promotion gate)
2. **< 50% of walk-forward folds have a positive test Sharpe**
3. **<= 100 pooled OOS trades across all folds** (expected ~8,000+ at baseline:
   ~242 trade days per 12-month test fold x 33 folds)
4. **The net WF Sharpe does not exceed the same-fold close-to-close
   benchmark's** (the edge is equity beta, not an edge)
5. **The edge does not survive the 10 bp-per-unit cost row** (the documented
   "hidden cost of buying at the open")

It is a **credible candidate for further validation** only if all of 1-5 hold
and the DSR does not reject.

---

## Cost Model Assumptions

Identical to `calendar_effects_001`, `csmomentum_001`, `sectorrotation_001` and
the incumbent:

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bp per unit of weight change | `config/settings.yaml: backtest.default_commission_bps` |
| Slippage | 2.0 bp per unit of weight change | `config/settings.yaml: backtest.default_slippage_bps` |
| **Total (decision configuration)** | **3.0 bp per unit** | `src/backtest/engine.py: get_cost_params()` |
| Sensitivity rows (pre-registered, not a grid) | 5.0 bp and 10.0 bp per unit | this hypothesis |
| Funding / borrow | 0.0 (fully funded long-only ETF basket) | `config/settings.yaml: backtest.default_funding_rate_annual` |
| Risk-free rate in research metrics | 2.0% annual | `config/settings.yaml: evaluation.risk_free_rate_annual` |
| Dividends | **not received** (the leg is closed before the ex-date payout is captured) | raw prices; conservative bias |
| Market impact / latency | not modelled (flat slippage) | disclosed confounder #3 |

Cost drag at the decision configuration: 504 units of annual turnover x 3 bp =
**1.512%/yr**.

---

## Walk-Forward Design

`src/evaluation/walkforward.py: generate_walkforward_splits` with
`train_years=10.0`, `test_months=12.0`, `step_months=6.0`, `purge_days=21`,
`embargo_days=21`, start `2000-05-26`, end `2026-10-16`. The strategy has **no
fitted parameter**, so the train window only bounds each fold; the per-fold
statistic is the **test-period net Sharpe**. The evaluation script MUST assert
the generated fold count (33) and print the first and last fold.

Expected fold geometry (asserted, not assumed):
first fold test `2010-02-22 -> 2011-02-08`; last fold test `2025-08-06 ->
2026-07-23`.

---

## Promotion Gates (pre-registered, repository convention)

| Gate | Threshold | Statistic |
|------|-----------|-----------|
| WF mean OOS Sharpe | >= 0.9 | Mean of the 33 per-fold test Sharpes |
| Positive fold rate | >= 50% | Share of folds with test Sharpe > 0 |
| Pooled OOS trades | > 100 | Sum of per-fold trade counts |
| DSR at N = 3 | not rejected | `src/evaluation/statistics.py: compute_dsr` |
| Block-bootstrap 95% CI | lower bound > 0 | `src/evaluation/statistics.py: block_bootstrap_sharpe` |

The primary WF-Sharpe gate statistic is computed with the repository's
backtest-research metric convention (`src/backtest/engine.py: compute_metrics`,
CAGR-based, 2% risk-free rate) so that the number is directly comparable with
the rejected `calendar_effects_001` candidate (WF mean OOS Sharpe -0.0254) and
with the other candidate records in this repository. The canonical arithmetic
Sharpe (`src/evaluation/sharpe.py: sharpe_ratio`, rf 0) is **also** reported
for every fold and for the pooled series, so the verdict can be checked on both
scales. No gate threshold is changed by this hypothesis.

---

## Erratum (added 2026-10-19, AFTER the backtest was executed; disclosure only)

The v001 text above states the cost drag at the decision configuration as
"**~1.51%/yr**" and the net-return prior as "+5% to +10% after ~1.51%/yr cost".
That cost figure is an **arithmetic error**: 504 units of annual turnover x
3 bp per unit = 1512 bp = **15.12%/yr**, not 1.512%/yr. The error is in the
narrative cost statement and in the prior derived from it; nothing else.

**What is unchanged:** the decision cost configuration (3 bp/unit), the
sensitivity rows (5 bp and 10 bp), N = 3, every gate threshold, every
falsification condition, the universe, the signal, the execution convention
and the walk-forward design. The executed backtest applied the repository's
cost model exactly as specified (`turnover_units x cost_per_unit`, verified in
the script's self-checks) and is unaffected by the narrative error.

**Consequence:** the stated net-return prior was unreachable under the
correctly computed cost drag (a 10 bp/unit row implies 50.4%/yr of cost), and
the candidate was in fact evaluated and **rejected** (WF mean OOS Sharpe
-0.599718; decision label **Rejected/Failed**; see
`research/reports/overnight_capture_backtest_001.md`). The erratum removes a
prior that the executed data had already contradicted; it does not change the
verdict, and it is recorded rather than silently repaired.
