# Next Agent Task: Cycle 866 — rolling 63d gate evidence refresh (read-only)

## Context
Cycle 865 shows continuation horizon of 252-504 sessions needed for PSR>=0.95, exceeding plausible research cadence. Rolling 63d and max DD gates remain unresolved.

## Objective
Read-only refresh of rolling 63d sharpe and max DD evidence from committed record; quantify gap to promotion thresholds.

## Acceptance Criteria
1. Report `research/reports/rolling_63d_gate_refresh_001.md`.
2. Script `research/rolling_63d_gate_refresh.py`.
3. Verification: re-derive canonical full-period Sharpe 1.748401.

## Scope & Constraints
Read-only. No changes to data/configs/thresholds/src.

## Validation Commands
```bash
python research/sharpe_convention_audit.py
python research/rolling_63d_gate_refresh.py
```
