# Next Agent Task: Cycle 870 — make the frozen month-end rebalance schedule executable in shared code

## Context
- Cycle 869 ran the long-sample feasibility backtest of the frozen `sectorrotation_001` candidate
  and **rejected it** on its own pre-registered falsification condition (walk-forward mean OOS
  Sharpe 0.847243 < 0.9; long-sample canonical Sharpe 0.472367; repository gate table NO-GO).
  Evidence: `research/reports/sectorrotation_long_sample_feasibility_001.md`,
  `research/experiments/sectorrotation_long_sample_feasibility_001.md`.
- Cycle 869 also measured **two defects in the shared engines** (evidence: the report's §2 and
  §10). No repository code path currently executes the frozen candidate configurations as frozen:
  1. `src/backtest/engine.py:run_backtest` accepts a `rebalance_freq` argument and **never uses
     it**: `build_weights` re-ranks the universe every session. Measured on the 9-sector universe
     (1998-12-22..2026-10-08): engine path 1,088 trade days / 16.4849x annualized turnover /
     Sharpe 0.471379 vs config-faithful month-end path 175 trade days / 2.9961x / Sharpe 0.472367.
     The frozen month-end schedule appears in `config/sectorrotation_candidate_001.yaml`,
     `config/csmomentum_candidate_001.yaml` and `config/macroregime_candidate_001.yaml`.
  2. `src/simulation/engine.py:_apply_rebalance_schedule` ("M") uses the **calendar**
     `index.is_month_end` on a *trading* calendar: it is True on only 235 of the 6,991 sector
     sessions and equals the month's last trading session in **0 of 335** months, so it rebalances
     on the wrong session and carries the previous month's weights through ~30% of months.
- The live paper-trading path is unaffected by both defects (`config/simulation_candidate_001.yaml`
  uses `rebalance_schedule: "daily"`), and the incumbent's recorded artifacts must not move.

## Objective
Implement **one** correct month-end rebalance schedule in shared code — month-end = the last
*trading* session of the calendar month, signal formed on that session, positions effective from
the next session — and make it executable from the backtest engine behind an **explicit opt-in**
parameter, without changing any existing default behavior or artifact.

## Acceptance Criteria
1. `src/backtest/engine.py` gains an opt-in rebalance-schedule parameter whose **default
   preserves today's behavior**, so `research/promotion_feasibility_backtest.py` still reproduces
   the committed incumbent numbers exactly (canonical Sharpe 0.5646255767978904, max DD
   -0.6224126346564325, PSR 2.2219753177036448e-08, decision NO-GO, failed gates
   `['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown', 'psr']`).
2. With the opt-in enabled, the engine reproduces the config-faithful monthly path of
   `research/sectorrotation_long_sample_feasibility.py` on the 9-sector universe
   (1998-12-22..2026-10-08) to `max |net_return - research path| <= 1e-12`.
3. Deterministic tests pin: (a) a month whose last calendar day is a weekend rebalances on the
   Friday session; (b) the 1-day lag (a signal formed on the month-end session is held from the
   next session); (c) no position exists before the first valid signal; (d) the incumbent
   artifacts of criterion 1 are unchanged.
4. `research/reports/rebalance_schedule_001.md` documents both defects, the fix, the before/after
   numbers, the falsification conditions and the explicit statement that the simulation engine's
   "M" branch was left behaviorally unchanged (its live path is "daily") and how much it differs
   from the shared implementation.
5. `python -m pytest -q` passes, `git status --porcelain data/` is empty, `config/` is unchanged,
   and the incumbent's code-level decision stays **NO-GO**.

## Validation
```
python -m pytest -q
python research/sectorrotation_long_sample_feasibility.py   # must still print OVERALL: PASS and Sharpe 0.472367
python research/promotion_feasibility_backtest.py             # incumbent artifacts must be unchanged
git status --porcelain data/                                 # empty
```

## Scope boundaries
- No change to any gate threshold, candidate configuration, cost model, universe or Sharpe
  convention; no change to the default behavior of `run_backtest` or of the live paper-trading
  path; no write to `data/`.
- Do not re-open the `sectorrotation_001` verdict in this cycle (rejected on its pre-registered
  condition; its long-sample excess over 1/N is +0.0156 pp annualized at 3.0x turnover).
- Known limitation, out of scope here: the 9 sector ETFs are not covered by
  `research/refresh_raw_cache.py` and are 6 sessions stale (2026-10-08 vs the core cache's
  2026-10-16); a later cycle may extend the refresh scope.
