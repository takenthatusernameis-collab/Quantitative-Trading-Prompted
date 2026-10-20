# NEXT_AGENT_TASK.md

## Cycle 915 — Paper-trading record status evidence

### Context
Cycle 914 documented incumbent phase stability; paper-trading record remains time-bound constraint.

### Objective
Record current paper-trading replay status and evidence without changing signal/folds.

### Acceptance criteria
1. New tool `research/paper_trading_record_status_audit.py` (read-only, cache-only, deterministic, prints `OVERALL: PASS`, exits 0).
2. New report/experiment `research/reports/paper_trading_record_status_001.md` and `research/experiments/paper_trading_record_status_001.md`.
3. Tests `tests/test_paper_trading_record_status_audit.py`.
4. Verification: tool, pytest focused, git status data/config clean.

### Scope boundaries
Measurement only; no candidate selection, promotion, or gate changes. No data/config writes, no network.
" filePath">
NEXT_AGENT_TASK.md