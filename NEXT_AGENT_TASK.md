# Next Agent Task: Post-Close Data Acquisition & Track Record Extension — Cycle 80

## Context

Cycle 79 (session 2026-10-15T04:45:49Z) ran before the post-close gate (2026-10-16T20:00:00Z). No fetch was attempted per protocol. All non-fetch verifications passed: independent rolling-63-day Sharpe recomputed = 0.1133313687018628 (diff 5.1e-16 vs `state.drift_flags.low_rolling_sharpe.value` 0.11333136870186329, float64 rounding), regime flips recomputed = 6 (matches documented count), `pytest .github/scripts/test_kilo_supervisor_loop.py -v` → 10/10 passed.

The paper-trading track record (tsmomentum_spytrend_001) remains at 447 days (2025-01-02 → 2026-10-14), NAV $135,043.35, Sharpe 1.9272, max DD -2.93%, rolling 63-day Sharpe 0.1133. Drift flag persists 3 consecutive days (2026-10-12 0.4892, 2026-10-13 0.3669, 2026-10-14 0.1133), not yet at >20-day persistence threshold. Regime risk-on (132 days).

Artifacts: `data/processed/paper_trading_state.yaml` (unchanged), `research/reports/paper_trading_validation_079.md`.

## Objective

1. **Timestamp gate**: Record the UTC session timestamp. Only attempt the post-close fetch if `session_time >= 2026-10-16T20:00:00Z`. If before that gate, do NOT fetch — document the timing and hand off with the same gate for the next cycle.
2. **Post-close fetch (only if gate met)**: Re-run `fetch_universe(['SPY','QQQ','IWM','TLT','GLD','EFA','EEM','^VIX'], start_date='2025-01-01', end_date='2026-11-30', force=True, raw_dir='data/raw')`; verify per-symbol max dates. If a new real trading day (nonzero volume, incumbent ETFs) exists beyond 2026-10-14, bump the replay script's `end_date` to capture it (preserve yfinance exclusive-end semantics), run `research/run_paper_trading_replay.py`, and record the extended track record. If no new real trading day exists, document the confirmed blocker.
3. **Independent rolling-63-day Sharpe verification**: Recompute from `data/processed/paper_trading_state.yaml` `cumulative_returns` (last 63 entries) via `(mean*252)/(std(ddof=1)*sqrt(252))`. Must match `state.drift_flags.low_rolling_sharpe.value`. (Note: NEXT_AGENT_TASK.md Cycle 77 quoted `sqrt(256/252)`, which is a typo — the code at `src/simulation/paper_trading.py:280-282` implements `sqrt(252)` and that reproduces the stored value exactly.)
4. **Regime flip verification**: Recompute regime flips from `run_history` `regime_exposure` transitions; must equal 6 (unless replay was re-run, in which case recompute and confirm).
5. **Tests**: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v` — must pass 10/10.
6. Write `research/reports/paper_trading_validation_080.md` with results.
7. Update `NEXT_AGENT_TASK.md` with one narrow, testable next task for the following cycle.

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

(End of file - total 35 lines)