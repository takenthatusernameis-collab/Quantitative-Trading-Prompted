# Paper-Trading Rolling Report

**Generated:** 2026-11-18 22:00:08 UTC
**Last Run Date:** 2026-11-18
**Days Tracked:** 472

## Current State

| Metric | Value |
|---|---|
| Current NAV | $130,307.21 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 30.31% |
| Annualized Return | 15.18% |
| Volatility (ann.) | 9.94% |
| Sharpe Ratio (ann.) | 1.5277 |

## Positions Table



## Drift Monitoring

- **high_turnover**: {'value': 0.5132058911351663, 'threshold': 0.5, 'date': '2026-11-18'}
- **regime_flip**: {'from': 1.0, 'to': 0.0, 'date': '2026-11-18'}
- **low_rolling_sharpe**: {'value': -1.9744867954469325, 'threshold': 0.5, 'date': '2026-11-18', 'persistence_days': 16}
- **regime_persistence_low**: {'value': 1, 'threshold': 5, 'date': '2026-11-18'}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -1.9745
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 1 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.15% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-12: NAV=$133,039.93, Ret=-0.49%, Turnover=0.18%
- 2026-11-13: NAV=$132,654.46, Ret=-0.29%, Turnover=0.01%
- 2026-11-16: NAV=$131,036.61, Ret=-1.22%, Turnover=0.55%
- 2026-11-17: NAV=$130,327.28, Ret=-0.54%, Turnover=0.35%
- 2026-11-18: NAV=$130,307.21, Ret=-0.02%, Turnover=51.32%

## Drift Persistence Provenance

- **git_sha:** c6865694f6ac7dcc9f0056a04ae0e2f0dcd16288
- **paper_trading_state_sha256:** bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
