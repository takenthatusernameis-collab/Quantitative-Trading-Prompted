# NEXT_AGENT_TASK.md

## Cycle 915 — Decide promotion for tsmomentum_spytrend_001 with SMA-175

### Context
Cycle 914 validated SMA-175 under the full published protocol (48-fold walk-forward, plateau). The reports show SMA-175 improves phase stability (Cycle 913) and passes all validation gates with data/config unchanged, run_cycle6.py still uses SMA-200.

### Objective
Make a promotion decision for the SMA-175 variant: update decision records if warranted, or document why not promoting. If promoting, change only what is necessary and record evidence. If not promoting, produce concrete evidence-based next task.

### Acceptance criteria
1. Review `research/reports/tsmomentum_sma175_validation_001.md` and `research/experiments/tsmomentum_sma175_validation_001.md`.
2. If SMA-175 meets all promotion gates (wf mean >= 0.9, positive folds >= 50%, plateau passes), consider promoting to candidate definition; otherwise explain rejection with evidence.
3. If promoting, update `research/run_cycle6.py` to use `SPY_SMA_WINDOW = 175` and regenerate affected artifacts; run verification. If not promoting, do not change gates/thresholds/cost model.
4. Write decision to `research/reports/tsmomentum_sma175_decision_001.md` and update experiment record if changed.
5. No new dependencies/workflows; preserve read-only guarantees for data/config.

### Scope boundaries
Bounded decision cycle; if uncertain, prefer not promoting and propose specific test.
