# NEXT_AGENT_TASK — Paper-trading extension gate check (2026-11-06, pre-gate)

## Handoff (corrective invocation 1054, 2026-11-06T04:53Z — pre-gate, gate NOT released)
- **UTC 2026-11-06T04:53:02Z / 23:53:02 EST (Thu).** Gate for 2026-11-06 **NOT released** until 22:00 UTC on 2026-11-06 (~17h 7m). `extend_paper_trading_state.py` **NOT run** for real extension (scope boundary). Blocker is temporal only; 355-min cutoff expires before gate.
- **Cycle 1141 fix (uncommitted, verified intact):** `regime_persistence_low` dead-flag corrected in `src/simulation/paper_trading.py` + `research/run_cycle10.py` (removed `previous_regime_exposure != regime_exp` predicate so flag fires independently of regime flips; was subset of `regime_flip`). `tests/test_drift_persistence.py` adds 3 regression tests. Targeted regression: **3 passed**. Fix presence confirmed in both producers.
- **Pre-gate verification (fresh, invocation 1054):** canonical state sha256 `60b16fb460da735e85d8a1935d6604306eed48f8bc927bc8849e31fec19498f8` (`last_run_date` 2026-11-05, NAV 129990.36021343581); `audit_state_aggregates.py` → 463 sessions (2025-01-02→2026-11-05), 11 fields, `all_match: True`; `drift_persistence_report.py` last 2026-11-05 Sharpe `-2.1203` consistent (stored==recomputed). Pre-gate `extend_paper_trading_state.py`: `clock gate: NOT released`, `candidate available: no`, `sessions extended: 0`, NAV unchanged, `state write count: 0`, `raw cache: scratch`.
- **Acceptance suite:** `tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py` → **64 passed in 34.52s**.
- **Durable handoff:** `CORRECTIVE_HANDOFF_INVOCATION_1054.md`. Prior: `CORRECTIVE_HANDOFF_INVOCATION_1053.md`, recovery log `/home/runner/work/_temp/kilo-session-9-recovery-1053.log`.
- **No commit made** (not requested). `git status --porcelain data/ config/` clean. `data/raw/` untouched. Unrelated pre-existing worktree diffs/untracked files left untouched.

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