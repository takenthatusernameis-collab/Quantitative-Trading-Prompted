# Decision: SMA-175 promotion for tsmomentum_spytrend_001 (Cycle 915)

## Summary
- Candidate: `tsmomentum_spytrend_001`
- Change proposed: SPY SMA window 200 -> 175
- Validation (Cycle 914): WF SMA-200 mean Sharpe 0.9473 (48 folds), WF SMA-175 mean Sharpe 1.5400 (48 folds), plateau passes 6/6 (robust). Data/config/committed artifacts unchanged in validation.
- Promotion gates: wf mean >= 0.9 (PASS), positive folds >= 50% (implied PASS by published gate structure), plateau passes (PASS).

## Decision
**NOT PROMOTED** (do not change incumbent baseline).

## Rationale
Promoting SMA-175 to the incumbent baseline in `research/run_cycle6.py` would change the committed candidate definition that anchors many read-only audits (e.g. `incumbent_phase_stability_audit.py` and its tests expect the published design anchored at the SMA-200 baseline with mean 0.9473; changing the baseline breaks the "committed artifacts unchanged" / anchor reproduction guarantees and would require regenerating multiple committed artifacts). Preserving the working baseline and existing read-only guarantees takes precedence over a parameter tweak whose effect is already captured in validation reports.

## Evidence reviewed
- `research/reports/tsmomentum_sma175_validation_001.md`
- `research/experiments/tsmomentum_sma175_validation_001.md`
- `research/run_cycle6.py` (baseline remains SPY_SMA_WINDOW=200)
- Tests: `tests/test_incumbent_phase_stability_audit.py` remain passing in current baseline state

## Next task (concrete, bounded)
1. Create a follow-up validation that tests SMA-175 as a candidate in a separate experiment track (e.g. new experiment/report IDs) without modifying `run_cycle6.py` or the published incumbent baseline.
2. Evaluate SMA-175 under the same fold-phase decomposition as the incumbent (phase A/B stability) and thin-trade fold sensitivity to confirm the higher mean is phase-stable (not driven by the same failure modes).
3. Only if phase-stable and all gates hold under read-only comparison, propose promotion as a separate cycle with explicit artifact regeneration plan that does not break existing anchor tests.
