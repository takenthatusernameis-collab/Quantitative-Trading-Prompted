# NEXT_AGENT_TASK.md

## Cycle 914 — Incumbent phase stability and paper-trading record (time-bound constraint)

### Context
Cycle 913 measured the cost boundary of the promotion-gate statistic for `tsmomentum_spytrend_001`, `csmomentum_001`, and `sectorrotation_001`. The incumbent's published PASS survives cost levels above the measured bid-ask floor, so the cost axis is not the binding constraint on the incumbent; the remaining weakness is the phase stability of the published PASS (Cycle 911 even-fold phase 0.5096, gate 1 FAIL) and the prospective paper-trading record (a time-bound constraint).

### Objective
Document and bound the incumbent's phase stability by re-running the walk-forward fold path split by even/odd phase and recording the paper-trading record status, without changing the signal, folds, sample, universe, or gates.

### Acceptance criteria
1. New tool `research/incumbent_phase_stability_audit.py` (read-only, cache-only, deterministic, prints `OVERALL: PASS`, exits 0).
2. New report `research/reports/incumbent_phase_stability_001.md` and experiment record `research/experiments/incumbent_phase_stability_001.md`.
3. Regression: incumbent walk-forward mean at 3.0 bp/unit reproduces 0.9473 (≤1e-9).
4. Tests `tests/test_incumbent_phase_stability_audit.py`.
5. Verification: tool, pytest focused, pytest full, git status data/config clean.

### Scope boundaries
Measurement only; no candidate selection, promotion, or gate changes. No data/config writes, no network.
"