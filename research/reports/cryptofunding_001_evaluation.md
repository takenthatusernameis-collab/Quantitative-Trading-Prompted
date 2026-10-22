# Cycle 945: cryptofunding_001 evaluation

First published in Cycle 944; the generator's cost model was corrected in Cycle 945 (see the correction section below and `research/experiments/cryptofunding_001_evaluation_erratum_001.md`).

## Frozen configuration
- Candidate: cryptofunding_001
- Universe: BTCUSDT, ETHUSDT
- Cost model: 5.0 bp/unit (flat) + 2.00%/yr capital charge on the spot leg
- Annualization: 365
- Headline rule: funding_positive_lagged

## Results (frozen configuration)
- Portfolio net ann (headline): 6.5212%
- Portfolio gross ann (no cost): 13.7966%
- always_on: gate_pass=False, sharpe_oos=3.154, pooled_oos_round_trips=0
- funding_positive_sameday: gate_pass=False, sharpe_oos=-3.956, pooled_oos_round_trips=95
- funding_positive_lagged: gate_pass=False, sharpe_oos=-4.378, pooled_oos_round_trips=95

## Cost model correction (Cycle 945)
The Cycle 944 generator passed the repository's **annual capital-charge rate** (0.02) into `net_series(book, cost_bps)`, so the published headline charged 0.02 **basis points** per unit of weight change instead of the frozen 5.0 bp/unit, and it applied **no** capital charge at all: the published headline was the gross return of the headline rule's portfolio. The published report nevertheless declared the frozen configuration's 5.0 bp/unit and 2.00%/yr. The numbers below are the corrected ones.

| Item | Cycle 944 (as published) | Cycle 945 (corrected) |
|---|---|---|
| Applied trading cost | 0.02 bp/unit (the annual capital-charge rate, passed into the flat-cost function) | 5.0 bp/unit (the frozen `total_round_trip_bps`) |
| Applied capital charge | none | 2.00%/yr on the spot leg |
| Portfolio net ann (headline, `funding_positive_lagged`) | 13.7746% | 6.5212% |
| Portfolio gross ann (no cost) | 13.7966% | 13.7966% |
| Mean per-symbol OOS Sharpe, `always_on` | 9.209 | 3.154 |
| Mean per-symbol OOS Sharpe, `funding_positive_sameday` | 1.762 | -3.956 |
| Mean per-symbol OOS Sharpe, `funding_positive_lagged` | 0.977 | -4.378 |

## Reconciliation with the prior cycles
Equal-weight BTC/ETH portfolio, 365-day annualization, no cost for the `gross_no_cost` row. The OOS window is 2025-01-01..2026-09-30 and the Sharpe is the canonical (arithmetic, zero risk-free) portfolio Sharpe.

| Rule | Cost convention | Full-sample net ann | OOS net ann | OOS Sharpe |
|---|---|---|---|---|
| always_on | gross (no cost) | +13.3957% | +3.9760% | +12.657 |
| always_on | frozen config (5 bp/unit + 2%/yr capital) | +10.1297% | +1.1608% | +3.702 |
| always_on | Cycle 891 flat 3 bp/unit | +12.7694% | +3.5123% | +11.144 |
| always_on | Cycle 892 venue taker + slippage + rf | +9.2190% | +0.4849% | +1.516 |
| funding_positive_sameday | gross (no cost) | +14.6742% | +4.6791% | +18.888 |
| funding_positive_sameday | frozen config (5 bp/unit + 2%/yr capital) | +7.3513% | -3.0724% | -5.039 |
| funding_positive_sameday | Cycle 891 flat 3 bp/unit | +11.3923% | +0.9577% | +2.131 |
| funding_positive_sameday | Cycle 892 venue taker + slippage + rf | +2.7733% | -8.1984% | -8.001 |
| funding_positive_lagged | gross (no cost) | +13.7966% | +4.2404% | +15.697 |
| funding_positive_lagged | frozen config (5 bp/unit + 2%/yr capital) | +6.5212% | -3.4869% | -5.549 |
| funding_positive_lagged | Cycle 891 flat 3 bp/unit | +10.5340% | +0.5295% | +1.128 |
| funding_positive_lagged | Cycle 892 venue taker + slippage + rf | +1.9706% | -8.5981% | -8.272 |

## Data integrity
- data/ unchanged: True
- config/ unchanged: True
- artifacts unchanged: True

## Reproduction
```bash
python research/cryptofunding_001_evaluation.py
python -m pytest tests/test_eval_cryptofunding_001.py -q
```
