# Paper-Trading Rolling Report

**Generated:** 2026-10-18 20:16:44 UTC
**Last Run Date:** 2026-10-16
**Days Tracked:** 449

## Current State

| Metric | Value |
|---|---|
| Current NAV | $133,729.22 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -4.99% |
| Total Return | 33.73% |
| Annualized Return | 17.72% |
| Volatility (ann.) | 9.59% |
| Sharpe Ratio (ann.) | 1.8485 |

## Positions Table

- SPY: 15.7831%
- QQQ: 15.7831%
- IWM: 15.7831%
- EEM: 15.7831%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': np.float64(-0.21188351222842883), 'threshold': 0.5, 'date': '2026-10-16'}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -0.2119
- **Rolling 63-day Max DD:** -4.99%
- **Regime Persistence:** 134 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.13% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-12: NAV=$136,905.02, Ret=-0.34%, Turnover=0.49%
- 2026-10-13: NAV=$136,593.98, Ret=-0.23%, Turnover=0.09%
- 2026-10-14: NAV=$135,043.35, Ret=-1.14%, Turnover=0.56%
- 2026-10-15: NAV=$135,230.10, Ret=0.14%, Turnover=0.23%
- 2026-10-16: NAV=$133,729.22, Ret=-1.11%, Turnover=1.70%
