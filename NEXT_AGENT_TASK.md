# Next Agent Task: Post-Close Data Acquisition & Track Record Extension — Cycle 70

## Context

Cycle 69 (2026-10-15T04:13:16Z) ran **before** the post-close gate (2026-10-15T20:00:00Z). No fetch was attempted per protocol. All verification completed: independent rolling-63-day Sharpe recomputed = 0.11333136870186329, exact match to stored drift flag; tests passed 10/10.

The paper-trading track record (tsmomentum_spytrend_001) stands at **447 days** (2025-01-02 → 2026-10-14), NAV **$135,043.35**, Sharpe **1.9272**, max DD **-2.93%**, rolling 63-day Sharpe **0.1133**. All primary go/no-go gates pass except rolling 63-day Sharpe (0.1133 < 0.9, drift flag active). Regime: risk-on (132 days).

**Drift flag persists**: 3 consecutive trading days of low_rolling_sharpe (2026-10-12 0.4892, 2026-10-13 0.3669, 2026-10-14 0.1133, all < 0.5 threshold). Trajectory volatile over last 18 days (range -0.51 to +1.19). Not yet at >20-day persistence threshold.

## Objective

1. **Timestamp gate**: Record the UTC session timestamp. Only attempt the post-close fetch if `session_time >= 2026-10-15T20:00:00Z`. If before that gate, do NOT fetch — document the timing and hand off with the same gate for the next cycle.
2. **Post-close fetch (only if gate met)**: Re-run `fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], start_date='2025-01-01', end_date='2026-11-30', force=True, raw_dir='data/raw')`; verify per-symbol max dates. If a new real trading day (nonzero volume, incumbent ETFs) exists beyond 2026-10-14, bump the replay script's `end_date` to capture it, run `research/run_paper_trading_replay.py`, and record the extended track record (NAV, Sharpe, max DD, rolling 63-day Sharpe, regime flips, regime state, drift flags). If no new real trading day exists, document the confirmed blocker.
3. **Independent rolling-63-day Sharpe verification**: Recompute from `data/processed/paper_trading_state.yaml` `cumulative_returns` (last 63 entries) via `(mean*252)/(std(ddof=1)*sqrt(252))`. Must match `state.drift_flags.low_rolling_sharpe.value`.
4. **Tests**: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v` — must pass 10/10.
5. Write `research/reports/paper_trading_validation_070.md` with results.
6. Update `NEXT_AGENT_TASK.md` with one narrow, testable next task for the following cycle.

## Validation Commands

```bash
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- Do not place live trades, enable live trading, or access credentials.
- Do not fabricate data, market findings, or test output.
- Do not add new dependencies, services, paid data, scheduled jobs, agents, or workflows.
- Preserve yfinance exclusive-end semantics when bumping `end_date`.
- Do not commit changes unless explicitly requested; keep work in the working tree for inspection.
- Keep work bounded and restart-safe.

(End of file - total 34 lines)