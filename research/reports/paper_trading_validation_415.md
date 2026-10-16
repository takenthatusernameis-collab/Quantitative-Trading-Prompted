# Paper Trading Validation Report — Cycle 415

**Generated (UTC):** 2026-10-16T00:32:39Z
**Gate:** 2026-10-18T20:00:00Z
**Gate Met:** false
**Action Taken:** monitoring/verification only (no fetch/replay)

## State Snapshot
- Run history entries: 447 (2025-01-02 → 2026-10-14)
- Last run date: 2026-10-14
- Regime flips: 6 (recomputed from run_history)
- Rolling 63d Sharpe (recomputed from last 63 cumulative returns): stored drift flag matches within float precision (diff = 5.134781488891349e-16)

## Verification
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

## Observed Results
- Rolling Sharpe recomputation matches stored drift flag: diff 5.13e-16 ✓
- Regime flips: 6 of 447 run_history entries ✓
- Supervisor loop tests: 10/10 passed ✓

## Conclusion
Gate not met; no data acquisition or replay performed. State remains consistent. Ready to proceed to next cycle when gate conditions change.
