# Next Agent Task — Session 17 (paper-trading readiness diagnostic shipped; next: real-time extension gate)

## Context
- Session 16's blocker is **diagnosed and documented, not a logic bug**. Verified directly against the live clock:
  - `state.last_run_date` = `2026-10-23` (Friday).
  - The extension clock gate (`research/extend_paper_trading_state.py:125`) checks the calendar day *after* `last_run_date` = `2026-10-24` (Saturday). `session_is_complete('2026-10-24')` is `False` because a Saturday has no US equity session and the local clock is still Friday evening.
  - Even if the gate released, the candidate scan skips weekends; the next trading session is **2026-10-26 (Monday)**, usable only after 17:00 ET that day.
  - Therefore no new completed session exists. This is a **timing/data-readiness condition**, not a defect in the extension logic.
- The prior supervisor recommendation (`40020074911-attempt-1-review-0008-05f72af781f1`, premise: parquet `ImportError` in `_save_cached`) is **superseded**: `pyarrow 26.0.0` is installed and `pandas 3.1.0` resolves to it; the dry-run exits cleanly. Disposition written to `.kilo-runtime/worker-disposition.json`.
- **This session shipped acceptance criterion 2**: an explicit, testable readiness diagnostic. New pure functions `next_trading_session()` and `build_readiness()` in `research/extend_paper_trading_state.py` surface the same clock gate the extension logic uses, reporting last processed session, gate state, next expected session, and the local time at which it becomes usable. `main()` prints it on every invocation. No strategy/gate/threshold/config change; `data/raw` untouched; no commit.

## Objective
Wait for the next completed US trading session (Monday 2026-10-26, after 17:00 ET) and run the real (non-dry-run) extension path idempotently, OR — if a completed session already exists at the time of the next invocation — extend to it and verify integrity. Do not fabricate data; do not change strategy/gate/threshold/config.

## Acceptance criteria
1. Run `python research/extend_paper_trading_state.py` (no `--dry-run`). If a new completed session exists, it must extend by exactly one session and write state once.
2. Verify idempotency: a second invocation must be a no-op (`sessions extended: 0`, `state write count: 0`, `git status --porcelain data/` empty).
3. Verify integrity after any write:
   - `python research/drift_persistence_report.py` -> `stored == recomputed: True`.
   - `git status --porcelain data/` empty (canonical raw cache untouched).
   - `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> all pass.
4. If no new completed session exists, the run must exit 0 with `no new completed session`, the readiness block printed, and `data/` untouched — exactly as today's dry-run does.
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

## Verification record — Session 292 (2026-10-24 00:44 UTC / Fri 20:44 ET)
- `python research/extend_paper_trading_state.py` (real, no `--dry-run`): EXIT=0; readiness block printed; `clock gate: NOT released`; `no new completed session`; `sessions extended: 0`; `state write count: 0`; `raw cache: scratch (canonical data/raw untouched)`. Acceptance criterion #4 satisfied.
- `git status --porcelain data/`: empty output (canonical raw cache untouched).
- `python research/drift_persistence_report.py`: `stored == recomputed: True`; rolling 63d Sharpe -0.25492616117205563 (2026-10-23).
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q`: 29 passed in 2.69s.

## Unresolved blocker (timing, not a defect)
- `state.last_run_date` = 2026-10-23 (Friday). Today is Saturday 2026-10-24. The clock gate checks the calendar day after last_run_date (2026-10-24, Saturday) which has no US equity session, so `session_is_complete` is False and the gate is not released.
- Acceptance criteria #1-3 (real extension by one session, idempotency, integrity after write) cannot be exercised until the next completed US trading session exists: Monday 2026-10-26, usable only after 17:00 ET that day (or once the local day after has started).
- No commit made; changes remain in the working tree (NEXT_AGENT_TASK.md, research/extend_paper_trading_state.py, tests/test_paper_trading_extend.py). `data/raw` untouched.

## Next cycle task
- On/after Monday 2026-10-26 17:00 ET: run `python research/extend_paper_trading_state.py` (real). Verify it extends by exactly one session and writes state once (criteria #1-2). Then run a second invocation confirming idempotent no-op (criterion #2), verify `stored == recomputed: True` and `git status --porcelain data/` empty (criterion #3), and re-run the two test files (criterion #3).