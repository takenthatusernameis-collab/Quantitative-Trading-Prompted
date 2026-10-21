# Experiment: Fold regime bootstrap CIs for `tsmomentum_spytrend_001` (tsmomentum_fold_regime_bootstrap_ci_001, Cycle 924)

## Hypothesis reference
- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (incumbent)
- Base attribution: `research/experiments/tsmomentum_fold_regime_attribution_001.md` (Cycle 923)
- Published walk-forward record: `research/experiments/tsmomentum_regime_filter_wf_001.md`

## Objective
Add read-only fold-block bootstrap CIs for within-bucket phase gaps (A-B) over F2/F3/F4, determine distinguishability from zero at 95%, and finalize a monitoring statement. Descriptive only.

## Method
- Unit: 48 folds resampled with replacement, preserving test_sharpe, phase label, bucket labels
- Statistic: phase_A mean - phase_B mean within bucket
- Resamples: 5000, seed 924, two-sided 95% percentile CI
- Buckets: F2/F3/F4 only (exactly as published)
- Distinguishable from zero if 95% CI excludes 0

## Results
- Anchor: 48 folds, mean 0.947307, median 1.293299, pooled trades 6013

### Bootstrap CIs (F2/F3/F4)

#### F2 SPY trend state at test-window start
| Bucket | n | Point gap (A-B) | 95% CI | Distinguishable from zero |
|---|---|---|---|---|
| risk_on | 37 | +0.006679 | [-0.625127, 0.597668] | no |
| risk_off | 11 | +3.447556 | [-1.207164, 11.680698] | no |

#### F3 SPY trailing 12-month return sign at test-window start
| Bucket | n | Point gap (A-B) | 95% CI | Distinguishable from zero |
|---|---|---|---|---|
| up | 38 | -0.013636 | [-0.617270, 0.578052] | no |
| down | 10 | +5.338808 | [-1.356871, 17.982161] | no |

#### F4 training-window 63-day realised volatility tercile
| Bucket | n | Point gap (A-B) | 95% CI | Distinguishable from zero |
|---|---|---|---|---|
| low_vol | 17 | +0.388819 | [-0.719057, 1.399440] | no |
| med_vol | 18 | +2.639079 | [-1.036874, 9.569775] | no |
| high_vol | 13 | -0.420066 | [-1.044460, 0.168416] | no |

## Finalized monitoring statement

Based on bootstrap 95% CIs (fold-block bootstrap, 5000 resamples, seed 924), none of the tested observable states (F2/F3/F4) show within-bucket phase gaps distinguishable from zero at 95% confidence. The apparent state-dependence is consistent with sampling noise in small buckets. This is a candidate monitoring input only — not wired into any gate, drift flag, threshold or decision mapping, and does not change the incumbent's published verdict (Credible Candidate).

## Decision
- No change to the incumbent's verdict (Credible Candidate). Bootstrap adds inference only; not used for selection/ranking/gate changes.

## Reproduction commands
```bash
python research/tsmomentum_fold_regime_bootstrap_ci.py
python -m pytest -q tests/test_tsmomentum_fold_regime_bootstrap_ci.py
git status --porcelain data/ config/
git diff --name-only HEAD -- research/run_cycle6.py research/experiments/tsmomentum_regime_filter_wf_001.md
```
