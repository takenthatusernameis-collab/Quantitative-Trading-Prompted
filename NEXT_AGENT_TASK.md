# Next Agent Task — Session 19 (Monday 2026-10-26 after 17:00 ET)

## Context
- Last processed session: 2026-10-23 (Friday). Today is 2026-10-24 (Saturday); no new completed US trading session exists yet.
- All integrity checks pass: drift `stored == recomputed: True` (rolling 63d Sharpe -0.25492616117205563 as of 2026-10-23); `git status --porcelain data/` empty; tests 29 passed.
- Real run on 2026-10-24 exited 0 with `no new completed session`, readiness block printed, `sessions extended: 0`, `state write count: 0`, `data/` untouched.

## Objective
On/after Monday 2026-10-26 17:00 ET, run the real (non-dry-run) extension path. If a completed session exists, extend by exactly one session, write state once, verify idempotency with a second invocation, verify drift integrity and tests. If no completed session exists yet, follow criterion 4. Do not fabricate data; do not change strategy/gate/threshold/config.

## Acceptance criteria
1. Run `python research/extend_paper_trading_state.py` (no `--dry-run`). If a new completed session exists, extend by exactly one session and write state once.
2. Verify idempotency: second invocation must be no-op (`sessions extended: 0`, `state write count: 0`, `git status --porcelain data/` empty).
3. Verify integrity after any write:
   - `python research/drift_persistence_report.py` -> `stored == recomputed: True`.
   - `git status --porcelain data/` empty.
   - `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> all pass.
4. If no new completed session exists, run exits 0 with `no new completed session`, readiness block printed, `data/` untouched.
5. Report exact commands and observed results.

## Scope boundaries
- No strategy/gate/threshold/config changes. Do not commit unless explicitly requested. Raw cache (`data/raw`) untouched. Research/backtesting only.

## Validation commands
- `git status --porcelain data/`
- `python research/drift_persistence_report.py`
- `python research/extend_paper_trading_state.py`
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q`
