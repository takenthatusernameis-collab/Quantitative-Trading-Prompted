# Cycle 961 — Paper-trading replay validation audit

## Context
Cycle 960 replay completed all 453 trading days (2025-01-02 .. 2026-10-23); state saved to data/processed/paper_trading_state.yaml; report at research/reports/paper_trading_rolling.md. Track length 453, NAV $133,719.54, Sharpe 1.8292, max DD -4.99%.

## Objective
Audit saved state and report for consistency: track length/dates, NAV, Sharpe, max DD, rolling 63d Sharpe, regime flips, drift flag.

## Acceptance criteria
1. State track length matches replay days (453).
2. Report metrics match state.
3. Tests pass.

## Scope
No strategy changes.
