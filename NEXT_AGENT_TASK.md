# Next Agent Task: Cycle 24 — Continued Prospective Monitoring or New Research Cycle

## Context
Cycle 23 completed the deployment preparation for `tsmomentum_spytrend_001`. The deployment dossier at `research/reports/deployment_dossier_001.md` documents the final strategy specification, live trading infrastructure requirements, monitoring protocol, evidence base, decision audit trail, and risk assessment. The go/no-go evaluation (Cycle 22) recommended **GO** for live deployment subject to operational controls.

Since this system is for **research/backtesting only** and does not engage in live trading, the subsequent cycle has two viable paths:

1. **Option A (Continued Monitoring):** Extend the paper trading track record further to accumulate more live-like evidence, monitor for regime changes, and maintain the validated candidate in a "ready" state.
2. **Option B (New Research Cycle):** Begin a new hypothesis-driven research cycle exploring a different market inefficiency (e.g., alternative regime filters, new asset classes, cross-sectional signals), as all prior momentum/calendar/macro candidates have been evaluated and either rejected or promoted.

## Objective
Choose and execute **one** of the two paths above as a bounded, verifiable task. The choice should be justified by the current evidence state and research priorities.

## Acceptance Criteria

### If Option A (Continued Monitoring):
- [ ] Run `research/run_paper_trading_replay.py` to extend the paper trading track record by at least 20 trading days (using cached data up to the latest available date)
- [ ] Update `research/reports/paper_trading_rolling.md` with latest state
- [ ] Update `research/reports/paper_trading_validation_003.md` with extended validation results
- [ ] Verify no drift flags triggered (or document any triggered flags with analysis)
- [ ] Update README.md with Cycle 24 monitoring summary
- [ ] Prepare NEXT_AGENT_TASK.md for Cycle 25

### If Option B (New Research Cycle):
- [ ] Review `research/reports/opportunity_shortlist.md` and `research/reports/data_inventory.md` for viable candidates
- [ ] Select one candidate with sufficient data support for valid testing
- [ ] Create pre-registered hypothesis document in `research/hypotheses/`
- [ ] Create frozen config in `config/`
- [ ] Define evaluation plan (walk-forward design, benchmarks, falsification conditions)
- [ ] Document in NEXT_AGENT_TASK.md for Cycle 25 (evaluation execution)

## Scope Boundaries
- Research/analysis and documentation only. No live trading, no credentials, no network access within this system.
- Must follow AGENTS.md research standards (hypothesis-first, baseline-before-complexity, honest accounting).
- If Option B: Candidate must have real cached data support; no speculative data assumptions.
- If Option A: Use only existing cached data; no new data fetching required.

## Validation Commands

```bash
# Verify deployment dossier exists
ls -la research/reports/deployment_dossier_001.md

# Check current paper trading state
python3 -c "
import yaml
with open('data/processed/paper_trading_state.yaml') as f:
    state = yaml.safe_load(f)
print(f'Track record: {len(state[\"run_history\"])} days')
print(f'Last run: {state[\"last_run_date\"]}')
print(f'Current NAV: \${state[\"current_nav\"]:,.2f}')
print(f'Max DD: {state[\"max_drawdown\"]:.2%}')
regimes = [r['regime_exposure'] for r in state['run_history']]
flips = sum(1 for i in range(1, len(regimes)) if regimes[i] != regimes[i-1])
print(f'Regime flips: {flips}')
"

# Check available cached data end date
ls -la data/raw/*.parquet | head -5

# Verify opportunity shortlist exists
cat research/reports/opportunity_shortlist.md | head -30

# Check for any new hypothesis/config files
ls -la research/hypotheses/*.md config/*.yaml
```