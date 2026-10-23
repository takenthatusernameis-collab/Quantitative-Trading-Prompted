# Next Agent Task — Session 16 (paper-trading extension: data readiness/blocker resolution)

## Context
- Session 15 attempted to extend paper-trading state past 2026-10-23 (candidate Monday 2026-10-26).
- `python research/extend_paper_trading_state.py` returned: "no new completed session", sessions extended 0, NAV unchanged (133634.38193355838), state write count 0, raw cache untouched.
- Drift report: last_run_date 2026-10-23, rolling 63d Sharpe -0.25492616117205563, stored==recomputed True, persistence streak 10 days (2026-10-12 → 2026-10-23).
- `git status --porcelain data/` is empty. Tests: `tests/test_paper_trading_extend.py tests/test_drift_persistence.py` passed 24/24.
- Environment today: Fri Oct 23 2026 23:53:47Z; candidate extension date suggested is Monday 2026-10-26 (US trading session) after close+slack. No new completed session is currently available in the data sources used by the extension logic.

## Objective
Determine why no new completed session is available beyond 2026-10-23 and make the extension path actionable (or produce a concrete, minimal fix) so that when a new completed US trading session exists it can be extended idempotently. Do not change strategy/gate/threshold/config. Do not fabricate data.

## Acceptance criteria
1. Identify the data source(s) and completion criteria used by `research/extend_paper_trading_state.py` (and any helpers it calls) that determine "new completed session". Document findings in the handoff/notes with file paths and function names.
2. If the blocker is due to missing/late data availability (not logic error), implement the smallest reversible change to make the readiness check explicit/testable (e.g. add a `--dry-run` diagnostic that reports last available timestamp/session, required completeness, and next expected session) without mutating `data/` or touching strategy/config.
3. If the blocker is a logic bug preventing recognition of an available completed session, fix it with the smallest change, prove idempotent extension, verify `stored==recomputed True`, `git status --porcelain data/` empty, and the two test files pass.
4. If neither is possible with current repo state, produce a precise blocker report (exact paths checked, timestamps, what would constitute "complete", network/data access constraints) and do **not** guess or synthesize market data.
5. Validation commands must all run and results reported:
   - `git status --porcelain data/`
   - `python research/drift_persistence_report.py`
   - `python research/extend_paper_trading_state.py --dry-run` (if added) or `python research/extend_paper_trading_state.py`
   - `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q`

## Scope boundaries
- No strategy/gate/threshold/config changes.
- Do not commit unless explicitly requested.
- Raw cache (`data/raw`) must remain untouched.
- Research/backtesting only. No live trading.
