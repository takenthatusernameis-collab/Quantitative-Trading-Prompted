# Paper-Trading Rolling Report

**Generated:** 2026-11-05 22:00:12 UTC
**Last Run Date:** 2026-11-05
**Days Tracked:** 463

## Current State

| Metric | Value |
|---|---|
| Current NAV | $129,990.36 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 29.99% |
| Annualized Return | 15.35% |
| Volatility (ann.) | 9.87% |
| Sharpe Ratio (ann.) | 1.5546 |

## Positions Table

- SPY: 14.0269%
- QQQ: 14.0269%
- IWM: 14.0269%
- EEM: 14.0269%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -2.1202794870108126, 'threshold': 0.5, 'date': '2026-11-05', 'persistence_days': 7}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -2.1203
- **Rolling 63-day Max DD:** -6.56%
- **Regime Persistence:** 148 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.14% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-30: NAV=$133,019.54, Ret=-1.58%, Turnover=3.05%
- 2026-11-02: NAV=$132,606.80, Ret=-0.31%, Turnover=2.84%
- 2026-11-03: NAV=$132,866.04, Ret=0.20%, Turnover=0.16%
- 2026-11-04: NAV=$133,995.42, Ret=0.85%, Turnover=0.98%
- 2026-11-05: NAV=$129,990.36, Ret=-2.99%, Turnover=12.08%

## Drift Persistence Provenance

- **git_sha:** 08055741293010673b6e11e28419d41af9bb6d1e
- **paper_trading_state_sha256:** f9572aed9ca9c90d5c2ba7c2dbde2cbc573509636de2b5cc231073f06eee0c28
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
