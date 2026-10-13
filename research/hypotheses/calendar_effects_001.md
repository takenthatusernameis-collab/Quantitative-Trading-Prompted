# Hypothesis: Calendar / Rebalancing Effects — Turn-of-Month Window Exposure (calendar_effects_001)

## Version History

- v001 (calendar_effects_001, 2026-10-13): Initial pre-registered
  hypothesis for Cycle 17 (evaluation Cycle 18). Parent cycle:
  Cycle 11 Opportunity Shortlist (C6, 26/35 — Exploratory
  signal, rank 4 of 10). Code revision: 1d540f8
  Pre-registered BEFORE any backtest execution.

---

## Mechanism Description

Recurring institutional flows at predictable calendar dates —
month-end and month-start pension/401(k)/index-fund
rebalancing, payroll and contribution flows, and window
dressing — create short-horizon price pressure concentrated
around the turn of the month (the "turn-of-month" or TOM
effect; Lakonishok & Smidt 1988; Arik & Bhardwaj 2019 for
ETFs). The structural explanation is flow synchronization:
many institutional rebalancing rules fire on the same
calendar dates, and their combined order flow moves prices
temporarily before dissipating.

The pre-registered test isolates the first-order calendar
effect: hold an equal-weight basket of the three most liquid
US equity ETFs (SPY, QQQ, IWM) during the turn-of-month
window (the last `pre_days` trading days of each month plus
the first `post_days` trading days of the following month),
and hold cash otherwise. This is a pure timing rule: the
signal is the deterministic trading calendar, not prices.
Quarter-end concentration and index-reconstitution-day
refinements are deliberately EXCLUDED from the baseline
(AGENTS.md "baseline before complexity"); they are reserved
for post-gate cycles only if this baseline clears all
promotion gates.

This mechanism is distinct from all prior repository work:
the incumbent and the C3/C4 family are momentum strategies
(price-derived signals); this candidate's signal is
exogenous calendar membership.

---

## Expected direction and magnitude (Pre-Specified Prior)

The prior is conservative, consistent with the Cycle 11
shortlist score (c) Expected net return = 2/5 ("Expected
effect is typically below the 3bps round-trip hurdle"):

| Metric | Prior (this hypothesis) | Note |
|--------|--------------------------|------|
| Gross annualized excess return over always-invested 1/N | **0%–1.5%** | Prior, not a result; documented TOM premia have decayed and are competed |
| Net annualized excess return over always-invested 1/N (after ~72 bps/yr turnover cost) | **-0.5% to +1.0%** | Prior; ~24 trade days/yr at baseline |
| Net out-of-sample Sharpe (walk-forward) | >= 0.9 (promotion gate) | Gate fixed by AGENTS.md; prior probability of clearing it is LOW |
| Maximum drawdown (test) | < 20% | Timing strategies carry concentrated-window exposure |
| Annualized turnover | ~24x | ~24 full-position boundary changes/yr (12 windows x 2 boundaries); constant across the grid |

Direction: positive (calendar-window returns are expected to
exceed always-invested returns, net of costs), but the prior
expectation is that the effect is small relative to costs.

Falsification: If the net walk-forward mean OOS Sharpe < 0.9
OR < 50% of walk-forward folds have positive test Sharpe, the
hypothesis is **rejected** (downgraded to Rejected/Failed).
This condition is pre-stated BEFORE any backtest execution.

---

## Holding horizon

Event-driven: exposure is held only during calendar windows
(baseline: 4 consecutive trading days per month — the last
trading day plus the first 3 of the next month, ~19.2% of
trading days). Position established at the prior trading
day's close; no intra-window trading.

---

## Asset Universe

The three most liquid cached US equity ETFs (per the Cycle 11
shortlist, "SPY, QQQ, IWM primary"):

1. SPY — SPDR S&P 500 ETF
2. QQQ — Invesco QQQ (Nasdaq-100)
3. IWM — iShares Russell 2000

**Data integrity (verified 2026-10-13, pre-freeze,
cache-only)**:

| Symbol | Rows | Start | End | Close NaN | Dup dates |
|--------|------|-------|-----|-----------|-----------|
| SPY | 8,482 | 1993-01-29 | 2026-10-09 | 0 | 0 |
| QQQ | 6,940 | 1999-03-10 | 2026-10-09 | 0 | 0 |
| IWM | 6,632 | 2000-05-26 | 2026-10-09 | 0 | 0 |

- Common trading calendar: **6,632 days, 2000-05-26 →
  2026-10-09** (~26.3 years; bounded by IWM inception).
- Union calendar: 8,482 days, 1993-01-29 → 2026-10-09.
- Aligned Close frame (union calendar, forward-filled):
  8,482 × 3, 100% completeness after each inception,
  content hash `204f6ca3bac2ff75`.
- No new data fetched. Pre-inception cells are NaN (not
  back-filled); the strategy history starts 2000-05-26, so
  cross-sectional breadth is constant at 3 for the full
  strategy history (no point-in-time breadth growth).
- Calendar rules require no signal warmup (the calendar is
  exogenous); the first tradable date is the common-calendar
  start.

---

## Features and Data Sources

| Feature | Specification | Source |
|---------|---------------|--------|
| Prices | Daily Close (OHLCV) | `data/raw/{SPY,QQQ,IWM}.parquet` (Yahoo Finance via yfinance, cached) |
| Calendar mask | Trading-day-based month boundaries: last `pre_days` and first `post_days` trading days of each month | Computed from the trading calendar (deterministic) |
| Weights | Equal-weight 1/3 per asset when exposed; 0 otherwise | `run_cycle18.py` (to be created) |
| Point-in-time | Exposure on day T is decided at T-1 close (calendar membership of T is public knowledge indefinitely in advance) | Engine convention: `port_ret[t] = weights[t] * ret[t]` |

### Execution convention (pre-specified, IMPORTANT)

The exposure mask marks the trading days whose close-to-close
returns the strategy captures. Positions are established at
the prior trading day's close. NO 1-day shift is applied to
the mask, because the calendar is exogenous public
information known indefinitely in advance: there is no
price-derived signal and therefore no price-signal lookahead
channel. This differs deliberately from the momentum
convention (`build_weights` shift(1)), which exists to
prevent lookahead on price-derived signals. The Cycle 18
script MUST implement month boundaries on TRADING days (the
k-th-to-last / k-th trading day of each month), NOT on
calendar `is_month_end`/`is_month_start` flags, which are
False whenever a month's last/first calendar day is a
non-trading day.

### Pre-Specified Default Configuration

- `pre_days = 1` (last 1 trading day of the month)
- `post_days = 3` (first 3 trading days of the following month)

This is the classic TOM window (Lakonishok & Smidt 1988;
Arik & Bhardwaj 2019). Baseline mechanics (verified on the
cached calendar): ~48.3 exposure days/yr (19.2% of days),
~24.1 trade days/yr, ~72 bps/yr turnover cost at 3 bps per
unit of weight change.

### Pre-Specified Robustness Grid (Fixed Count for Multiple-Testing Control)

| Parameter | Values | Count |
|-----------|--------|-------|
| `pre_days` | {1, 2, 3} | 3 |
| `post_days` | {1, 2, 3, 5, 7, 10} | 6 |
| **Total** | | **18** |

**Grid arithmetic**: 3 x 6 = **18 unique configurations**;
the pre-registered trial count IS the product (no
pre-registered/evaluated discrepancy this cycle). The Cycle 18
script MUST assert `len(pre_days) * len(post_days) == 18`
before any evaluation runs. Baseline (1, 3) is a grid member.
No additional configurations will be added post-hoc.

---

## Entry/Exit Rules

1. **Calendar mask (deterministic)**: For each month, mark
   the last `pre_days` trading days and the first
   `post_days` trading days of the following month.
2. **Exposure**: When the mask is True, hold the equal-weight
   basket (1/3 SPY, 1/3 QQQ, 1/3 IWM). When False, hold
   cash (0 exposure).
3. **Execution**: Positions change only at window boundaries
   — entry at the close before the first window day, exit at
   the close after the last window day. No intra-window
   trading.
4. **Long-only, no leverage**: gross exposure is either 1.0
   (in-window) or 0.0 (cash).
5. **Costs applied**: 3 bps per unit of weight change (1 bps
   commission + 2 bps slippage) on boundary days.
6. **Cash return**: 0% (engine convention; the Sharpe ratio
   subtracts the 2% flat risk-free rate — a conservative
   drag on timing strategies, documented as a limitation).

---

## Benchmark

Two benchmarks, evaluated on the identical date ranges and
cost model:

1. **Always-Invested 1/N Equal-Weight Basket**: constant 1/3
   target weights in SPY/QQQ/IWM, 1-day lag (shift(1)),
   monthly month-end schedule (the C3/C4 1/N convention).
   This isolates the value of calendar timing vs. passive
   holding of the identical basket. Within the engine's
   exogenous-weights framework, constant weights with the
   monthly calendar imply ~zero observed turnover and ~zero
   cost drag — a mild upward bias in the benchmark's net
   return (same noted limitation as C3/C4).
2. **Incumbent TSMOM (tsmomentum_spytrend_001)**: Cycle 6
   validated candidate on its core 7-asset universe (SPY,
   QQQ, IWM, TLT, GLD, EFA, EEM) with vol-target (10%), DD
   control (15%), SPY 200d SMA filter, 3 bps costs,
   evaluated with its validated overlay-warmup conventions
   ("slice" for the test period; "full" for walk-forward
   folds). Context benchmark: the incumbent's WF statistics
   were validated on the 1993-start 48-fold design and are
   not directly comparable to this candidate's 33-fold
   design; it is reported as context, not a gate.

Both benchmarks are evaluated on the **test period**
(2018-01-01 to 2026-10-09) and in the **identical
walk-forward folds**.

---

## Known Confounders

1. **Effect decay and competition**: the TOM effect is
   well-documented and competed; post-2000s premia are
   smaller. This is the primary reason the prior is
   conservative.
2. **Cash earns 0% in the engine**: no money-market accrual;
   the 2% flat risk-free rate is subtracted in the Sharpe
   ratio. This is conservative for a part-time-exposure
   strategy.
3. **Flat 3 bps cost model**: no bid-ask spread,
   market-impact, or asset-differentiated cost modeling.
   Window-boundary trades cluster on predictable dates, where
   real spreads may be wider (closing-auction pressure).
4. **Window composition**: TOM windows mechanically cluster
   around month boundaries, so window returns partly reflect
   weekend/holiday composition effects; gridding window
   widths (the pre-registered grid) partially addresses this.
5. **Multiple-testing risk across calendar definitions**:
   calendar rules are researcher degrees of freedom.
   Controlled by the fixed 18-config grid and DSR at N=18;
   no post-hoc calendar variants.
6. **Shorter history than C3**: 26.3 years (2000-05-26 start)
   vs C3's 33 years; 33 walk-forward folds vs 48. Adequate
   but lower power.
7. **Constant breadth**: universe breadth is 3 for the full
   history (no point-in-time breadth growth); the basket is
   concentrated in large-cap US equity beta and overlaps the
   incumbent's equity exposure.
8. **Execution-convention difference**: the calendar mask is
   not 1-day-shifted (justified above); benchmark
   conventions differ by design and are documented.
9. **No risk overlay in baseline**: per AGENTS.md, the
   baseline has NO volatility targeting, drawdown control,
   or regime filter.

---

## Falsification Condition

The hypothesis is **falsified (Rejected/Failed)** if ANY of
the following hold on the pre-registered walk-forward
evaluation (33 folds, fixed parameters, 10yr train / 12m
test / 6m step, 21-day purge & embargo):

1. **Walk-forward mean OOS Sharpe < 0.9** (primary promotion
   gate)
2. **< 50% of walk-forward folds have positive test Sharpe**
3. **< 100 pooled OOS trades across all folds** (expected
   ~790 at baseline: ~24.1 trade days per 12-month test
   fold x 33 folds)
4. **Parameter plateau check fails**: < 2 of the 3 `pre_days`
   values (1, 2, 3) achieve test Sharpe within 10% of the
   baseline (1, 3) test Sharpe, evaluated at the baseline's
   `post_days=3` (repository plateau convention: threshold =
   max(0.1, 10% x |baseline test Sharpe|)).

This condition is pre-stated BEFORE any backtest execution.
If falsified, the candidate is labeled "rejected/failed" and
archived, and the next cycle moves to the next untested
candidate on the Cycle 11 shortlist (C5 macro regime overlay
extension, 24/35 — noting its overlay-only constraint).

---

## Cost Model Assumptions

Identical to C3 (csmomentum_001), C4 (sectorrotation_001),
the incumbent (tsmomentum_spytrend_001) and
`config/simulation_candidate_001.yaml`:

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bps/trade | `config/settings.yaml:backtest.default_commission_bps` |
| Slippage | 2.0 bps/trade | `config/settings.yaml:backtest.default_slippage_bps` |
| Round-trip | 3.0 bps per unit of weight change | `config/simulation_candidate_001.yaml:cost_model` |
| Funding rate | 0.0% annualized (placeholder) | `config/settings.yaml:backtest.default_funding_rate_annual` |
| Risk-free rate | 2.0% annualized (flat) | `config/settings.yaml:evaluation.risk_free_rate_annual` |
| Minimum trade size | $10.00 | `config/settings.yaml:backtest.min_trade_size_usd` |

**Cost model gaps acknowledged**: no bid-ask spread model, no
borrow/short cost (long-only avoids this), no market-impact
model (flat slippage), no latency model, flat risk-free
rate. These are documented limitations per
`research/reports/data_inventory.md`.

---

## Pre-Registered Evaluation Plan

### Chronological Splits (Repo Convention)

| Split | Period | Purpose |
|-------|--------|---------|
| Train | 2000-05-26 to 2009-12-31 | Parameter selection (NOT used — baseline is pre-specified) |
| Validation | 2010-01-01 to 2017-12-31 | Robustness grid evaluation, configuration screening (diagnostic only) |
| Test | 2018-01-01 to 2026-10-09 | Final holdout, promotion-gate decision |

**Point-in-time treatment**: the calendar mask uses only the
exogenous trading calendar; prices enter via lagged
execution (positions at T-1 close). No look-ahead in any
split.

### Walk-Forward Design (Matches Cycle 6 / C3 / C4)

- **Rolling window**: 10-year train, 12-month test, 6-month
  step
- **Purge**: 21 days between train end and test start
- **Embargo**: 21 days after test period end
- **Parameters**: Fixed across all folds (NO per-fold
  re-optimization)
- **Folds**: **33** (verified 2026-10-13 via
  `src/evaluation/walkforward.py:generate_walkforward_splits`
  from the 2000-05-26 common-calendar start; the C3 48-fold
  and C4 36-fold counts do NOT apply because this universe's
  common history starts 2000-05-26 with IWM inception).
  Fold 1: train 2000-05-26 → 2010-01-21, test 2010-02-22 →
  2011-02-08. Fold 33: train 2015-11-10 → 2025-07-07, test
  2025-08-06 → 2026-07-23. The Cycle 18 script MUST assert
  the generated fold count equals 33.
- **Evaluation**: Each fold produces test-period Sharpe,
  annual return, max DD, trade count.

### Promotion Gates (ALL Must Pass to Advance to Simulation/Paper-Trading)

| Gate | Threshold | Measured On |
|------|-----------|-------------|
| Walk-forward mean OOS Sharpe | >= 0.9 | All folds, net of 3 bps costs |
| Positive fold rate | >= 50% | Count of folds with test Sharpe > 0 |
| Pooled OOS trades | > 100 | Sum of trades across all test folds |
| Parameter plateau | >= 2 of 3 pre_days within 10% of baseline test Sharpe | Baseline `post_days=3` |

### Multiple-Testing Control

- **Exact configuration count tracked**: 18 pre-specified
  combinations (3 x 6), with an explicit arithmetic assertion
  in the Cycle 18 script.
- **Deflated Sharpe Ratio**: computed via
  `src/evaluation/statistics.py:compute_dsr` using the true
  trial count N=18.
- **No test-set peeking**: configurations are NEVER selected
  based on test-period results. The baseline is pre-specified;
  the robustness grid is diagnostic (plateau +
  multiple-testing control) only.
- **PSR** (vs SR=0 and vs the 0.9 gate), **block-bootstrap
  Sharpe 95% CI** (1000 samples, 22-day block, seed=42), and
  **PBO/CSCV** via `src/evaluation/statistics.py:compute_pbo`
  over the 18-config grid (train=2000-2009 vs test=2018-2026).

### Reproduction Commands

```bash
# Cycle 18 (to be created) will execute the baseline backtest and walk-forward
python3 research/run_cycle18.py

# Verification that the frozen config parses
python3 -c "import yaml; yaml.safe_load(open('config/calendar_effects_001.yaml'))"
```

---

## Evidence Artifacts (To Be Persisted in Cycle 18)

Per AGENTS.md "Evidence artifacts", Cycle 18 will persist:

- Data-source details, date ranges, frequency, asset
  universe, point-in-time treatment
- Missing-data handling (pre-inception cells are NaN and
  excluded; strategy history starts at the common-calendar
  start 2000-05-26)
- Integrity hashes/counts (row counts per symbol, date-range
  coverage, aligned-frame content hash `204f6ca3bac2ff75`)
- Code revision (git SHA)
- Configurations tested (all 18, with parent/lineage to this
  hypothesis)
- Trial count (18)
- Cost assumptions (3 bps per unit of weight change, prior-
  close execution, Close field)
- Baseline metrics (Sharpe, Sortino, CAGR, max DD, profit
  factor, turnover, exposure, trade count, tail risk)
- Benchmark-relative results (vs always-invested 1/N and vs
  incumbent TSMOM)
- Walk-forward folds (33), purge/embargo, parameter plateau
  results
- Deflated Sharpe Ratio (N=18), PBO/CSCV, probabilistic
  Sharpe, block-bootstrap CIs
- Reproduction commands

---

## Decision Discipline (Pre-Committed)

Results will be labeled as exactly one of:

- **Credible candidate for further validation** — All
  promotion gates passed, robustness confirmed, net-of-cost
  performance credible
- **Exploratory signal** — Some promise but gates not fully
  cleared; warrants limited follow-up
- **Rejected/Failed** — Falsification condition met;
  documented and archived
- **Blocked by data/infrastructure** — Cannot form valid test
  with available data

---

## References

- Lakonishok, J., & Smidt, S. (1988). "Are Seasonal
  Anomalies Real? A Ninety-Year Perspective". *Review of
  Financial Studies*, 1(4), 403-425.
- Arik, R., & Bhardwaj, R. (2019). "The Turn-of-the-Month
  Effect in ETFs". (Documented persistence of TOM premia in
  large US ETFs.)
- Cycle 11 Opportunity Shortlist:
  `research/reports/opportunity_shortlist.md` (C6 = 26/35,
  rank 4 of 10 — Exploratory signal)
- Cycle 16 consolidation:
  `research/reports/cross_momentum_consolidation.md`
- Cycle 6 Walk-Forward Design:
  `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Evaluation stats: `src/evaluation/statistics.py`
  (`compute_dsr`, `compute_psr`, `compute_pbo`; seeded
  bootstrap, seed=42 convention)
- Walk-forward splits: `src/evaluation/walkforward.py`
  (`generate_walkforward_splits`)
- AGENTS.md: Research Documentation Standards; "Baseline
  before complexity"; "Hypothesis first"; "Independent
  evaluation"; "Multiple-testing control"

---

*Created: 2026-10-13*
*Code revision: 1d540f8*
*Status: PRE-REGISTERED — No backtest executed. Cycle 18 will execute evaluation (after Cycle 17 re-executes C4 correctly).*
