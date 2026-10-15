# Paper Trading Validation — Cycle 150

**Session UTC**: 2026-10-15T15:49:39Z
**Post-Close Gate**: 2026-10-17T20:00:00Z
**Gate Status**: NOT MET (session time < gate)

## Gate Enforcement
- Session time recorded via `TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ`: 2026-10-15T15:49:39Z
- Post-close gate: 2026-10-17T20:00:00Z
- Gate not met → no fetch, no replay executed

## Independent Verifications (on unchanged state)

### Rolling 63-Day Sharpe
- Recomputed from `data/processed/paper_trading_state.yaml` `cumulative_returns[-63:]`:
  - Formula: `(mean * 252) / (std(ddof=1) * sqrt(252))`
  - Computed: **0.11333136870186278**
  - Stored in `drift_flags.low_rolling_sharpe.value`: **0.11333136870186329**
  - Difference: **5.13e-16** (within float precision) ✓

### Regime Flip Count
- Recomputed from `run_history.regime_exposure` transitions:
  - Transitions detected: **6**
  - Run history entries: **447**
  - Matches prior cycle count ✓

### Supervisor Loop Tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: **10/10 tests passed** ✓

## Track Record (Unchanged)
- Length: **447 days** (2025-01-02 → 2026-10-14)
- NAV: **$135,043.35** (+35.04%)
- Full-period Sharpe: **1.9272**
- Max Drawdown: **-2.93%**
- Rolling 63-day Sharpe: **0.1133**
- Regime: **Risk-on** (132 days)
- Drift flag: `low_rolling_sharpe` on 2026-10-12 (0.4892), 2026-10-13 (0.3669), 2026-10-14 (0.1133) — **3 consecutive days**, not yet >20-day persistence threshold

## Primary Go/No-Go Gates (All Pass)
- Track record ≥ 126 days: **447** ✓
- Full-period Sharpe ≥ 0.9: **1.9272** ✓
- Max drawdown < 15%: **-2.93%** ✓
- Regime flips ≥ 1: **6** ✓

## Next Cycle
Gate unchanged (2026-10-17T20:00:00Z). Next session at or after gate should attempt post-close fetch and replay per NEXT_AGENT_TASK.md.
