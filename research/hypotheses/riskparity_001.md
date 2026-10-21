# Hypothesis: Risk-Balanced (Inverse-Volatility) Multi-Asset Allocation — `riskparity_001`

## Version history

- v001 (`riskparity_001`, Cycle 929): initial pre-registration. Written **before**
  any backtest execution of this candidate, following the Cycle 929 data-and-cost
  inventory (`research/reports/data_cost_inventory_002.md`). Parent evidence: the
  Cycle-912/929 inventories and the committed shortlist
  (`research/reports/opportunity_shortlist.md`).
  Code revision: see `git log -1`.

---

## Mechanism description

**Risk balancing by inverse volatility.** A multi-asset book whose capital is
allocated in proportion to each asset's inverse *realised* volatility gives every
asset an approximately equal contribution to portfolio risk, instead of an
approximately equal contribution to capital. The structural argument is two-part:

1. **Volatility clustering.** Volatility is persistent but not constant across
   regimes (Schwert's GARCH evidence; the volatility of an asset in a calm period
   is a poor estimate of its volatility in a stressed one). A capital-weighted
   multi-asset book concentrates risk in whichever assets happen to be calm, so
   its *risk* concentration moves with the market; a risk-balanced book does not.
2. **Non-uniform correlation structure.** The classic multi-asset ETF set mixes
   equity beta (SPY, QQQ, IWM, EFA, EEM) with genuinely different risk drivers
   (TLT: duration/rates; GLD: real rates and the dollar). Those diversifiers
   contribute little *capital* but a large share of *portfolio risk* when equity
   volatility rises, and a capital-weighted book therefore under-uses them
   exactly when they matter.

The mechanism contains **no directional prediction**: the rule never forecasts the
sign of a return. It is a *risk* mechanism, and it is therefore mechanistically
distinct from every candidate the repository has executed (all of which are
momentum/rank rules on price, plus the VIX regime gate and the crypto funding
carry).

**Why this candidate and not another.** The Cycle 929 inventory
(`research/reports/data_cost_inventory_002.md`) established what the cache can
support: 22 ETFs, 4 futures, 8 crypto files and one index, all with complete daily
history, and a cost model of 1 bp commission + 2 bp slippage per unit of weight
change. Every candidate in the committed shortlist that the cache can support
is a *momentum* rule, and the momentum family (time-series, cross-sectional,
sector, macro-regime, parameter variants) has been executed and rejected. The
only mechanism left in the cache that is (a) not a momentum rule, (b) fully
covered by committed daily data, (c) implementable long-only with the
repository's existing cost model (no borrow, no margin, no short leg, no
contract roll), and (d) cheap to run, is risk balancing. It is also the one
mechanism whose *cost* profile is structurally benign: a monthly rebalance of a
seven-asset book turns over a few units a year, so the candidate's net result
barely depends on the 3 bp/unit cost model — the exact opposite of the
high-turnover momentum candidates, whose edge is eaten by the cost model.

---

## Expected direction and magnitude (pre-specified prior)

The prior is deliberately conservative and is stated **before** execution. It is
a prior, not a result.

| Metric | Prior (this hypothesis) | Note |
|--------|--------------------------|------|
| Gross annualised return | 5%–9% | mostly the equity premium of the book |
| Net annualised return (3 bp/unit, ~4–8 units/yr of turnover) | 4.5%–8.5% | cost drag is small by construction |
| Net walk-forward mean OOS Sharpe | 0.50–0.90 | **prior probability of clearing the 0.9 gate is LOW (order 25%)** |
| Maximum drawdown (test period) | -15% to -25% | the book is long-only and equity-heavy |
| Annualised turnover | 3–8 units/yr | one rebalance a month, seven assets, weights move slowly |
| Positive walk-forward folds | 55%–75% | materially above 50% only in crisis regimes |

Direction: **positive but modest**. The mechanism is not expected to produce a
high Sharpe; it is expected to produce a *stable, low-turnover, equity-like*
return stream whose Sharpe is competitive with a capital-weighted book on a risk
basis, not on a return basis.

**Falsification (pre-stated).** The candidate is **Rejected/Failed** if any of
the following holds on the pre-registered evaluation:

1. walk-forward mean OOS Sharpe **< 0.9**; or
2. positive-fold rate **< 0.5**; or
3. pooled out-of-sample trades **<= 100**; or
4. the baseline's net Sharpe does **not exceed** the 1/N equal-weight benchmark
   on the same window (a "survival, not edge" outcome — the lesson of the
   cost-admissibility screen, which the repository applies to every candidate).

No parameter may be re-tuned after the baseline is executed. The grid in
"Pre-registered evaluation plan" is fixed in advance and the trial count is
declared in advance so that the Deflated Sharpe Ratio is computed against the
true number of trials.

---

## Holding horizon

- **Rebalance:** monthly, at the month end (the repository's
  `src/backtest/rebalance.py:build_month_end_weights` convention).
- **Signal lag:** 1 session. Weights are formed from data available up to and
  including the last session of the month and become effective on the next
  session.
- **Volatility estimate:** a trailing window of daily returns ending **one
  session before** the rebalance date (the estimate is *lagged*; see
  "Point-in-time treatment"). This is the single most important implementation
  detail: the Cycle-926 same-session volatility defect applies to any
  volatility-scaled rule, so the estimate is lagged from the start rather than
  corrected later.
- **No holding constraint:** positions are re-formed at every rebalance; there
  is no stop, no take-profit and no signal-driven exit. Exits are mechanical
  (the weight changes at the next rebalance).

---

## Asset universe

**Seven multi-asset ETFs, identical to the incumbent's universe**
(`tsmomentum_spytrend_001`): SPY, QQQ, IWM, TLT, GLD, EFA, EEM.

Rationale:

- **Mechanism isolation.** Using the same seven assets as the incumbent makes the
  comparison *mechanism versus mechanism* (risk balancing versus momentum
  selection) rather than universe versus universe. The incumbent's 1/N
  benchmark over exactly these seven assets is already published.
- **Point-in-time completeness (the Cycle 929 lesson).** The seven members did
  not exist simultaneously at the start of the sample: their first valid
  volatility estimates run from SPY (1994) to GLD (2005-11-10). The Cycle-929
  membership audit measured that the incumbent's published 48-fold mean mixes
  seven folds measured on an incomplete cross-section with 41 measured on the
  complete one, and that the two regimes have materially different statistics.
  **This candidate is pre-registered on the point-in-time-complete window
  only** — the evaluation starts on the first session on which all seven members
  carry a valid lagged volatility estimate. The published statistic is therefore
  homogeneous in the universe's membership, which is the defect the audit found.
- **No new data.** All seven series are in the committed cache with complete
  daily history, 0 missing prices and 0 duplicate timestamps (measured, Cycle
  929).

The universe is deliberately *not* widened in the baseline. A wider universe
(sector ETFs, DBC, VNQ) is a **post-gate** variation only, and only if the
baseline clears every gate; AGENTS.md's "baseline before complexity" applies.

---

## Features and data sources

| Feature | Definition | Source |
|---|---|---|
| `ret_i(t)` | daily simple return of member *i* | `data/raw/<SYMBOL>.parquet` (Close, UTC) |
| `vol_i(t)` | standard deviation of `ret_i` over the trailing `L` sessions ending at **t-1** | derived from the same cached Close series |
| `raw_w_i` | `1 / vol_i`, with `vol_i` floored at 1e-6 to avoid division by zero | derived |
| `w_i` | `raw_w_i` normalised to sum to 1, then per-asset **capped at 30%** and renormalised (the cap is applied iteratively, at most 5 iterations, and the result is stated, not approximated) | derived |
| `w_i^{final}` | `w_i` shifted by 1 session (effective on the next session) | derived |

Data provenance: the committed parquet cache only. The fetcher is **never**
called. Prices are the cached adjusted closes (dividends included), so the
return series is a total-return series and the ETF expense ratio is already
embedded in the price.

---

## Entry and exit rules

- **Entry:** a member is held in proportion to its lagged inverse volatility;
  no member is held if its volatility estimate is unavailable (in the
  pre-registered window this never happens — see the universe section).
- **Sizing:** weights are normalised to 1.0 in total. **No leverage, no
  shorting, no borrowing, no margin.** A member whose capped weight would fall
  below 0 is set to 0 (there is no floor below zero by construction).
- **Exit:** mechanical at the next month-end rebalance. There is no discretionary
  exit rule.
- **Cash:** none. The book is fully invested at all times, so the comparison
  with the 1/N benchmark is like-for-like. A cash-like T-bill leg is **not**
  part of the baseline.

---

## Benchmarks

1. **1/N equal weight** over the same seven assets on the same window and the
   same cost model (the incumbent's published benchmark; Sharpe 0.4716 on the
   incumbent's 2018-2026 test window).
2. **SPY buy-and-hold** on the same window (the "is it just equity beta"
   reference).
3. **The incumbent's published record** (`tsmomentum_spytrend_001`), quoted as a
   *reference only* — it is measured on a different path and a different
   window, and the comparison is reported as such.
4. **Correlation of the candidate's out-of-sample returns with the incumbent's**
   must be reported: a candidate that is a high-correlation duplicate of an
   already-rejected-or-credible candidate adds no diversification (AGENTS.md,
   "Incremental value").

---

## Known confounders

1. **Equity beta.** A long-only seven-asset book is an equity book. Part of any
   Sharpe it produces is the equity premium, not the risk-balancing mechanism.
   The 1/N benchmark controls for this; the excess Sharpe over 1/N is the
   mechanism's contribution and is reported as such.
2. **Regime luck.** The rule is by construction defensive: it de-risks after
   volatility has risen, which flatters the statistic in 2008, 2020 and 2022 and
   flattens it in calm bull markets. The pre-registered window contains both.
3. **Slow de-risking.** A 63-session volatility estimate moves slowly, so the
   book is *not* protected during a volatility spike itself; the protection
   arrives at the following rebalance. This is a real limitation of the
   mechanism, not an artefact of the implementation.
4. **Cap binding in calm periods.** Volatility is inversely related across
   assets, so a 30% cap binds exactly when volatility estimates are lowest and
   concentrates the book. The cap is a *risk* control whose side effect is
   concentration; the grid varies the cap precisely to measure this.
5. **Training-window regime.** The pre-registered 10-year training window
   (2005-11 → 2015) contains the global financial crisis, a regime the rule
   handles well; the later test windows are calmer. The published per-fold
   training Sharpe is reported so this is visible.
6. **Membership regime.** The pre-registration starts the evaluation on the
   point-in-time-complete window, so the candidate does not inherit the
   membership heterogeneity the Cycle-929 audit measured in the incumbent.
   This is a *deviation from the incumbent's published window* and is disclosed.
7. **Stale tail of the panel.** The seven files end on 2026-10-08/2026-10-19
   and the fetcher forward-fills a member's last close across the union
   calendar, so the final sessions carry stale prices for some members. The
   effect is confined to the last sessions of the sample.
8. **Multiple testing.** Nine configurations are pre-registered; the DSR/PSR
   must be computed at N = 9, not at a smaller N chosen after the fact.

---

## Cost model assumptions

| Component | Assumption | Basis |
|---|---|---|
| Commission | 1.0 bp per unit of weight change | `config/settings.yaml` (`default_commission_bps`), the repository's committed model |
| Slippage | 2.0 bp per unit of weight change | `config/settings.yaml` (`default_slippage_bps`) |
| Round trip | 3.0 bp per unit of weight change | the convention every committed candidate is costed on |
| Bid-ask spread | **not separately configured** | the repository's committed cost screen (Cycle 913) measures the break-even cost per unit from the cache; the candidate's turnover is low, so the break-even is far above 3 bp and the cost axis is not the binding constraint |
| Borrow / short-leg cost | none | the book is long-only |
| Roll cost | none | the instruments are ETFs, not futures; the futures series in the cache are not used |
| Market impact | assumed negligible | seven among the most liquid ETFs, monthly rebalance; **assumed, not measured** |
| Funding | none | spot ETFs |
| Dividends | included in the cached prices | the cached closes are adjusted |

**Cost-model sensitivity to be reported:** the net walk-forward mean OOS Sharpe
at 3 bp/unit and the break-even cost per unit at which the walk-forward mean
falls below 0.9 (measured on the fold-level path, as in the committed
break-even audit).

---

## Point-in-time treatment

- The volatility estimate at a rebalance date uses daily returns up to and
  including the **previous** session (lagged estimate).
- Weights are shifted by one session: a book formed on the last session of a
  month is effective from the next session.
- No forward fill of a member's price before its inception is used: the
  evaluation window starts when all seven members have a valid estimate.
- The walk-forward applies the repository's purge and embargo (21 days each).
- The final holdout is not inspected until the configuration is frozen.

---

## Pre-registered evaluation plan

| Item | Value |
|---|---|
| Evaluation start | the first session on which all seven members carry a valid lagged volatility estimate (GLD's first valid 63-session estimate ends 2005-11-10) |
| Evaluation end | the last session available in the committed cache |
| Splits | train 2005-11-10 → 2015-12-31; validation 2016-01-01 → 2020-12-31; test 2021-01-01 → end of cache (chronological, no overlap) |
| Walk-forward | 10-year train, 12-month test, 6-month step, 21-day purge, 21-day embargo, fixed parameters (no per-fold re-optimisation) |
| Baseline configuration | volatility lookback `L = 63`, per-asset cap `0.30` |
| Pre-registered grid | `L` in {21, 63, 126} x cap in {0.25, 0.30, 0.40} = **9 configurations**; baseline = (63, 0.30) |
| Declared trial count | **9** (used for the Deflated Sharpe Ratio) |
| Promotion gates | walk-forward mean OOS Sharpe >= 0.9; positive-fold rate >= 0.5; pooled out-of-sample trades > 100 (AGENTS.md, `config/promotion_gates.yaml`) |
| Robustness (post-gate only) | plateau: at least 2 of 3 volatility lookbacks within 10% of the baseline; DSR and PSR at N = 9 |
| Metrics to report | net Sharpe, Sortino, CAGR, max drawdown, profit factor, turnover, exposure, trade count, positive-fold rate, pooled trades, correlation with the 1/N benchmark and with the incumbent, break-even cost per unit |

**No post-hoc changes.** The configuration file frozen for the execution cycle
must be generated from this document without modification, and the number of
configurations actually evaluated must be reported (it may be fewer than nine
if a configuration cannot be run, and the trial count must then be the number
actually evaluated).

---

## Data readiness

| Criterion | Status | Evidence |
|---|---|---|
| Real historical observations | Ready | 7 daily series, 1993-2026, complete (Cycle 929 inventory: 0 missing prices, 0 duplicate timestamps) |
| Timestamps | Ready | UTC session index in the committed cache |
| Point-in-time universe membership | **Addressed by design** | the evaluation starts on the point-in-time-complete window (the membership defect the Cycle-929 audit measured in the incumbent) |
| Sufficient history | Ready for the pre-registered window | ~21 years, ~20 walk-forward folds |
| Independent provenance | Ready | the committed cache with per-file SHA-256 digests, re-verified every cycle |

## Scope boundaries of the execution cycle

- Evaluate the pre-registered baseline and grid; report the gates.
- Do not modify any committed record, gate, protocol or shortlist row.
- Do not call the fetcher, add a dependency, or place a trade.
- A rejected candidate is archived with its evidence; a candidate that clears
  every gate becomes a **Credible Candidate** and enters the promotion process
  (it is not promoted by this evaluation alone).
