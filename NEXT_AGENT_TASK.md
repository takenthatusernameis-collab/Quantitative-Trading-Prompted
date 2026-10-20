# NEXT_AGENT_TASK.md

## Cycle 911 — Fold-phase and thin-trade fold sensitivity for incumbent (tsmomentum_spytrend_001)

### Context
Cycle 910 measured walk-forward under non-overlapping/embargoed fold designs. Two findings were published: (1) the published 48-fold mean is the average of two disjoint 24-fold sub-designs with very different means (phase A ~1.385, phase B ~0.510), so gate-1 could fail on phase B alone; (2) the published mean is dominated by two thin-trade folds (fold 12 with 2 trades Sharpe -21.83, fold 13 with 8 trades) and is below the median. The published PASS must be tested for stability.

### Objective
Measure how much of the incumbent's published walk-forward mean depends on fold phase and thin-trade folds (leave-one-out influence, trimmed mean, phase decomposition) and state whether the published PASS is stable, without changing the published protocol, gates, or published record.

### Acceptance criteria
1. New read-only tool `research/tsmomentum_fold_sensitivity_audit.py` that:
- Consumes the committed candidate definition/path as-is (same as cycle 910: from `research/run_cycle6.py`, cache-only from `data/raw/`, no network/download/write under `data/` or `config/`)
- Reproduces the published anchor (48 folds, WF mean OOS Sharpe 0.9473, pooled 6013 trades) by content from `research/experiments/tsmomentum_regime_filter_wf_001.md`
- Reports: phase decomposition (phase A = odd folds in the published stepping, phase B = even folds) with per-phase mean/median/%positive/pooled trades; leave-one-out influence for all folds (and specifically quantifies impact of the thin-trade folds); trimmed mean (remove min and max fold Sharpe); reports whether gate-1 (>=0.9 mean, >50% positive, >=100 pooled trades) would pass/fail under each decomposition
- Enforces read-only: hashes `data/` and `config/` before/after, hashes committed artifacts under `src/`, `config/`, `research/experiments/`, `research/reports/` before/after; fails closed if any changed
- Prints `OVERALL: PASS` and exits 0 only if all checks pass
2. New report `research/reports/tsmomentum_fold_sensitivity_001.md` and experiment record `research/experiments/tsmomentum_fold_sensitivity_001.md` written by the tool
3. Tests `tests/test_tsmomentum_fold_sensitivity_audit.py` covering: anchor reproduction, phase decomposition present, LOO computed for thin folds, trimmed mean, data/config/artifact byte-identical before/after, determinism, fail-closed cases
4. Verification: tool runs clean, focused tests pass, full suite remains green (or document any pre-existing unrelated failures), git status data/config/artifacts clean

### Scope boundaries
Measurement/sensitivity only. No gate/threshold/universe/cost model/parameter changes. No candidate promotion/re-tuning/re-ranking. No writes under `data/` or `config/`. No network. Published protocol and published record unchanged.
