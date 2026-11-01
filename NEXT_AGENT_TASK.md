# NEXT_AGENT_TASK — Re-check paper-trading state extension for 2026-11-02 (after close)

## Context
This session (UTC 2026-11-01T15:13Z, 10:13 EST, Sunday) verified the assigned extension task. The clock gate is released but the 2026-11-02 (Monday) US trading session has not closed yet — `session already complete: False`, `candidate available: no`. The session becomes usable only after 17:00 ET on Monday 2026-11-02.

Verification completed this session:
- `python research/extend_paper_trading_state.py` -> exit 0, `sessions extended: 0`, NAV before == NAV after == 133019.54382525434, state write count: 0, raw cache scratch (canonical data/raw untouched)
- `python research/drift_persistence_report.py` -> `stored == recomputed: True`, provenance block present (git_sha, state sha256, config hash)
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> 39 passed in 2.05s
- `git status --porcelain data/ config/` -> empty

Current state:
- `data/processed/paper_trading_state.yaml` `last_run_date`: 2026-10-30 (460 cumulative sessions)
- NAV: 133019.54382525434
- Rolling 63d Sharpe at 2026-10-30: -0.7689729823169228

## Objective
Run `python research/extend_paper_trading_state.py` at or after 17:00 ET on 2026-11-02 (or the start of the following local day) to extend the paper-trading state by one session if a completed 2026-11-02 bar is available. Record exact commands and outputs. Do not force writes or alter the clock gate.

## Acceptance criteria
- `python research/extend_paper_trading_state.py` exits 0.
- If a completed 2026-11-02 bar exists: `sessions extended: 1`, state `last_run_date` becomes `2026-11-02`, NAV updates, drift report `stored == recomputed: True`.
- If no completed bar is available: `sessions extended: 0`, state unchanged, NAV unchanged.
- `python research/drift_persistence_report.py` -> `stored == recomputed: True`.
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` passes.
- `git status --porcelain data/ config/` is empty (canonical data untouched).

## Validation commands
```bash
python research/extend_paper_trading_state.py
python research/drift_persistence_report.py
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, the cost model, the universe, or the clock-gate logic.
- Do not commit unless explicitly asked.
- Do not modify `data/raw/`; the fetcher uses scratch cache only.

## Supervisor disposition
- `.kilo-runtime/current-supervisor-recommendation.json` (recommendation_id `41287846582-attempt-1-review-0006-d2c561880272`, review cycle 6) claimed `get_provenance` is defined but never called and has no test coverage. **Premise is false**: `get_provenance` is defined at line 83, called at line 126 inside `build_report`, and emitted by `print_report` at lines 221-236. Disposition recorded as `verified` in `.kilo-runtime/worker-disposition.json` with grep and CLI evidence. No code change required.

## Notes
- This is a time-gated blocker, not a code defect. Do not attempt to force the extension before 17:00 ET on 2026-11-02.
- `research/reports/paper_trading_rolling.md` shows as modified (generated `git_sha` artifact rewritten to match HEAD); this is not data/config and should be left as-is.