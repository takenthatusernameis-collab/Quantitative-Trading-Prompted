# Cycle 958 — Re-derive SMA-175 trailing 63d Sharpe/PSR on committed paper series

## Context
- Cycle 957 diagnostic note: research/reports/tsmomentum_sma175_rolling63_psr_diagnosis_001.md.
- Failing gates: rolling_63d_sharpe (-0.118932 < 0.9) and psr (0.899699 < 0.95).
- Need to determine whether the SMA-175 failing window is a tail state of its own rolling distribution (as with the incumbent, Cycle 925) or a structural shortfall, and whether the PSR gap is closable at current record length.

## Objective
Re-derive the SMA-175 candidate's trailing 63d Sharpe and PSR on the committed paper-trading return series using existing machinery (Cycle 925 rolling63 diagnosis pattern), read-only over cached parquet and paper-trading state.

## Acceptance criteria
1. A diagnostic note under research/reports/ citing specific dates/periods and metrics.
2. No new backtest executed; no data fetched; no production code changed.
3. Existing tests still pass.

## Scope boundaries
- Reuse cached data and existing machinery only.
- No promotion to production/paper-trading state.
