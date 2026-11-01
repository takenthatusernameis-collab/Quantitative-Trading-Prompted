# NEXT_AGENT_TASK — Add explicit provenance for drift persistence report

## Context
`research/drift_persistence_report.py` prints `stored flag value` and `stored == recomputed` but does not record the data source hash or config snapshot used for the recomputation. To make the drift persistence check independently reproducible and auditable, add provenance fields to its output and to `research/reports/paper_trading_rolling.md` when generated/updated.

## Objective
Modify `research/drift_persistence_report.py` to emit provenance (git SHA, config hash or names, data file hashes for `data/processed/paper_trading_state.yaml` and any inputs used to compute rolling Sharpe) and update the rolling report to include a short provenance block. Keep changes minimal and deterministic.

## Acceptance criteria
- Running `python research/drift_persistence_report.py` prints a `provenance:` section with at least `git_sha`, `paper_trading_state_sha256`, and `config` (or equivalent).
- `research/reports/paper_trading_rolling.md` updated to include the same provenance (if the script writes it; if not, add a small update path consistent with existing behavior).
- `python -m pytest tests/test_drift_persistence.py -q` still passes.
- `git status --porcelain` shows only expected files modified (no unrelated changes).

## Validation commands
```bash
python research/drift_persistence_report.py
python -m pytest tests/test_drift_persistence.py -q
git status --porcelain
```

## Scope boundaries
- Do not change thresholds/gates or recomputation logic.
- Do not add new dependencies.
- Keep output format readable and backward compatible where reasonable.
