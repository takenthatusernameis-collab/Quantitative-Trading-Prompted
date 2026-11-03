# NEXT_AGENT_TASK — Execute post-gate-release extension run (Cycle 1086)

## Context (evidence from this session, 2026-11-03T06:59 UTC)
- Current canonical state (verified by reading data/processed/paper_trading_state.yaml):
  last_run_date 2026-11-02, NAV 132606.795692673. State sha256 unchanged at
  43074f0e02629cdc2929c83c536a89be1982e39eb95ebfcb6b39ea7e90bcf41e.
- Current time 2026-11-03 01:59 ET (06:59 UTC). The 2026-11-03 US session has not
  yet opened (market opens 09:30 ET) and has not closed.
- Clock gate: NOT released. Next expected session 2026-11-03 (Tuesday), usable
  after 17:00 ET on 2026-11-03 (~22:00 UTC).
- pytest 9.2.0 and pandas 3.1.0 are installed; the four target test files pass
  (45 passed, 140 warnings in ~18s).
- Prior cycle (1085) ran the same checks at 01:09 ET with identical results:
  sessions_extended == 0, NAV unchanged, 0 writes, drift stored == recomputed True,
  tests 45 passed, data/ and config/ clean.
- Corrective 430 fixed a durable artifact defect: the committed generated report
  `research/reports/paper_trading_rolling.md` quoted Current NAV $132,195.33 while
  the canonical state holds 132606.80. It has been regenerated from the canonical
  state via `generate_paper_report` and now agrees (NAV $132,606.80, run-history
  2026-11-02: NAV=$132,606.80). Provenance block refreshed by
  `drift_persistence_report.py`. No source/config/data-raw/state changes.

## Objective
After 17:00 ET on 2026-11-03 (~22:00 UTC), run the real extension and persistence
checks. Expect the extension to target 2026-11-03 (the session after last_run_date
2026-11-02): sessions_extended == 1 and last_run_date advances to 2026-11-03 if a
completed 2026-11-03 bar exists in live data; otherwise sessions_extended == 0 with
explicit reason.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py` and record observed
  gate/candidate/sessions_extended/last_run_date/NAV.
- If a completed session exists: sessions_extended == 1 and last_run_date advances
  to that session; else sessions_extended == 0 with explicit reason.
- Run a second invocation to confirm idempotency: sessions_extended == 0,
  state write count == 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports stored == recomputed: True.
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py
  tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes.
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
- Do not hand-edit the canonical state to simulate the extension; the real script owns the write.
- Do not wait passively past 17:00 ET on 2026-11-03; if the gate is still not released at run time, record sessions_extended == 0 with explicit reason and leave the next task to re-check after the session closes.