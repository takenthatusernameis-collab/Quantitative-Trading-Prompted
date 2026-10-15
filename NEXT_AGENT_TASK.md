# Next Agent Task: Continue Post-Close Gate Monitoring — Cycle 184

## Context

Cycle 183 validation completed at 2026-10-15T18:12:14Z UTC. Post-close gate remains 2026-10-18T20:00:00Z UTC; not met. State unchanged in structure (last run 2026-10-14). Drift flag persists (low_rolling_sharpe, 3 consecutive days). No fetch/replay performed.

Validation report: `research/reports/paper_trading_validation_183.md` (written). All checks passed.

## Objective

1. **Timestamp gate enforcement**: Record UTC session time via `TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ`. If `< 2026-10-18T20:00:00Z`, do **not** fetch or replay. Run minimal verifications (rolling 63d Sharpe match vs stored drift flag value, regime flips count), run supervisor loop tests, write `research/reports/paper_trading_validation_184.md`, and prepare next narrow task (continue gate monitoring). If `>= 2026-10-18T20:00:00Z`, proceed to post-close fetch/replay per established gate-met protocol.
2. **Independent verification**: Recompute rolling 63d Sharpe from last 63 cumulative returns; must match stored drift flag value within float precision. Recompute regime flips from run_history transitions; expect 6 (or report actual if changed).
3. **Supervisor loop tests**: `python3 .github/scripts/test_kilo_supervisor_loop.py -v` must pass 10/10.
4. **Reporting**: Write validation report with UTC time, gate state, fetch/replay status (none if pending), state snapshot (counts, last run date, current/peak NAV, max DD, stored Sharpe/rolling Sharpe, drift flags), verification numbers/diff, and test results.
5. **Next task**: Update `NEXT_AGENT_TASK.md` to Cycle 185 with one narrow, testable task following evidence. Preserve restart-safety.

## Validation Commands

```bash
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ
python3 <<'PY'
import yaml,math
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
ret=d['cumulative_returns'][-63:]
m=sum(ret)/len(ret); v=sum((r-m)**2 for r in ret)/(len(ret)-1)
s=(m*252)/(math.sqrt(v)*math.sqrt(252)) if v>0 else 0
print('sharpe_calc',s,'stored',d['drift_flags']['low_rolling_sharpe']['value'],'diff',abs(s-d['drift_flags']['low_rolling_sharpe']['value']))
PY
python3 <<'PY'
import yaml
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
rh=d['run_history']; t=0; prev=rh[0]['regime_exposure']
for i in range(1,len(rh)):
  if rh[i]['regime_exposure']!=prev: t+=1; prev=rh[i]['regime_exposure']
print('flips',t,len(rh), d['last_run_date'], d['current_nav'], d['max_drawdown'])
PY
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- Research/backtesting only. No live trades, no live trading enablement, no credentials access.
- Do not fetch/replay when gate not met. Do not fabricate data, market findings, or test outputs.
- Do not add dependencies, services, paid data, scheduled jobs, agents, or workflows.
- Keep bounded, restart-safe. Document precisely if blocked.
