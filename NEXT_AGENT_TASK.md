# NEXT_AGENT_TASK — Paper-trading extension gate check (post-236 verification)

## Handoff (invocation 2026-11-05T12:31Z — verified, pre-gate)
- **UTC 2026-11-05T12:31:24Z / 07:31:24 EST (Thu). Gate NOT released** (~9.5h until 22:00 UTC 2026-11-05). `extend_paper_trading_state.py` **NOT run** (scope boundary). No source/data/config/test/gate/threshold/cost/universe/canonical-state changes. No commit.
- **Fresh pre-gate verification (this invocation):** (1) `date -u && TZ=America/New_York date` -> Thu Nov 5 12:31:24 UTC / 07:31:24 EST 2026. (2) `python3 research/drift_persistence_report.py` -> rolling 63d Sharpe `2026-10-26 0.1284, 2026-10-27 0.7423, 2026-10-28 0.4459, 2026-10-29 0.1752, 2026-10-30 -0.7690, 2026-11-02 -1.3784, 2026-11-03 -1.3997, 2026-11-04 -0.8724`; `low_rolling_sharpe` persistence 6. (3) Raw audit (`data/raw/*.parquet`): no bar dated >= 2026-11-05 (`scan done`). (4) `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` -> **45 passed in 15.49s**. (5) `git status --porcelain data/ config/` -> empty.
- **State (unchanged):** `data/processed/paper_trading_state.yaml` last_run_date `2026-11-04`, NAV `133995.4210085515`. Working tree shows only `research/reports/paper_trading_rolling.md` self-generated `git_sha` provenance bump from drift report run (expected; do not commit unless asked). `.kilo-runtime/` empty (no recommendation/disposition).
- **Wakeup:** `wku_1abb1e800001jFF4cT25K8bBx9` scheduled **2026-11-05T22:05:00Z** to resume post-gate verification (commands 1–6 below).
- **Unresolved external blocker:** clock gate not released until 22:00 UTC; post-gate acceptance criteria unverifiable pre-gate. If no completed 2026-11-05 bar exists after release, expect `sessions_extended==0` with explicit reason and unchanged state. At/after gate run verification commands 1–6 in order.

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
