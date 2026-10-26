# NEXT_AGENT_TASK — TSMomentum date-range blocker follow-on (2026-10-26)

## Context
Full suite run (2026-10-26) result: 24 failed, 689 passed, 1 skipped, 106 warnings, 39 errors in 1853.55s.
csmomentum_001 tests pass (data/raw/DBC.parquet already at freeze value 2026-10-08).
Remaining failures cluster in tsmomentum_same_session_vol_correction and
tsmomentum_vol_estimate_consolidation: their cached simulation series ends
2026-10-19 (8488 rows) but published record dates extend to 2026-10-23,
causing KeyError on .loc[record_dates].

## Objective
Resolve the tsmomentum cached-series / record-date mismatch (extend or
truncate consistently) without editing test tolerances or published constants.

## Acceptance criteria
- python -m pytest -q passes in full
- git status --porcelain data/ config/ empty

## Validation commands
git status --porcelain
python -m pytest -q
git status --porcelain data/ config/
