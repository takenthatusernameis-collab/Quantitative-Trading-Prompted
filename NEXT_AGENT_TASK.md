# Cycle 962 — Drift-flag persistence audit

## Context
Cycle 961 audit passed: state track length 453, NAV $133,719.54, Sharpe 1.8292, max DD -4.99%, rolling 63d Sharpe -0.1429 flagged low_rolling_sharpe with persistence_days 9.

## Objective
Audit drift-flag persistence accounting against state: verify persistence_days matches consecutive sub-threshold days and threshold value.

## Acceptance criteria
1. persistence_days equals recomputed consecutive sub-threshold streak.
2. Threshold and date match state.
3. Tests pass.

## Scope
No strategy changes.
