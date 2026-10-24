# Next Agent Task — Monday 2026-10-26 extension
## Context
- Last processed session: 2026-10-23 (Friday). Saturday 2026-10-24 run: no new completed session, clock gate NOT released (current ET 2026-10-24 00:54), data/ untouched.
- Integrity as of 2026-10-24: drift `stored == recomputed: True` (rolling 63d Sharpe -0.25492616117205563); git status --porcelain data/ empty; tests 29 passed (test_paper_trading_extend + test_drift_persistence).
- On/after Monday 2026-10-26 17:00 ET the clock gate should release and a completed Monday session may be available.

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
" filePath="/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/NEXT_AGENT_TASK.md