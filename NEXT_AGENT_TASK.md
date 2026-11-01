# NEXT_AGENT_TASK — Add provenance coverage to drift persistence tests

## Context
`research/drift_persistence_report.py` already emits a `provenance:` section
(`git_sha`, `paper_trading_state_sha256`, `config`) and updates
`research/reports/paper_trading_rolling.md`. Existing tests do not assert these
fields, so regressions could pass silently.

## Objective
Add focused tests to `tests/test_drift_persistence.py` asserting that
`build_report` includes non-null provenance fields and that `main()` prints a
`provenance:` block. Keep changes minimal and deterministic.

## Acceptance criteria
- `python -m pytest tests/test_drift_persistence.py -q` passes.
- New tests fail if provenance fields are removed.
- `git status --porcelain` shows only expected files modified.

## Validation commands
```bash
python -m pytest tests/test_drift_persistence.py -q
python research/drift_persistence_report.py
git status --porcelain
```

## Scope boundaries
- Do not change thresholds/gates or recomputation logic.
- Do not add new dependencies.
"""