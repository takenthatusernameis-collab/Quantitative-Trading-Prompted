# Paper Trading Validation Report — Cycle 229

**Generated:** 2026-10-15T19:45:14Z (UTC)
**Session time:** 2026-10-15T19:45:14Z
**Post-close gate:** 2026-10-18T20:00:00Z — **NOT MET**

## Timestamp Gate Enforcement

- Session time `2026-10-15T19:45:14Z` < gate `2026-10-18T20:00:00Z`.
- **No fetch or replay performed** per protocol.

## State Snapshot

| Metric | Value |
|---|---|
| Track record length | 447 days (2025-01-02 → 2026-10-14) |
| Current NAV | $135,043.35 |
| Peak NAV | $139,120.07 |
| Max drawdown | -2.93% |
| Full-period Sharpe | 1.9272 |
| Rolling 63-day Sharpe | 0.1133 |
| Regime flips | 6 |
| Regime | risk-on (132 days) |
| Drift flag `low_rolling_sharpe` | active=False |

## Independent Verification

### Rolling 63-day Sharpe
- Recomputed from last 63 cumulative returns: **0.11333136870186278**
- Stored drift flag value: **0.11333136870186329**
- **Difference: 5.13e-16** (< 1e-12 float-precision threshold) — **MATCH**

### Regime Flips
- Recomputed from `run_history` transitions: **6 flips** over 447 entries — consistent with stored count.

### Supervisor Loop Tests
- `python3 .github/scripts/test_kilo_supervisor_loop.py -v` → **10/10 passed**.

### Repository State
- `git status --short` → **clean** (no unstaged/staged changes, no state mutations).

## Fetch / Replay Status

- **Fetch:** NOT ATTEMPTED (gate not met).
- **Replay:** NOT RUN (gate not met).
- Track record unchanged at 447 days.

## Drift Flag Status

`low_rolling_sharpe` value 0.1133 remains below the 0.5 threshold but **active=False** (not currently triggered per stored state). The flag has persisted intermittently across recent cycles (2026-10-12: 0.4892, 2026-10-13: 0.3669, 2026-10-14: 0.1133) — 3 consecutive trading days. Trajectory over last 18 days volatile (range -0.51 to +1.19). Not yet at the >20-day persistence threshold.

## Conclusion

Gate not met; protocol respected. All verifications passed; no state mutations. Awaiting post-close gate (2026-10-18T20:00:00Z) before any fetch/replay.