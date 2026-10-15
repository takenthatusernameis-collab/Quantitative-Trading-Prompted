# Paper Trading Validation Report — Cycle 384

## Timestamp
UTC: 2026-10-15T23:34:05Z

## Gate Status
Post-close gate: 2026-10-18T20:00:00Z UTC
Current time < gate time → Gate not met
Fetch/replay performed: No

## State Snapshot
- Run history entries: 447
- Regime flips: 6
- Rolling window: 63d

## Verification Results

### Rolling 63d Sharpe (last 63 cumulative returns)
- Returns count: 63
- Mean: 3.565835e-05
- Annualized Sharpe: 0.11333136870186278
- Stored (drift_flags.low_rolling_sharpe.value): 0.11333136870186329
- Difference: 5.134781e-16
- Match: Yes (diff < 1e-12)

### Regime Flips
- Flips computed: 6
- Run history length: 447
- Match: Yes

## Supervisor Loop Tests
Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
Result: 10/10 passed (OK)

## Conclusion
Gate remains unmet; no fetch/replay performed. All verifications passed. State unchanged.

## Disposition
Worker disposition to be recorded in `.kilo-runtime/worker-disposition.json` using current supervisor recommendation (if present) per protocol.
