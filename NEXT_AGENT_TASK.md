# Next Agent Task: Cycle 23 — Deployment Preparation Steps for Live Trading

## Context
Cycle 22 evaluated go/no-go for live deployment of `tsmomentum_spytrend_001` based on the accumulated evidence (Cycle 6 walk-forward, Cycles 8-21 paper trading). The go/no-go evaluation report at `research/reports/go_nogo_evaluation_001.md` recommended a **GO** decision with conditions for continued monitoring and operational controls.

## Objective
Define deployment preparation steps for transitioning the candidate `tsmomentum_spytrend_001` to live trading, given the research/backtesting-only constraint of this system. Since live trading is not permitted in this environment, the steps will focus on finalizing the research validation, documenting the live trading protocol, and preparing the necessary infrastructure specifications.

### Action Required
Create a deployment preparation plan that:
1. Documents the final validated strategy specification and parameters
2. Specifies the live trading infrastructure requirements (data feeds, execution, risk controls)
3. Outlines the monitoring and validation protocol for live trading
4. Documents the decision audit trail and evidence base
5. Prepares the final research handoff for potential live deployment outside this system

### Implementation Steps
1. **Finalize strategy specification** — document the exact parameters, risk overlays, and execution rules from `config/simulation_candidate_001.yaml` and the paper trading configuration
2. **Specify live trading infrastructure** — define requirements for market data feed, brokerage integration, order execution, and risk management systems
3. **Outline live monitoring protocol** — adapt the paper trading monitoring system for live trading, including real-time drift alerts and performance tracking
4. **Document evidence base** — compile all validation artifacts (walk-forward, paper trading, go/no-go report) into a comprehensive deployment dossier
5. **Update README.md** with deployment preparation summary
6. **Prepare NEXT_AGENT_TASK.md** for the subsequent cycle (which would be live trading monitoring if permitted, or a new research cycle)

## Acceptance Criteria
- [ ] Document final strategy specification and parameters
- [ ] Specify live trading infrastructure requirements (data, execution, risk controls)
- [ ] Outline live monitoring and validation protocol
- [ ] Compile evidence base into deployment dossier (`research/reports/deployment_dossier_001.md`)
- [ ] Update README.md with deployment preparation summary
- [ ] Prepare NEXT_AGENT_TASK.md for subsequent cycle

## Scope Boundaries
- Research/analysis and documentation only. No live trading, no credentials, no network access within this system.
- Focus on preparing the research handoff for potential live deployment outside this environment.
- Decision must be based on documented evidence from Cycle 22 go/no-go evaluation.

## Validation Commands
```bash
# Verify strategy specification
cat config/simulation_candidate_001.yaml

# Verify paper trading configuration (if exists)
ls -la config/paper_trading_*.yaml 2>/dev/null || echo "No paper trading config file"

# Verify go/no-go report exists and recommends GO
grep -i "decision:.*go" research/reports/go_nogo_evaluation_001.md

# Verify deployment dossier will be created
ls -la research/reports/deployment_dossier_001.md 2>/dev/null || echo "Deployment dossier not yet created"

# Check README.md for deployment preparation summary
grep -A 10 -B 2 "Cycle 23" README.md
```