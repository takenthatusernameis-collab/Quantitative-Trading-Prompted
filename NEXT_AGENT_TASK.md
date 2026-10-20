# NEXT_AGENT_TASK.md

## Cycle 913 — Make tsmomentum_spytrend_001 phase-stable or identify the minimal fix

### Context
Cycle 912 decision audit downgraded the incumbent to **Exploratory (not promotable as-is)** because the published 48-fold PASS is not phase-stable: phase A (odd folds) passes gate-1 (mean ~1.385) while phase B (even folds) fails gate-1 (mean ~0.510). The folds are interleaved by the 6m-step/12m-test design; excluding thin-trade folds does not restore stability. Phase-stable evidence is required before promotion.

### Objective
Determine why phase B fails and test the smallest reversible fix to achieve phase-stable gate-1 (both phases >= 0.9) under the published protocol, or if impossible with smallest change, produce a concrete failure analysis and a bounded redesign plan. Do not change gates/thresholds/cost model arbitrarily.

### Acceptance criteria
1. New read-only analysis tool `research/tsmomentum_phase_stability_fix_audit.py` that reuses the committed candidate definition from `research/run_cycle6.py` and the cycle 911/912 artifacts; writes `research/reports/tsmomentum_phase_stability_fix_001.md` and `research/experiments/tsmomentum_phase_stability_fix_001.md`.
2. Diagnose phase B failure (inspect regime filter behavior, overlay, turnover, exposure, fold windows) with evidence from the same cached path.
3. Test at most one or two smallest reversible parameter/logic tweaks (if any). Each attempted fix must be evaluated on both phases under the published walk-forward design with read-only hashes before/after.
4. If phase-stable PASS is achieved: report the minimal change and show both phases pass gate-1 with pooled trades >100; do not promote.
5. If not achievable with smallest safe change: report root-cause evidence and leave a bounded next task (no speculative broad refactor).
6. Tests `tests/test_tsmomentum_phase_stability_fix_audit.py`; `python research/tsmomentum_phase_stability_fix_audit.py` prints `OVERALL: PASS` and exits 0 only if checks pass.
7. Verification clean: no writes under `data/` or `config/`; committed artifacts unchanged.

### Scope boundaries
Measurement/analysis first; changes only if smallest reversible fix is identified and verified. No gate threshold changes. No promotion. No new dependencies/workflows.
