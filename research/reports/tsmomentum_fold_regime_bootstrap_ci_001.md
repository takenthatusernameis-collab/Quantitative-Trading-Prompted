# Fold Regime Bootstrap CIs for the Incumbent Walk-Forward (tsmomentum_fold_regime_bootstrap_ci_001, Cycle 924)

## Summary

- Candidate: `tsmomentum_spytrend_001` (incumbent)
- Base attribution: Cycle 923 (tsmomentum_fold_regime_attribution_001)
- Bootstrap method: fold-block bootstrap (resample 48 folds with replacement), 5000 resamples, fixed seed 924, 95% CI
- Anchor reproduced: **YES** (48 folds, mean 0.947307)
- Incumbent verdict unchanged: **Credible Candidate (unchanged)**
- Descriptive only: no selection, re-ranking, re-fitting, gate changes, or verdict changes.

## F2 SPY trend state at test-window start

*risk-on if SPY Close >= its 200-day SMA at test-window start (point-in-time); risk-off otherwise*

| Bucket | n | Phase A n | Phase B n | Phase A mean | Phase B mean | Point-est gap (A-B) | 95% CI [lo, hi] | Distinguishable from zero |
|---|---|---|---|---|---|---|---|---|
| risk_on | 37 | 19 | 18 | 1.427814 | 1.421135 | +0.006679 | [-0.625127, 0.597668] | no |
| risk_off | 11 | 5 | 6 | 1.222473 | -2.225084 | +3.447556 | [-1.207164, 11.680698] | no |

## F3 SPY trailing 12-month return sign at test-window start

*sign of SPY trailing ~12-month (252 trading-day) return at test-window start; up / down*

| Bucket | n | Phase A n | Phase B n | Phase A mean | Phase B mean | Point-est gap (A-B) | 95% CI [lo, hi] | Distinguishable from zero |
|---|---|---|---|---|---|---|---|---|
| up | 38 | 18 | 20 | 1.393986 | 1.407622 | -0.013636 | [-0.617270, 0.578052] | no |
| down | 10 | 6 | 4 | 1.358181 | -3.980627 | +5.338808 | [-1.356871, 17.982161] | no |

## F4 training-window 63-day realised volatility tercile

*trailing 63-day realised vol of the strategy's own net returns at train_end, terciled within that fold's training window only; low / medium / high*

| Bucket | n | Phase A n | Phase B n | Phase A mean | Phase B mean | Point-est gap (A-B) | 95% CI [lo, hi] | Distinguishable from zero |
|---|---|---|---|---|---|---|---|---|
| low_vol | 17 | 7 | 10 | 1.767392 | 1.378572 | +0.388819 | [-0.719057, 1.399440] | no |
| med_vol | 18 | 10 | 8 | 1.489874 | -1.149205 | +2.639079 | [-1.036874, 9.569775] | no |
| high_vol | 13 | 7 | 6 | 0.852907 | 1.272973 | -0.420066 | [-1.044460, 0.168416] | no |

## Finalized monitoring statement

Based on bootstrap 95% CIs (fold-block bootstrap, 5000 resamples, seed 924), none of the tested observable states (F2/F3/F4) show within-bucket phase gaps distinguishable from zero at 95% confidence. The apparent state-dependence is consistent with sampling noise in small buckets. This is a candidate monitoring input only — not wired into any gate, drift flag, threshold or decision mapping, and does not change the incumbent's published verdict (Credible Candidate).

## Reproduction commands

```bash
python research/tsmomentum_fold_regime_bootstrap_ci.py
python -m pytest -q tests/test_tsmomentum_fold_regime_bootstrap_ci.py
git status --porcelain data/ config/
git diff --name-only HEAD -- research/run_cycle6.py research/experiments/tsmomentum_regime_filter_wf_001.md
```
