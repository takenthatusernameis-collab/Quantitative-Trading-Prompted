# Next Agent Task: Paper-Trading Drift Flag Investigation

## Context

The incumbent TSMOM candidate (C1: SPY, QQQ, IWM, TLT, GLD, EFA, EEM) is the only strategy that has met the promotion gate (net OOS Sharpe >= 0.9) in prior cycles. It has been in paper-trading validation for 447 days (2025-01-02 to 2026-10-14).

**Current paper-trading state** (from `research/reports/paper_trading_validation_035.md` and `research/reports/paper_trading_rolling.md`):

| Metric | Value |
|--------|-------|
| NAV | $135,043.35 |
| Total Return | +35.04% |
| Annualized Return | 18.46% |
| Sharpe Ratio | 1.9272 |
| Max Drawdown | -2.93% |
| Rolling 63-day Sharpe | **0.1133** |
| Regime | Risk-on (132 days) |

**Active drift flag:** `low_rolling_sharpe` — rolling 63-day Sharpe of 0.1133 falls below the 0.5 threshold. This flag has been present in recent validation cycles (034, 035) and is independently verified from the state YAML cumulative returns array.

**Other context:**
- Microcap mom121 hypothesis: confirmed BLOCKED by data/infrastructure (data source survey completed, no free source viable for confirmatory test)
- Overnight drift: exploratory signal only, not stable, not promoted
- All other exploratory candidates (C3, C4, C6): rejected via pre-registered walk-forward tests
- No new market data available since 2026-10-14

## Objective

Investigate the paper-trading drift flag (`low_rolling_sharpe`) to determine whether it represents:
1. A genuine regime change / performance degradation in the strategy
2. A statistical artifact of the recent return window
3. A data or calculation issue

**Do not** disable the drift flag or change the threshold without evidence. **Do not** make code changes to the strategy logic to "fix" the Sharpe ratio.

## Acceptance Criteria

1. **Decompose the rolling Sharpe:** Compute the rolling 63-day Sharpe over the full 447-day track record and identify when it first crossed below 0.5. Report the exact date, the window's return/volatility components, and the strategy's position/turnover during that window.

2. **Compare to backtest expectation:** Extract the equivalent 63-day rolling Sharpe from the historical backtest (from `data/processed/simulation_candidate_001.parquet` or equivalent) over the same dates. Determine whether the paper-trading underperformance is anomalous relative to backtest behavior.

3. **Regime analysis:** Cross-reference the low-Sharpe window with the regime state (`data/processed/regime_*.parquet` or `paper_trading_state.yaml`). Determine whether the low Sharpe coincides with a specific regime (risk-on, risk-off, volatility regime) or spans multiple regimes.

4. **Position/turnover diagnostic:** Report average position count, turnover, and exposure during the low-Sharpe window vs. the prior 180 days. Determine whether the strategy is behaving as designed or showing signs of degradation (e.g., excessive turnover, low exposure, wrong asset selection).

5. **Document findings** in `research/reports/paper_trading_drift_investigation_001.md` with:
   - Exact dates and window metrics
   - Comparison to backtest expectation
   - Regime correlation
   - Position/turnover diagnostic
   - Clear verdict: "explained by regime", "anomalous vs backtest", "data issue", or "requires further investigation"
   - Recommended action (none / monitor / parameter review / halt)

## Validation Commands

```bash
# 1. Load paper-trading state and compute rolling Sharpe
PYTHONPATH=. .venv/bin/python3 -c "
import pandas as pd
import numpy as np
state = pd.read_yaml('data/processed/paper_trading_state.yaml')
returns = pd.Series(state['cumulative_returns']).pct_change().dropna()
rolling_sharpe = returns.rolling(63).apply(lambda x: x.mean() / x.std() * np.sqrt(252))
print('Current rolling Sharpe:', rolling_sharpe.iloc[-1])
print('First date below 0.5:', rolling_sharpe[rolling_sharpe < 0.5].index[0] if (rolling_sharpe < 0.5).any() else 'Never')
"

# 2. Compare to backtest
PYTHONPATH=. .venv/bin/python3 -c "
import pandas as pd
import numpy as np
sim = pd.read_parquet('data/processed/simulation_candidate_001.parquet')
returns = sim['net_return'].dropna()
rolling_sharpe = returns.rolling(63).apply(lambda x: x.mean() / x.std() * np.sqrt(252))
print('Backtest rolling Sharpe over same period:', rolling_sharpe.iloc[-1])
"

# 3. Run existing test suite
.venv/bin/python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- **Do not** modify strategy logic, parameters, or the drift threshold.
- **Do not** disable or silence the drift flag.
- **Do not** claim the strategy is performing well or poorly based on this diagnostic alone.
- **Do** use only existing infrastructure and cached data.
- **Do** report all findings honestly, including if the cause remains unexplained.

## Evidence Base

- Paper-trading state: `data/processed/paper_trading_state.yaml`
- Paper-trading rolling report: `research/reports/paper_trading_rolling.md`
- Latest validation: `research/reports/paper_trading_validation_035.md`
- Backtest simulation: `data/processed/simulation_candidate_001.parquet`
- Regime data: `data/processed/regime_*.parquet` (if available)
- Prior drift analysis: `research/reports/paper_trading_drift_analysis_001.md`
- Data inventory: `research/reports/data_inventory.md`