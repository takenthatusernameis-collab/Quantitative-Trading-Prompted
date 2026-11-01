# Paper-Trading Rolling Report

**Generated:** 2026-11-01 12:16:13 UTC
**Last Run Date:** 2026-10-26
**Days Tracked:** 455

## Current State

| Metric | Value |
|---|---|
| Current NAV | $134,060.18 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -4.99% |
| Total Return | 34.06% |
| Annualized Return | 17.63% |
| Volatility (ann.) | 9.57% |
| Sharpe Ratio (ann.) | 1.8413 |

## Positions Table

- SPY: 16.2550%
- QQQ: 16.2550%
- IWM: 16.2550%
- EEM: 16.2550%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': 0.12839020554259503, 'threshold': 0.5, 'date': '2026-10-26', 'persistence_days': 11}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** 0.1284
- **Rolling 63-day Max DD:** -4.99%
- **Regime Persistence:** 140 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.14% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-20: NAV=$134,725.63, Ret=0.31%, Turnover=0.10%
- 2026-10-21: NAV=$135,218.87, Ret=0.37%, Turnover=0.79%
- 2026-10-22: NAV=$133,719.54, Ret=-1.11%, Turnover=1.31%
- 2026-10-23: NAV=$133,634.38, Ret=-0.06%, Turnover=0.06%
- 2026-10-26: NAV=$134,060.18, Ret=0.32%, Turnover=0.53%
