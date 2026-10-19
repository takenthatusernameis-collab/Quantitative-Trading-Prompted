# Experiment: Shared Month-End Rebalance Schedule (rebalance_schedule_001, Cycle 870)

## Hypothesis reference

This is not a strategy experiment: it is an **execution-engine** experiment. It closes the two
shared-engine defects measured in Cycle 869
(`research/reports/sectorrotation_long_sample_feasibility_001.md`, §2 and §10):

1. `src/backtest/engine.py:run_backtest` accepts a `rebalance_freq` argument and never uses it --
   the universe is re-ranked **every session**, so the frozen month-end schedule of
   `config/sectorrotation_candidate_001.yaml`, `config/csmomentum_candidate_001.yaml` and
   `config/macroregime_candidate_001.yaml` was never executed by the repository's own backtest path;
2. `src/simulation/engine.py:_apply_rebalance_schedule` ("M") uses the **calendar**
   `index.is_month_end` on a *trading* calendar.

The frozen candidate configurations are unchanged by this cycle.

## Objective

Implement **one** correct month-end rebalance schedule in shared code, make it executable from the
backtest engine behind an **explicit opt-in** parameter, and prove that

* the default behaviour (and therefore every committed artifact) does not change,
* the opt-in path reproduces the config-faithful research path exactly,
* the size of the remaining simulation-engine defect is measured, not assumed.

## Data used

- **Source**: committed raw cache `data/raw/*.parquet` (Yahoo Finance via yfinance, cached). No
  network access; nothing written under `data/`.
- **Date range / frequency / universe**: the frozen candidate's own sample -- 1998-12-22 ..
  2026-10-08, 6,991 sessions, 9 GICS sector ETFs (`XLB XLE XLF XLI XLK XLP XLU XLV XLY`), EOD
  `Close`. The incumbent's own sample (7 assets, 2004-11-18 .. 2026-10-16, 8,487 sessions) is used
  for the "nothing moved" check.
- **Point-in-time treatment**: momentum = `Close_{t-21} / Close_{t-273} - 1` ranked cross-sectionally,
  top 50% equal-weight; the month-end signal is formed **on** the last session of the calendar month
  and the positions are effective from the **next** session (`signal_lag_days: 1`).
- **Missing data**: 0 NaN in every cached `Close` series; the aligned frame is 6,991 x 9 and
  reproduces the pre-registered content hash `5e2d48e6579a53cd...`.
- **Costs**: 1 bps commission + 2 bps slippage = 3 bps round-trip (`config/settings.yaml`, equal to
  the frozen candidate cost model), charged on absolute weight change.
- **Integrity**: SHA-256 of the 9 sector parquet files is byte-identical before and after the run
  (`git status --porcelain data/` empty).

## Configuration

- New shared module `src/backtest/rebalance.py`:
  - `month_end_sessions(index)` -- the last session of every calendar month;
  - `build_month_end_weights(mask)` -- equal-weight month-end segments, 1-session lag, no back-fill;
  - `normalize_schedule(name)` -- canonical schedule name; an unknown schedule is a hard error.
- New opt-in engine parameter `run_backtest(..., rebalance_schedule=None)`:
  `None` / `"daily"` (default, unchanged daily re-ranking) or `"month_end"` / `"monthly"`.
- `research/sectorrotation_long_sample_feasibility.py` now **delegates** its month-end construction
  to the shared module (one implementation instead of two that must be kept in sync); its published
  numbers are unchanged (`max |net_return - research path| = 0.000e+00`).
- `rebalance_freq` is kept as a **descriptive** argument (it is recorded in the experiment metadata
  and never changed a computation) and is documented as *not* being the schedule selector.
- The simulation engine's `"M"` branch is **unchanged**; its live path is `"daily"`.
- **Trials**: 3 execution paths (default / opt-in / simulation-"M"-style) x 1 universe + 1 incumbent
  check. No parameter grid, no tuning, no re-fit.

## Splits

None: this cycle measures an execution path, not a strategy. The measured sample is the frozen
candidate's whole available history; the incumbent check uses the incumbent's whole available
history.

## Results

### Execution paths on the frozen candidate's universe

| Path | Trade days | Annualized turnover | Canonical Sharpe | Max DD |
|---|---|---|---|---|
| default engine (daily re-rank, the defect) | 1,088 | 16.4849x | 0.471379 | -48.4683% |
| opt-in `rebalance_schedule="month_end"` (the fix) | 175 | 2.9961x | 0.472367 | -47.1578% |
| config-faithful research path (reference) | 175 | 2.9961x | 0.472367 | -47.1578% |

`max |net_return(opt-in) - net_return(research path)| = 0.000e+00` (tolerance 1e-12); the two weight
matrices are bit-identical. The defect was a **cost/turnover** defect, not a return defect: the
Sharpe is essentially unchanged (0.471379 -> 0.472367) while the annualized turnover falls 5.5x
(16.4849x -> 2.9961x).

### The shared schedule

335 month-end sessions for 335 calendar months, each of them the last session of its month and a
session of the aligned price calendar; 321 month-end rebalances with a valid signal; the first signal
is formed on 2000-01-31 and is effective from 2000-02-01; no position exists before that date.

### The simulation engine's "M" branch (measured, deliberately unchanged)

It fires on 235 of 6,991 sessions and has **no rebalance at all in 100 of the 335 months (29.9%)**,
whose last calendar day was a weekend or a market holiday -- in those months the branch carries the
previous month's weights through the whole month. Where it does fire, it rebalances **one session
earlier** than the shared schedule (on the month's last session itself, using the previous
session's signal), so the two calendars change the portfolio on **0 common sessions**. Applied to
the same lagged daily signal weights it differs from the shared implementation on 1,872 of 6,991
sessions and produces 137 trade days / 2.4400x turnover / Sharpe 0.462708 (shared: 175 / 2.9961x /
0.472367). Its live path is `"daily"` (`config/simulation_candidate_001.yaml`), so no paper-trading
artifact can move.

### The incumbent did not move

Default-argument `run_backtest` on the incumbent's universe: canonical Sharpe
**0.5646255767978904** (committed value identical), max drawdown **-0.6224126346564325**, PSR
**2.2219753177036448e-08**; the code-level decision stays **NO-GO** with failed gates
`['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown', 'psr']`.

## Reproduction

```bash
python research/rebalance_schedule_audit.py          # OVERALL: PASS (12/12 checks)
python research/sectorrotation_long_sample_feasibility.py   # OVERALL: PASS, Sharpe 0.472367
python research/promotion_feasibility_backtest.py     # incumbent artifacts byte-identical
python -m pytest -q                                  # 82 passed
git status --porcelain data/                         # empty
```

## Classification

**Engineering fix, no new evidence about any strategy.** The candidate's verdict is unchanged
(`sectorrotation_001` remains rejected/failed on its own pre-registered condition, Cycle 869); the
incumbent's decision remains NO-GO; live deployment remains unsupported. The cycle's deliverable is
that the repository can now execute a frozen month-end schedule faithfully, and that the size of the
remaining defect is quantified.

## Known limitation carried forward

The 9 sector ETFs are not covered by `research/refresh_raw_cache.py` and are 6 sessions stale
(2026-10-08 vs the core cache's 2026-10-16). The two other frozen candidates that specify the same
month-end schedule -- `csmomentum_001` (`research/run_cycle13.py`) and `macroregime_001`
(`research/run_cycle19.py`) -- were evaluated with a **calendar-based** `is_month_end` schedule of
the same defective kind as the simulation engine's "M" branch; their published numbers therefore
need to be re-derived on the now-executable config-faithful path before any verdict is re-opened.
