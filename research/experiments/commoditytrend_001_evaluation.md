# Commoditytrend_001 evaluation (Cycle 950)

## Verdict

- **Label:** Rejected/Failed
- **Falsified:** True
- **Fired conditions:** wf_mean_oos_sharpe, benchmark_relative_excess_ci, fold_or_trade_gate, no_post_2010_excess

## Walk-forward

- WF mean OOS Sharpe: 0.294913
- WF median OOS Sharpe: 0.321287
- Positive fold rate: 0.6667
- Pooled OOS trades: 62

## Benchmark-relative (net)

- Mean excess (annualized approx): -0.033764
- Bootstrap 95% CI (block 4, 2000 draws, seed 20240101): [nan, nan]

## Gross capture fraction

- Median: 0.652530, Mean: 0.723861, Observations: 162

## Expense ratio band

- Band: 0.0040 - 0.0085 (40-85 bps/yr)

## Post-2010 sub-period

- Excess (annualized): -0.033764

## Turnover and cost drag

- Reported via engine cost model (3.0 bp/unit).

## Deflated Sharpe Ratio

- Declared trial count: 3

## Falsification conditions fired

- wf_mean_oos_sharpe: fired=True
- benchmark_relative_excess_ci: fired=True
- gross_capture_below_cost_hurdle: fired=False
- fold_or_trade_gate: fired=True
- no_post_2010_excess: fired=True
- expense_ratio_band: fired=False

## Config hash

- 3ddfcf0a7b5ac42fcee7f9a60318286b2f85cabd6e14a3c71b46f5cff3d72af0
