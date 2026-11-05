# Paper-Trading Rolling Report

**Generated:** 2026-11-04 22:00:14 UTC
**Last Run Date:** 2026-11-04
**Days Tracked:** 462

## Current State

| Metric | Value |
|---|---|
| Current NAV | $133,995.42 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -4.99% |
| Total Return | 34.00% |
| Annualized Return | 17.31% |
| Volatility (ann.) | 9.62% |
| Sharpe Ratio (ann.) | 1.7988 |

## Positions Table

- SPY: 17.0471%
- QQQ: 17.0471%
- IWM: 17.0471%
- EEM: 17.0471%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -0.872439579425076, 'threshold': 0.5, 'date': '2026-11-04', 'persistence_days': 6}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -0.8724
- **Rolling 63-day Max DD:** -4.99%
- **Regime Persistence:** 147 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.14% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-10-29: NAV=$135,161.06, Ret=-0.36%, Turnover=0.12%
- 2026-10-30: NAV=$133,019.54, Ret=-1.58%, Turnover=3.05%
- 2026-11-02: NAV=$132,606.80, Ret=-0.31%, Turnover=2.84%
- 2026-11-03: NAV=$132,866.04, Ret=0.20%, Turnover=0.16%
- 2026-11-04: NAV=$133,995.42, Ret=0.85%, Turnover=0.98%

## Drift Persistence Provenance

- **git_sha:** 1e646ad4147f5b7a4c39cc0933faa39973395179
- **paper_trading_state_sha256:** 0f15797eb0707b90b77c32a3a6426d701c7ace8837587f1c0a8cc6a48dd27887
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
