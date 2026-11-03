# NEXT_AGENT_TASK — Execute post-gate-release extension run (Cycle 1088)

## Context (evidence from corrective invocation 429, 2026-11-03T06:00 UTC)
- Gate releases at 17:00 ET on 2026-11-03 (~22:00 UTC). At probe time (01:00 ET)
  the gate was NOT released and the active path could not be exercised against
  the real script.
- Active write path is now **verified end-to-end against live yfinance data**:
  `research/reports/active_path_probe_429.md` shows RESULT: PASS with a clock
  pinned to the gate-release instant (2026-11-03 22:00 UTC), target 2026-11-02,
  sessions_extended 1, state_writes 1, NAV advanced, canonical state and
  `data/raw` byte-hashes unchanged.
- Live fetch is reachable and returns data through 2026-11-02 for all 7 universe
  symbols. The committed `data/raw` cache stops at 2026-10-19 and cannot by
  itself prove the 2026-11-02 session.
- Current canonical state: last_run_date 2026-11-02, NAV 132606.795692673.

## Objective
After 17:00 ET on 2026-11-03, run the real extension and persistence checks.
Expect sessions extended == 1 and last_run_date advances to 2026-11-02 if a
completed 2026-11-02 bar exists in live data; otherwise sessions extended == 0
with explicit reason. (A completed 2026-11-03 bar cannot exist before 17:00 ET,
so the realistic target is 2026-11-02, not 2026-11-03.)

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py` and record observed
  gate/candidate/sessions_extended/last_run_date/NAV.
- If a completed session exists: sessions_extended == 1 and last_run_date advances
  to that session; else sessions_extended == 0 with explicit reason.
- Run a second invocation to confirm idempotency: sessions_extended == 0,
  state write count == 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports stored == recomputed: True.
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py
  tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`
  passes.
- `git status --porcelain data/ config/` empty (no unintended writes).

## Validation commands
```bash
python3 research/extend_paper_trading_state.py 2>&1 | tail -40
python3 research/extend_paper_trading_state.py 2>&1 | tail -8
python3 research/drift_persistence_report.py 2>&1 | grep -i "stored == recomputed"
python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, cost model, universe, or clock-gate logic.
- Do not commit unless explicitly asked.
- Do not modify data/raw/.
- Do not revert pre-existing data/processed/paper_trading_state.yaml modifications.
- Do not hand-edit the canonical state to simulate the extension; the real script
  owns the write.