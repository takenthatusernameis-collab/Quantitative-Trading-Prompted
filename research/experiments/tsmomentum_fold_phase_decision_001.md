# Experiment: Fold-phase decision for `tsmomentum_spytrend_001` (tsmomentum_fold_phase_decision_001, Cycle 912)

## Hypothesis reference

- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (Cycle 5 promoted candidate)
- Published record: `research/experiments/tsmomentum_regime_filter_wf_001.md` (resolved by content)
- Cycle 911 evidence: `research/experiments/tsmomentum_walkforward_mean_robustness_001.md`

## Objective

Produce a decision record comparing the published walk-forward evidence under fold-phase decomposition and state whether the incumbent remains a credible candidate or should be downgraded to exploratory, without changing gates/params/protocol.

## Evidence (from Cycle 911)

- Phase A (odd folds): mean 1.385035, gate-1 PASS
- Phase B (even folds): mean 0.509580, gate-1 FAIL
- Thin-trade folds: [12, 13]; most influential fold 12
- Published PASS stable: False

## Decision

- Label: Downgrade to Exploratory (not promotable as-is)
- Detail: Published PASS is not phase-stable: phase B (even folds) fails gate-1 (mean 0.509580 < 0.9) while phase A passes; the 48-fold mean is an interleaving average. Thin-trade folds (12,13) dominate influence but excluding them still gives mean 1.468851 (PASS); the instability is primarily phase-based, not thin-trade-based. Evidence insufficient for promotion without phase-stable validation.

## Conclusion

The incumbent's published PASS is not phase-stable (phase B fails gate-1). As-is promotion is not supported by the evidence; the candidate should be downgraded to exploratory pending phase-stable validation or redesign.

## Reproduction

```bash
python research/tsmomentum_fold_phase_decision_audit.py
python -m pytest -q tests/test_tsmomentum_fold_phase_decision_audit.py
```
