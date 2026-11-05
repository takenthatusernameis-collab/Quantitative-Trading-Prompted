# NEXT_AGENT_TASK — Paper-trading extension gate check (post-236 verification)

## Context
- Last processed session: **2026-11-04** (NAV `133995.4210085515`, 462 cumulative dates).
- Rolling 63d Sharpe at 2026-11-04: **-0.8724** (`low_rolling_sharpe`, persistence_days 6).
- Clock gate releases at **17:00 ET / 22:00 UTC on 2026-11-05** (Wednesday). Candidate session 2026-11-05 must be closed before extension.
- Idempotency and active extension path previously verified (offline + live verifier PASS, corrective 343; 45-test suite repeatedly PASS).
- `git status --porcelain data/ config/` must remain clean; `research/reports/paper_trading_rolling.md` git_sha provenance bumps on drift report runs are expected self-generated metadata (do not commit unless asked).

## Objective
At/after 22:00 UTC on 2026-11-05, run the real extension and persistence checks. Extend by at most one session to 2026-11-05 if a completed bar exists; otherwise `sessions_extended==0` with explicit reason and state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-05 session exists: `sessions_extended==1`, `last_run_date` advances to 2026-11-05, NAV changes, state write count 1, raw cache scratch.
- If not: `sessions_extended==0` with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent: `sessions_extended==0`, write count 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports drift metrics updated.
- `git status --porcelain data/ config/` shows only expected state update (no unintended changes).
- Full test suite (`tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py`) passes.

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify `data/raw/`.
- Do not hand-edit canonical state.
- **Do NOT run `extend_paper_trading_state.py` before 22:00 UTC on 2026-11-05** (gate not released; premature no-op).

## Verification commands (exact, in order)
1. `date -u && TZ=America/New_York date`
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -4`
4. `python3 research/extend_paper_trading_state.py 2>&1 | tail -6`
5. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`
6. `git status --porcelain data/ config/`

## Handoff (latest verified baseline — 2026-11-05T09:24Z corrective invocation 134)
- **UTC 2026-11-05T09:23:54Z** (04:23:54 EST, Thu). Gate **NOT released** (~12.6h until 22:00 UTC 2026-11-05). Scope boundary respected: `extend_paper_trading_state.py` not run (pre-gate premature no-op forbidden).
- **Inspected prior corrective log:** `/home/runner/work/_temp/kilo-session-19-recovery-133.log` shows status 1 due to model/auth error ("Sign up for free...") with no durable project changes. Working tree already contained uncommitted self-generated/regenerated report diffs (git_sha bumps in `research/reports/paper_trading_rolling.md` and regenerated `tsmomentum_*` report artifacts) and a consolidated `NEXT_AGENT_TASK.md`; `data/` and `config/` were clean.
- **Fresh verification (this invocation, pre-gate safe):**
  1. `date -u && TZ=America/New_York date` → Thu Nov 5 09:23:54 UTC 2026 / Thu Nov 5 04:23:54 EST 2026.
  2. `python3 research/drift_persistence_report.py 2>&1 | tail -6` → rolling 63d Sharpe `-0.8724` at 2026-11-04 (2026-10-28 0.4459 … 2026-11-04 -0.8724).
  3. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` → **45 passed in 30.99s**.
  4. `git status --porcelain data/ config/` → (empty).
- **State:** `data/processed/paper_trading_state.yaml` last_run_date `2026-11-04`, current_nav `133995.4210085515`, drift flags present (`low_rolling_sharpe` persistence 6). HEAD `115169e`. No 2026-11-05 bar in canonical `data/raw` (per prior evidence; `data/raw` unchanged).
- **Decision:** no trading verdict published, no canonical state written, no strategy/gate/threshold/cost-model/universe/data change, no commit.
- **Materially different corrective action (justified, minimal):** updated this durable handoff to record invocation 134 evidence, prior-log diagnosis, and exact verification outputs; did not run `extend_paper_trading_state.py` pre-gate and did not touch `data/`/`config/`. Left uncommitted self-generated/regenerated report diffs uncommitted (no user request to commit; reverting would be unnecessary churn).
- **Unresolved blocker (external):** clock gate not released until 22:00 UTC 2026-11-05 and no completed 2026-11-05 bar in canonical `data/raw`. Post-gate acceptance criteria (real extension / idempotency of a real extend / expected state advancement if bar exists) cannot be verified before gate release; after release, `sessions_extended==0` remains possible if no completed bar is available.
- **Next distinct action at/after 22:00 UTC:** run verification commands 1–6 in order from this file. Extend by at most one session to 2026-11-05 only if a completed bar exists; otherwise record `sessions_extended==0` with explicit reason and keep state unchanged. Do not commit unless asked.

## Prior handoff summary (compressed)
- 2026-11-04T22:47Z–2026-11-05T08:48Z: repeated pre-gate checks confirmed gate closed, state unchanged (2026-11-04/NAV 133995.4210085515), drift -0.8724, 45 tests pass, `data/config` clean, idempotent no-op behavior. Corrective 343 additionally verified active extension path (offline pinned clock + live real-clock/yfinance) PASS with canonical artifacts untouched. Supervisor dispositions/wakeups recorded in prior logs; post-gate verification sequence remains the active task.
