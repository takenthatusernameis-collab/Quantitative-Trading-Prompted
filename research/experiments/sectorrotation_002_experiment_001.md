# Experiment: sectorrotation_002 — Sector Rotation Cross-Sectional Momentum (Baseline)

## Metadata
- Hypothesis: research/hypotheses/sectorrotation_002.md (v002, 2026-10-14)
- Frozen config: config/sectorrotation_002.yaml
- Code revision: current
- Execution: Cycle 26→27
- Data: 9 sector ETFs XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY (1998-12-22 to 2026-10-08)

## Baseline (Fixed)
- lookback=252, skip=21, top_fraction=0.5; long-only equal-weight, 1-day lag, monthly
- Costs 3bps round-trip

## Test Period (2018-01-01 to 2026-10-08)
- Sharpe (net): 0.4906
- Ann return: 10.86%
- Ann vol: 18.06%
- Max DD: -34.01%
- Annualized turnover: 16.10x
- Trade count: 349
- Profit factor: 1.1335
- Total return: 146.39%

## Walk-Forward (10yr/1yr/6mo, purge 21d, embargo 21d)
- Folds: 34
- Mean OOS Sharpe: 0.6627
- Median OOS Sharpe: 0.6559
- Positive folds: 79.4% (27/34)
- Pooled OOS trades: 1236

## Benchmarks (Test 2018-01-01 to 2026-10-08)
- 1/N equal-weight of 9-sector universe (monthly, 1-day lag, same costs): Sharpe ~ (compute quickly) - let us compute
- 1/N equal-weight (9-sector), monthly/1-day lag, same costs: Sharpe 0.4430, AnnRet 9.96%, MaxDD -37.43%, trades 0
- Incumbent TSMOM context (7-ETF): reported test Sharpe 1.4178 (Cycle 7)

## Multiple-Testing Control
- Robustness grid N=18 (pre-specified)
- DSR (n_configs=18, test period, sr_target=0): -0.1683, prob 0.4332

## Promotion Gates
1. WF mean OOS Sharpe >= 0.9? 0.6627 → FAIL
2. >=50% positive folds? 79.4% → PASS
3. >100 pooled OOS trades? 1236 → PASS
4. Parameter plateau: requires running robustness grid (not executed this cycle) - baseline only

Overall: Gate 1 fails → hypothesis FALSIFIED (Rejected/Failed) per pre-registered conditions.

## Verdict
Rejected/Failed. Sector-restricted cross-sectional momentum (9 GICS sectors) shows modest positive performance but WF mean OOS Sharpe 0.6627 < 0.9. Positive fold rate is solid; DSR negative after accounting for multiple testing. Insufficient to meet promotion threshold.

## Reproduction
```bash
PYTHONPATH=/path/to/repo python3 << 'PY'
from src.backtest.engine import run_backtest, compute_metrics, get_risk_free_rate, get_cost_params
import pandas as pd
syms=['XLB','XLE','XLF','XLI','XLK','XLP','XLU','XLV','XLY']
net_ret,w,_ = run_backtest(syms,'1998-12-22','2026-10-08',252,21,0.5)
mask=(net_ret.index>=pd.Timestamp('2018-01-01',tz='UTC'))&(net_ret.index<=pd.Timestamp('2026-10-08',tz='UTC'))
m=compute_metrics(net_ret[mask],w[mask],*get_cost_params(),get_risk_free_rate())
print(m)
PY
```

## Next Steps
Per falsification: do not promote to simulation/paper-trading. Document rejection. Select next candidate from shortlist (C5 TSMOM parameter variants already rejected; C6 Macro regime overlay extension - rank 6, Exploratory signal with macro regime component). Consider C6 as next bounded cycle.
