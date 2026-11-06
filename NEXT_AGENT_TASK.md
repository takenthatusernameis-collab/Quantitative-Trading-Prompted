# NEXT_AGENT_TASK — Paper-trading extension gate check (2026-11-06, pre-gate)

## Handoff (corrective invocation 515, 2026-11-06T00:51Z — pre-gate, gate NOT released)
- **UTC 2026-11-06T00:51:04Z / 19:51:04 EST (Thu).** Gate for 2026-11-06 **NOT released** until 22:00 UTC on 2026-11-06. `extend_paper_trading_state.py` **NOT run** for extension (scope boundary).
- **Durable project change this cycle (first in the corrective loop):** producer defect `rolling_max_dd_63d` corrected — see README "Cycle 1140". Canonical state rewritten (single field, sha256 `f9572aed...` -> `60b16fb4...`); `src/simulation/paper_trading.py`, `research/audit_state_aggregates.py`, `tests/test_state_aggregate_audit.py` updated; new tool `research/correct_rolling_max_dd_field.py`.
- **Pre-gate verification (fresh, no extension):** `extend_paper_trading_state.py` -> clock gate NOT released; `candidate available: no` (2026-11-06 future); `sessions extended: 0`; NAV `129990.36021343581` unchanged; `state write count: 0`; raw cache scratch. Required suite **61 passed (36.38s)** this cycle (was 47; +14 from `test_state_aggregate_audit.py` + `test_rolling_63d_gate_refresh.py`); drift report `stored == recomputed: True` (Sharpe `-2.1203`, persistence 7).
- **Supervisor:** recommendation `42124771982-attempt-1-review-0003-6eb37be3c38d` dispositioned `verified` in `.kilo-runtime/worker-disposition.json`.
- **Wakeup scheduled:** `wku_1ae20e821001r0As4ETUv5Vttt` at **2026-11-06T22:00:00Z** to run acceptance commands 1–6 for the 2026-11-06 gate.
- **Durable handoff:** `CORRECTIVE_HANDOFF_INVOCATION_515.md`.
- **Next candidate:** 2026-11-09 (Monday), usable after 17:00 ET / 22:00 UTC on 2026-11-09.

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