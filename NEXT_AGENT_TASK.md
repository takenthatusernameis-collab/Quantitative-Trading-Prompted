# Cycle 957 — Diagnose SMA 175 rolling 63d Sharpe and PSR gate failures

## Context
- Cycle 956 promotion-gate evaluation recorded OVERALL: PASS (structural) but DECISION: NO-GO.
- Failing gates: rolling_63d_sharpe (-0.119 < 0.9) and psr (0.8997 < 0.95).
- Artifact: research/reports/tsmomentum_sma175_promotion_gate_eval_001.md.

## Objective
Identify the dominant contributors to the rolling 63-day Sharpe shortfall and PSR gap using existing cached artifacts and evaluation code; propose one bounded, testable next experiment or rejection.

## Acceptance criteria
1. A short diagnostic note added under research/reports/ citing specific dates/periods and metrics.
2. No new backtest executed; no data fetched.
3. Existing tests still pass.

## Scope boundaries
- Reuse cached data and existing machinery only.
- No promotion to production/paper-trading state.
