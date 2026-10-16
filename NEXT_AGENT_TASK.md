# Next Agent Task: Post-Gate Data Acquisition Check — Cycle 484

## Context
Cycle 483 completed at 2026-10-16T02:29:52Z. Gate is 2026-10-18T20:00:00Z. State unchanged from 482: 447 run_history (2025-01-02 → 2026-10-14), 6 regime flips, last_run_date 2026-10-14. Drift: low_rolling_sharpe persists (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133); not yet >20d persistence threshold. All primary gates pass. Validation report 483 written. Worker disposition recorded (verified, recommendation_id 38817660960-attempt-1-review-0003-2ac0cb7d6609).

## Objective
1. Record UTC time (TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ).
2. If < 2026-10-18T20:00:00Z: do NOT fetch or replay. Run minimal verifications:
- Rolling 63d Sharpe computed from last 63 cumulative_returns matches stored drift flag within float precision.
- Regime flips count recomputed from run_history matches 6.
- Supervisor loop tests: python3 .github/scripts/test_kilo_supervisor_loop.py -v must pass 10/10.
3. Write research/reports/paper_trading_validation_484.md with UTC time, gate state, status, verification numbers/diff, test results.
4. Supervisor disposition: record disposition in .kilo-runtime/worker-disposition.json within next two tool calls, using current recommendation_id from .kilo-runtime/current-supervisor-recommendation.json if it exists; otherwise null. Follow schema_version 1 with reason/evidence/verification/updated_at as ISO-8601 UTC.
5. If >= 2026-10-18T20:00:00Z: proceed per established gate-met protocol — re-attempt data acquisition from Yahoo Finance (force=True, end_date 2026-11-30) for 7-ETF incumbent universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) plus SPY and ^VIX; verify per-symbol max dates; re-run research/run_paper_trading_replay.py (end_date per yfinance exclusive-end semantics); confirm track record extension/regime/drift state; write detailed validation report.

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
- Monitoring/verification only while gate < 2026-10-18T20:00:00Z.
- Do not commit changes unless explicitly requested.
