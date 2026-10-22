# Cycle 944: cryptofunding_001 evaluation

## Frozen configuration
- Candidate: cryptofunding_001
- Universe: BTCUSDT, ETHUSDT
- Cost model: 5.0 bp/unit
- Annualization: 365

## Results
- Portfolio net ann (headline): 13.7746%
- always_on: gate_pass=False, sharpe_oos=9.209
- funding_positive_sameday: gate_pass=False, sharpe_oos=1.762
- funding_positive_lagged: gate_pass=False, sharpe_oos=0.977

## Data integrity
- data/ unchanged: True
- config/ unchanged: True
- artifacts unchanged: True

## Reproduction
```bash
python research/cryptofunding_001_evaluation.py
python -m pytest tests/test_eval_cryptofunding_001.py -q
```
