# Corrective Handoff 431

## Diagnosis
- Recovery-430 (the previous corrective invocation) made a durable source change
  (regenerated `research/reports/paper_trading_rolling.md`), but the *live
  extension path* it left behind still emitted a real defect: the installed
  pandas 3.1.0 emits `Pandas4Warning: DatetimeIndex.weekday is deprecated and
  will be removed in a future version. Use DatetimeIndex.day_of_week instead.`
  from `src/data/yfinance_fetcher.py:215`. The 4-target test suite showed
  **140 warnings**, of which the `DatetimeIndex.weekday` deprecation was the
  dominant class (replay logs confirm it fires on every live fetch through
  `_align`). This is a genuine forward-compatibility break in the path that the
  real `extend_paper_trading_state.py` run after gate release will execute —
  materially different from the previous no-op/verification-only approaches,
  which never touched the live fetch path.
- The gate for 2026-11-03 is still NOT released (now 02:11 ET; releases 17:00 ET
  ~22:00 UTC). The real extension therefore still cannot advance the state, but
  the fetch path it will use is now clean.
- Verified that the scalar `pd.Timestamp.weekday()` (used in
  `extend_paper_trading_state.py:77`) is NOT deprecated in pandas 3.1.0, so it
  was correctly left untouched (scope discipline: fix only the deprecated
  accessor).

## Changes made
- `src/data/yfinance_fetcher.py:215`: `all_index.weekday` -> `all_index.day_of_week`
  (semantically identical: both return Monday=0..Sunday=6; verified on
  2026-11-03/04/05 -> [1,2,3]).

## Verification (exact commands and outputs)
1. Live extension run (gate still not released):
   - `python3 research/extend_paper_trading_state.py 2>&1 | tail -25` -> exit 0;
     clock gate NOT released; next expected session 2026-11-03 (Tuesday);
     candidate available: no (today and still in progress); `no new completed
     session`; `sessions extended: 0`; NAV before/after 132606.795692673;
     `state write count: 0`; raw cache: scratch. No Pandas4 warning emitted.
2. Idempotency:
   - second run -> `sessions extended: 0`, NAV unchanged, `state write count: 0`.
3. Drift persistence:
   - `python3 research/drift_persistence_report.py 2>&1 | grep -i "stored == recomputed"`
     -> `stored == recomputed:     True`
4. Target test suite:
   - `python3 -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py
     tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py -q`
     -> `45 passed, 136 warnings in 17.97s` (was 140 warnings; the 4 removed are
     the `DatetimeIndex.weekday` deprecations from the live `_align` path;
     confirmed by grepping the pytest output for "weekday" -> no matches).
5. Direct `_align` probe (warning-free):
   - `python3 -c "...YFinanceFetcher._align({'A':f1,'B':f2})..."` with
     `warnings.catch_warnings(record=True)` -> `align warnings: []`; index and
     `day_of_week` values correct ([1,2,3]).
6. Canonical state integrity:
   - `sha256sum data/processed/paper_trading_state.yaml` ->
     `43074f0e02629cdc2929c83c536a89be1982e39eb95ebfcb6b39ea7e90bcf41e`
     (unchanged from the provenance block; matches committed hash).
7. Tree cleanliness:
   - `git status --porcelain data/ config/` -> empty (canonical data/config untouched).
   - `git status --porcelain` -> ` M research/reports/paper_trading_rolling.md`
     (pre-existing from 430) and ` M src/data/yfinance_fetcher.py` (this fix).

## Durable evidence produced
- `src/data/yfinance_fetcher.py:215` now uses `DatetimeIndex.day_of_week`; the live
  fetch path no longer emits the pandas-3.1 deprecation warning.

## Unresolved blockers
- Clock gate for 2026-11-03 not released (releases 17:00 ET ~22:00 UTC). The real
  `extend_paper_trading_state.py` run after gate release remains the authoritative
  acceptance action; expected to extend to 2026-11-02 (the last completed session
  in live data) per the task's "if a completed session exists" branch, not
  2026-11-03, because the 2026-11-03 session has not closed yet.
- Canonical state must still not be advanced by hand; the real script owns the write.

## Safety
Research/backtesting only, no live trades. No deps/services added, no secrets
accessed, no workflow/agent changes, no threshold/gate/cost-model/universe edits,
no commits, no data/raw writes. Clean-tree invariant for data/ config/ respected.
All pre-registrations and promotion gates preserved.