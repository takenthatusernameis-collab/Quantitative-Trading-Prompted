# Next Agent Task: Continue Post-Close Gate Monitoring — Cycle 221

## Context

Cycle 220 validation completed at 2026-10-15T19:34:22Z UTC. Post-close gate remains 2026-10-18T20:00:00Z UTC; not met. No fetch/replay performed (git status clean). State unchanged relative to cycle 219 baseline (447 run_history entries, 6 regime flips). Validation report: `research/reports/paper_trading_validation_220.md`. All checks passed.

## Objective

1. **Timestamp gate enforcement**: Record UTC session time via `TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ`. If < 2026-10-18T20:00:00Z, do NOT fetch or replay. Run minimal verifications (rolling 63d Sharpe match vs stored, regime flips count), run supervisor loop tests, write `research/reports/paper_trading_validation_221.md`, and prepare next narrow task. If >= 2026-10-18T20:00:00Z, proceed per established gate-met protocol.
2. **Independent verification**: Recompute rolling 63d Sharpe from last 63 cumulative returns; must match stored drift flag value within float precision. Recompute regime flips from run_history transitions.
3. **Supervisor loop tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` must pass 10/10.
4. **Reporting**: Write validation report 221 with UTC time, gate state, fetch/replay status, state snapshot, verification numbers/diff, test results.
5. **Supervisor disposition**: Record disposition in `.kilo-runtime/worker-disposition.json` within next two tool calls.

## Validation Commands

```bash
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ
python3 <<'PY'
import yaml,math
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
ret=d['cumulative_returns'][-63:]
m=sum(ret)/len(ret); v=sum((r-m)**2 for r in ret)/(len(ret)-1) if len(ret)>1 else 0
s=(m*252)/(math.sqrt(v)*math.sqrt(252)) if v>0 else 0
stored = d['drift_flags']['low_rolling_sharpe']['value']
print('sharpe_calc',s,'stored',stored,'diff',abs(s-stored))
PY
python3 <<'PY'
import yaml
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
rh=d['run_history']
t=0
if rh:
    prev=rh[0]['regime_exposure']
    for i in range(1,len(rh)):
        if rh[i]['regime_exposure']!=prev: t+=1; prev=rh[i]['regime_exposure']
df=d['drift_flags']['low_rolling_sharpe']
print('flips',t,'len',len(rh),'last_run_date',d['last_run_date'],'current_nav',d['current_nav'],'peak_nav',d['peak_nav'],'max_dd',d['max_drawdown'],'rolling',df.get('value'),'active',df.get('active',df.get('triggered',False)))
PY
git status --short
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries
- Research/backtesting only. No live trades/credentials.
- No fetch/replay if gate not met. No fabricated data/outputs.
- No new dependencies/services/workflows. Bounded, restart-safe.