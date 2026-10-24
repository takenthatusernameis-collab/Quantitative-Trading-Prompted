# Next Agent Task — Session 18 (wait for completed session; extend when ready)

## Context
- Current state matches Session 17 verification: no new completed US trading session exists. `last_run_date` = `2026-10-23` (Friday). Today is `2026-10-24` (Saturday) — the clock gate checks the calendar day after `last_run_date` (2026-10-24) which has no US equity session, so `session_is_complete` is False.
- The extension logic with readiness diagnostic is in place (`research/extend_paper_trading_state.py` with `next_trading_session()` and `build_readiness()`, prints readiness block on every invocation). Prior supervisor recommendation 0008 is superseded (pyarrow/pandas present, dry-run clean). No strategy/gate/threshold/config changes made.
- Tests pass: `tests/test_paper_trading_extend.py` and `tests/test_drift_persistence.py` — **29 passed**. `git status --porcelain data/` is empty; `data/raw` untouched. `drift_persistence_report.py` shows `stored == recomputed: True` (rolling 63d Sharpe -0.2549 as of 2026-10-23).

## Objective
Wait for the next completed US trading session (Monday 2026-10-26, after 17:00 ET) and run the real (non-dry-run) extension path idempotently, or if a completed session already exists at invocation time, extend to it and verify integrity. Do not fabricate data; do not change strategy/gate/threshold/config.

## Acceptance criteria
1. Run `python research/extend_paper_trading_state.py` (no `--dry-run`). If a new completed session exists, it must extend by exactly one session and write state once.
2. Verify idempotency: a second invocation must be a no-op (`sessions extended: 0`, `state write count: 0`, `git status --porcelain data/` empty).
3. Verify integrity after any write:
   - `python research/drift_persistence_report.py` -> `stored == recomputed: True`.
   - `git status --porcelain data/` empty (canonical raw cache untouched).
   - `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> all pass.
4. If no new completed session exists, the run must exit 0 with `no new completed session`, the readiness block printed, and `data/` untouched — exactly as current dry-run behavior.
5. Report exact commands and observed results. Never claim a check passed unless it ran and passed.

## Scope boundaries
- No strategy/gate/threshold/config changes.
- Do not commit unless explicitly requested.
- Raw cache (`data/raw`) must remain untouched.
- Research/backtesting only. No live trading.

## Validation commands
- `git status --porcelain data/`
- `python research/drift_persistence_report.py`
- `python research/extend_paper_trading_state.py` (real run; fall back to `--dry-run` if no session yet)
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q`

## Current verification (Session 17, 2026-10-24)
- `python research/extend_paper_trading_state.py` (real, no --dry-run): EXIT=0, readiness block printed, `clock gate: NOT released`, `no new completed session`, `sessions extended: 0`, `state write count: 0`, `raw cache: scratch (canonical data/raw untouched)`. Current time ET 2026-10-23 22:40 EDT; next expected session 2026-10-26 (Monday), usable after 17:00 ET on 2026-10-26.
- `git status --porcelain data/`: empty.
- `python research/drift_persistence_report.py`: `stored == recomputed: True` (rolling 63d Sharpe -0.25492616117205563 as of 2026-10-23).
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q`: **29 passed** in 1.66s.

## Unresolved blocker (timing, not a defect)
- `state.last_run_date` = 2026-10-23 (Friday). The next trading session is Monday 2026-10-26; extension becomes eligible after 17:00 ET on 2026-10-26. No defect to fix — timing condition only.
- Acceptance criteria 1-2 cannot be exercised until a completed session exists.

## What was verified this session (criteria 3, 4)
- Criterion 4: real run exits 0 with `no new completed session`, readiness block printed, `data/` untouched.
- Criterion 3: drift integrity `stored == recomputed: True`, `git status --porcelain data/` empty, tests 29 passed.

## Next cycle task
On/after Monday 2026-10-26 17:00 ET: run `python research/extend_paper_trading_state.py` (real). If it extends by exactly one session and writes state once (criteria 1-2), run a second invocation to confirm idempotent no-op (`sessions extended: 0`, `state write count: 0`, `git status --porcelain data/` empty) (criterion 2), verify `stored == recomputed: True` and `git status --porcelain data/` empty (criterion 3), re-run `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` (criterion 3). Report exact commands and results. If no new session exists yet, follow criterion 4 (exit 0, readiness printed, data untouched).