# Next Agent Task: Post-Gate Monitoring (Cycle 642)

## Context
Post-gate monitoring phase (Cycle 641 completed). No new trading days beyond 2026-10-16. All verification checks pass.

## Objective
Continue post-gate monitoring-only. On each cycle, record UTC. If new trading days exist beyond 2026-10-16, extend state via `src.simulation.paper_trading.run_daily_paper_update` (deterministic continuation, single state save), regenerate reports, re-run verification checks, and update disposition. Otherwise perform verification-only with no state changes.

## Acceptance Criteria
1. Record current UTC in cycle notes when updating documentation.
2. Verify no new trading days beyond 2026-10-16 (per-symbol max_date check for SPY, QQQ, IWM, TLT, GLD, EFA, EEM, ^VIX).
3. If no new trading days: verification-only — run `python -m pytest -q`, `python research/_tmp_cycle77_verify.py`, and `python .github/scripts/test_kilo_supervisor_loop.py`; confirm all pass.
4. If new trading days present: extend state via `src.simulation.paper_trading.run_daily_paper_update` (deterministic, single state save), regenerate `research/reports/paper_trading_rolling.md` as needed, re-run all verification checks, document changes made.
5. Update `.kilo-runtime/worker-disposition.json` to `verified` with current UTC, concrete evidence, and verification details. Copy `recommendation_id` exactly from the current recommendation.
6. Prepare a bounded handoff in NEXT_AGENT_TASK.md for the next agent.

## Verification Commands
- `python -m pytest -q`
- `python research/_tmp_cycle77_verify.py`
- `python .github/scripts/test_kilo_supervisor_loop.py`

## Scope Boundaries
- Monitoring-only. Do not modify strategy/data sources, infrastructure, workflow orchestration, or add dependencies unless a new bounded task is explicitly defined.
- Do not commit changes unless explicitly requested.
- Preserve working baseline and safety controls.

## Known State
- Track length: 449 days (2025-01-02 to 2026-10-16)
- last_run_date: 2026-10-16
- NAV: $133,729.22; peak: $139,120.07; max DD: -4.99%
- Rolling 63d Sharpe: -0.21188351222842883 (17 consecutive days persistence; below >20-day threshold)
- Regime flips: 6/449 (match verified)
- Data ends 2026-10-16; no new trading days observed
