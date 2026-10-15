# Paper Trading Validation Report — Cycle 326

- **Generated (UTC)**: 2026-10-15T21:58:19Z
- **Post-close gate**: 2026-10-18T20:00:00Z UTC — **NOT MET** (21:58:19Z < gate)
- **Fetch/replay**: NOT performed (gate unmet; protocol hold respected)
- **Prior cycle**: Cycle 325 completed 2026-10-15T21:57:13Z

## State Snapshot
- `run_history` length: 447
- Last `run_history` date: 2026-10-14
- Regime flips (recomputed): 6

## Verification Results

### 1. Rolling 63d Sharpe vs stored drift flag
- Recomputed from last 63 cumulative returns: 0.11333136870186278
- Stored `drift_flags.low_rolling_sharpe.value`: 0.11333136870186329
- **Diff**: 5.134781488891349e-16 (< 1e-12 threshold) — **PASS**

### 2. Regime flips
- Recomputed flips: 6
- run_history length: 447, last date 2026-10-14 — consistent with stored state — **PASS**

### 3. Supervisor loop tests
```
Ran 10 tests in 0.405s
OK
```
— **PASS 10/10**

## Gate Decision
Gate not met as of 2026-10-15T21:58:19Z. No data ingestion, backtest, strategy change, or dependency modification performed. Monitoring/verification only, per scope boundaries.

## Reproduction Commands
```bash
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ
python3 -c "import yaml,math; d=yaml.safe_load(open('data/processed/paper_trading_state.yaml')); ret=d['cumulative_returns'][-63:]; m=sum(ret)/len(ret); v=sum((r-m)**2 for r in ret)/(len(ret)-1); s=(m*252)/(math.sqrt(v)*math.sqrt(252)) if v>0 else 0; print('diff',abs(s-d['drift_flags']['low_rolling_sharpe']['value']))"
python3 -c "import yaml; d=yaml.safe_load(open('data/processed/paper_trading_state.yaml')); rh=d['run_history']; t=0; prev=rh[0]['regime_exposure']; [ (t:=t+1, prev:=rh[i]['regime_exposure']) for i in range(1,len(rh)) if rh[i]['regime_exposure']!=prev]; print('flips',t,'len',len(rh))"
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```
