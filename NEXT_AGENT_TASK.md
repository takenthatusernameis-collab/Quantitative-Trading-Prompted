# NEXT_AGENT_TASK — Paper-trading extension gate check (2026-11-06, post-gate)

## Handoff (cycle 1145, corrective invocation 1, 2026-11-06T11:41Z — pre-gate, gate NOT released)
- **UTC 2026-11-06T11:41Z / 06:41 EST (Fri).** Gate for 2026-11-06 **NOT released** until 22:00 UTC (~10h 19m). `extend_paper_trading_state.py` **NOT run** (scope boundary). Temporal blocker remains.
- **Corrective action (durable):** Resolved cycle 1144 environment blocker — project deps installed for system `python3` (`pip3 install --user -r requirements.txt`; pandas 3.1.1). Verification commands in this file are runnable in this environment.
- **State (unchanged):** `data/processed/paper_trading_state.yaml` SHA256 `60b16fb460da735e85d8a1935d6604306eed48f8bc927bc8849e31fec19498f8` (`last_run_date 2026-11-05`, NAV `129990.36021343581`). `git status --porcelain data/ config/` clean (pre-handoff doc edits).
- **Verification (this session):** acceptance suite `tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py` → **64 passed** (40.01s). `tests/test_go_no_go_evaluation.py tests/test_candidate_shortlist_934.py` → **41 passed, 24 warnings** (19.52s). No commit made. `data/raw/` untouched. No source/data/config/test/gate/threshold/cost model/universe/clock-gate/canonical state modified.

## Handoff (corrective invocation 302, 2026-11-06T13:40Z — pre-gate, gate NOT released)
- **UTC 2026-11-06T13:40Z / 08:40 EST (Fri).** Gate for 2026-11-06 **NOT released** until 22:00 UTC (~8h 20m). `extend_paper_trading_state.py` **NOT run** (scope boundary). Temporal blocker remains.
- **Durable code correction verified:** `research/candidate_shortlist_934.py:900` — `pd.Timestamp.dayofyear` → `day_of_year` (pandas 4.x compatible; removes pre-existing deprecation warning). Confirmed present in worktree via grep.
- **Re-verification (this invocation):** acceptance suite → **64 passed in 38.96s**. `git status --short` → empty (clean working tree). `git status --porcelain data/ config/` → empty. Canonical state SHA256 unchanged.
- **Wakeup re-scheduled:** prior session's wakeup `wku_1b1154bb3001oJk8BMewX9UON3` was not visible in this session's pending-wakeup list. Fresh wakeup `wku_1b117ae8b001WHHxiZz6Qg62I5` scheduled for **2026-11-06T22:27:21Z** to resume the post-gate sequence.
- **Handoff recorded:** `CORRECTIVE_HANDOFF_302.md`. No commit made. No source/data/config/test/gate/threshold/cost model/universe/clock-gate/canonical state modified.

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
- `pytest` passes for: `tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py` (64 must pass).

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