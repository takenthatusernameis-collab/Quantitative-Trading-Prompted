# Hypothesis: Commodity/Rate Futures Basis and Roll Yield Candidate (`futuresbasis_001`)

## Version History

- v001 (`futuresbasis_001`, 2026-10-19): initial pre-registered hypothesis for
  Cycle 883. Parent: shortlist rank 7 in `research/reports/opportunity_shortlist.md`.
  Code revision at registration: `170a1ad` (HEAD of Cycle 882).
- v002 (data block, 2026-10-19, post-data-readiness, disclosure only): the
  front-month futures series *is* cached (`data/raw/{CL-F,NG-F,GC-F,ZB-F}.parquet`),
  but **no point-in-time roll can be constructed from the available data**
  (no individual contract leg prices, all probed legs 404 / delisted). The
  roll date, roll price and roll cost are therefore unobservable, and no
  honest roll-yield backtest can be executed this cycle. The candidate is
  recorded as **Blocked by data/infrastructure**. No threshold, gate,
  falsification condition or configuration was changed by this block.
  **Pre-registered BEFORE any backtest was executed (no backtest exists yet).**
- v003 (Cycle 884, data-fact correction, disclosure only): the v002 claim that
  the **roll dates** are undetectable from the cached series is **falsified and
  corrected**. The cached series carry the front contract's `Volume` column, and
  the expiring contract's volume run-off followed by the new front's volume
  recovery is a detectable signature: 127/125/72/62 roll events for
  CL/NG/GC/ZB with modal spacings of 29/30/63/91 days, matching each product's
  contract cycle, and the one externally verified roll (2026-09-23) is detected
  in the committed cache. The **roll prices** and the **roll cost actually
  paid** remain unobservable (nine source classes probed; no source serves
  individual contract legs), so the candidate stays **Blocked by
  data/infrastructure** on a narrower, *price*-only block. **No mechanism,
  threshold, gate, falsification condition, cost-model value or configuration
  was changed by v003**, and no backtest exists yet.

---

## Mechanism Description

The shortlist rank 7 candidate is **commodity/rate futures basis and roll yield**.

When a futures curve is in **backwardation** (near contract cheaper than the deferred contract), rolling the front-month contract forward each cycle delivers a positive **roll yield**: the position converges toward the spot price as expiration approaches, earning basis compensation. When the curve is in **contango**, rolling delivers a negative roll (a cost). The structural sources are storage costs, convenience yield, and hedging pressure; the effect is regime-dependent and can be negative for sustained periods.

The repository's opportunity inventory records this family at shortlist rank 7 with a documented structural mechanism (roll yield, basis convergence, forced flows) but no cached futures series and an undocumented continuous-contract roll methodology (Cycle 1 verification). This hypothesis pre-registers the candidate so the data gate and the cost test are applied in order.

## Expected Direction and Magnitude (pre-specified prior)

| Metric | Prior (this hypothesis) | Note |
|---|---|---|
| Gross annualized roll-yield + spot return of a long front-month position | regime-dependent; **not signed** | Roll yield can be positive (backwardation) or negative (contango) for years; **not** a result |
| Expected direction | two-sided / regime-dependent | No directional prior; the mechanism pays basis compensation only in backwardation regimes |
| Net annualized return after roll cost + 3 bp/unit model cost | regime-dependent | Cannot be signed until a point-in-time roll is priced |
| Annualized turnover | ~12-26x | One full round-trip (sell front, buy next) per roll; rolls occur roughly monthly (~12/yr), each round-trip = 2 units of turnover |
| Falsification gate | net walk-forward mean OOS Sharpe < 0.9 | Same promotion gate as every other candidate in the repository |

Direction: **not pre-specified** (the mechanism is regime-dependent). This distinguishes it from directional candidates; the test is whether a documented, cost-paid roll construction covers its own turnover cost plus the 3 bp/unit model.

## Holding Horizon

The baseline holds the front-month futures contract continuously and rolls into the next contract at the documented roll date. Position is held at the front contract's close up to and including the roll date, then switched to the next contract at the roll date's close. No intraday trading; no parameter search; no optimisation.

## Asset Universe

Shortlist rank 7's stated universe: **CL=F** (crude oil), **NG=F** (natural gas), **GC=F** (gold), **ZB=F** (US Treasury bond front month). For Cycle 883 the data-readiness probe caches all four continuous front-month series; CL (crude) is the most liquid representative and is the reference series for the block record.

**No in-sample asset selection; no other symbol may enter the candidate.**
Cached range per the integrity record: 2015-01-02 .. 2026-10-15 (2,964–2,965 sessions each, complete, no missing closes, no duplicate dates).

## Data Integrity (pre-registered expectation, verified before execution)

| Symbol | Stored as | Rows | Start | End | Missing `Close` | Duplicate dates |
|---|---|---:|---|---|---:|---:|
| `CL=F` | `data/raw/CL-F.parquet` | 2,964 | 2015-01-02 | 2026-10-15 | 0 | 0 |
| `NG=F` | `data/raw/NG-F.parquet` | 2,965 | 2015-01-02 | 2026-10-15 | 0 | 0 |
| `GC=F` | `data/raw/GC-F.parquet` | 2,964 | 2015-01-02 | 2026-10-15 | 0 | 0 |
| `ZB=F` | `data/raw/ZB-F.parquet` | 2,964 | 2015-01-02 | 2026-10-15 | 0 | 0 |

- **Source**: Yahoo Finance via `src/data/yfinance_fetcher.py` (`auto_adjust=False`), `group_by='ticker'`, raw OHLCV. No forward-looking calls.
- **Point-in-time roll requirement**: to pay the roll at observable prices, the candidate needs **individual contract legs** (front month and next contract) with observable daily closes on both sides of the roll. Cycle 883 probed eleven individual crude legs (`CLZ24` .. `CLZ25`) through yfinance: **all returned 404 "Quote not found" / "possibly delisted"**. Cycle 884 probed nine further source classes (Yahoo per-contract suffix symbols, Nasdaq Data Link CHRIS `CL1`/`CL2`, the CME settlement service, WSJ, Barchart, Stooq, FT Markets, Investing.com, Yahoo symbol search): **none serves individual contract legs**; the currently listed Yahoo per-contract symbols return five-year series (chain aliases, not a contract's own life) and the expired ones still 404.
- **Roll dates**: **observable** (corrected in v003). The cached series' `Volume` column is the *front contract's* volume, and at a roll the contract behind the series changes, so the volume identity changes with it. The expiring contract's run-off followed by the new front's volume recovery is a deterministic, point-in-time signature (`research/futures_roll_visibility.py`): 127/125/72/62 events for CL/NG/GC/ZB, modal spacings 29/30/63/91 days, matching each product's monthly / bi-monthly / quarterly contract cycle. The one roll verified independently against Yahoo's per-contract volume and price series (2026-09-23) is detected in the committed cache. The detector's recall is imperfect and it is a visibility diagnostic, not an exhaustive roll calendar.
- **Roll prices / roll spread**: **unobservable**. The continuous series is a single spliced front-month price; the expiring contract's close on the roll date is not in it, and no source in scope serves the individual legs.
- **Conclusion**: a point-in-time front-month roll that pays the roll at observable prices **still cannot be constructed** (the *price* block survives even though the *date* block is lifted). A backtest on the spliced continuous series would embed the roll at an unobservable price and would misstate the roll yield — the exact trap this gate is designed to catch.

## Features and Data Sources

| Feature | Specification | Source |
|---|---|---|
| Front-month price | Daily continuous front-month Close | `data/raw/{CL-F,NG-F,GC-F,ZB-F}.parquet` (Yahoo Finance, `auto_adjust=False`, cached) |
| Roll rule | Point-in-time switch from front to next contract at the documented roll date | **Roll dates available** from the cached volume signature (`research/futures_roll_visibility.py`); the *documented roll rule* (which contract is front on which date) is still not published by the source |
| Roll cost | (next contract close − front contract close) / front close at the roll | **Not available** — the leg closes are unobservable |
| Signal | Roll-yield carry: long front-month when backwardation is expected | **Not computable** — no term structure, no leg prices |
| Point-in-time | Roll executed only on information available at the roll date's close | Roll **dates** detectable point-in-time (v003 volume signature); the leg **prices** at the roll date are not observable |

**This hypothesis cannot be executed as a backtest until the roll block is resolved.** The data gate (integrity record `research/reports/futures_basis_data_integrity_001.md`) records the block and what would unblock it.

## Entry/Exit Rules (pre-specified, conditional on the block being resolved)

1. **Long the front-month contract** (the contract nearest expiration that is still the front month at the prior close).
2. **Roll**: on the roll date, sell the front contract at its close and buy the next contract at its close — both prices observable, so the roll cost paid is `(Close_next[t] − Close_front[t]) / Close_front[t]`.
3. **Position sizing**: gross exposure 1.0 (one front-month contract notional), long-only, no leverage.
4. **Roll frequency**: determined by the detected roll dates (roughly monthly), not by a parameter grid.
5. **Costs applied**: the roll spread actually paid at observable closes (market cost), plus the repository's 3 bp per unit of weight change on the round-trip turnover (2 units per roll: sell front + buy next) — `config/settings.yaml` (1 bp commission + 2 bp slippage).
6. **No volatility targeting, drawdown control, regime filter, or parameter optimisation** (per AGENTS.md baseline principle).

## Benchmark

Two benchmarks, evaluated on identical date ranges, cost model and (once resolvable) walk-forward folds:

1. **Spot/roll decomposition reference**: the close-to-close return of the continuous front-month series **minus** the roll cost actually paid. This isolates pure roll yield from spot price change.
2. **Passive cash / flat**: a zero-exposure baseline (0% return), because the roll-yield mechanism is a carry trade, not directional beta. A credible roll-yield candidate must earn a positive net roll after costs, not merely ride spot appreciation.

The benchmark must be costed identically (turnover of its own rebalancing) so the comparison is like-for-like.

## Known Confounders

1. **Regime dependence**: roll yield is positive in backwardation and negative in contango; sustained contango regimes can produce negative returns for years. No directional prior is defensible.
2. **Spliced-series trap**: a backtest on the continuous front-month series without an observable roll understates roll cost and misstates roll yield. This hypothesis explicitly refuses that construction.
3. **Flat cost model**: no bid-ask spread, market impact, margin, borrow or funding model beyond the 3 bp/unit per-unit cost; the actual executed roll cost (commission, slippage, spread crossing) may exceed the model.
4. **Contract specifications**: point value, tick size, margin and delivery differ across CL/NG/GC/ZB; a single per-unit cost model is an approximation.
5. **Roll-date ambiguity**: the roll *dates* are detectable from the cached volume signature (v003), but the *roll rule* the source uses is undocumented, the detector's recall is imperfect, and the leg prices on the roll date are unobservable — so the roll cost, not the roll date, is the binding constraint. A calendar rule would need first-notice-day / expiration data external to the cache.
6. **Multiple-testing risk**: N = 1 mechanism (roll carry), no parameter grid; if extended to multiple contracts or roll rules, control via Deflated Sharpe Ratio / block bootstrap.
7. **Limited power**: ~11 years of monthly roll observations (~120–130 rolls) per contract; adequate for a directional carry test only if the effect is stable across regimes.
8. **No tradeable spot basis**: no spot series is cached, so the spot–futures basis itself cannot be computed; only roll yield on the front-month contract is addressable.

## Falsification Condition (pre-specified)

The candidate is **Rejected/Failed on cost** if, once a point-in-time roll is constructible:

1. The roll-adjusted net walk-forward mean OOS Sharpe **< 0.9** (repository promotion gate), or
2. The net annualized return does **not** cover the roll cost actually paid plus the 3 bp/unit model cost on the candidate's own window, or
3. The net walk-forward Sharpe does **not** exceed the same-fold passive benchmark's.

The candidate is **Blocked by data/infrastructure** (this cycle's actual decision) if the point-in-time roll cannot be constructed from available data — the roll cost cannot be quantified, so no valid cost test exists. A negative result recorded with its numbers is a successful cycle; a spliced series passed off as point-in-time is not.

## Cost Model Assumptions

| Component | Value | Source |
|---|---|---|
| Commission | 1.0 bp per unit of weight change | `config/settings.yaml: backtest.default_commission_bps` |
| Slippage | 2.0 bp per unit of weight change | `config/settings.yaml: backtest.default_slippage_bps` |
| Total per-unit cost | 3.0 bp per unit | `src/backtest/engine.py: get_cost_params()` |
| Roll cost | paid at observable closes (`Close_next − Close_front`) | **not available this cycle** |
| Turnover per roll | 2 units (sell front + buy next) | this hypothesis; ~12 rolls/yr -> ~24 units/yr baseline |
| Sensitivity rows | 5.0 bp and 10.0 bp per unit | cost screen convention |
| Funding / borrow / margin | not modelled | disclosed confounder #3 |
| Dividends | n/a (futures; no dividend on the contract) | — |
| Market impact / latency | not modelled | flat per-unit cost only |

## Walk-Forward Design (conditional on block resolution)

`src/evaluation/walkforward.py: generate_walkforward_splits` with
`train_years=10.0`, `test_months=12.0`, `step_months=6.0`, `purge_days=21`,
`embargo_days=21`. The baseline has **no fitted parameter**. Fold count and first/last fold are asserted, not assumed.

## Promotion Gates (pre-registered, repository convention)

| Gate | Threshold | Statistic |
|---|---|---|
| WF mean OOS Sharpe | >= 0.9 | mean of per-fold test Sharpes |
| Positive fold rate | >= 50% | share of folds with test Sharpe > 0 |
| Pooled OOS trades | > 100 | sum of per-fold trade counts |

No gate threshold is changed by this hypothesis. The candidate is currently **Blocked by data/infrastructure**; no gate is evaluated this cycle.

---
*The cost-admissibility screen (`research/cost_admissibility_screen.py`) is NOT extended to this candidate, because no honest gross-return + turnover pair can be built without the roll *price*: the roll dates are observable (v003) but the two leg closes at a roll are not, and extending the screen to a spliced series would violate the data gate. See `research/experiments/futuresbasis_001.md` for the decision record and `research/reports/futures_roll_visibility_001.md` for the roll-date measurement.*
