# NEXT_AGENT_TASK — Paper-trading extension gate check (post-236 verification)

## Handoff (corrective invocation 494, 2026-11-05T14:19Z — pre-gate re-verification; wakeup scheduled)
- **UTC 2026-11-05T14:19:42Z / 09:19:42 EST (Thu). Gate NOT released** (~7.67h until 22:00 UTC 2026-11-05). `extend_paper_trading_state.py` **NOT run** this invocation (scope boundary: do not run before 22:00 UTC). No canonical state/source/data/config/test/gate/threshold/cost/universe changes. No commit.
- **Fresh pre-gate-safe verification (observed):** (1) `date -u && TZ=America/New_York date` -> `Thu Nov  5 14:19:42 UTC 2026 / 09:19:42 EST 2026`. (2) `python3 research/drift_persistence_report.py` -> last 10 sessions include `2026-10-28 0.4459, 2026-10-29 0.1752, 2026-10-30 -0.7690, 2026-11-02 -1.3784, 2026-11-03 -1.3997, 2026-11-04 -0.8724`; `low_rolling_sharpe` persistence 6 consistent. (3) `pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` -> **45 passed in 18.32s**. (4) `git status --porcelain data/ config/` -> empty.
- **State (unchanged):** `data/processed/paper_trading_state.yaml` `last_run_date 2026-11-04`, `current_nav 133995.4210085515`. `.kilo-runtime/` empty (no recommendation/disposition). Durable handoff: `CORRECTIVE_HANDOFF_CORRECTIVE_494.md`.
- **Wakeup scheduled:** `wku_1ac150945001zugOnEZDIUT24K` at **2026-11-05T22:05:00Z** for post-gate verification commands 1–6 (this file).
- **Unresolved external blocker:** clock gate not released until 22:00 UTC 2026-11-05; 2026-11-05 bar availability unknown until post-gate. At/after gate run commands 1–6 with observed output; extend by <=1 session only if completed bar exists, else `sessions_extended==0` with explicit reason, NAV unchanged, 0 writes.

## Context
- Last processed session: **2026-11-04** (NAV `133995.4210085515`).
- Rolling 63d Sharpe at 2026-11-04: **-0.8724** (`low_rolling_sharpe`, persistence 6).
- Clock gate releases at **17:00 ET / 22:00 UTC on 2026-11-05**. Candidate session 2026-11-05 must be closed before extension.
- `git status --porcelain data/ config/` must remain clean (except expected state update only after a real extension write, if any).

## Objective
At/after **22:00 UTC on 2026-11-05**, run the real extension and persistence checks. Extend by at most one session to 2026-11-05 **only if a completed bar exists**; otherwise record `sessions_extended==0` with explicit reason and keep state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-05 session exists: `sessions_extended==1`, `last_run_date` advances to 2026-11-05, NAV changes, state write count 1, raw cache scratch/canonical rules respected by script.
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
- **Do NOT run `extend_paper_trading_state.py` before 22:00 UTC on 2026-11-05** (premature no-op; scope boundary).

## Verification commands (exact, in order; run at/after 22:00 UTC)
1. `date -u && TZ=America/New_York date`
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -6`
4. `python3 research/extend_paper_trading_state.py 2>&1 | tail -8`  (idempotency)
5. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`
6. `git status --porcelain data/ config/`

## Prior compressed context
- 2026-11-05 pre-gate invocations (10:30Z–12:22Z, many): gate closed, state 2026-11-04/NAV 133995.4210085515, drift -0.8724 persistence 6, 45 tests pass, `data/config` clean, no 2026-11-05 raw bar observed. Wakeup `wku_1aba9f229001aI7WBr7KMWagXg` scheduled 22:05Z.
- Corrective 343 / earlier: idempotent no-op behavior and active extension path previously verified; real extension remains post-gate.
