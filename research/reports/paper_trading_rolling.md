# Paper-Trading Rolling Report

**Generated:** 2026-11-16 22:00:09 UTC
**Last Run Date:** 2026-11-16
**Days Tracked:** 470

## Current State

| Metric | Value |
|---|---|
| Current NAV | $131,036.61 |
| Peak NAV | $139,120.07 |
| Paper Drawdown | -6.56% |
| Total Return | 31.04% |
| Annualized Return | 15.60% |
| Volatility (ann.) | 9.95% |
| Sharpe Ratio (ann.) | 1.5677 |

## Positions Table

- SPY: 12.7433%
- QQQ: 12.7433%
- IWM: 12.7433%
- EEM: 12.7433%

## Drift Monitoring

- **low_rolling_sharpe**: {'value': -1.5917275518816598, 'threshold': 0.5, 'date': '2026-11-16', 'persistence_days': 14}

## Enhanced Drift Monitoring

- **Rolling 63-day Sharpe:** -1.5917
- **Rolling 63-day Max DD:** -6.54%
- **Regime Persistence:** 155 days in current regime
- **vol_scale range:** [0.437, 1.000]
- **dd_scale range:** [1.000, 1.000]
- **Turnover (median/p95):** 0.15% / 50.00%

## Performance Tracking

- Go/No-Go Status (after 63 days): READY TO EVALUATE
- Target Sharpe: >= 0.9
- Max DD Threshold: <= 15.00%

## Run History (Recent)

- 2026-11-10: NAV=$132,498.03, Ret=-0.33%, Turnover=0.24%
- 2026-11-11: NAV=$133,688.64, Ret=0.90%, Turnover=0.95%
- 2026-11-12: NAV=$133,039.93, Ret=-0.49%, Turnover=0.18%
- 2026-11-13: NAV=$132,654.46, Ret=-0.29%, Turnover=0.01%
- 2026-11-16: NAV=$131,036.61, Ret=-1.22%, Turnover=0.55%

## Drift Persistence Provenance

- **git_sha:** c2cc1aafeeadc7b31e0d41a0328085efb18e7942
- **paper_trading_state_sha256:** 8a1d29960142bca9aa4d9673e06f64775593d9402622612209bae66bf9965ee1
- **paper_trading_config_sha256:** 37a2a654c7f6f41924aba13d986d5aa2dd4072770d1142485d76a92c5e92bd8d
