# Paper-Trading Rolling Report

**Generated:** 2026-11-17 22:00:05 UTC
**Last Run Date:** 2026-11-17
**Days Tracked:** 471

## Current State

| Metric | Value |
|---|---|
| Current NAV | $130,327.28 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 30.33% |
| Annualized Return | 15.23% |
| Volatility (ann.) | 9.95% |
| Sharpe Ratio (ann.) | 1.5306 |

## Positions Table

- SPY: 12.8301%
- QQQ: 12.8301%
- IWM: 12.8301%
- EEM: 12.8301%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -2.008333566199979, 'threshold': 0.5, 'date': '2026-11-17', 'persistence_days': 15}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -2.0083
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 156 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.15% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-11: NAV=$133,688.64, Ret=0.90%, Turnover=0.95%
- 2026-11-12: NAV=$133,039.93, Ret=-0.49%, Turnover=0.18%
- 2026-11-13: NAV=$132,654.46, Ret=-0.29%, Turnover=0.01%
- 2026-11-16: NAV=$131,036.61, Ret=-1.22%, Turnover=0.55%
- 2026-11-17: NAV=$130,327.28, Ret=-0.54%, Turnover=0.35%

## Drift Persistence Provenance

- **git_sha:** b3d551b8ff7f4926300a7748139cfc22779e3c6c
- **paper_trading_state_sha256:** 05ca6c2f7ef25c00c8e1f02a05589931c8020b670f1117a09154df5d2cdf0ce7
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
