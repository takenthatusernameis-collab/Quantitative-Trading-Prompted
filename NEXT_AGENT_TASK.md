# NEXT_AGENT_TASK — resolve DBC/csmomentum governance blocker (owner decision required)
## Context
As documented in README and previous corrective handoffs, `data/raw/DBC.parquet` was extended from 2026-10-08 to 2026-10-21 after `csmomentum_001` artifacts were frozen. Frozen `data/processed/simulation_csmomentum_001.parquet` no longer matches recomputation from current DBC cache. This requires a governance decision among (a),(b),(c). Working tree clean. `tests/test_cost_admissibility_screen.py` passes (40/40). No explicit owner decision is recorded in recent commits/governance records.

## Objective
Obtain and commit an explicit owner decision among:
(a) restore historical DBC to frozen cut-off (truncate DBC.parquet back to 2026-10-08)
(b) recreate csmomentum artifacts from frozen historical cache (regenerate weights/simulation/trades_csmomentum_001.parquet)
(c) amend published results with supersession record (update experiment/report artifacts with staleness/supersession note)

Record the decision in a commit message/dedicated governance record, then apply minimal changes required by that option and verify.

## Acceptance criteria
- Owner decision executed as committed (decision documented)
- `python -m pytest -q` exits 0 (full suite; README notes long runtime ~3934s)
- `git status --porcelain data/ config/` empty

## Validation commands
```bash
python -m pytest -q  # may take long
git status --porcelain data/ config/
```

## Scope boundaries
- If no explicit owner decision exists in recent commits/governance records, do NOT guess; obtain/record it per repo process before changing data/config/tests.
- Only change data/config/tests as explicitly required by the committed owner decision.
- Preserve commodity gate clean-tree invariant.
- Do not edit tests/thresholds to mask the inconsistency.
- If regeneration required, ensure outputs consistent with chosen option without breaking other gates.
- This is a governance blocker, not a code defect. No safe unilateral code change resolves it without violating constraints.

## Evidence
- README.md (blocker/options)
- CORRECTIVE_HANDOFF_CORR_CURRENT.md, CORRECTIVE_HANDOFF_CORR2.md
- tests/test_cost_admissibility_screen.py passes (40/40)
- git log shows recent commits; working tree clean
