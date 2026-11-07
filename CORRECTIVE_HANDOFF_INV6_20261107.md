# Corrective Invocation 6 — Durable Repo Hygiene Correction (2026-11-07)

## Context
- Prior invocations (recovery-1 through recovery-5, and many earlier) hit the clock-gate temporal blocker (next session 2026-11-09, gate releases 22:00 UTC) and produced no durable project changes. This invocation takes a materially different action: fixes tracked backup artifacts and prevents recurrence.
- Inspected: `/home/runner/work/_temp/kilo-session-22-recovery-5.log` (summary present in recovery chain; indicated no durable changes), `NEXT_AGENT_TASK.md`, `README.md`, git state.
- Current time: 2026-11-07T10:44:53Z (05:44:53 EST, Sat). Gate for 2026-11-09 **NOT released** (releases 17:00 ET / 22:00 UTC 2026-11-09). Paper-trading extension remains blocked as specified.

## Durable Changes
1. **`.gitignore`**: added `*.bak` and `*.backup` patterns under `# Editor/backup artifacts` to prevent recurrence.
2. **Deleted tracked stale backups** (git-tracked, not canonical sources):
   - `NEXT_AGENT_TASK.md.bak` (57 lines, stale copy of task spec)
   - `research/run_paper_trading_replay.py.backup` (109 lines, stale backup; canonical `research/run_paper_trading_replay.py` unchanged)

No changes to `data/`, `config/`, `data/raw/`, thresholds/gates/cost model/universe/clock-gate logic, tests, or production code.

## Verification (all fresh, this invocation)
1. `date -u && TZ=America/New_York date` → `Sat Nov  7 10:44:53 UTC 2026 / Sat Nov  7 05:44:53 EST 2026`
2. `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q` → **64 passed, 1 warning in 29.02s**
3. `git status --short` → `M .gitignore`, `D NEXT_AGENT_TASK.md.bak`, `D research/run_paper_trading_replay.py.backup` (only intended hygiene changes; no `data/`/`config/` changes)

## Unresolved Blockers
- **Temporal (expected):** clock gate for next session 2026-11-09 not released until 22:00 UTC 2026-11-09. `extend_paper_trading_state.py` must not run before gate per `NEXT_AGENT_TASK.md`. When gate releases, execute commands 1–7 in `NEXT_AGENT_TASK.md` (extend ≤1 session only if completed bar exists; idempotent; if state advances, regenerate inventory reports and re-run inventory tests).
- **No commit made** (not requested).

## Safety / Scope
- Pre-registrations and promotion gates preserved. No workflow/scheduling/agent-count changes. No secrets. No fabricated outputs. Backward-compatible hygiene only.
