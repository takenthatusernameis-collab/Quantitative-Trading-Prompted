# NEXT_AGENT_TASK — Corrective invocation 2 follow-on (2026-10-25T20:28Z)

## Context
Corrective invocation 2 regenerated the scratch-only upstream commodity fetch
(`/tmp/scratchpad/commodity_fetch/`, via `research/commodity_data_gate_fetch.py`,
network, writes only outside the repository) that the Cycle-949 data-gate
measurement depends on. It had been deleted, which was the direct cause of
`tests/test_commodity_data_gate_001.py` failing. The repository tree is now
byte-identical to HEAD (`git diff --quiet` exit 0). See
`CORRECTIVE_HANDOFF_CORR2.md` for the full diagnosis.

## Objective
Resolve the remaining blocker: a **committed repository inconsistency** between
`data/raw/DBC.parquet` (extended to 2026-10-21 after the Cycle-13 csmomentum
artifacts were frozen) and the frozen `data/processed/simulation_csmomentum_001.parquet`
(ends 2026-10-09). This is what breaks:

- `tests/test_cost_admissibility_screen.py::test_every_published_number_of_the_new_candidates_is_reproduced[csmomentum_001]`
- `tests/test_cost_admissibility_screen.py::test_csmomentum_reproduces_its_test_window_numbers`
- `tests/test_month_end_candidate_reaudit.py` (3 reproduction checks)
- the full-suite hang at `test_the_incumbent_is_the_only_candidate_with_a_positive_gate_headroom`

## Bounded task (pick exactly one, do not chain)
Choose **one** of the following auditable resolutions and execute only it:

1. **Truncate `data/raw/DBC.parquet` to 2026-10-08** (its freeze value) and
   commit. Verified to reproduce the frozen artifacts bit-exactly (legacy net
   max abs diff 1.4e-17 over 8482 sessions; faithful-path test Sharpe 0.663540
   vs published 0.6635). Then re-run `python -m pytest -q` and confirm the
   full suite passes.
2. **Freeze the cache at the published window end** (2026-10-09) and regenerate
   the csmomentum artifacts (`data/processed/simulation_csmomentum_001.parquet`,
   `trades_csmomentum_001.parquet`, `weights_csmomentum_001.parquet`) plus the
   affected `data/processed/*.parquet` that share the 8482-row window, then
   commit. `run_cycle13.py` is too slow (>280s); a bounded re-implementation
   of its `run_baseline` artifact-writing path is acceptable if it reproduces
   the published numbers to the records' own tolerances.
3. **Amend the published records** (`research/experiments/csmomentum_baseline_wf_001.md`,
   `research/experiments/csmomentum_001_experiment_001.md`,
   `research/reports/month_end_candidate_reaudit_001.md`,
   `research/reports/cost_admissibility_screen_001.md`) with the numbers
   recomputed from the current cache, plus an explicit staleness note naming
   the DBC extension as the cause, then commit.

Do **not** edit test tolerances, thresholds, or the published-number constants
to make tests pass — that is out of scope and would violate the pre-registration
and promotion-gate rules.

## Acceptance criteria
- Exactly one of the three resolutions above is committed (git commit required;
  this agent does not commit).
- `python -m pytest -q` passes in full (the full suite currently hangs at
  `test_the_incumbent_is_the_only_candidate_with_a_positive_gate_headroom`,
  ~55s in isolation, so allow adequate time).
- `git status --porcelain data/ config/` empty after the work.
- No strategy, gate, threshold, cost model, universe, candidate verdict, workflow,
  or agent-count change. Raw cache for the four commodity instruments (DBC, BNO,
  UNG, GLD) and the `/tmp/scratchpad/commodity_fetch/` scratch artifact untouched
  by this task.

## Validation commands
```
git status --porcelain
python -m pytest -q
git status --porcelain data/ config/
```

## Scope boundaries
- No commits unless explicitly requested by the human (this task describes the
  commit as the resolution, but the agent must not commit on its own).
- Do not alter or force the 2026-10-26 17:00 ET session-completeness gate for
  `extend_paper_trading_state.py`; that gate is still pending (last processed
  session 2026-10-23) and `data/` is clean.
- No new dependencies, services, paid data, scheduled jobs, or infrastructure.