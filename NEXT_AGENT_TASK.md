# Next Agent Task — Extend paper trading state on/after Monday 2026-10-26 17:00 ET
## Context
- Current state: last processed session `2026-10-23` in `data/processed/paper_trading_state.yaml`. Current time at session start was `2026-10-24 03:08:09 EDT`; clock gate NOT released. Next expected session is `2026-10-26` (Monday), session usable after `17:00 ET on 2026-10-26`.
- Prior run of `python research/extend_paper_trading_state.py` (this session): exit 0 with `no new completed session`, `sessions extended: 0`, `NAV before == NAV after: 133634.38193355838`, `state write count: 0`, `raw cache: scratch (canonical data/raw untouched)`. Readiness block printed as above.
- Integrity verified now: `python research/drift_persistence_report.py` shows `stored == recomputed: True` (rolling 63d Sharpe -0.25492616117205563, persistence 10 days `2026-10-12 -> 2026-10-23`); `git status --porcelain data/` clean (only unrelated `research/reports/tsmomentum_sma175_candidate_eval_001.md` modified); `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> `29 passed`.

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
