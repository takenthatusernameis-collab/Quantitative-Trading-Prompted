# Next Agent Task: Post-Gate Data Acquisition Check — Cycle 417

## Context
Cycle 416 completed at 2026-10-16T00:35:06Z. Gate is 2026-10-18T20:00:00Z; now is < gate. No fetch/replay performed. State: 447 run_history (2025-01-02 → 2026-10-14), 6 regime flips, last_run_date 2026-10-14. Report: research/reports/paper_trading_validation_416.md. Supervisor disposition recorded in .kilo-runtime/worker-disposition.json (schema_version 1, disposition verified).

## Objective
1. Record UTC time (TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ).
2. If < 2026-10-18T20:00:00Z: do NOT fetch or replay. Run minimal verifications (rolling 63d Sharpe vs stored, regime flips count), run supervisor loop tests, write research/reports/paper_trading_validation_417.md, prepare next narrow task with same gate.
3. If >= 2026-10-18T20:00:00Z: proceed per established gate-met protocol — re-attempt data acquisition from Yahoo Finance (force=True, end_date 2026-11-30) for the 7-ETF incumbent universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) plus SPY and ^VIX, verify per-symbol max dates, re-run research/run_paper_trading_replay.py (end_date per yfinance exclusive-end semantics), confirm track record extension/regime/drift state, write validation report with results.
4. Independent verification: recompute rolling 63d Sharpe from last 63 cumulative returns; must match stored drift flag within float precision. Recompute regime flips from run_history.
5. Supervisor loop tests: python3 .github/scripts/test_kilo_supervisor_loop.py -v must pass 10/10.
6. Reporting: write validation report 417 with UTC time, gate state, fetch/replay status, state snapshot, verification numbers/diff, test results.
7. Supervisor disposition: record disposition in .kilo-runtime/worker-disposition.json within next two tool calls, using current recommendation_id from .kilo-runtime/current-supervisor-recommendation.json if it exists; otherwise null. Follow schema_version 1 with reason/evidence/verification/updated_at as ISO-8601 UTC.

## Validation Commands
```bash
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ
python3 <<'PY'
import yaml,math
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
ret=d['cumulative_returns'][-63:]
if len(ret)>1:
    m=sum(ret)/len(ret); v=sum((r-m)**2 for r in ret)/(len(ret)-1)
else: m=ret[0] if ret else 0; v=0
s=(m*252)/(math.sqrt(v)*math.sqrt(252)) if v>0 else 0
stored = d['drift_flags']['low_rolling_sharpe']['value']
print('diff',abs(s-stored))
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
print('flips',t,'len',len(rh))
PY
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries
- No strategy changes or dependency modifications.
- Data ingestion/replay only if the post-close gate is met; otherwise monitoring/verification and reporting only.
- Do not commit changes unless explicitly requested.
