# NEXT_AGENT_TASK — Paper-trading extension gate check (2026-11-06, post-gate)

## Handoff (corrective invocation 1, 2026-11-05T23:06:53Z — pre-gate re-verified; gate NOT released)
- **UTC 2026-11-05T23:06:53Z / 18:06:53 EST (Thu).** Gate NOT released for 2026-11-06 (releases 17:00 ET / 22:00 UTC on 2026-11-06). No state extension performed (scope boundary: do not run extension before 22:00 UTC).
- **Observed:** `extend_paper_trading_state.py` -> `candidate available: no` (next session 2026-11-06 not closed yet; today 2026-11-05), `sessions extended: 0`, NAV before/after `129990.36021343581`, state write count 0.
- **Drift report:** rolling 63d Sharpe includes `2026-11-05 -2.1203` (consistent; `low_rolling_sharpe` persists).
- **Tests:** 47 passed in 18.55s (`tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py`).
- **Git:** `git status --porcelain data/ config/` clean. No commits made.
- **Supervisor (review-0006, advisory):** decompose negative 63d Sharpe into gross vs cost/turnover drag — follow-up, out of scope for this bounded gate-check.
- **Next candidate:** 2026-11-06 (Friday), usable after 17:00 ET / 22:00 UTC on 2026-11-06.

## Prior handoff (invocation 511, 2026-11-05T23:04:21Z)
- Gate NOT released; `sessions_extended: 0`, NAV unchanged `129990.36021343581`, 0 writes; 47 tests passed; `data/ config/` clean.

## Context
- Last processed session: **2026-11-05** (NAV `129990.36021343581`).
- Rolling 63d Sharpe at 2026-11-05: **-2.1203** (low_rolling_sharpe).
- Clock gate for 2026-11-06 releases at **17:00 ET / 22:00 UTC on 2026-11-06**.
- `git status --porcelain data/ config/` must remain clean except expected state update only after a real extension write.

## Objective
At/after **22:00 UTC on 2026-11-06**, run the real extension and persistence checks. Extend by at most one session to 2026-11-06 only if a completed bar exists; otherwise record `sessions_extended==0` with explicit reason and keep state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-06 session exists: `sessions_extended==1`, `last_run_date` advances to 2026-11-06, NAV changes, state write count 1.
- If not: `sessions_extended==0` with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent: `sessions_extended==0`, write count 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports drift metrics updated/consistent.
- `git status --porcelain data/ config/` shows only expected state update (no unintended changes).
- `pytest` passes for: `tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py`.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify `data/raw/`.
- Do not hand-edit canonical state.
- Do NOT run `extend_paper_trading_state.py` before 22:00 UTC on 2026-11-06.

## Verification commands (exact, in order; run at/after 22:00 UTC)
1. `date -u && TZ=America/New_York date`
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -6`
4. `python3 research/extend_paper_trading_state.py 2>&1 | tail -8`  (idempotency)
5. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`
6. `git status --porcelain data/ config/`
