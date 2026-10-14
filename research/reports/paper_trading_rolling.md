# Paper-Trading Rolling Report

**Generated:** 2026-10-14 04:14:17 UTC
**Last Run Date:** 2026-10-12
**Days Tracked:** 445

## Current State

| Metric | Value |
|---|---|
| Current NAV | $136,905.02 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -1.59% |
| Total Return | 36.91% |
| Annualized Return | 19.47% |
| Volatility (ann.) | 9.54% |
| Sharpe Ratio (ann.) | 2.0404 |

## Positions Table

- SPY: 16.3145%
- QQQ: 16.3145%
- IWM: 16.3145%
- EEM: 16.3145%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': np.float64(0.48917289692364996), 'threshold': 0.5, 'date': '2026-10-12'}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** 0.4892
- **Rolling 63-day Max DD:** -4.99%
- **Regime Persistence:** 130 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.12% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-06: NAV=$138,273.88, Ret=-0.06%, Turnover=0.01%
- 2026-10-07: NAV=$137,600.70, Ret=-0.49%, Turnover=0.30%
- 2026-10-08: NAV=$136,804.15, Ret=-0.58%, Turnover=31.56%
- 2026-10-09: NAV=$137,376.42, Ret=0.42%, Turnover=33.65%
- 2026-10-12: NAV=$136,905.02, Ret=-0.34%, Turnover=0.49%
