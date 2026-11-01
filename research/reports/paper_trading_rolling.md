# Paper-Trading Rolling Report

**Generated:** 2026-11-01 14:08:16 UTC
**Last Run Date:** 2026-10-30
**Days Tracked:** 459

## Current State

| Metric | Value |
|---|---|
| Current NAV | $133,019.54 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -4.99% |
| Total Return | 33.02% |
| Annualized Return | 16.96% |
| Volatility (ann.) | 9.63% |
| Sharpe Ratio (ann.) | 1.7610 |

## Positions Table

- SPY: 16.5410%
- QQQ: 16.5410%
- IWM: 16.5410%
- EEM: 16.5410%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -0.7689729823169228, 'threshold': 0.5, 'date': '2026-10-30', 'persistence_days': 3}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -0.7690
- **Rolling 63-day Max DD:** -4.99%
- **Regime Persistence:** 144 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.14% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-26: NAV=$134,060.18, Ret=0.32%, Turnover=0.53%
- 2026-10-27: NAV=$134,964.32, Ret=0.67%, Turnover=0.55%
- 2026-10-28: NAV=$135,651.64, Ret=0.51%, Turnover=3.76%
- 2026-10-29: NAV=$135,161.06, Ret=-0.36%, Turnover=0.12%
- 2026-10-30: NAV=$133,019.54, Ret=-1.58%, Turnover=3.05%

## Drift Persistence Provenance

- **git_sha:** 4e3c96035da0f9c6cd9565fdf62b92e8d3f13993
- **paper_trading_state_sha256:** 46571f7ac64e203d7802ae13b1594edae82830f86468ff958b90b3e9117cd200
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
