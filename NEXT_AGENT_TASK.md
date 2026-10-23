# Cycle 960 — Paper-trading replay network blocker

## Context
Cycle 959 replay hung at day 191/453 (2025-10-07) after ~9 min; process Rl, no further progress. Likely yfinance fetch stall. Partial state written through day 191. No validation report produced.

## Objective
Resolve replay stall and complete Cycle 959 protocol: rerun with per-symbol timeout/retry or cached data; verify completion and state; write report.

## Acceptance criteria
1. Replay completes all trading days without hang.
2. State track length/dates, NAV, Sharpe, max DD, rolling 63d Sharpe, regime flips, drift flag recorded.
3. Validation report written.
4. Tests pass.

## Scope
No strategy changes.
