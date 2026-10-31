# NEXT_AGENT_TASK — obtain repository owner decision on DBC/csmomentum cache inconsistency

## Context
As documented in README and previous corrective handoffs (CORR2/CORR132-CORR158), `data/raw/DBC.parquet` was extended from 2026-10-08 to 2026-10-21 after the Cycle-13 `csmomentum_001` artifacts were frozen. The frozen `data/processed/simulation_csmomentum_001.parquet` (ends 2026-10-09) no longer matches recomputation from the current DBC cache. This is a committed repository inconsistency requiring governance decision. The working tree is clean (`git status --porcelain data/ config/` empty). All individually tested components pass (cost admissibility screen: 40/40; month-end candidate re-audit: 17/17; commodity data gate tests pass).

## Objective
Obtain and record an explicit repository owner decision among (a), (b), or (c), commit it if data/config changes are part of the chosen option, then verify the full test suite passes.

## Options (from NEXT_AGENT_TASK)
(a) restore historical DBC to frozen cut-off (truncate DBC.parquet back to 2026-10-08)
(b) recreate csmomentum artifacts from frozen historical cache (regenerate weights_csmomentum_001.parquet, simulation_csmomentum_001.parquet, trades_csmomentum_001.parquet from cache frozen at published window end)
(c) amend published results with supersession record (update experiment/report artifacts to reflect new numbers with staleness/supersession note)

## Acceptance criteria
- Owner decision recorded (documented in commit message or dedicated governance record)
- `python -m pytest -q` exits 0 (full suite)
- `git status --porcelain data/ config/` empty

## Validation commands
```bash
python -m pytest -q  # may take long; see README notes
git status --porcelain data/ config/
```

## Scope boundaries
- Do not unilaterally choose among (a)/(b)/(c).
- Do not edit tests/thresholds/config/data without an explicit owner decision committing to one of the options.
- Preserve working tree cleanliness of data/ and config/ except as explicitly required by the owner-decided option.
- If the chosen option requires regenerating artifacts, ensure outputs are bit-exact as needed and do not break other gates (commodity gate clean-tree invariant must remain satisfied).

## Evidence
- README.md lines ~4, ~131+ (documents blocker and options)
- CORRECTIVE_HANDOFF_CORR2.md, CORRECTIVE_HANDOFF_CORR132.md, CORRECTIVE_HANDOFF_CORR134.md, CORRECTIVE_HANDOFF_CORR135.md, CORRECTIVE_HANDOFF_CORR158.md
- research/month_end_candidate_reaudit.py checks csmomentum_legacy_net_returns_match_committed_simulation against data/processed/simulation_csmomentum_001.parquet
- tests/test_cost_admissibility_screen.py affected per README
