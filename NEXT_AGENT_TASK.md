# NEXT_AGENT_TASK.md

## Cycle 919 — Confirm full test suite green after Cycle 918 (read-only regression check)

### Context
Cycle 918 added `research/tsmomentum_sma175_candidate_eval.py` + `tests/test_tsmomentum_sma175_candidate_eval.py` (SMA-175 independent candidate eval, read-only, 48 folds, mean Sharpe 1.5400, OVERALL: PASS). Cycle 918's acceptance criterion #3 requires "existing anchor tests remain green." The full suite has not yet been run against the final tree with the new test added, so criterion #3 is not yet evidenced.

### Objective
Run the full test suite and confirm it stays green (no regressions from the Cycle 918 addition), and verify data/, config/, and committed artifacts are byte-identical before/after (immutability). Read-only: no network, no writes under data/ or config/, no changes to run_cycle6.py or any committed artifact.

### Acceptance criteria
1. `python -m pytest -q` exits 0 with all tests passing (existing anchor tests remain green; the new `tests/test_tsmomentum_sma175_candidate_eval.py` included).
2. `git status --porcelain data/ config/` -> empty (nothing written under data/ or config/).
3. `git diff --stat -- research/run_cycle6.py` -> empty (incumbent baseline not mutated).
4. Committed artifacts under `research/experiments/` and `research/reports/` byte-identical before and after the run (the SMA-175 report may be re-stamped by its own generator; that is the tool's own behavior, not a suite regression — confirm no *other* committed artifact moved).
5. No new dependencies; no network access.

### Scope boundaries
- Do not change any source, config, data, or committed artifact.
- Do not add dependencies, services, or infrastructure.
- Research/backtesting only; no live trading, no secrets, no credentials.

### Validation commands
```bash
python -m pytest -q
git status --porcelain data/ config/
git diff --stat -- research/run_cycle6.py
```

### Evidence artifacts
- Full-suite exit code and pass/fail count.
- `git status` / `git diff` output showing data/, config/, run_cycle6.py unchanged.

### Handoff (for the cycle after)
- Changed: NEXT_AGENT_TASK.md prepared (Cycle 919).
- Verified (this session): Cycle 918 tool -> OVERALL: PASS (48 folds, mean Sharpe 1.5400); Cycle 918 test -> 5 passed; run_cycle6.py, data/, config/ unmutated; no new deps.
- Unresolved: full-suite green status (criterion #3) — pending this cycle's run.
- Failed approaches: none.
- Next task: run `python -m pytest -q` and confirm green + immutability; then advance to the next evidence-based cycle.
