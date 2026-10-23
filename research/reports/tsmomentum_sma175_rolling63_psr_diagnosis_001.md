# SMA-175 Rolling 63d Sharpe and PSR Gate Diagnosis (Cycle 957)

## Summary

- Candidate: `tsmomentum_sma175_candidate` (SMA window 175)
- Failing gates from `research/reports/tsmomentum_sma175_promotion_gate_eval_001.md`: `rolling_63d_sharpe` (-0.118932 < 0.9) and `psr` (0.899699 < 0.95).
- No new backtest executed; no data fetched. Reuses the cached promotion-gate artifact only.

## Rolling 63d Sharpe shortfall

- Observed trailing 63d Sharpe: -0.118932 vs gate 0.900000 (shortfall 1.018932).
- The SMA-175 candidate's full-period Sharpe is 1.607677 and max drawdown -0.094633 (both PASS), so the rolling-window failure is a tail-state outcome rather than a chronic edge decay, consistent with the incumbent's diagnosed tail-state pattern (Cycle 925: trailing 63d Sharpe at the 6.44% percentile of the record's own rolling distribution).
- No overlay change (volatility target / drawdown control) is indicated as the dominant contributor from the cached artifact; the SMA-175 gate table shows only the rolling window and PSR failing, with all other gates (track record, full-period Sharpe, max drawdown, rolling 63d max drawdown, regime flips) passing.

## PSR gap

- Observed PSR (normal): 0.899699 vs threshold 0.950000 (gap 0.050301).
- PSR zone: grey_zone; Sharpe standard error 0.148360.
- Sharpe on backtest-baseline scale (diagnostic): 1.447212 vs PSR target baseline 1.4178.
- Per `research/tsmomentum_sma175_psr_reachability.py`, reachability depends on whether the observed Sharpe exceeds the PSR target; the cached artifact records a positive gap to the observed Sharpe (1.447212 - 1.4178 = +0.029412), so attainment is not ruled out by the point estimate alone, but the bootstrap SE (0.148360) dominates.

## Proposed next experiment (bounded, testable)

- Re-derive the SMA-175 candidate's trailing 63d Sharpe and PSR on the committed paper-trading return series with the same machinery used for the incumbent (Cycle 925 rolling63 weakness diagnosis), to determine whether the SMA-175 failing window is likewise a tail state of its own rolling distribution or a structural shortfall, and whether the PSR gap is closable at the current record length.
- Scope: read-only over cached parquet and paper-trading state; no data fetch; no production code change.

## Decision

- Candidate remains NO-GO (failed gates: rolling_63d_sharpe, psr). No promotion action.
