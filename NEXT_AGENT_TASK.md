# Next Agent Task — Monday 2026-10-26 extension
## Context
- This session (2026-10-24 01:56 ET): ran `python research/extend_paper_trading_state.py` -> exit 0, `no new completed session`, `sessions extended: 0`, `NAV before == NAV after: 133634.38193355838`, `state write count: 0`, `raw cache: scratch (canonical data/raw untouched)`. Readiness block printed: `clock gate: NOT released`, `gate checks day after: 2026-10-24`, `next expected session: 2026-10-26 (Monday)`, `session usable after: 17:00 ET on 2026-10-26`. Integrity re-verified: `git status --porcelain data/` empty; `python research/drift_persistence_report.py` -> `stored == recomputed: True` (rolling 63d Sharpe -0.25492616117205563, persistence 10 days `2026-10-12 -> 2026-10-23`); `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> 29 passed; `python -m ruff check` -> 1 remaining error (SIM103, intentionally skipped per prior handoff — unsafe fix, may change runtime behavior).
- On/after Monday 2026-10-26 17:00 ET the clock gate should release and a completed Monday session may be available. Corrective verification confirms no safe change now; extension must wait for gate release.

## Objective
On/after Monday 2026-10-26 17:00 ET, extend paper trading state by exactly one completed session if present. If still no completed session (holiday/market closure), follow criterion 4. Do not fabricate data; do not change strategy/gate/threshold/config.

## Acceptance criteria
1. Run `python research/extend_paper_trading_state.py` (no `--dry-run`). If a new completed session exists, extend by exactly one session and write state once.
2. Verify idempotency: second invocation must be no-op (`sessions extended: 0`, `state write count: 0`, `git status --porcelain data/` empty).
3. Verify integrity after any write:
   - `python research/drift_persistence_report.py` -> `stored == recomputed: True`.
   - `git status --porcelain data/` empty.
   - `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> all pass.
4. If no new completed session exists, run exits 0 with `no new completed session`, readiness block printed, `data/` untouched.
5. Report exact commands and observed results.

## Scope boundaries
- No strategy/gate/threshold/config changes. Do not commit unless explicitly requested. Raw cache (`data/raw`) untouched. Research/backtesting only.