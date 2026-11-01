# Paper-Trading Rolling Report

**Generated:** 2026-11-01 13:11:17 UTC
**Last Run Date:** 2026-10-29
**Days Tracked:** 458

## Current State

| Metric | Value |
|---|---|
| Current NAV | $135,161.06 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -4.99% |
| Total Return | 35.16% |
| Annualized Return | 18.03% |
| Volatility (ann.) | 9.56% |
| Sharpe Ratio (ann.) | 1.8856 |

## Positions Table

- SPY: 17.3037%
- QQQ: 17.3037%
- IWM: 17.3037%
- EEM: 17.3037%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': 0.17524759593550826, 'threshold': 0.5, 'date': '2026-10-29', 'persistence_days': 2}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** 0.1752
- **Rolling 63-day Max DD:** -4.99%
- **Regime Persistence:** 143 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.14% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-23: NAV=$133,634.38, Ret=-0.06%, Turnover=0.06%
- 2026-10-26: NAV=$134,060.18, Ret=0.32%, Turnover=0.53%
- 2026-10-27: NAV=$134,964.32, Ret=0.67%, Turnover=0.55%
- 2026-10-28: NAV=$135,651.64, Ret=0.51%, Turnover=3.76%
- 2026-10-29: NAV=$135,161.06, Ret=-0.36%, Turnover=0.12%

## Drift Persistence Provenance

- **git_sha:** bfe58f51544e9b33e303f09103aeabcbfbd4fafa
- **paper_trading_state_sha256:** bd0867338224e78aaf916c2399b4cb4e475eeb37fc528d92b9a7e4aa7d4fbb17
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
