# Paper Trading Validation Report — Cycle 85

## Session Timestamp
- **UTC session time**: 2026-10-15T05:53:06Z (recorded via `TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ`)

## Timestamp Gate
- **Post-close gate**: 2026-10-16T20:00:00Z
- **Gate status**: NOT MET (session time 2026-10-15T05:53:06Z < gate)
- **Action**: No fetch attempted per protocol. Documenting timing and handing off with the same gate for the next cycle.

## Verification Results

### 1. Independent Rolling-63-Day Sharpe
- Recomputed from `data/processed/paper_trading_state.yaml` `cumulative_returns` (last 63) via `(mean*252)/(std(ddof=1)*sqrt(252))`
- **Computed**: 0.11333136870186278
- **Stored** (`drift_flags.low_rolling_sharpe.value`): 0.11333136870186329
- **Difference**: 5.13e-16 (float64 rounding only) — **MATCH**

### 2. Regime Flip Verification
- Recomputed from `run_history` `regime_exposure` transitions
- **Computed**: 6
- **Expected**: 6 — **MATCH**
- **run_history length**: 447 records

### 3. Tests
- Command: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v`
- **Result**: 10/10 PASSED

## Track Record (Unchanged)
- **Length**: 447 days (2025-01-02 → 2026-10-14)
- **NAV**: $135,043.35 (+35.04%)
- **Sharpe**: 1.9272
- **Max Drawdown**: -2.93%
- **Rolling 63-day Sharpe**: 0.1133
- **Regime**: risk-on (132 days)
- **Drift flag**: `low_rolling_sharpe` persists — 3 consecutive trading days (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133). Not yet at the >20-day persistence threshold.

## Primary Go/No-Go Gates
- Track record 447 > 126: **PASS**
- Sharpe 1.9272 > 0.9: **PASS**
- Max DD -2.93% < 15%: **PASS**
- Regime flips 6 > 1: **PASS**

## Data Freshness
- No fetch attempted (pre-gate). Raw cache max date remains 2026-10-14 for incumbent ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, EEM); ^VIX.parquet ends at 2026-10-14 with placeholder row (Volume=0).

## Next Cycle Gate
- Same post-close gate: **2026-10-16T20:00:00Z**
- If gate met: re-run `fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], start_date='2025-01-01', end_date='2026-11-30', force=True, raw_dir='data/raw')`, verify per-symbol max dates, bump replay `end_date` if a new real trading day exists, run `research/run_paper_trading_replay.py`, record extended track record.

## Reproduction Commands
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
print('flips',t)
"
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```