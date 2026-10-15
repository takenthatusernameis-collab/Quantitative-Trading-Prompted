# Next Agent Task: Prepare for Post-Close Gate Monitoring — Cycle 256

## Context

Cycle 255 validation completed (UTC 2026-10-15T20:21:09Z). Post-close gate remains 2026-10-18T20:00:00Z UTC. Gate not met; no fetch/replay performed. State unchanged (447 run_history entries, 6 regime flips). Rolling 63d Sharpe matches stored (diff 5.13e-16 < 1e-12). Supervisor loop tests passed 10/10. Report: `research/reports/paper_trading_validation_255.md`. Supervisor disposition recorded in `.kilo-runtime/worker-disposition.json` (recommendation_id `38762216276-attempt-1-review-0005-6996e9659a28`, disposition accepted).

## Objective

1. **Timestamp gate enforcement**: Record UTC time (`TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ`). If < 2026-10-18T20:00:00Z, do NOT fetch or replay. Run minimal verifications (rolling 63d Sharpe vs stored, regime flips count), run supervisor loop tests, write `research/reports/paper_trading_validation_256.md`, and prepare next narrow task. If >= 2026-10-18T20:00:00Z, proceed per established gate-met protocol (inspect for fetch/replay readiness, execute only if explicitly required and verifiably safe).
2. **Independent verification**: Recompute rolling 63d Sharpe from last 63 cumulative returns; must match stored drift flag value within float precision. Recompute regime flips from run_history transitions.
3. **Supervisor loop tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` must pass 10/10.
4. **Reporting**: Write validation report 256 with UTC time, gate state, fetch/replay status, state snapshot, verification numbers/diff, test results.
5. **Supervisor disposition**: Record disposition in `.kilo-runtime/worker-disposition.json` within next two tool calls (schema_version 1, recommendation_id copied exactly, disposition with reason/evidence/verification/updated_at as ISO-8601 UTC). Use current `recommendation_id` from `.kilo-runtime/current-supervisor-recommendation.json` if it exists; otherwise, include `recommendation_id` as `null` and proceed safely.

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
