# CORRECTIVE_HANDOFF_INVOCATION_1159.md

## Correction: stale report revision lines (2026-11-08)

- Found `research/reports/sectorrotation_long_sample_feasibility_001.md` and `research/reports/cost_admissibility_screen_001.md` carried stale code-revision lines vs HEAD `bd6086e`.
- Regenerated both with canonical tools. Only revision/generated-date lines changed; headline metrics unchanged.
- Verification: `pytest tests/test_sectorrotation_long_sample_feasibility.py tests/test_sectorrotation_walkforward_embargo_audit.py tests/test_cost_admissibility_screen.py -q` → 50 passed, 4 warnings in 104.01s.
- Gate still blocked (2026-11-09 not released). No data/config changes.
"