# Experiment: cryptofunding_001_evaluation (Cycle 945)

First published in Cycle 944. **Correction (Cycle 945):** the Cycle 944 generator applied 0.02 bp/unit of trading cost and no capital charge instead of the frozen 5.0 bp/unit and 2.00%/yr, so the published headline was the gross return of the headline rule's portfolio. The generator is corrected, the artifacts are regenerated, and the correction is of record in `research/experiments/cryptofunding_001_evaluation_erratum_001.md`. The verdict (exploratory signal, not promoted) is unchanged.

## Hypothesis
- research/hypotheses/cryptofunding_001.md (frozen)

## Configuration
- config/cryptofunding_001.yaml (frozen)

## Evaluation
- Overall: PASS
- Portfolio net ann (headline, funding_positive_lagged): 6.5212%
- always_on: gate_pass=False, sharpe_oos=3.154
- funding_positive_sameday: gate_pass=False, sharpe_oos=-3.956
- funding_positive_lagged: gate_pass=False, sharpe_oos=-4.378
- Cache-only: true
- Network fetches: none

## Reproduction
```bash
python research/cryptofunding_001_evaluation.py
python -m pytest tests/test_eval_cryptofunding_001.py -q
```
