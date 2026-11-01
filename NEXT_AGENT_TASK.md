# NEXT_AGENT_TASK — Extend paper-trading state to 2026-11-02 (after close)

## Context
The paper-trading state (`data/processed/paper_trading_state.yaml`) currently
ends at **2026-10-30** (459 cumulative sessions). The extension tool was run
on 2026-11-01 and confirmed:
- clock gate: released
- next expected session: **2026-11-02 (Monday)**
- session usable after: **17:00 ET on 2026-11-02**
- candidate available: no (session not yet closed)
- drift report: `stored == recomputed: True`

## Objective
Run `python research/extend_paper_trading_state.py` at or after 17:00 ET on
2026-11-02 (or the start of the following local day) to extend the
paper-trading state by one session if a completed 2026-11-02 bar is available.
Record exact commands and outputs. Do not force writes or alter the clock gate.

## Acceptance criteria
- `python research/extend_paper_trading_state.py` exits 0.
- If a completed 2026-11-02 bar exists: `sessions extended: 1`, state
  `last_run_date` becomes `2026-11-02`, NAV updates, drift report
  `stored == recomputed: True`.
- If no completed bar is available: `sessions extended: 0`, state unchanged,
  NAV unchanged.
- `python research/drift_persistence_report.py` -> `stored == recomputed: True`.
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q`
  passes.
- `git status --porcelain data/ config/` is empty (canonical data untouched).

## Validation commands
```bash
python research/extend_paper_trading_state.py
python research/drift_persistence_report.py
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q
git status --porcelain data/ config/
```

## Scope boundaries
- Do not change thresholds/gates, the cost model, the universe, or the clock-gate
  logic.
- Do not commit unless explicitly asked.
- Do not modify `data/raw/`; the fetcher uses scratch cache only.
