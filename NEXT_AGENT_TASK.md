# NEXT_AGENT_TASK.md

## Cycle 917 — Promote SMA-175 as separate tracked candidate (no baseline change yet)

### Context
Cycle 916 confirms SMA-175 (variant of tsmomentum_spytrend_001, SPY SMA 175) is phase-stable: phase A/B gate-1 unchanged, thin-trade fold exclusion does not change gate-1, mean Sharpe 1.539964 across 48 folds with folds averaging correctly. Read-only audit passed with all artifacts unchanged. Cycle 915 correctly refused to mutate run_cycle6.py/incumbent baseline due to anchor test breakage.

### Objective
Track SMA-175 as a separate promoted candidate (new experiment IDs) without modifying incumbent baseline. Prepare concrete artifact-regeneration/promotion plan and optionally create a parallel candidate entry that does not break existing anchor-based audits.

### Acceptance criteria
1. Create `research/tsmomentum_sma175_promoted_candidate_001.md` (experiment) and `research/reports/tsmomentum_sma175_promoted_candidate_001.md` documenting candidate definition (SMA-175), full WF results, phase stability, costs, point-in-time guarantees, and explicit "not the incumbent baseline" status.
2. If feasible without breaking `tests/test_incumbent_phase_stability_audit.py` and related anchors, add a separate registered candidate config/path (e.g. new function/registry entry) that can be evaluated independently; otherwise provide a detailed, safe regeneration script/plan with exact files to touch and verification commands.
3. Run verification: keep all existing tests passing (`pytest tests/test_incumbent_phase_stability_audit.py tests/test_tsmomentum_sma175_phase_stability_audit.py -v`); if new files added, add focused tests.
4. Document migration path: how to promote to incumbent later (exact diffs, which committed artifacts must be regenerated, and anchor-updates) without breaking read-only guarantees.
5. No new dependencies/workflows.

### Scope boundaries
Do not change incumbent baseline in run_cycle6.py or existing committed artifacts that anchors depend on. Keep changes additive/read-only where possible.
