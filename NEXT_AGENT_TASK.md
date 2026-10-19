# Next Agent Task: Cycle 864 — PSR feasibility under canonical convention (read-only)

## Context
Cycle 863 produced `research/rolling_63d_rolloff_projection.py` and `research/reports/rolling_63d_rolloff_001.md`. Key findings (committed 449-session record, 2026-10-16):
- Canonical trailing 63d Sharpe: -0.211884 (fails gate). Mechanical roll-off: under flat continuation never reaches ≥0.9 within 63 sessions; under record-mean continuation reaches ≥0.9 around +49 sessions purely mechanically — but this does **not** imply recovery.
- PSR: 0.684041 < 0.95 (canonical pairing), SE 0.690150. To reach PSR≥0.95 at current SE need observed Sharpe ≥ 2.552996; current full-period observed Sharpe 1.748401. Gap is numerator-driven (tail added 5 sessions: 1.11% of record, SE fell 0.722984→0.690150, PSR fell 0.762425→0.684041).

The question: is reaching observed Sharpe ~2.553 on the same canonical convention even feasible given the record’s distribution/costs/overlays, or is the requirement implausible? Also need to quantify what full-period mean/std would be required and whether it’s consistent with plausible continuation (and costs).

## Objective
Produce a read-only, evidence-based feasibility analysis for the PSR numerator requirement (observed Sharpe ≥ 2.553) under canonical convention. Do not propose changing gates or thresholds.

## Acceptance Criteria
1. **Feasibility report** `research/reports/psr_feasibility_001.md` covering:
- Required full-period mean daily return given current full-period std(ddof=1)=? (compute from committed record) to achieve canonical observed Sharpe 2.553: mean_req = 2.553*std/sqrt(252). Show numbers.
- Compare mean_req to: record mean 0.00066578, trailing-63 mean -0.000069, and the “record-mean continuation” that made rolling Sharpe cross 0.9 at +49 sessions (0.00066578). Also show what continuation horizon at record mean would lift full-period Sharpe to ~2.553 (mechanical effect) — quantify.
- Using `src/evaluation/statistics.py` block bootstrap (or existing tools), report current PSR components (observed, se, psr, n) and sensitivity: how much must observed Sharpe increase (and/or SE decrease) to reach PSR≥0.95? Include the numbers from Cycle 862 context.
- Assess plausibility: given overlays (vol-targeting reduced risk-taking in adverse periods), costs, universe, turnover, can record-mean continuation realistically achieve the required mean/std over a reasonable horizon without degrading other gates (max DD, rolling 63d max DD)? Be explicit about assumptions.
- State clearly: mechanical roll-off of trailing window alone does not satisfy PSR numerator requirement; quantify gap.

2. **Reproducible script** `research/psr_feasibility.py` (read-only) that computes required means/stds and prints the key numbers in a deterministic form (anchored to committed record). Must use canonical Sharpe convention.

3. **Verification**: Re-derive current canonical numbers (full-period Sharpe, trailing 63d, stds) from committed record and show they match `sharpe_convention_audit.py`. No state/raw modifications.

## Scope & Constraints
- Read-only. No changes to data, configs, thresholds, or code under src/ (except maybe adding minimal read-only helper if strictly necessary, but prefer using existing).
- Use canonical convention only (arithmetic annualized rf=0). Never mix with backtest scale.
- Evidence-based; do not forecast alpha — state requirements and mechanical effects.
- Follow project conventions (deterministic checks, document evidence).

## Validation Commands
```bash
python research/sharpe_convention_audit.py
python research/psr_feasibility.py
cat research/reports/psr_feasibility_001.md | head -80
```
