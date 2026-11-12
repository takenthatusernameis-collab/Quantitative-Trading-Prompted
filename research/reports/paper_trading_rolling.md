# Paper-Trading Rolling Report

**Generated:** 2026-11-12 22:01:19 UTC
**Last Run Date:** 2026-11-12
**Days Tracked:** 468

## Current State

| Metric | Value |
|---|---|
| Current NAV | $133,039.93 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 33.04% |
| Annualized Return | 16.62% |
| Volatility (ann.) | 9.92% |
| Sharpe Ratio (ann.) | 1.6747 |

## Positions Table

- SPY: 12.8786%
- QQQ: 12.8786%
- IWM: 12.8786%
- EEM: 12.8786%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -1.3137210439928235, 'threshold': 0.5, 'date': '2026-11-12', 'persistence_days': 12}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -1.3137
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 153 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.15% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-06: NAV=$130,874.77, Ret=0.68%, Turnover=0.65%
- 2026-11-09: NAV=$132,932.13, Ret=1.57%, Turnover=3.05%
- 2026-11-10: NAV=$132,498.03, Ret=-0.33%, Turnover=0.24%
- 2026-11-11: NAV=$133,688.64, Ret=0.90%, Turnover=0.95%
- 2026-11-12: NAV=$133,039.93, Ret=-0.49%, Turnover=0.18%

## Drift Persistence Provenance

- **git_sha:** ebe98fe306c085a9e56d926415f7bc8baabeee36
- **paper_trading_state_sha256:** 2dace0e3e1accf00a749cde2baf6470b5e2abc61e542fe636854910361dec88a
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
