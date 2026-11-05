# NEXT_AGENT_TASK — Paper-trading extension gate check (post-gate, 2026-11-05 22:00 UTC)

## Handoff (invocation 509, 2026-11-05T21:43Z — pre-gate recheck; durable handoff produced)
- **UTC 2026-11-05T21:42:59Z / 16:42:59 EST (Thu). Gate NOT released** (~17m until 22:00 UTC 2026-11-05). `extend_paper_trading_state.py` **NOT run** (scope boundary). No source/data/config/test/gate/threshold/cost/universe/clock-gate/canonical state changes. No commit.
- **Corrective/durable:** created `CORRECTIVE_HANDOFF_INVOCATION_509.md` with fresh observed evidence. Backup wakeup `wku_1adaa7f1a0016d6AQa6UenR0Ky` scheduled @ 2026-11-05T22:08:14Z (post-gate commands 1–6); session-10 wakeup `wku_1ada7f53a0011NTIfjZnhfAmOs` @ 22:05Z still reported.
- **Supervisor protocol:** no current recommendation file at session start. `.kilo-runtime/worker-disposition.json` unchanged: `42076487843-attempt-1-review-0006-16aaace0809d` remains `superseded` (gross-vs-cost/turnover decomposition = separate post-gate bounded follow-up; pre-gate extension boundary preserved).
- **Fresh pre-gate verification (observed 21:42–21:43Z):** (1) `date -u && TZ=America/New_York date` -> `Thu Nov  5 21:42:59 UTC 2026 / 16:42:59 EST 2026`. (2) `python3 research/drift_persistence_report.py` tail -> `2026-10-28 0.4459 ... 2026-11-04 -0.8724`; `low_rolling_sharpe` persistence 6. (3) `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` -> **47 passed in 18.09s**. (4) Raw max (`data/raw/*.parquet`) -> **2026-11-04**; **no 2026-11-05 bar** observed. (5) `git status --porcelain data/ config/` -> empty. Canonical state (YAML, prior evidence): `last_run_date 2026-11-04`, `current_nav 133995.4210085515`, `low_rolling_sharpe -0.872439579425076` (2026-11-04, persistence 6).
- **Unresolved external blockers:** clock gate not released until 22:00 UTC 2026-11-05; 2026-11-05 completed bar availability unknown until post-gate. At/after gate run commands 1–6 with observed output; extend by <=1 session only if completed bar exists, else `sessions_extended==0` with explicit reason, NAV unchanged, 0 writes.
- **Handoff file:** `CORRECTIVE_HANDOFF_INVOCATION_509.md`. Prior: `CORRECTIVE_HANDOFF_INVOCATION_508.md`, `CORRECTIVE_HANDOFF_INVOCATION_507.md`.
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
- `pytest` passes for: `tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py` (observed: **47 passed in 18.26s** at 2026-11-05T17:44Z).

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
- 2026-11-05 pre-gate invocations (10:30Z–14:42Z, many): gate closed, state 2026-11-04/NAV 133995.4210085515, drift -0.8724 persistence 6, 45 tests pass, `data/config` clean, no 2026-11-05 raw bar observed. Wakeup `wku_1ac2a3c10001V5vnFDtnpQNy0k` scheduled 22:05Z.
- Corrective 343 / earlier: idempotent no-op behavior and active extension path previously verified; real extension remains post-gate.
