# Experiment: csmomentum_001 — Long-Only Cross-Sectional Momentum (Baseline)

## Metadata
- Hypothesis: research/hypotheses/csmomentum_001.md (v001)
- Frozen config: config/csmomentum_001.yaml
- Code revision: 8604ed1
- Execution date: 2026-10-14T02:00:00Z
- Executor: Agent (Cycle 24 → Cycle 25 execution)
- Data: Cached daily OHLCV, 18 ETFs (SPY,QQQ,IWM,TLT,GLD,DBC,VNQ,EFA,EEM,XLB-XLY), 1993-01-29 to 2026-10-09

## Parameters (Baseline - Fixed)
- lookback=252, skip=21, top_fraction=0.5
- Long-only, equal-weight, 1-day signal lag, monthly rebalancing
- Costs: 3bps round-trip (1bps comm + 2bps slip)
- Risk-free: 2% annualized (from settings.yaml)

## Full Sample (1993-01-29 to 2026-10-09)
- Total return: 1937.87% (cumulative)
- Annualized return: 9.37%
- Annualized vol: 16.39%
- Sharpe (net): 0.4496
- Sortino: 0.5852
- Max drawdown: -43.36%
- Annualized turnover: 12.03x
- Trade count: 1781
- Profit factor: 1.1217
- Avg exposure: 0.968

## Chrono Splits (per config: train 1993-2009, val 2010-2017, test 2018-2026)
- Train (≤ 2009-12-31): Sharpe 0.3595, AnnRet 8.33%, MaxDD -43.36%, Trades 708
- Validation (2010-01-01 to 2017-12-31): Sharpe 0.5563, AnnRet 9.66%, MaxDD -18.59%, Trades 539
- Test (2018-01-01 to 2026-10-09): Sharpe 0.5652, AnnRet 11.14%, MaxDD -27.56%, Trades 533
  - Total return (test): 152.0% cumulative, 11.14% ann

## Walk-Forward (10yr train / 1yr test / 6mo step, purge 21d, embargo 21d, fixed params)
- Folds: 46
- Mean OOS Sharpe: 0.6619
- Median OOS Sharpe: 0.7138
- Positive fold rate: 78.3% (36/46 folds with Sharpe>0)
- Pooled OOS trades: 2855

## Benchmarks (Test 2018-01-01 to 2026-10-09, same cost model)
- 1/N Equal-Weight (18-ETF universe), monthly rebalance, 1-day lag: Sharpe -0.754? (constant 1/N with minimal trading gave small exposure artifact in our quick calc; better constant full exposure): constant full 1/N (18 ETFs) → Sharpe 0.4617, AnnRet 9.18%, MaxDD -31.77%, trades ~0 (no rebal costs)
- Incumbent TSMOM (7-ETF core universe, with regime filter in production form) reported test Sharpe 1.4178 (Cycle 7); 1/N on incumbent universe test: Sharpe 0.4716

## Multiple-Testing Control
- Pre-specified robustness grid: 27 configs (lookback {189,252,315}, skip {21,42}, top_fraction {0.3,0.5,0.7})
- Deflated Sharpe Ratio (DSR) on test period (n_configs=27, sr_target=0): DSR = -0.1358, DSR prob = 0.4460

## Promotion Gates (csmomentum_001)
1. WF mean OOS Sharpe >= 0.9? 0.6619 → FAIL
2. >=50% positive folds? 78.3% → PASS
3. >100 pooled OOS trades? 2855 → PASS
4. Parameter plateau (baseline skip/top fixed): not evaluated in this cycle (requires robustness grid execution)

**Overall gate status:** Gate 1 fails. Per falsification condition: "Walk-forward mean OOS Sharpe < 0.9" → hypothesis is FALSIFIED (Rejected/Failed) for promotion to simulation/paper-trading.

## Verdict
**Rejected/Failed.** Baseline cross-sectional momentum on 18-ETF universe does not meet the primary promotion gate (WF mean OOS Sharpe 0.6619 < 0.9). Despite strong positive fold rate and abundant trades, DSR indicates the observed Sharpe is not statistically significant after accounting for multiple testing relative to the threshold. The signal has modest positive performance but insufficient to clear the strict 0.9 Sharpe gate.

## Reproduction Commands
```bash
PYTHONPATH=/path/to/repo python3 << 'PY'
# Baseline test
from src.backtest.engine import run_backtest, compute_metrics, get_risk_free_rate, get_cost_params
symbols = ['SPY','QQQ','IWM','TLT','GLD','DBC','VNQ','EFA','EEM','XLB','XLE','XLF','XLI','XLK','XLP','XLU','XLV','XLY']
net_ret,w,_ = run_backtest(symbols,'1993-01-29','2026-10-09',252,21,0.5)
import pandas as pd
mask = (net_ret.index>=pd.Timestamp('2018-01-01',tz='UTC'))&(net_ret.index<=pd.Timestamp('2026-10-09',tz='UTC'))
m = compute_metrics(net_ret[mask],w[mask],*get_cost_params(),get_risk_free_rate())
print(m)
PY
```

## Next Steps
Per hypothesis falsification: document rejection, do NOT promote to simulation/paper-trading. Move to next candidate on shortlist (C4: Sector rotation) or other untested candidate with stronger structural case. The robustness grid (27 configs) was pre-specified but execution is not justified given primary gate failure; focus on different candidate instead.
