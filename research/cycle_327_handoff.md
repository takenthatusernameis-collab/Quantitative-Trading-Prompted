# Cycle 327 corrective handoff — append-only canonical raw cache guard

## Context
Corrective invocation 327. The previous corrective log (cycle 325) reported only a
timing blocker (no new completed US trading session; next eligible 2026-10-26
17:00 ET) and emitted `CORRECTIVE_VERIFICATION=BLOCKED`. Re-inspection of the
worktree found a **second, previously documented but unimplemented** defect that
*is* fixable now: cycle 865's handoff recorded that `data/raw/SPY.parquet` had been
truncated from 8,491 rows to 17 rows, and explicitly recommended making the
canonical `data/raw` cache append-only so a partial scratch fetch could never
overwrite committed history. That recommendation was never implemented.

## Root cause (verified by code inspection)
`YFinanceFetcher._save_cached` in `src/data/yfinance_fetcher.py:169` wrote the
downloaded window straight to the canonical cache path with no history check:
```python
def _save_cached(self, symbol, df):
    df.to_parquet(self._cache_path(symbol))
```
Any `force=True` fetch with `raw_dir=None` (the canonical default) therefore
overwrote committed history with only the requested window — exactly the SPY.parquet
truncation. Callers using `raw_dir=<scratch>` (e.g. `extend_paper_trading_state.py`,
`refresh_raw_cache.py`) were already safe; the defect was in the shared fetcher.

## Correction applied (smallest sufficient change)
1. `src/data/yfinance_fetcher.py`:
   - Added `append_only: bool = True` parameter to `YFinanceFetcher.__init__`.
   - `_save_cached` now, before writing, reads the existing committed frame and
     **raises `RuntimeError`** if the download's max date is *earlier* than the
     committed history's max date (fail closed, never truncate). Writes that reach
     further (a genuine append) or target a missing cache file are allowed.
   - `fetch_universe` defaults to append-only, so the canonical path is protected
     by default; callers can opt out explicitly if a true overwrite is intended.
2. New test file `tests/test_yfinance_fetcher_append_only.py` (5 tests, all
   offline, network stubbed): allows append when download reaches further, refuses
   a truncating download (and leaves the file byte-identical), allows opt-out via
   `append_only=False`, allows write when no committed cache exists, and confirms
   `fetch_universe` defaults to append-only.

## Verification (exact commands and observed results)
- `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py tests/test_refresh_raw_cache.py tests/test_yfinance_fetcher_append_only.py -q`
  -> **46 passed** in 3.25s.
- `python research/drift_persistence_report.py` -> `stored == recomputed: True`;
  rolling 63d Sharpe -0.25492616117205563 as of 2026-10-23.
- `python research/extend_paper_trading_state.py` -> EXIT=0; `no new completed
  session`; `sessions extended: 0`; `state write count: 0`; `raw cache: scratch
  (canonical data/raw untouched)`. Timing blocker unchanged (still correct).
- Raw-cache integrity scan over all 26 `data/raw/*.parquet` -> 0 suspect files
  (all >100 rows, 0 duplicate dates, 0 nulls). `SPY.parquet` intact at 8,491 rows,
  max 2026-10-22.
- `git status --porcelain data/` -> empty (canonical raw cache untouched by this
  cycle). Working tree: `M src/data/yfinance_fetcher.py`, untracked
  `tests/test_yfinance_fetcher_append_only.md` and `research/cycle_325_handoff.md`.
- `ruff` not installed in this environment; no lint command available. Style follows
  the existing file's conventions.

## Unresolved blocker (timing, not a defect)
Paper-trading extension remains timing-gated: `last_run_date` = 2026-10-23; the
next completed US trading session is Monday 2026-10-26, eligible after 17:00 ET.
Acceptance criteria 1-3 of NEXT_AGENT_TASK.md (real extension, idempotency,
integrity) still cannot be exercised until then. Criterion 4 (no-op with correct
readiness output) is satisfied.

## Next distinct investigation
On/after 2026-10-26 17:00 ET: run `python research/extend_paper_trading_state.py`
(real, no `--dry-run`). If it extends by exactly one session and writes state once,
run a second invocation to confirm the idempotent no-op, then verify
`stored == recomputed: True`, `git status --porcelain data/` empty, and re-run the
four test files above. Also run `python research/refresh_raw_cache.py` (real) to
append the new session to `data/raw` through the safe append path, and confirm the
new append-only guard does not block it (the refresh uses a scratch dir, so it is
unaffected, but worth confirming end-to-end).

## Safety
Research/backtesting only; no live trading. No strategy/gate/threshold/config
changes. Canonical raw cache untouched. Promotion gates, tests, and workflow
boundaries preserved. No commit performed (not requested).