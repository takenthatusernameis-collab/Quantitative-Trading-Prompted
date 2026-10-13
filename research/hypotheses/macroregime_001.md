# Hypothesis: Macro Regime Overlay Extension (macroregime_001)

## Version History

- v001 (macroregime_001, 2026-10-13): Initial pre-registered
  hypothesis for Cycle 19. Parent cycle: Cycle 11 Opportunity Shortlist
  (C5, 24/35 — Exploratory signal, rank 6 of 10). Code revision: 052135d
  Pre-registered BEFORE any backtest execution (evaluation is Cycle 19).

**Note:** C5 had NO frozen pre-registration in the repository at the start of
Cycle 19. This document and `config/macroregime_candidate_001.yaml` were created
in Cycle 19 as the pre-registration, per NEXT_AGENT_TASK.md Cycle 19 ("If C5 is
not yet frozen/pre-registered in the expected files, inspect the codebase to
locate the correct C5 hypothesis/config and execute it as specified").

---

## Mechanism Description

Volatility regimes are persistent (volatility clustering; Mandelbrot 1963,
Bollerslev 1986) and VIX spikes lead equity drawdowns (S&P 500 realized vol
and VIX co-move with equity drawdowns during stress). The structural
explanation: risk appetite compresses in high-volatility regimes as leveraged
participants de-risk, margin calls force forced selling, and hedging demand
absorbs liquidity \u2014 producing temporarily lower risk-adjusted returns during
high-volatility windows. Reducing equity exposure in high-volatility regimes
is therefore a *defensive* overlay: it does not predict the *level* of returns,
it reduces exposure during the regime in which the incumbent's risk-adjusted
performance is worst.

This is the **Macro Regime Overlay Extension**: apply, on top of the incumbent
226-day TSMOM + combined vol-target (10%) + drawdown-control (15%) base, an
additional **VIX regime exposure multiplier** that trims equity exposure in
high-volatility regimes. The SPY 200-day SMA trend filter (already validated
within the incumbent, Cycle 5/6/7) is retained as the *base* regime gate; the
C5 extension adds a **VIX-level** gate on top of it.

**Explicit acknowledgment (per Cycle 11 shortlist and Cycle 5 regime analysis)**:
- The incumbent alone (226-day TSMOM + vol+dd overlay + SPY 200d SMA filter)
  is a **Credible Candidate** (Cycle 6 walk-forward mean OOS Sharpe 0.9473,
  48 folds, 6,013 pooled trades; Cycle 7 test Sharpe 1.4178). C5 is an
  *overlay-on-overlay* extension, not a replacement.
- Cycle 5 already tested a **VIX-level filter in isolation** (50% exposure
  when VIX > 30, on top of the Cycle 4 base, WITHOUT the SPY trend filter):
  test Sharpe 1.0463 (see `tsmomentum_regime_filter_001.md`). That single-filter
  result cleared the 0.9 gate. C5 is distinct: it adds the VIX gate **on top of
  the already-validated SPY-trend-filtered incumbent**, i.e. a *multi-indicator*
  overlay. The prior therefore acknowledges that the marginal value of adding
  a second regime indicator to an already-gated candidate is likely small and
  may even hurt (over-trimming).
- ^VIX is an **index, not a tradeable instrument** (per `data_inventory.md`).
  No VIX futures, VIX ETNs, or options history are cached. C5 is therefore
  testable **only as an exposure multiplier on the cached ETF universe**;
  there is no direct volatility risk premium to harvest. This is the
  "overlay-only" constraint noted in the Cycle 11 shortlist.

---

## Expected direction and magnitude (Pre-Specified Prior)

The prior is conservative and explicitly acknowledges that C5 is an
overlay-on-overlay extension of an already-gated candidate:

| Metric | Incumbent (C1, validated) | C5 prior (this hypothesis) | Note |
|--------|---------------------------|----------------------------|------|
| Net test Sharpe (test period) | 1.4178 | **0.9\u20131.4** | Prior; SPY trend filter already does most of the work |
| Net walk-forward mean OOS Sharpe | 0.9473 | **>= 0.9 (promotion gate)** | Gate fixed by AGENTS.md; prior prob of *raising* the incumbent's WF mean is LOW |
| Max drawdown (test) | -7.79% | **-5% to -9%** | VIX gate may trim tail, but over-trimming can hurt |
| Annualized turnover | 13.3x | **13x\u201316x** | Extra gate adds boundary trades only in stress |
| Avg exposure (test) | 65.1% | **55%\u201365%** | VIX gate trims exposure in high-vol windows |

Direction: **ambiguous / defensive**. A VIX regime gate can *improve* consistency
(Sharpe, max DD) by reducing exposure during the worst risk-adjusted windows,
but it can also *reduce* raw return and net Sharpe by exiting (or trimming)
positions during periods that subsequently rebound. The prior therefore does
**not** predict a sign for the marginal effect of the VIX gate over the
SPY-trend-filtered incumbent; it predicts a *small* effect in either direction.

Falsification: If the net walk-forward mean OOS Sharpe < 0.9 OR < 50% of
walk-forward folds have positive test Sharpe, the hypothesis is **rejected**
(downgraded to Rejected/Failed). This condition is pre-stated BEFORE any
backtest execution.

---

## Holding horizon

Same as the incumbent: monthly rebalancing (~21 trading days), 226-day
momentum lookback with 21-day skip, top-50% selection, equal-weight.
The VIX regime gate is evaluated **daily** (VIX is observed daily) but its
exposure multiplier is applied at the monthly rebalance boundary, consistent
with the incumbent's rebalance schedule. No intra-month regime trading.

---

## Asset Universe

Same as the incumbent (C1) and the Cycle 5 regime analysis:

1. SPY \u2014 SPDR S&P 500 ETF
2. QQQ \u2014 Invesco QQQ (Nasdaq-100)
3. IWM \u2014 iShares Russell 2000
4. TLT \u2014 iShares 20+ Year Treasury Bond ETF
5. GLD \u2014 SPDR Gold Shares
6. EFA \u2014 iShares MSCI EAFE ETF
7. EEM \u2014 iShares MSCI Emerging Markets ETF

**Regime driver (input only, NOT a position)**:
- ^VIX \u2014 CBOE Volatility Index (cached 1993-01-04 to 2026-10-08, 8,502 rows,
  100% Close completeness, 0 duplicate dates; see `data_inventory.md`).
  ^VIX is an index and is **never held as a position**; it enters only as a
  daily regime input to the exposure multiplier.

**Data integrity (verified 2026-10-13, pre-freeze, cache-only)**:

| Symbol | Rows | Start | End | Close NaN | Dup dates |
|--------|------|-------|-----|-----------|-----------|
| SPY | 8,482 | 1993-01-29 | 2026-10-09 | 0 | 0 |
| QQQ | 6,940 | 1999-03-10 | 2026-10-09 | 0 | 0 |
| IWM | 6,632 | 2000-05-26 | 2026-10-09 | 0 | 0 |
| TLT | 6,089 | 2002-07-30 | 2026-10-09 | 0 | 0 |
| GLD | 5,507 | 2004-11-18 | 2026-10-09 | 0 | 0 |
| EFA | 6,317 | 2001-08-27 | 2026-10-09 | 0 | 0 |
| EEM | 5,911 | 2003-04-14 | 2026-10-09 | 0 | 0 |
| ^VIX | 8,502 | 1993-01-04 | 2026-10-08 | 0 | 0 |

- Common trading calendar (intersection of the 7 ETFs): **5,507 days,
  2004-11-18 \u2192 2026-10-09** (~21.9 years; bounded by GLD inception).
- Union calendar: 8,482 days, 1993-01-29 \u2192 2026-10-09.
- ^VIX is observed on the union calendar (8,502 days); on the common ETF
  calendar it is 100% complete after forward-fill.
- No new data fetched. Pre-inception cells are NaN (not back-filled); the
  strategy history starts at the common-calendar start, so cross-sectional
  breadth is constant at 7 for the full strategy history (no point-in-time
  breadth growth).
- Signal warmup: the first date on which all 7 momentum values are valid is
  ~2006-01 for the baseline (226, 21); pre-warmup dates carry no positions
  (point-in-time, no back-fill).

---

## Features and Data Sources

| Feature | Specification | Source |
|---------|---------------|--------|
| Prices | Daily Close (OHLCV) | `data/raw/{SPY..EEM}.parquet` (Yahoo Finance via yfinance, cached) |
| Momentum signal | 226-day return with 21-day skip: `lookback=226`, `skip=21` | `src/features/momentum.py:compute_momentum` |
| Ranking | Cross-sectional rank each period (higher momentum = higher rank) | `src/features/momentum.py:rank_assets` |
| Selection | Top `top_fraction=0.5` by rank, equal-weight | `src/features/momentum.py:select_top_decile`, `build_weights` |
| Point-in-time | Weights shifted by 1 day (signal on T-1 -> position on T) | `src/features/momentum.py:build_weights` line 98 |
| Regime driver | ^VIX daily Close (regime input only) | `data/raw/^VIX.parquet` |
| SPY trend gate | 0% exposure when SPY < 200-day SMA; 100% otherwise | Incumbent, Cycle 5/6/7 |
| VIX regime gate | Exposure multiplier from VIX level vs. threshold | `run_cycle19.py` (to be created) |

### Pre-Specified Default Configuration (Baseline)

The baseline is the **incumbent configuration** (validated in Cycles 5/6/7):

- `lookback = 226`, `skip = 21`, `top_fraction = 0.5`
- Volatility targeting: target annualized vol = 10% (63-day trailing realized
  vol, cap at 100% exposure)
- Drawdown control: reduce exposure by 50% when cumulative drawdown exceeds 15%
- SPY trend filter: 0% exposure when SPY < 200-day SMA
- **C5 baseline overlay**: VIX regime gate with `vix_threshold = 30`,
  `vix_exposure = 0.5` (50% exposure when VIX > 30; full exposure when VIX <= 30).
  This is the *same VIX filter tested in Cycle 5* (`tsmomentum_regime_filter_001.md`),
  re-applied **on top of the SPY-trend-filtered incumbent** rather than on top of
  the unfiltered Cycle 4 base. Using the already-tested Cycle 5 VIX definition
  (rather than a novel, tuned threshold) is a deliberate anti-overfitting choice.

### Pre-Specified Robustness Grid (Fixed Count for Multiple-Testing Control)

The grid varies **only the VIX regime definition** (the incumbent's other
parameters are fixed at their validated values). This bounds the
multiple-testing burden to the new researcher degrees of freedom (the VIX
gate), not the incumbent's already-validated parameters.

| Parameter | Values | Count |
|-----------|--------|-------|
| `vix_threshold` | {20, 25, 30, 35} | 4 |
| `vix_exposure` | {0.0, 0.5, 1.0} | 3 |
| **Total** | | **12** |

**Grid arithmetic**: 4 x 3 = **12 unique configurations**. The Cycle 19 script
MUST assert `len(vix_thresholds) * len(vix_exposures) == 12` before any
evaluation runs. Baseline `(30, 0.5)` is a grid member. The `vix_exposure = 1.0`
member is the **incumbent with no VIX gate** (the control arm: it isolates the
marginal effect of the VIX gate by holding all else equal). No additional
configurations will be added post-hoc.

---

## Entry/Exit Rules

1. **Signal formation (T-1 close)**: Compute 226-day momentum for each of the
   7 ETFs (lookback=226, skip=21). Select top 50% by momentum, equal-weight.
   Weights shifted 1 day (point-in-time).
2. **SPY trend gate (incumbent)**: Set exposure to 0% (cash) when SPY close <
   200-day SMA; 100% otherwise. Applied as a multiplier on the base momentum
   weights.
3. **VIX regime gate (C5 extension)**: Apply a second exposure multiplier:
   - If ^VIX Close > `vix_threshold`: exposure multiplier = `vix_exposure`
     (0.0 = full trim to cash, 0.5 = half trim, 1.0 = no VIX gate / control arm)
   - If ^VIX Close <= `vix_threshold`: exposure multiplier = 1.0
   The VIX value used for day T is the day T-1 close (point-in-time: the
   regime is observable at the prior day's close, so no look-ahead).
4. **Combined exposure**: final weights = base momentum weights x SPY trend
   multiplier x VIX regime multiplier.
5. **Risk overlay**: Apply the incumbent's combined volatility-targeting (10%)
   and drawdown-control (15%) overlay on the regime-gated weights, exactly as
   in `run_cycle15_c4_corrected.py::_incumbent_overlay` (vol scale first, then
   DD scale). This is the validated Cycle 6 overlay path.
6. **Rebalancing**: Monthly (month-end calendar). No intra-month trading.
7. **Long-only, no leverage**: gross exposure <= 100%.
8. **Costs applied**: 3 bps per unit of weight change (1 bps commission + 2 bps
   slippage) on all weight-change days, identical to the incumbent and all
   pre-registered candidates.

---

## Benchmark

Two benchmarks, evaluated on the identical date ranges and cost model:

1. **Incumbent TSMOM (tsmomentum_spytrend_001) \u2014 the CONTROL arm**:
   The validated candidate with NO VIX gate (`vix_exposure = 1.0` in the grid,
   i.e. baseline SPY-trend-filtered incumbent). This is the correct benchmark
   because C5 is an *overlay-on-overlay*: the question is whether the VIX gate
   adds value **over the already-validated incumbent**, not over a passive
   index. Evaluated with its validated overlay-warmup conventions: "slice"
   (overlay state initializes at the period start) for the test period and
   "full" (overlay state initializes at history_start, then sliced) for the
   walk-forward folds.
2. **1/N Equal-Weight Portfolio**: Constant 1/7 target weights in the 7-ETF
   universe, 1-day lag, monthly schedule, 3bps round-trip cost model. Context
   benchmark only (the incumbent is the operative comparison).

Both benchmarks are evaluated on the **test period** (2018-01-01 to
2026-10-09) and in the **identical walk-forward folds**.

---

## Known Confounders

1. **Overlay-on-overlay / diminishing returns**: The incumbent already clears
   the promotion gate (WF mean OOS Sharpe 0.9473). Adding a second regime
   indicator to an already-gated candidate has a low prior probability of
   *raising* the OOS Sharpe; the more likely outcomes are (a) no change (the
   SPY trend filter already captures the equity-downturn regime) or (b) a
   decline (over-trimming exits winning positions in rebounding high-vol
   windows). This is the primary reason the C5 prior is flat/ambiguous rather
   than positive.
2. **VIX is an index, not tradeable**: ^VIX cannot be shorted or hedged
   directly. The VIX gate is a *position-sizing* rule, not a volatility risk
   premium harvest. Any net edge it produces is an equity-timing edge, and it
   inherits the incumbent's equity-beta concentration.
3. **Regime definitions are researcher degrees of freedom**: The grid
   (4 thresholds x 3 exposure levels = 12) bounds the multiple-testing burden
   but does not eliminate it. A VIX threshold near 30 is conventional (Cycle 5
   used 30); the grid spans 20\u201335 to test sensitivity.
4. **VIX-SPY correlation is regime-dependent**: In very sharp sell-offs VIX and
   SPY can move together intraday; the gate uses the prior day's VIX close, so
   it cannot react to same-day stress. This is conservative (no look-ahead) but
   means the gate is always at least 1 day stale.
5. **Over-trimming in short, sharp drawdowns**: A 0.0 exposure arm can exit
   equity during a VIX spike and miss the rebound; a 0.5 arm can be too timid
   to help. The grid includes 0.0 and 1.0 arms to bound this behavior.
6. **Same cost model, same gaps as all candidates**: flat 3 bps, no bid-ask
   spread model, no market-impact model, no latency model, flat 2% risk-free
   rate. The incumbent's extra turnover from the SPY trend filter is already
   baked into the validated 13.3x turnover figure; the VIX gate adds boundary
   trades only when VIX crosses the threshold.
7. **Shorter common history than the incumbent's 48-fold design**: the 7-ETF
   common calendar starts 2004-11-18 (GLD inception), giving ~21.9 years and
   **24 walk-forward folds** (verified via `generate_walkforward_splits` from
   the 2004-11-18 common-calendar start; the incumbent's 48 folds use the
   1993-start union calendar). Adequate but lower power; the incumbent
   benchmark is evaluated on the *same* 24 folds for comparability.
8. **No point-in-time breadth growth**: universe breadth is constant at 7 for
   the full history (all 7 ETFs incept at different dates but the common
   calendar starts at the latest inception).

---

## Falsification Condition

The hypothesis is **falsified (Rejected/Failed)** if ANY of the following hold
on the pre-registered walk-forward evaluation (24 folds, fixed parameters,
10yr train / 12m test / 6m step, 21-day purge & embargo, from the 2004-11-18
common-calendar start):

1. **Walk-forward mean OOS Sharpe < 0.9** (primary promotion gate)
2. **< 50% of walk-forward folds have positive test Sharpe**
3. **< 100 pooled OOS trades across all folds** (expected ~2,500+ at baseline:
   ~104 trade days per 12-month test fold x 24 folds; the incumbent's extra
   turnover from the SPY trend filter raises this)
4. **VIX-gate plateau check fails**: < 2 of the 4 `vix_threshold` values
   (20, 25, 30, 35) achieve test Sharpe within 10% of the baseline (30, 0.5)
   test Sharpe, when evaluated at the baseline's `vix_exposure=0.5`
   (repository plateau convention: threshold = max(0.1, 10% x |baseline test
   Sharpe|)).

This condition is pre-stated BEFORE any backtest execution. If falsified, the
candidate is labeled "rejected/failed" and archived, and the next cycle moves
to the next untested candidate on the Cycle 11 shortlist (the shortlist's
remaining untested candidates after C3/C4/C5/C6 are all evaluated: C7-C10 are
blocked by data, C2 is rejected, C1 is the incumbent; see
`research/reports/opportunity_shortlist.md`).

---

## Cost Model Assumptions

Identical to the incumbent (tsmomentum_spytrend_001), C3 (csmomentum_001),
C4 (sectorrotation_001) and `config/simulation_candidate_001.yaml`:

| Component | Value | Source |
|-----------|-------|--------|
| Commission | 1.0 bps/trade | `config/settings.yaml:backtest.default_commission_bps` |
| Slippage | 2.0 bps/trade | `config/settings.yaml:backtest.default_slippage_bps` |
| Round-trip | 3.0 bps per unit of weight change | `config/simulation_candidate_001.yaml:cost_model` |
| Funding rate | 0.0% annualized (placeholder) | `config/settings.yaml:backtest.default_funding_rate_annual` |
| Risk-free rate | 2.0% annualized (flat) | `config/settings.yaml:evaluation.risk_free_rate_annual` |
| Minimum trade size | $10.00 | `config/settings.yaml:backtest.min_trade_size_usd` |

**Cost model gaps acknowledged**: no bid-ask spread model, no borrow/short
cost (long-only avoids this), no market-impact model (flat slippage), no
latency model, flat risk-free rate. These are documented limitations per
`research/reports/data_inventory.md`.

**Turnover note**: the incumbent's validated 13.3x annualized turnover already
includes the SPY trend filter's boundary trades. The VIX gate adds boundary
trades only on days when ^VIX crosses the threshold (a few times per year in
normal regimes, more in stress); the grid's `vix_exposure` values (0.0 vs 0.5
vs 1.0) have different boundary-trade profiles, which is part of what the
grid evaluates honestly.

---

## Pre-Registered Evaluation Plan

### Chronological Splits (Repo Convention)

| Split | Period | Purpose |
|-------|--------|---------|
| Train | 2004-11-18 to 2009-12-31 | Parameter selection (NOT used \u2014 baseline is pre-specified) |
| Validation | 2010-01-01 to 2017-12-31 | Robustness grid evaluation, configuration screening (diagnostic only) |
| Test | 2018-01-01 to 2026-10-09 | Final holdout, promotion-gate decision |

**Point-in-time treatment**: momentum signals use only data available at
formation (1-day lag); the SPY 200-day SMA and VIX regime use only data up to
(and including) the prior day's close; the combined overlay uses only
realized-volatility and drawdown history up to the period start. No look-ahead
in any split.

### Walk-Forward Design (Matches Cycle 6 / C3 / C4 / C6)

- **Rolling window**: 10-year train, 12-month test, 6-month step
- **Purge**: 21 days between train end and test start
- **Embargo**: 21 days after test period end
- **Parameters**: Fixed across all folds (NO per-fold re-optimization)
- **Folds**: **24** (verified 2026-10-13 via
  `src/evaluation/walkforward.py:generate_walkforward_splits` from the
  2004-11-18 common-calendar start; the incumbent's 48-fold count does NOT
  apply because the 7-ETF common history starts at GLD inception 2004-11-18).
  Fold 1: train 2004-11-18 \u2192 2014-07-16, test 2014-08-15 \u2192 2015-08-03.
  Fold 24: train 2015-12-29 \u2192 2025-08-25, test 2025-09-24 \u2192 2026-09-10.
  The Cycle 19 script MUST assert the generated fold count equals 24.
- **Evaluation**: Each fold produces test-period Sharpe, annual return, max DD,
  trade count.

### Promotion Gates (ALL Must Pass to Advance to Simulation/Paper-Trading)

| Gate | Threshold | Measured On |
|------|-----------|-------------|
| Walk-forward mean OOS Sharpe | >= 0.9 | All folds, net of 3 bps costs |
| Positive fold rate | >= 50% | Count of folds with test Sharpe > 0 |
| Pooled OOS trades | > 100 | Sum of trades across all test folds |
| VIX-gate plateau | >= 2 of 4 vix_thresholds within 10% of baseline test Sharpe | Baseline `vix_exposure=0.5` |

### Multiple-Testing Control

- **Exact configuration count tracked**: 12 pre-specified combinations
  (4 x 3), with an explicit arithmetic assertion in the Cycle 19 script.
- **Deflated Sharpe Ratio**: computed via
  `src/evaluation/statistics.py:compute_dsr` using the true trial count N=12.
- **No test-set peeking**: configurations are NEVER selected based on
  test-period results. The baseline is pre-specified; the robustness grid is
  diagnostic (plateau + multiple-testing control) only.
- **PSR** (vs SR=0 and vs the 0.9 gate), **block-bootstrap Sharpe 95% CI**
  (1000 samples, 22-day block, seed=42), and **PBO/CSCV** via
  `src/evaluation/statistics.py:compute_pbo` over the 12-config grid
  (train=2004-2009 vs test=2018-2026).

### Reproduction Commands

```bash
# Cycle 19 will execute the baseline backtest and walk-forward
python3 research/run_cycle19.py

# Verification that the frozen config parses
python3 -c "import yaml; yaml.safe_load(open('config/macroregime_candidate_001.yaml'))"
```

---

## Evidence Artifacts (To Be Persisted in Cycle 19)

Per AGENTS.md "Evidence artifacts", Cycle 19 will persist:

- Data-source details, date ranges, frequency, asset universe, point-in-time
  treatment
- Missing-data handling (pre-inception cells are NaN and excluded from
  ranking; strategy history starts at the common-calendar start 2004-11-18)
- Integrity hashes/counts (row counts per symbol, date-range coverage,
  aligned Close frame content hash `7393bf74d806c40b`)
- Code revision (git SHA)
- Configurations tested (all 12, with parent/lineage to this hypothesis and
  to the incumbent tsmomentum_004)
- Trial count (12)
- Cost assumptions (3 bps per unit of weight change, prior-close execution,
  Close field)
- Baseline metrics (Sharpe, Sortino, CAGR, max DD, profit factor, turnover,
  exposure, trade count, tail risk)
- Benchmark-relative results (vs incumbent control arm and 1/N 7-ETF)
- Walk-forward folds (24), purge/embargo, VIX-gate plateau results
- Deflated Sharpe Ratio (N=12), PBO/CSCV, probabilistic Sharpe, block-bootstrap CIs
- Reproduction commands

---

## Decision Discipline (Pre-Committed)

Results will be labeled as exactly one of:

- **Credible candidate for further validation** \u2014 All promotion gates
  passed, robustness confirmed, net-of-cost performance credible
- **Exploratory signal** \u2014 Some promise but gates not fully cleared;
  warrants limited follow-up
- **Rejected/Failed** \u2014 Falsification condition met; documented and archived
- **Blocked by data/infrastructure** \u2014 Cannot form valid test with
  available data

**Post-gate guidance (pre-committed)**: If C5 passes all gates, the next
cycle would run a prospective simulation/paper-trading validation of the
VIX-overlay incumbent (extending the incumbent's existing paper-trading
track record), since C5 is an overlay-on-overlay and cannot stand alone.
If C5 is rejected, the next cycle moves to the next untested shortlist
candidate; per the Cycle 11 shortlist, all remaining candidates C7\u2013C10
are blocked by data and C2 is rejected, so the shortlist is exhausted and
the next cycle should either (a) extend the incumbent's prospective
paper-trading validation (gate: 63 days of track record), or (b) document
a new evidence-based shortlist per AGENTS.md Market Opportunity Search.

---

## References

- Bollerslev, T. (1986). "Generalized Autoregressive Conditional
  Heteroskedasticity". *Journal of Econometrics*, 31(3), 307-327.
- Mandelbrot, B. (1963). "The Variation of Certain Speculative Prices".
  *Journal of Business*, 36(4), 394-419.
- Cycle 5 regime analysis: `research/experiments/tsmomentum_regime_001.md`
- Cycle 5 regime filter test: `research/experiments/tsmomentum_regime_filter_001.md`
  (the VIX filter definition reused in C5's baseline: 50% exposure when
  VIX > 30)
- Cycle 6 walk-forward design: `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Cycle 11 Opportunity Shortlist: `research/reports/opportunity_shortlist.md`
  (C5 = 24/35, rank 6 of 10 \u2014 Exploratory signal)
- Data inventory: `research/reports/data_inventory.md` (^VIX index only, not
  tradeable)
- Incumbent hypothesis: `research/hypotheses/tsmomentum_004.md`
- Ranking Machinery: `src/features/momentum.py` (`compute_momentum`,
  `rank_assets`, `select_top_decile`, `build_weights`)
- Backtest engine: `src/backtest/engine.py`
- Evaluation stats: `src/evaluation/statistics.py` (`compute_dsr`, `compute_psr`,
  `compute_pbo`; seeded bootstrap, seed=42 convention)
- Walk-forward splits: `src/evaluation/walkforward.py` (`generate_walkforward_splits`)
- AGENTS.md: Research Documentation Standards; "Baseline before complexity";
  "Hypothesis first"; "Independent evaluation"; "Multiple-testing control"

---

*Created: 2026-10-13*
*Code revision: 052135d*
*Status: PRE-REGISTERED \u2014 No backtest executed. Cycle 19 will execute evaluation.*
