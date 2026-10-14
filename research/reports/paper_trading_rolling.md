# Paper-Trading Rolling Report

**Generated:** 2026-10-14 07:15:04 UTC
**Last Run Date:** 2026-10-13
**Days Tracked:** 446

## Current State

| Metric | Value |
|---|---|
| Current NAV | $136,593.98 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -1.82% |
| Total Return | 36.59% |
| Annualized Return | 19.27% |
| Volatility (ann.) | 9.53% |
| Sharpe Ratio (ann.) | 2.0210 |

## Positions Table

- SPY: 16.2930%
- QQQ: 16.2930%
- IWM: 16.2930%
- EEM: 16.2930%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': np.float64(0.3668744153541084), 'threshold': 0.5, 'date': '2026-10-13'}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** 0.3669
- **Rolling 63-day Max DD:** -4.99%
- **Regime Persistence:** 131 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.12% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-07: NAV=$137,600.70, Ret=-0.49%, Turnover=0.30%
- 2026-10-08: NAV=$136,804.15, Ret=-0.58%, Turnover=31.56%
- 2026-10-09: NAV=$137,376.42, Ret=0.42%, Turnover=33.65%
- 2026-10-12: NAV=$136,905.02, Ret=-0.34%, Turnover=0.49%
- 2026-10-13: NAV=$136,593.98, Ret=-0.23%, Turnover=0.09%
