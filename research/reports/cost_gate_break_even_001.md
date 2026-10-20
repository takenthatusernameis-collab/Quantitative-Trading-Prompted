# Cost Gate Break-Even Audit (cost_gate_break_even_001, Cycle 913)

## Pre-registration (written before measurement)

- Candidates: tsmomentum_spytrend_001, csmomentum_001, sectorrotation_001
- Gate thresholds (unchanged): wf mean OOS Sharpe >= 0.9, positive fold rate >= 0.5, pooled OOS trades > 100
- Cost grid/bisection: pre-registered on fold-level path
- Spread proxy percentiles: [10, 25, 50] (daily (High-Low)/Close; upper bound on traded spread)
- Falsification: if the incumbent's published PASS survives a cost level of at least the measured bid-ask floor (times the two legs actually traded), the cost axis is not the binding constraint on the incumbent and this axis is closed.

## Cost model reference

- get_cost_params(): commission=1.0 bp, slippage=2.0 bp (total 3.0 bp/unit) per get_cost_params()/settings.yaml
- get_risk_free_rate(): 0.02
- Note: committed cost screen break-evens (aggregate statistic) differ from fold-level break-evens reported here.

## Bid-ask floor (measured from committed cache, upper bound)

| Percentile | Median (High-Low)/Close across symbols |
|------------|----------------------------------------|
| p10 | 67.96 bp |
| p25 | 94.18 bp |
| p50 | 127.82 bp |

## Per-candidate results

### tsmomentum_spytrend_001 (incumbent)

- Published WF mean OOS Sharpe @ 3.0 bp/unit: 0.9473; recomputed: 0.947307 (diff <= 1e-9)
- Gates @ 3.0 bp/unit: wf_mean=0.947307 [PASS], pos_fold_rate=0.9167 [PASS], pooled_trades=6013 [PASS]
- Gate flip costs (bps/unit): gate1=None, gate2=inf, gate3=inf

### csmomentum_001

- Published WF mean OOS Sharpe @ 3.0 bp/unit: backtest 0.697524, canonical 0.840389; recomputed backtest 0.697524, canonical 0.840389 (diff <= 1e-9)
- Gates @ 3.0 bp/unit: wf_mean=0.697524 [FAIL], pos_fold_rate=0.7917 [PASS], pooled_trades=400 [PASS]
- Gate flip costs (bps/unit): gate1=None, gate2=inf, gate3=inf

### sectorrotation_001

- Published WF mean OOS Sharpe @ 3.0 bp/unit: 0.847243; recomputed 0.847243 (diff <= 1e-9)
- Gates @ 3.0 bp/unit: wf_mean=0.847243 [FAIL], pos_fold_rate=0.9167 [PASS], pooled_trades=215 [PASS]
- Gate flip costs (bps/unit): gate1=None, gate2=inf, gate3=inf

## Verdict

- The fold-level gate flip costs are measured against the same path/statistic used by promotion gates.
- The bid-ask floor is a conservative upper bound (daily range contains intraday volatility).
- Does the published PASS survive a realistic cost floor? Measured from above; which gates bind first depends on each candidate's margin.
- Read-only: data/config/committed artifacts unchanged.
