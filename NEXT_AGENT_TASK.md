# NEXT_AGENT_TASK — regenerate scratch provenance report (2026-10-29)

## Context
Full `python -m pytest -q` fails at `tests/test_commodity_data_gate_001.py::test_tool_runs_read_only_and_passes_its_own_checks` because `/tmp/scratchpad/commodity_fetch/commodity_fetch_report.json` is missing in this environment. The suite otherwise progresses (targeted cost-admissibility test passes in ~21s).

## Objective
Restore the scratch provenance report (or the test's prerequisite) so `python -m pytest -q` exits 0, without weakening tests.

## Acceptance criteria
- `python -m pytest -q` exits 0
- `git status --porcelain data/ config/` empty

## Validation commands
python -m pytest -q
git status --porcelain data/ config/

## Scope boundaries
- Do not edit test thresholds or weaken checks.
- Investigate `research/commodity_data_gate_001.py` provenance report generation and the expected scratchpad location.