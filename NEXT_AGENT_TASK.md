# NEXT_AGENT_TASK — Execute post-gate-release extension run (Cycle 1088)

## Context (evidence from this session, 2026-11-03T07:11 UTC)
- Current canonical state (verified by reading data/processed/paper_trading_state.yaml):
  last_run_date 2026-11-02, NAV 132606.795692673. State sha256 unchanged at
  43074f0e02629cdc2929c83c536a89be1982e39eb95ebfcb6b39ea7e90bcf41e.
- Current time 2026-11-03 02:11 ET (07:11 UTC). The 2026-11-03 US session has not
  yet closed (closes 16:00 ET; gate releases 17:00 ET ~22:00 UTC).
- Clock gate: NOT released. Next expected session 2026-11-03 (Tuesday), usable
  after 17:00 ET on 2026-11-03.
- Corrective 431 fixed a real forward-compatibility defect in the live fetch path:
  `src/data/yfinance_fetcher.py:215` used the deprecated `DatetimeIndex.weekday`
  accessor (removed in a future pandas; emitted 4 of the 140 warnings in the
  target suite). It is now `DatetimeIndex.day_of_week` (semantically identical,
  verified [1,2,3] on 2026-11-03/04/05). The scalar `pd.Timestamp.weekday()` used
  in extend_paper_trading_state.py:77 is NOT deprecated in pandas 3.1.0 and was
  left untouched. Target suite now: 45 passed, 136 warnings (was 140); no
  "weekday" warnings remain.
- Prior cycle (1087) ran the same checks at 02:06 ET with identical results:
  sessions_extended == 0, NAV unchanged, 0 writes, drift stored == recomputed True,
  tests 45 passed.
- Corrective 430 fixed a durable artifact defect: the committed generated report
  `research/reports/paper_trading_rolling.md` quoted Current NAV $132,195.33 while
  the canonical state holds 132606.80. It has been regenerated from the canonical
  state via `generate_paper_report` and now agrees (NAV $132,606.80).
- Corrective 429 ran a clock-pinned active-path probe (PASS) against live data and
  confirmed the real write path reproduces the committed 2026-11-02 state
  bit-for-bit (132606.80); the 132,195.33 figure in that probe's report was an
  artifact of the probe truncating run_history without resetting current_nav,
  not a state defect — the committed state is reproducible from live data.

## Objective
After 17:00 ET on 2026-11-03 (~22:00 UTC), run the real extension and persistence
checks. Expect the extension to target the last completed session in live data:
since 2026-11-03 has not closed yet, the target is 2026-11-02, giving
sessions_extended == 1 and last_run_date advancing to 2026-11-02 if a completed
2026-11-02 bar exists in live data; otherwise sessions_extended == 0 with explicit
reason. (Note: the canonical state already reflects 2026-11-02, so the real run
after gate release is expected to be a no-op on the state itself — the value is
in confirming the live path executes cleanly with the fixed fetcher.)

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py` and record observed
  gate/candidate/sessions_extended/last_run_date/NAV.
- If a completed session exists: sessions_extended == 1 and last_run_date advances
  to that session; else sessions_extended == 0 with explicit reason.
- Run a second invocation to confirm idempotency: sessions_extended == 0,
  state write count == 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports stored == recomputed: True.
- `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py
  tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q` passes,
  with no `DatetimeIndex.weekday` warnings.
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