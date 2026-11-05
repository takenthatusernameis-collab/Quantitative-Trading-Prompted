# NEXT_AGENT_TASK — Paper-trading extension gate check (2026-11-09, pre-gate)

## Handoff (current invocation, 2026-11-05T23:51:18Z — pre-gate, gate NOT released)
- **UTC 2026-11-05T23:51:18Z / 18:51:18 EST (Thu).** Gate for 2026-11-06 **NOT released** until 22:00 UTC on 2026-11-06. `extend_paper_trading_state.py` **NOT run** (scope boundary; pre-gate no-op).
- **Pre-gate verification (no state changes):** drift report tail shows 2026-11-05 `-2.1203` (consistent). `pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` -> **47 passed in 27.42s**. `git status --porcelain data/ config/` empty. `git diff --name-only HEAD` empty. State sha256 `f9572aed9ca9c90d5c2ba7c2dbde2cbc573509636de2b5cc231073f06eee0c28` unchanged: `last_run_date 2026-11-05`, `current_nav 129990.36021343581`.
- **Supervisor:** recommendation `42124771982-attempt-1-review-0003-6eb37be3c38d` dispositioned `accepted` in `.kilo-runtime/worker-disposition.json`.
- **Wakeup scheduled:** `wku_1ae20e821001r0As4ETUv5Vttt` at **2026-11-06T22:00:00Z** to run acceptance commands 1–6 for the 2026-11-06 gate.
- **Next candidate:** 2026-11-09 (Monday), usable after 17:00 ET / 22:00 UTC on 2026-11-09.

## Context
- Last processed session: **2026-11-05** (NAV `129990.36021343581`).
- Rolling 63d Sharpe at 2026-11-05: **-2.1203** (low_rolling_sharpe).
- Clock gate for 2026-11-09 releases at **17:00 ET / 22:00 UTC on 2026-11-09**.
- `git status --porcelain data/ config/` must remain clean except expected state update only after a real extension write.

## Objective
At/after **22:00 UTC on 2026-11-09**, run the real extension and persistence checks. Extend by at most one session to 2026-11-09 only if a completed bar exists; otherwise record `sessions_extended==0` with explicit reason and keep state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-09 session exists: `sessions_extended==1`, `last_run_date` advances to 2026-11-09, NAV changes, state write count 1.
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
- Do NOT run `extend_paper_trading_state.py` before 22:00 UTC on 2026-11-09.

## Verification commands (exact, in order; run at/after 22:00 UTC)
1. `date -u && TZ=America/New_York date`
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -6`
4. `python3 research/extend_paper_trading_state.py 2>&1 | tail -8`  (idempotency)
5. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`
6. `git status --porcelain data/ config/`