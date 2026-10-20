# NEXT_AGENT_TASK.md

## Cycle 914 — Validate tsmomentum_spytrend SMA-175 fix under published protocol

### Context
Cycle 913 found the smallest reversible fix for the incumbent's phase instability: change the SPY trend-filter SMA window from 200 to 175 days. Under the published walk-forward design this yields phase-stable gate-1 (phase A mean 1.5391, phase B mean 1.5408, both PASS, pooled trades > 2900 each). The fix has NOT been promoted and the candidate definition in `research/run_cycle6.py` still uses SMA 200.

### Objective
Validate the SMA-175 change as a candidate mutation under the full published protocol (all gates including SMA-plateau, cost model, robustness) without changing gates/thresholds/cost model. Determine whether it is a credible candidate for promotion.

### Acceptance criteria
1. New read-only analysis tool `research/tsmomentum_sma175_validation_audit.py` reusing the committed candidate definition and cached path; writes `research/reports/tsmomentum_sma175_validation_001.md` and `research/experiments/tsmomentum_sma175_validation_001.md`.
2. Evaluate SMA-175 on the published 48-fold walk-forward (gate-1, gate-2, gate-3) plus SMA-plateau check vs SMA-200.
3. Read-only hashes before/after for `data/`, `config/`, committed artifacts.
4. Tests `tests/test_tsmomentum_sma175_validation_audit.py`; tool prints `OVERALL: PASS` and exits 0 only if checks pass.
5. No promotion, no changes to `research/run_cycle6.py`, no writes under `data/` or `config/`.

### Scope boundaries
Measurement/validation only; no gate threshold changes; no promotion; no new dependencies/workflows.
" filePath="/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/NEXT_AGENT_TASK.md"