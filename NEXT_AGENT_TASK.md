# Next Agent Task: Post-Close Gate Readiness Check — Cycle 163 (Pending Gate)

## Context

Session from Cycle 162 completed at 2026-10-15T17:20:22Z UTC. Post-close gate remains 2026-10-18T20:00:00Z UTC; gate not met. Current paper trading state (from `data/processed/paper_trading_state.yaml` as of 2026-10-14):
- Track record: 447 days (2025-01-02 → 2026-10-14)
- NAV: $135,043.35
- Sharpe: 1.9272
- Max DD: -2.93%
- Rolling 63d Sharpe (stored): 0.11333136870186329
- Cumulative returns/run_history/cumulative_dates: 447
- Last run date: 2026-10-14
- Regime flips: 6
- Drift flag persists (3 consecutive days)

Cycle 162 validation report: `research/reports/paper_trading_validation_162.md`. All verifications passed; supervisor tests 10/10 passed. No data fetch or replay performed (gate not met).

## Objective

1. **Timestamp gate enforcement**: Record UTC session time via `TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ`. If `session_time < 2026-10-18T20:00:00Z`, do **not** fetch or replay. Run verifications (2-3), supervisor tests (4), write `research/reports/paper_trading_validation_163.md`, and prepare next narrow task (continue gate monitoring). If `session_time >= 2026-10-18T20:00:00Z`, proceed to post-close fetch/replay per Cycle 162 gate-met logic.
2. **Independent rolling-63-day Sharpe verification**: Recompute rolling 63d Sharpe from last 63 `cumulative_returns` using `(mean*252)/(std(ddof=1)*sqrt(252))`. Must match `state.drift_flags.low_rolling_sharpe.value` within float precision.
3. **Regime flip verification**: Recompute regime flips from `run_history.regime_exposure` transitions. Expect 6 (no replay extension).
4. **Supervisor loop tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` must pass 10/10.
5. **Reporting**: Write `research/reports/paper_trading_validation_163.md` with UTC time, gate result, fetch/replay status (none if gate not met), state snapshot (counts, last run date), verification numbers, and test results.
6. **Next task**: Update `NEXT_AGENT_TASK.md` with one narrow, testable next task following evidence. Preserve restart-safety.

## Validation Commands (reference)
```bash
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ
python3 -c "
import yaml,math
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
ret=d['cumulative_returns'][-63:]
m=sum(ret)/len(ret); v=sum((r-m)**2 for r in ret)/(len(ret)-1); s=(m*252)/(math.sqrt(v)*math.sqrt(252)) if v>0 else 0
print('sharpe',s,d['drift_flags']['low_rolling_sharpe']['value'])
"
python3 -c "
import yaml
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
rh=d['run_history']; t=0; prev=rh[0]['regime_exposure']
for i in range(1,len(rh)):
  if rh[i]['regime_exposure']!=prev: t+=1; prev=rh[i]['regime_exposure']
print('flips',t,len(rh))
"
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries
- Research/backtesting only. No live trades, no live trading enablement, no credentials access.
- Do not fetch/replay when gate not met. Do not fabricate data, market findings, or test outputs.
- Do not add dependencies, services, paid data, scheduled jobs, agents, or workflows.
- Keep bounded, restart-safe. Document precisely if blocked.
