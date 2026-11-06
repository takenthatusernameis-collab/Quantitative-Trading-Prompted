# NEXT_AGENT_TASK — Paper-trading extension gate check (2026-11-06, pre-gate)

## Handoff (cycle 1141/session 3, 2026-11-06T05:50Z — pre-gate, gate NOT released)
- **UTC 2026-11-06T05:50:40Z / 00:50:40 EST (Fri).** Gate for 2026-11-06 **NOT released** until 22:00 UTC on 2026-11-06 (~16h 9m). `extend_paper_trading_state.py` **NOT run** (scope boundary line 35). Temporal blocker only.
- **Supervisor/runtime:** `.kilo-runtime/` empty (no recommendation/disposition). No pending session wakeups; post-gate wakeup scheduled this session.
- **Fresh pre-gate verification (this session):** `sha256sum data/processed/paper_trading_state.yaml` = `60b16fb460da735e85d8a1935d6604306eed48f8bc927bc8849e31fec19498f8` (`last_run_date 2026-11-05`, NAV `129990.36021343581`). `drift_persistence_report.py` tail includes 2026-11-05 Sharpe `-2.1203`; `low_rolling_sharpe` persistence 7 consistent. Acceptance suite `tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py` → **64 passed in 34.23s**. `git status --porcelain` empty; `git status --porcelain data/ config/` empty.
- **No commit made** (not requested). `data/raw/` untouched. No source/data/config/test/gate/threshold/cost model/universe/clock-gate/canonical state modified.
- **Wakeup:** `wku_1ae22257e001r9IJETnXWckjbR` at **2026-11-06T22:00:00Z** to run acceptance commands 1–6 (NEXT_AGENT_TASK.md). At/after gate: extend by ≤1 session to 2026-11-06 only if a completed bar exists; else `sessions_extended==0` with explicit reason, state unchanged, idempotent re-run, drift report, pytest (61/64 suite as specified in handoff context), `git status --porcelain data/ config/`. Do not commit unless asked.

## Context
- Last processed session: **2026-11-05** (NAV `129990.36021343581`).
- Rolling 63d Sharpe at 2026-11-05: **-2.1203** (low_rolling_sharpe, persistence 7).
- Clock gate for 2026-11-06 releases at **17:00 ET / 22:00 UTC on 2026-11-06**.
- `rolling_max_dd_63d` is now the trailing-63 value (`-0.06544463769225417`); `max_drawdown` (full history) remains `-0.06562469374042057`. Gate 5 threshold `-0.15` passes under both.
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
- `pytest` passes for: `tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py` (61 must pass).

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic (the `rolling_max_dd_63d` window fix is already applied and verified).
- Do not commit unless asked.
- Do not modify `data/raw/`.
- Do not hand-edit canonical state (use `research/correct_rolling_max_dd_field.py` only if a future field correction is warranted, and only after verifying it is idempotent and field-only).
- Do NOT run `extend_paper_trading_state.py` before 22:00 UTC on 2026-11-06.

## Verification commands (exact, in order; run at/after 22:00 UTC)
1. `date -u && TZ=America/New_York date`
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -6`
4. `python3 research/extend_paper_trading_state.py 2>&1 | tail -8`  (idempotency)
5. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
6. `git status --porcelain data/ config/`