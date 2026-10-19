# NEXT AGENT TASK — Cycle 875

## Context

Cycle 874 completed the post-backfill verification pass: all 5 acceptance criteria passed (reaudit OVERALL: PASS 17/17, rebalance audit OVERALL: PASS 12/12, pytest 82 passed in 86.16s, `git status --porcelain config/ data/processed/` empty, `data/raw/^VIX.parquet` 5,514 rows 2004-11-18 .. 2026-10-16, 0 duplicate dates, 0 NaN Close). Cycle 873 corrected the stale `^VIX` row in `research/reports/data_inventory.md` and wrote `research/reports/vix_backfill_001.md`. README.md now records Cycles 873 and 874.

The go/no-go decision is now open for reconciliation: `research/reports/deployment_dossier_001.md` states "**GO for live deployment**" (based on Cycle 6 WF, Cycles 8-21 paper trading, Cycle 22 go/no-go; rolling 63d Sharpe 0.9356 ≥ 0.9 at that time), but the current record shows rolling 63d Sharpe -0.21188351222842883 (below the 0.5 degradation threshold; `low_rolling_sharpe` drift flag active for 5 consecutive trading days), PSR 0.6168, data ends 2026-10-16, and no new completed session since. `research/go_no_go_evaluation.py` and `research/rolling_63d_gate_refresh.py` exist to recompute the gates.

## Objective

Reconcile the go/no-go deployment decision against the current record: run the available go/no-go / rolling-63d-gate evaluation, compare its output (rolling 63d Sharpe, max drawdown, PSR, trade count, decision) with `deployment_dossier_001.md`'s GO claim, and record a single decision (GO / NO-GO / hold) with supporting metrics in a new evidence artifact under `research/reports/`. No code, config, data, or candidate changes; research/reports only; no live trading, no credential access.

## Acceptance criteria

1. `python research/go_no_go_evaluation.py` runs and prints a decision (exit 0), OR if it requires unavailable inputs, the task documents the blocker precisely instead of fabricating a result.
2. A new artifact `research/reports/go_no_go_reconciliation_001.md` (or equivalent dated record) states: current rolling 63d Sharpe, max drawdown, PSR, trade count; comparison vs. dossier thresholds (≥ 0.9 Sharpe, ≤ 15% max DD); resulting decision (GO / NO-GO / hold) and rationale.
3. `git status --porcelain` shows only the new report file under `research/reports/` (plus README.md if this session also logs the cycle — optional).
4. `python -m pytest -q` still passes (82 tests).

## Validation commands

- `python research/go_no_go_evaluation.py`
- `python -m pytest -q`
- `git status --porcelain`

## Scope boundaries

- Research/backtesting only. Never place live trades, enable live trading, access or print secrets, or modify account credentials.
- Do not modify `config/`, `data/`, or source code. Do not change the deployment decision itself beyond recording the evidence-based reconciliation.
- Do not dispatch this workflow or start additional agent sessions.
