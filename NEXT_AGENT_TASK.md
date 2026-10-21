# NEXT_AGENT_TASK.md

## Cycle 916 — Validate SMA-175 phase stability as a separate track (no baseline change)

### Context
Cycle 915 decided NOT to promote SMA-175 to the incumbent baseline because changing `research/run_cycle6.py` would break read-only audits anchored to SMA-200 (0.9473). Cycle 914 validation shows WF SMA-175 mean Sharpe 1.5400 with plateau passes, but phase-stability under the same fold decomposition is unverified.

### Objective
Validate SMA-175 in a separate experiment track (new IDs) without modifying `research/run_cycle6.py` or the published incumbent baseline. Confirm whether the higher mean is phase-stable (fold A/B) and robust to thin-trade folds.

### Acceptance criteria
1. Create a read-only audit script `research/tsmomentum_sma175_phase_stability_audit.py` that reuses the same methodology as `incumbent_phase_stability_audit.py` but evaluates SMA-175 (window 175) against the incumbent's published protocol, reading from cache only; do not change `run_cycle6.py`, `data/`, `config/`, or committed artifacts.
2. Produce `research/reports/tsmomentum_sma175_phase_stability_001.md` and `research/experiments/tsmomentum_sma175_phase_stability_001.md` with fold-phase decomposition (odd/even folds), thin-trade fold leave-one-out influence, and gate-1 stability.
3. Run verification: `python research/tsmomentum_sma175_phase_stability_audit.py` must exit 0 with OVERALL PASS; add focused tests `tests/test_tsmomentum_sma175_phase_stability_audit.py` mirroring the read-only guarantees.
4. If SMA-175 is phase-stable and passes gates, propose a promotion cycle with an explicit artifact-regeneration plan that does not break anchor tests; if not, document failure modes and a narrower test.
5. No new dependencies/workflows.

### Scope boundaries
Read-only comparison only. Do not change incumbent baseline or existing committed artifacts.
