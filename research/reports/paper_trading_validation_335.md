# Paper Trading Validation Report - Cycle 335

## Execution Timestamp
**UTC Session Time:** 2026-10-15T22:20:15Z

## Gate Status
**Post-Close Gate:** 2026-10-18T20:00:00Z UTC
**Gate Met:** false
**Time Until Gate:** > 2 days

## Fetch/Replay Status
**Fetch Performed:** false (gate not met)
**Replay Performed:** false (gate not met)
**Action Taken:** Monitoring only - no data ingestion per gate enforcement protocol

## State Snapshot (from data/processed/paper_trading_state.yaml)
- **Run History Entries:** 447
- **Regime Flips:** 6 (recomputed from run_history)
- **Drift Flag - Low Rolling Sharpe:** 0.11333136870186329 (stored)
- **Rolling 63d Sharpe (computed):** 0.11333136870186278
- **Diff vs stored:** 5.134781488891349e-16 (< 1e-12)

## Verification Results

### Rolling 63d Sharpe
```python
from last 63 cumulative_returns: mean/var computed, annualized Sharpe vs stored drift flag
Result: PASS (diff 5.13e-16 < 1e-12)
```

### Regime Flips
```python
Transitions in regime_exposure across 447 run_history entries
Result: 6 flips, matches expected
```

### Supervisor Loop Tests
```bash
python3 .github/scripts/test_kilo_supervisor_loop.py -v
Result: 10/10 tests passed
```

## Supervisor Disposition
Disposition recorded in `.kilo-runtime/worker-disposition.json` with schema_version 1.

## Notes
Gate remains unmet; no fetch/replay executed. Verifications completed successfully.
