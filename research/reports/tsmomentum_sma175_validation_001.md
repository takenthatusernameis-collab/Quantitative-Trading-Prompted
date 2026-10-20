# TSMomentum SMA-175 Validation (tsmomentum_sma175_validation_001, Cycle 914)

## Summary

- Candidate: `tsmomentum_spytrend_001`
- Change validated: SPY SMA window 200 -> 175 days
- run_cycle6.py still has SMA baseline: True
- WF SMA-200 mean Sharpe: 0.9473 (folds 48)
- WF SMA-175 mean Sharpe: 1.5400 (folds 48)
- Plateau (6 windows): passes 6/6 (robust=True)
- Data/config unchanged: True

## Checks

- [cache_loaded]: PASS
- [wf_sma200_folds]: PASS
- [wf_sma175_folds]: PASS
- [wf_sma200_mean_sharpe_exists]: PASS
- [wf_sma175_mean_sharpe_exists]: PASS
- [plateau_windows]: PASS
- [data_unchanged]: PASS
- [config_unchanged]: PASS
- [committed_artifacts_unchanged]: PASS
