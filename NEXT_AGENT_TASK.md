# NEXT_AGENT_TASK — resolve pre-existing full-suite failures blocking pytest exit 0
## Context
The DBC/csmomentum governance blocker is RESOLVED:
- Governance record `research/reports/dbc_csmomentum_governance_001.md` committed at 6c5fe01 documents decision: "No governance action required / Option (a) already satisfied" — DBC.parquet ends at 2026-10-08, no data/config changes required.
- `data/raw/DBC.parquet` max date = 2026-10-08 (5,201 rows); `data/processed/simulation_csmomentum_001.parquet` max date = 2026-10-09 (8,482 rows). The sim_end > dbc_end flag is a false positive (forward-fill behavior, 1.4e-17 max abs diff over 8,482 sessions).
- `tests/test_cost_admissibility_screen.py`: 40 passed.
- `git status --porcelain` and `git status --porcelain data/ config/`: empty.
- `tests/test_commodity_data_gate_001.py`: 15 passed.

Remaining pre-existing full-suite failures (unrelated to DBC/csmomentum blocker, documented in CORRECTIVE_HANDOFF_CORR_CURRENT.md):
1. `tests/test_leadlag_001_evaluation.py`: 2 FAILED — references git object `4f0947bca1289acd0c6d9ed6fc6424f21b8fe36d` which does not exist in this repo (`fatal: bad object`). Environment/data issue, not a code defect.
2. Paper trading state drift: `data/processed/paper_trading_state.yaml` has `last_run_date: '2026-10-30'` (459 sessions) but committed reports record `2026-10-23` (454 sessions). Affects `test_state_aggregate_audit.py`, `test_tsmomentum_rolling63_weakness_diagnosis.py`, `test_go_no_go_evaluation.py`, `test_tsmomentum_same_session_vol_correction.py`, `test_tsmomentum_vol_estimate_consolidation.py`.

## Objective
Resolve the paper trading state drift so the full suite passes. Investigate whether the state file or committed reports are correct, then apply the minimal consistent fix. Document the leadlag missing git object as an environment blocker if it cannot be resolved without network access.

## Acceptance criteria
- `python -m pytest -q` exits 0 (full suite; README notes long runtime ~3934s)
- `git status --porcelain data/ config/` empty
- Paper trading state consistent with committed reports (or reports updated to match state with documented rationale)
- Leadlag missing git object documented as environment blocker if unresolved

## Validation commands
```bash
PYTHONPATH=/home/runner/work/_temp/kilo-tmp/pylibs python3 -m pytest -q  # may take long (~minutes)
git status --porcelain data/ config/
```

## Scope boundaries
- Do not reopen the DBC/csmomentum governance blocker (already resolved).
- Do not edit tests/thresholds to mask failures.
- Preserve commodity gate clean-tree invariant.
- Only change data/config/tests as required to resolve the state drift, with documented rationale.
- Do not install packages or access network unless explicitly required.
- This is a data consistency issue, not a code defect.

## Evidence
- CORRECTIVE_HANDOFF_CORR_CURRENT.md (pre-existing failures documented)
- data/processed/paper_trading_state.yaml (last_run_date: 2026-10-30)
- Committed research reports recording 2026-10-23 / 454 sessions
- test_leadlag_001_evaluation.py: 2 failed on missing git object 4f0947b...
