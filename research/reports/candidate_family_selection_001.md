# Candidate Family Selection (Cycle 868)

## Candidate inventory
- `tsmomentum_spytrend_001` (incumbent): NO-GO on long sample (Sharpe 0.5646, PSR 0.000).
- `csmomentum_001`: cross-sectional momentum over 18 ETFs; common history limited by DBC inception 2006-02-06.
- `macroregime_001`: time-series momentum on 7 core ETFs + VIX regime gate; common start 2004-11-18.
- `sectorrotation_001`: cross-sectional momentum over 9 sector ETFs; common start 1998-12-22, aligned inception.

## Scoring (1-5)
| Family | Data readiness | Structural mechanism | Net capture feasibility | Robustness/power | Liquidity/capacity | Automation | Diversification | Total |
|---|---|---|---|---|---|---|---|---|
| csmomentum_001 | 3 | 3 | 3 | 4 | 4 | 4 | 3 | 24 |
| macroregime_001 | 4 | 3 | 3 | 3 | 5 | 4 | 2 | 24 |
| sectorrotation_001 | 5 | 4 | 4 | 4 | 5 | 5 | 4 | 31 |

## Chosen family
`sectorrotation_001` — selected for longest aligned history (1998-12-22), clean 9-ETF inception alignment, documented cross-sectional momentum mechanism, and diversification from incumbent large-cap crypto/SPY exposure.

## Next step
Prepare long-sample feasibility using `research/promotion_feasibility_backtest.py` pattern with `config/sectorrotation_candidate_001.yaml`, output `research/reports/sectorrotation_long_sample_feasibility_001.md`. No code/config/data changes in this cycle.
