# Paper-Trading Rolling Report

**Generated:** 2026-10-14 16:32:44 UTC
**Last Run Date:** 2026-10-14
**Days Tracked:** 447

## Current State

| Metric | Value |
|---|---|
| Current NAV | $135,057.00 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -2.92% |
| Total Return | 35.06% |
| Annualized Return | 18.46% |
| Volatility (ann.) | 9.57% |
| Sharpe Ratio (ann.) | 1.9302 |

## Positions Table

- SPY: 16.1606%
- QQQ: 16.1606%
- IWM: 16.1606%
- EEM: 16.1606%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': np.float64(0.11846018679204061), 'threshold': 0.5, 'date': '2026-10-14'}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** 0.1185
- **Rolling 63-day Max DD:** -4.99%
- **Regime Persistence:** 132 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.12% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-08: NAV=$136,804.15, Ret=-0.58%, Turnover=31.56%
- 2026-10-09: NAV=$137,376.42, Ret=0.42%, Turnover=33.65%
- 2026-10-12: NAV=$136,905.02, Ret=-0.34%, Turnover=0.49%
- 2026-10-13: NAV=$136,593.98, Ret=-0.23%, Turnover=0.09%
- 2026-10-14: NAV=$135,057.00, Ret=-1.13%, Turnover=0.53%
