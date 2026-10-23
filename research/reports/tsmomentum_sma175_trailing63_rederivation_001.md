# SMA-175 Trailing 63d Sharpe and PSR Re-derivation on Committed Paper Series (Cycle 958)

## Summary

- Candidate: `tsmomentum_sma175_candidate` (SMA window 175).
- Read-only re-derivation over cached parquet and paper-trading state; no new backtest, no data fetch, no production code change.
- Source machinery: Cycle 925 `research/tsmomentum_rolling63_weakness_diagnosis.py` pattern; cached artifacts `research/reports/tsmomentum_sma175_promotion_gate_eval_001.md` and `research/reports/tsmomentum_sma175_rolling63_psr_diagnosis_001.md`.

## Re-derived trailing 63d Sharpe

- Observed trailing 63d Sharpe: -0.118932 (gate 0.900000; shortfall 1.018932).
- Full-period Sharpe: 1.607677 (PASS); max drawdown -0.094633 (PASS).
- Conclusion: failing window is a tail-state outcome of the rolling distribution, not chronic edge decay, consistent with incumbent Cycle 925 diagnosis (trailing 63d Sharpe at 6.44% percentile of own rolling distribution).

## Re-derived PSR

- Observed PSR (normal): 0.899699 (threshold 0.950000; gap 0.050301).
- Sharpe standard error: 0.148360; grey zone.
- Diagnostic Sharpe on backtest-baseline scale: 1.447212 vs PSR target baseline 1.4178 (+0.029412).
- Conclusion: point estimate does not rule out attainment, but bootstrap SE dominates; gap not closable at current record length with confidence.

## Decision

- Candidate remains NO-GO (failed gates: rolling_63d_sharpe, psr). No promotion action.
