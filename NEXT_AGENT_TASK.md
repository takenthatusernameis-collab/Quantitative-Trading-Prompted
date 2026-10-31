# NEXT_AGENT_TASK — execute owner decision on DBC/csmomentum cache inconsistency
## Context
As documented in README and previous corrective handoffs, `data/raw/DBC.parquet` was extended from 2026-10-08 to 2026-10-21 after `csmomentum_001` artifacts were frozen. Frozen `data/processed/simulation_csmomentum_001.parquet` no longer matches recomputation from current DBC cache. This requires a governance decision among (a),(b),(c). Working tree clean. Cost admissibility screen (40/40) passes; other focused tests pass in isolation.

## Objective
Execute whichever option the repository owner has chosen (recorded in commit message/dedicated governance record). If no decision is committed yet, obtain and record it, then apply the minimal changes required by that option and verify.

## Options
(a) restore historical DBC to frozen cut-off (truncate DBC.parquet back to 2026-10-08)
(b) recreate csmomentum artifacts from frozen historical cache (regenerate weights/simulation/trades_csmomentum_001.parquet)
(c) amend published results with supersession record (update experiment/report artifacts with staleness/supersession note)

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

## Evidence
- README.md (blocker/options)
- CORRECTIVE_HANDOFF_CORR158.md, CORRECTIVE_HANDOFF_CORR2.md, CORRECTIVE_HANDOFF_CORR132.md-CORR135.md
- tests/test_cost_admissibility_screen.py passes (40/40)
- git log shows recent commits; working tree clean
