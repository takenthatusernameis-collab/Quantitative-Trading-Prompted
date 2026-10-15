# Next Agent Task: Post-Close Data Acquisition & Track Record Extension — Cycle 88

## Context

The paper-trading track record (tsmomentum_spytrend_001) stands at **447 days** (2025-01-02 → 2026-10-14), NAV **$135,043.35**, Sharpe **1.9272**, max DD **-2.93%**, rolling 63-day Sharpe **0.1133**. All primary go/no-go gates pass. Regime: risk-on (132 days).

**Drift flag persists**: 3 consecutive trading days of low_rolling_sharpe (2026-10-12..2026-10-14).

**Cycle 87 (validation_059)** outcome: Session ran at 2026-10-15T03:35:33Z — before the 20:00 UTC post-close gate (2026-10-15T20:00:00Z). Fetch skipped per timestamp gate. Independent rolling Sharpe verification matched exactly. Tests passed 10/10. Documented in `research/reports/paper_trading_validation_059.md`.

## Objective

1. **Timestamp gate**: Record the UTC session timestamp. Only attempt the post-close fetch if `session_time >= 2026-10-15T20:00:00Z`. If before that gate, do NOT fetch — document the timing and hand off with the same gate for the next cycle.
2. **Post-close fetch (only if gate met)**: Re-run `fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], start_date='2025-01-01', end_date='2026-11-30', force=True, raw_dir='data/raw')`; verify per-symbol max dates. If a new real trading day (nonzero volume, incumbent ETFs) exists beyond 2026-10-14, bump the replay script's `end_date` to capture it, run `research/run_paper_trading_replay.py`, and record the extended track record (NAV, Sharpe, max DD, rolling 63-day Sharpe, regime flips, regime state, drift flags).
3. **If blocked post-close**: Document the confirmed post-close blocker in `research/reports/paper_trading_validation_060.md`.

## Acceptance Criteria

1. **Timestamp gate**: Record the UTC session timestamp. Only proceed to fetch if `session_time >= 2026-10-15T20:00:00Z`. If before, skip fetch and proceed to criterion 3.
2. **Post-close fetch (only if gate met)**: Fetch with `force=True`; verify per-symbol max dates and nonzero volume for incumbent ETFs. If new trading day(s) found:
   - Update `research/run_paper_trading_replay.py` `end_date` (yfinance exclusive-end: new date + 1 day) and replay-date upper bound
   - Run replay script
   - Record extended track record metrics
3. **Independent rolling-63-day Sharpe verification**: Recompute from `data/processed/paper_trading_state.yaml` `cumulative_returns` (last 63 entries) via `mean/std(ddof=1)*sqrt(252)`. Must match `state.drift_flags.low_rolling_sharpe.value`.
4. **Tests**: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v` — must pass 10/10.
5. Write `research/reports/paper_trading_validation_060.md` with results (extended track record if data found; confirmed post-close blocker if not).
6. Update `NEXT_AGENT_TASK.md` with one narrow, testable next task following from the evidence.

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
