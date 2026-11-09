# Paper-Trading Rolling Report

**Generated:** 2026-11-09 22:00:13 UTC
**Last Run Date:** 2026-11-09
**Days Tracked:** 465

## Current State

| Metric | Value |
|---|---|
| Current NAV | $132,932.13 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 32.93% |
| Annualized Return | 16.68% |
| Volatility (ann.) | 9.92% |
| Sharpe Ratio (ann.) | 1.6811 |

## Positions Table

- SPY: 13.1015%
- QQQ: 13.1015%
- IWM: 13.1015%
- EEM: 13.1015%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -1.1566354312981708, 'threshold': 0.5, 'date': '2026-11-09', 'persistence_days': 9}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -1.1566
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 150 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.14% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-03: NAV=$132,866.04, Ret=0.20%, Turnover=0.16%
- 2026-11-04: NAV=$133,995.42, Ret=0.85%, Turnover=0.98%
- 2026-11-05: NAV=$129,990.36, Ret=-2.99%, Turnover=12.08%
- 2026-11-06: NAV=$130,874.77, Ret=0.68%, Turnover=0.65%
- 2026-11-09: NAV=$132,932.13, Ret=1.57%, Turnover=3.05%

## Drift Persistence Provenance

- **git_sha:** 5c29e0dd5ad53f8e59fb792724f2a69949ff1328
- **paper_trading_state_sha256:** 24cd92a33d138f9c12004ddad25931a109977a68e14143395b3231ffe38f53f2
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
