# Next Agent Task — Monday 2026-10-26 extension
## Context
- Last processed session: 2026-10-23 (Friday). Saturday 2026-10-24 run: no new completed session, clock gate NOT released (current ET 2026-10-24 01:40), data/ untouched.
- Integrity as of 2026-10-24 (re-verified): drift `stored == recomputed: True` (rolling 63d Sharpe -0.25492616117205563); git status --porcelain data/ empty; tests 29 passed (test_paper_trading_extend + test_drift_persistence).
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

## Corrective handoff — 2026-10-24 (this session)
- What changed: small, behavior-preserving import/style corrections in the two task-relevant scripts (no strategy/gate/threshold/config changes):
  - `research/drift_persistence_report.py`: removed unused import `DEFAULT_CALENDAR_DAYS` (-1 line).
  - `research/extend_paper_trading_state.py`: `typing.Callable` -> `collections.abc.Callable`; `datetime.now(timezone.utc)` -> `datetime.now(UTC)`; sorted import block; reordered `fetch_universe` import (+4/-4 lines).
  - Deliberately left SIM103 untouched — ruff flags it "unsafe fix / may change runtime behavior."
- Verification commands & outputs:
  - `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> 29 passed (exit 0).
  - `python -m ruff check research/extend_paper_trading_state.py research/drift_persistence_report.py` -> 1 remaining error (SIM103, intentionally skipped); 4 of 5 original ruff errors resolved.
  - `git status --porcelain` -> 2 files modified (durable); `git status --porcelain data/` empty.
- Unresolved blocker: paper-trading extension remains gated — clock gate not released until Mon 2026-10-26 17:00 ET (today is Sat 2026-10-24). No state write attempted; `data/raw` untouched.
- Next cycle: on/after Mon 2026-10-26 17:00 ET, run `python research/extend_paper_trading_state.py` (no `--dry-run`), then verify idempotency + integrity per acceptance criteria above.
" filePath="/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/NEXT_AGENT_TASK.md