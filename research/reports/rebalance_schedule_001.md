# Month-End Rebalance Schedule in Shared Code (rebalance_schedule_001, Cycle 870)

## Summary

Two defects in the repository's shared engines were measured in Cycle 869 and are addressed
here with **one** implementation of the month-end schedule
(`src/backtest/rebalance.py`), exposed by an **opt-in** parameter on the backtest engine
(`run_backtest(..., rebalance_schedule="month_end")`).

* Defect 1 (fixed): `src/backtest/engine.py:run_backtest` accepted a `rebalance_freq` argument and
  never used it -- the universe was re-ranked **every session**. The engine therefore never
  executed the frozen month-end schedule of `config/sectorrotation_candidate_001.yaml`,
  `config/csmomentum_candidate_001.yaml` or `config/macroregime_candidate_001.yaml`.
* Defect 2 (**measured only, behaviour unchanged**): `src/simulation/engine.py:_apply_rebalance_schedule`
  ("M") uses the **calendar** `index.is_month_end` on a *trading* calendar.

No gate threshold, candidate configuration, cost model, universe, Sharpe convention or committed
artifact was changed. The default behaviour of `run_backtest` and the live paper-trading path are
unchanged: the incumbent's code-level decision stays **NO-GO** with the committed numbers.

## The shared definition (one implementation)

`src/backtest/rebalance.py` is the single source of truth for the month-end schedule:

1. the **month-end session** of a calendar month is the *last session of the session calendar* in
   that month (the aligned price index; it contains trading sessions only). A month whose last
   calendar day is a weekend rebalances on the **Friday** session, and a month whose last calendar
   day is a market holiday rebalances on the last session that actually happened;
2. the signal is formed **on** that session, so the positions become effective on the **next**
   session (`signal_lag_days: 1`) and are held unchanged until the next month-end signal;
3. a month whose signal is not defined (momentum warm-up) opens **no** position: positions are
   never back-filled and no position exists before the first valid signal.

The engine parameter is opt-in: `rebalance_schedule=None` (default) or `"daily"` keeps the
historical daily re-ranking; `"month_end"` (aliases: `"monthly"`, `"m"`) selects the schedule
above. An unknown schedule is a hard error (no silent fallback).

## Before / after on the frozen candidate's universe

Universe: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY; sample 1998-12-22 .. 2026-10-08
(6991 sessions); signal lookback 252, skip 21,
top_fraction 0.5; cost 3.0 bps round-trip.

| Path | Trade days | Annualized turnover | Canonical Sharpe | Max DD | Total return |
|---|---|---|---|---|---|
| A. default engine (daily re-rank, the defect) | 1088 | 16.4849x | 0.471379 | -48.4683% | 517.7625% |
| B. opt-in `rebalance_schedule="month_end"` (the fix) | 175 | 2.9961x | 0.472367 | -47.1578% | 524.5935% |
| C. independent research path (reference) | 175 | 2.9961x | 0.472367 | -47.1578% | 524.5935% |

The opt-in path reduces the rebalancing frequency by ~6.2x
(1088 -> 175 trade days) and the annualized turnover from
16.4849x to 2.9961x, with an essentially
unchanged Sharpe (0.471379 -> 0.472367): the defect was
a *cost and turnover* defect, not a return defect.

**Equivalence evidence:** `max |net_return(opt-in) - net_return(research path)| =
0.000e+00` (tolerance 1e-12) over 6991 sessions, and the two weight
matrices are bit-identical. The research path
(`research/sectorrotation_long_sample_feasibility.py`) now delegates its month-end construction to
the shared module, so there is a single implementation rather than two that have to be kept in sync.

**Rebalance calendar actually used:** 321 month-end rebalances; the first signal is
formed on 2000-01-31 and becomes effective on 2000-02-01; the
last is formed on 2026-09-30 and effective on 2026-10-01.

## The simulation engine's "M" branch: measured, deliberately unchanged

`src/simulation/engine.py:_apply_rebalance_schedule` keeps the target weights only on the rows where
`index.is_month_end` is True and forward-fills the rest. `is_month_end` is a **calendar** predicate,
so on a trading calendar it fires only when the last *calendar* day of the month is itself a
trading session.

Measured on the same universe and sample:

* it fires on **235 of 6991 sessions**;
* **235 of 335 months** contain such a session -- in those
  months the rebalance happens on the month's last session, but on the *previous* session's signal
  (no extra lag), i.e. one session earlier than the shared schedule;
* in the remaining **100 months (29.9%)**
  there is no such session at all (the last calendar day was a weekend or a market holiday), so the
  branch carries the **previous month's weights through the whole month**;
* applied to the same lagged daily signal weights, it differs from the shared implementation on
  **1872 of 6991 sessions** (max row-wise weight difference
  1.0000), and it produces 137 trade days /
  2.4400x turnover / Sharpe 0.462708
  (shared: 175 / 2.9961x /
  0.472367);
* the two schedules change the portfolio on **0 common sessions**
  (137 "M"-branch sessions vs 175 shared-schedule
  sessions): the "M" branch rebalances **one session earlier** -- on the month's last session itself,
  using the previous session's signal -- while the shared schedule forms the signal on the month's
  last session and applies it from the next one. The two calendars therefore never rebalance on the
  same session.

**This branch was left behaviourally unchanged.** Its live path is `"daily"`
(`config/simulation_candidate_001.yaml`: `execution.rebalance_schedule: "daily"`), so no paper-trading
artifact can move; the difference above is the measured size of the defect should the branch ever be
selected. Adopting the shared implementation there is a separate, explicitly scoped change.

## The incumbent path is untouched

`run_backtest` was called with its default arguments on the incumbent's universe
(2004-11-18 .. 2026-10-16, 8487 sessions): canonical Sharpe
0.5646255767978904 (committed 0.5646255767978904), max drawdown -0.6224126346564325 (committed
-0.6224126346564325), PSR 2.2219753177036448e-08 (committed 2.2219753177036448e-08). The code-level decision
stays **NO-GO** with failed gates `['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown', 'psr']`.

## Falsification conditions

This cycle's conclusions are wrong if any of the following holds:

1. the opt-in engine path does not reproduce the config-faithful research path to 1e-12
   (it does: 0.000e+00);
2. the default path of `run_backtest` changes any incumbent number (it does not: the three values
   above are bit-identical to the committed ones);
3. a month-end session is not a session of the aligned price calendar, or a signal is not effective
   from the session after its month-end session;
4. a position exists before the first valid signal;
5. the raw cache or any committed artifact under `config/`, `data/` or
   `research/reports/promotion_feasibility_backtest_001.md` changes.

## Checks

| Check | Result | Detail |
|---|---|---|
| `opt_in_matches_config_faithful_research_path` | PASS | max |engine_opt_in - research_path| = 0.000e+00 (tolerance 1e-12) over 6991 sessions. |
| `opt_in_weights_are_identical_to_research_path` | PASS | the opt-in engine weights are bit-identical to the research path's weights. |
| `opt_in_reproduces_long_sample_sharpe` | PASS | opt-in canonical Sharpe 0.472367 (Cycle 869 published 0.472367). |
| `default_path_is_the_daily_rerank_defect` | PASS | default path: 1088 trade days / 16.4849x turnover; opt-in month-end path: 175 trade days / 2.9961x. |
| `month_end_is_the_last_session_of_the_month` | PASS | 335 month-end sessions for 335 calendar months; every one of them is the last session of its month. |
| `no_rebalance_on_a_non_session` | PASS | every month-end session is a session of the aligned price calendar (no weekend, no calendar-only date). |
| `signal_lag_is_one_session` | PASS | the first signal is formed on 2000-01-31 and becomes effective on 2000-02-01 (the next session). |
| `no_position_before_the_first_valid_signal` | PASS | the first valid momentum cross-section is 2000-01-24; no position exists before 2000-02-01. |
| `simulation_m_branch_is_calendar_based` | PASS | the simulation 'M' branch fires on 235 of 6991 sessions and has no rebalance at all in 100 of 335 months. |
| `simulation_m_never_rebalances_on_the_same_session_as_the_shared_schedule` | PASS | the two schedules change the portfolio on 0 common sessions (137 'M' branch sessions vs 175 shared-schedule sessions): the 'M' branch rebalances one session earlier, on the month's last session itself. |
| `incumbent_default_path_unchanged` | PASS | incumbent default path: canonical Sharpe 0.5646255767978904 (committed 0.5646255767978904), max DD -0.6224126346564325 (committed -0.6224126346564325), PSR 2.2219753177036448e-08 (committed 2.2219753177036448e-08). |
| `raw_cache_unchanged` | PASS | the raw cache is byte-identical. |

## Reproduction

```bash
python research/rebalance_schedule_audit.py     # this report; OVERALL: PASS
python research/sectorrotation_long_sample_feasibility.py
python research/promotion_feasibility_backtest.py
python -m pytest -q
git status --porcelain data/                    # empty
```

## Provenance

- Data: committed raw cache `data/raw/*.parquet` (read-only; SHA-256 byte-identical before and
  after the run).
- Source files that define the schedule (SHA-256):
  - `src/backtest/rebalance.py`: `445b7b1aaf2c0e427174f94d859a342d5cf12a5eeffcb1121516dc75717a3820`
  - `src/backtest/engine.py`: `66d66a0364decfd4c0c64d8cf38388747dc0bc15926c27b008b4379462630c99`
- Gate thresholds, candidate configurations, cost model and Sharpe convention: unchanged.
