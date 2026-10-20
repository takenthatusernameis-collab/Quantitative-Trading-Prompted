# NEXT_AGENT_TASK.md

## Cycle 912 — Fold-phase stability decision record for incumbent (tsmomentum_spytrend_001)

### Context
Cycle 911 measured fold-phase and thin-trade fold sensitivity. The published 48-fold PASS is NOT stable: phase B alone FAILS gate-1 (mean 0.5096) and the published mean is dominated by thin-trade folds. The incumbent's promotion status must be reassessed.

### Objective
Produce a decision record comparing the published walk-forward evidence under fold-phase decomposition and state whether the incumbent remains a credible candidate or should be downgraded to exploratory, without changing gates/params/protocol.

### Acceptance criteria
1. New read-only tool `research/tsmomentum_fold_phase_decision_audit.py` that consumes the cycle 911 sensitivity outputs and writes `research/reports/tsmomentum_fold_phase_decision_001.md` and `research/experiments/tsmomentum_fold_phase_decision_001.md`.
2. Enforces read-only hashes before/after.
3. Prints `OVERALL: PASS` and exits 0 only if all checks pass.
4. Tests `tests/test_tsmomentum_fold_phase_decision_audit.py`.
5. Verification clean.

### Scope boundaries
Measurement/decision only. No gate/threshold/param changes. No promotion. No writes under data/ or config/.
">
filePath">
/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/NEXT_AGENT_TASK.md