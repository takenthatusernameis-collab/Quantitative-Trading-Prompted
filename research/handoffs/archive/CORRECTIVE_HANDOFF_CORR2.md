# Corrective invocation 2 handoff (2026-10-25T20:28Z)

## Durable project change made
- Regenerated the scratch-only upstream commodity fetch at
  `/tmp/scratchpad/commodity_fetch/` (`research/commodity_data_gate_fetch.py`,
  network, writes only outside the repository). This restored the input the
  Cycle-949 data-gate measurement depends on; it had been deleted, which was
  the direct cause of `tests/test_commodity_data_gate_001.py` failing.
- Repository tree is byte-identical to HEAD (`git diff --quiet` exit 0;
  `git status --porcelain` empty). No strategy, gate, threshold, config,
  candidate verdict, raw cache, workflow, or agent-count change was made.

## Verification (all ran and passed)
```
python research/commodity_data_gate_fetch.py
# DBC: rows=5212 2006-02-06..2026-10-23 -> /tmp/scratchpad/commodity_fetch/DBC.parquet
# BNO: rows=4125 2010-06-02..2026-10-23 ...
# UNG: rows=4912 2007-04-18..2026-10-23 ...
# GLD: rows=5517 2004-11-18..2026-10-23 ...
# provenance report: /tmp/scratchpad/commodity_fetch/commodity_fetch_report.json

python research/commodity_data_gate_001.py --no-report
# OVERALL: PASS; Common inception 2010-06-02 (deadline 2011-10-20);
# Folds: 12 (business-day), 11 (traded-session), required 10;
# Business days 4278 (required 3906); all 13 internal checks PASS.

python -m pytest tests/test_commodity_data_gate_001.py -q
# 15 passed in 3.61s
```
`data/` and `config/` are byte-identical before and after the gate run
(the tool's own `data_unchanged` / `config_unchanged` checks PASS), and the
committed records `research/reports/commoditytrend_001_data_gate.md` and
`research/experiments/commoditytrend_001_data_gate.md` were **not** rewritten
(`--no-report`).

## Remaining blocker (unresolved, requires a governance decision)
The full suite still has 2 real failures plus a hang, all caused by one
**committed repository inconsistency**, not by my change:

- `data/raw/DBC.parquet` was extended from 2026-10-08 to 2026-10-21 *after*
  the Cycle-13 `csmomentum_001` artifacts and published numbers were frozen.
  The frozen `data/processed/simulation_csmomentum_001.parquet` ends 2026-10-09
  with `gross_return` 0.004901444961695357, but recomputing that gross from the
  current DBC cache gives 0.005053372148849312 (DBC's 2026-10-09 close
  changed after the freeze).
- Reproducing the frozen artifacts **bit-exactly** (legacy net max abs diff
  1.4e-17, 0 of 8482 sessions differ; faithful-path test Sharpe 0.663540 vs
  published 0.6635) requires truncating DBC to 2026-10-08. That truncation
  conflicts with the Cycle-949 commoditytrend cache (DBC to 2026-10-21) and
  would itself dirty `data/`, so it is not safe to apply unilaterally.
- Regenerating the csmomentum artifacts from the current cache is *not* a fix:
  `run_cycle13.py` runs >280s (timed out), and its output would extend the
  simulation to 2026-10-23 with 33k NaNs, dirtying `data/` and failing the
  commodity gate's clean-tree invariant (`test_working_tree_under_data_and_config_is_clean`)
  without reproducing the published numbers.

Affected tests:
- `tests/test_cost_admissibility_screen.py::test_every_published_number_of_the_new_candidates_is_reproduced[csmomentum_001]`
- `tests/test_cost_admissibility_screen.py::test_csmomentum_reproduces_its_test_window_numbers`
- `tests/test_month_end_candidate_reaudit.py` (3 checks: `csmomentum_legacy_net_returns_match_committed_simulation`, `csmomentum_legacy_reproduces_published_calendar_record`, `csmomentum_001_experiment_001_is_the_daily_rerank_path`)
- Full-suite hang at `test_cost_admissibility_screen.py::test_the_incumbent_is_the_only_candidate_with_a_positive_gate_headroom` (~55s in isolation; it passes alone but the suite exceeds the run budget). Isolated run: 1 passed in 55.15s.

## Next distinct investigation needed
Resolve the committed DBC/cache inconsistency with an explicit, auditable
decision (one of: truncate DBC to 2026-10-08 and commit; or regenerate and
commit the csmomentum artifacts from a cache frozen at the published window
end 2026-10-09; or amend the published records with the new numbers and a
staleness note). This requires a commit, which is outside this agent's
authorization. Until then the repo must stay byte-identical to HEAD.

## Time gate status
The 2026-10-26 17:00 ET session-completeness gate for
`extend_paper_trading_state.py` is still pending (last processed session
2026-10-23). Unchanged and unfaked; `data/` clean.