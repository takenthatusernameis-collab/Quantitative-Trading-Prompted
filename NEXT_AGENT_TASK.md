# Next Agent Task: Cycle 865 — continuation horizon and SE evolution for PSR (read-only)

## Context
Cycle 864 (`research/reports/psr_feasibility_001.md`, `research/psr_feasibility.py`) established that reaching PSR>=0.95 requires observed Sharpe >= 2.552996, i.e. daily mean 0.00097217 vs record mean 0.00066578 (+0.00030638, +46%). Mechanical window roll-off alone does not satisfy the PSR numerator. Remaining question: how many sessions of continuation at record mean (and at required mean) are needed for full-period observed Sharpe and/or bootstrap SE to reach PSR>=0.95, and is that horizon plausible?

## Objective
Produce a read-only, deterministic continuation-horizon analysis for PSR under canonical convention. Quantify required N at record-mean continuation and at required-mean continuation, and show whether SE decline can compensate. No gate/threshold changes.

## Acceptance Criteria
1. Report `research/reports/psr_continuation_horizon_001.md` with:
   - For r_future in {record mean 0.00066578, required mean 0.00097217}: compute full-period observed Sharpe and bootstrap SE (block size 22, 1000 samples, seed 20240101) as function of N added sessions, for N in {0, 30, 63, 126, 252, 504}; show PSR at each.
   - Identify minimum N (if any within grid) at which PSR>=0.95 under each continuation assumption.
   - State whether required horizon exceeds plausible research cadence and whether SE decline alone can reach PSR>=0.95 at current observed Sharpe (quantify max PSR at SE floor).
   - Note gate interactions (rolling 63d, max DD) qualitatively with evidence from committed record.
2. Script `research/psr_continuation_horizon.py` (read-only, deterministic, anchored to committed record) implementing above.
3. Verification: re-derive canonical full-period Sharpe 1.748401 and PSR 0.684041; match `sharpe_convention_audit.py`.

## Scope & Constraints
- Read-only. No changes to data/configs/thresholds/src.
- Canonical convention only (arithmetic annualized rf=0).
- Evidence-based; no performance forecasts.

## Validation Commands
```bash
python research/sharpe_convention_audit.py
python research/psr_continuation_horizon.py
cat research/reports/psr_continuation_horizon_001.md | head -80
```