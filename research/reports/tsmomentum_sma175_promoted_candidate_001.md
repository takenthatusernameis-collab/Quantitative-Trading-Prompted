# TSMomentum SMA-175 Promoted Candidate (tsmomentum_sma175_promoted_candidate_001, Cycle 917)

## Candidate definition
- Parent: tsmomentum_spytrend_001
- Variant: SPY SMA window = 175 (baseline SMA = 200)
- Cost model: repository default (get_cost_params)
- Point-in-time: published WF splits, purge 21d / embargo 21d

## Walk-forward results
- Folds: 48
- WF mean OOS Sharpe: 1.539964
- Phase A (odd folds) mean: 1.539145 (24 folds, 2922 pooled trades)
- Phase B (even folds) mean: 1.540784 (24 folds, 3024 pooled trades)
- Thin-trade folds (<=10 trades): [12]; excluding them mean 1.566792, gate-1 PASS

## Phase stability
- Gate-1 unchanged between phases: YES
- Thin-trade exclusion does not change gate-1: YES
- Phase means average to published mean: YES

## Costs and point-in-time guarantees
- Costs applied via repository cost params (fees + slippage).
- Point-in-time universe and splits per published design; no lookahead.

## Status
- NOT the incumbent baseline. Incumbent (SMA-200) baseline in run_cycle6.py unchanged.
- Tracked as separate candidate for independent evaluation.

## Migration path to incumbent (future)
1. Update SPY_SMA_WINDOW in research/run_cycle6.py from 200 to 175.
2. Regenerate committed artifacts dependent on baseline: validation, decision, phase-stability reports/experiments.
3. Update anchor tests (test_incumbent_phase_stability_audit.py) expected hashes/values.
4. Re-run full test suite; verify read-only guarantees for new baseline.
