# Reference-sample invariance after the 2026-10-19 data append (Cycle 901)

## Context

Cycle 900 executed the overdue data refresh: the committed raw cache
(`data/raw/*.parquet`) and the paper-trading record
(`data/processed/paper_trading_state.yaml`) each grew by exactly one completed
US session, 2026-10-19. The append was legitimate, but three verification
tools and one test assert numbers that are *specific to the length of the
record*, so they went stale and reported failures that have nothing to do
with the gates:

| Tool / test | Symptom after the append |
|---|---|
| `research/rolling_63d_gate_refresh.py` | exits 1, `OVERALL: FAIL` (10/11 checks): the canonical Sharpe of the 450-session record is 1.771084, the check demands 1.748401 |
| `research/rebalance_schedule_audit.py` | exits 1, `OVERALL: FAIL`: the incumbent's Sharpe/PSR are pinned to the 8487-session sample |
| `research/long_sample_overlay_attribution.py` | exits 1, `OVERALL: FAIL`: the committed backtest artifact is not "reproduced" and the Cycle 862 continuity check compares against a moved window |
| `tests/test_rebalance_schedule.py::test_incumbent_artifacts_are_unchanged` | fails on `assert "sharpe_canon=0.564626" in proc.stdout` |
| `tests/test_rolling_63d_gate_refresh.py::test_tool_runs_standalone_and_is_read_only` | fails on `assert proc.returncode == 0` |

A false failure in a read-only evidence tool is worse than no check: it hides
the gate results it is supposed to publish behind a self-check that has gone
stale, and it makes the repository's own test suite red, so real regressions
stop being visible.

This cycle makes those invariants **append-proof** instead of re-pinning them
to a new frozen constant every time a session is appended.

## 1. The delta is data, not drift (classification before editing)

Nothing was edited before the record was classified against `HEAD~1`.

**Paper-trading state** (`git show HEAD~1:data/processed/paper_trading_state.yaml`):

| Property | `HEAD~1` | Now |
|---|---|---|
| sessions | 449 | 450 |
| `cumulative_returns[:449]` | — | identical to `HEAD~1` (True) |
| `cumulative_dates[:449]` | — | identical to `HEAD~1` (True) |
| appended session | — | 2026-10-19, daily return +0.433912% |
| `current_nav` | 133729.224310211 | 134309.49196738843 |
| `peak_nav` | 139120.07235486925 | 139120.07235486925 (unchanged) |

**Raw cache** (all eight symbols, `HEAD~1` vs now):

| Symbol | rows | added dates | dropped dates | prefix index equal | prefix values equal |
|---|---|---|---|---|---|
| SPY | 8487 -> 8488 | 2026-10-19 | none | True | True |
| QQQ | 6945 -> 6946 | 2026-10-19 | none | True | True |
| IWM | 6637 -> 6638 | 2026-10-19 | none | True | True |
| TLT | 6094 -> 6095 | 2026-10-19 | none | True | True |
| GLD | 5512 -> 5513 | 2026-10-19 | none | True | True |
| EFA | 6322 -> 6323 | 2026-10-19 | none | True | True |
| EEM | 5916 -> 5917 | 2026-10-19 | none | True | True |
| ^VIX | 5514 -> 5515 | 2026-10-19 | none | True | True |

"prefix values equal" compares every column of every historical row with
`atol=0, rtol=0` (exact). The only difference in the files is the `Volume`
dtype widening from `int64` to `float64`, which the appended (already float)
row forces; the values themselves are identical.

**The anchors still hold on the reference samples**, which is the decisive
evidence that no history was rewritten:

| Reference sample | Recomputed | Published | Equal |
|---|---|---|---|
| state, first 449 sessions, canonical Sharpe | 1.748401 | 1.748401 | yes (1e-9) |
| incumbent path, 8487 sessions through 2026-10-16, Sharpe | 0.5646255767978904 | 0.5646255767978904 | yes (exact) |
| incumbent path, 8487 sessions, max drawdown | -0.6224126346564325 | -0.6224126346564325 | yes (exact) |
| incumbent path, 8487 sessions, PSR | 2.2219753177036448e-08 | 2.2219753177036448e-08 | yes (exact) |
| Cycle 862 trailing window (2026-07-21..2026-10-16) decomposition | max diff 4.587e-07 pp | Cycle 862 | yes (tol 1e-7) |

The full-sample numbers moved only because the sample grew by one session:

| Metric | 8487 sessions (through 2026-10-16) | 8488 sessions (through 2026-10-19) |
|---|---|---|
| incumbent canonical Sharpe | 0.5646255767978904 | 0.5657179297830458 |
| incumbent max drawdown | -0.6224126346564325 | -0.6224126346564325 |
| incumbent PSR | 2.2219753177036448e-08 | 1.6549061233035153e-08 |
| paper record canonical Sharpe | 1.748401 (449 sessions) | 1.771084 (450 sessions) |

## 2. The fix: assert on a reference sample, publish the current sample

A pinned metric that belongs to a *sample* has to be pinned to the sample.
The repository already had this convention in
`research/long_sample_overlay_attribution.py` (`PUBLISHED_BACKTEST` with
`label_start_date` / `label_end_date`); this cycle applies it to every
record-length-specific invariant:

* **Reference sample** — the pinned value is asserted on the committed data
  truncated at a fixed date (state: the first 449 sessions; incumbent
  backtest: the 8487 sessions through 2026-10-16; Cycle 862: the 63 sessions
  through 2026-10-16). Because the engine's path is point-in-time (the weights
  at t use data up to t only) and the state's prefix is immutable, truncating
  reproduces the published path exactly. An append-only extension of the data
  therefore cannot invalidate the invariant, while a rewrite of history still
  fails it.
* **Current sample** — the numbers that the committed reports publish for the
  current data are still pinned (snapshot), so a code change that moves them is
  still caught, and the raw-cache fingerprint (per-symbol row count, last
  date, SHA-256) is printed with them so a data change is visible in the
  evidence.
* **Independent re-derivation** — the gate-evidence tool no longer compares
  its published canonical Sharpe against a frozen constant at all: it
  re-derives it from the committed record with the canonical formula written
  out, and checks it against the production gate value.

Files changed:

| File | Change |
|---|---|
| `research/rolling_63d_gate_refresh.py` | the unconditional 1.748401 pin is replaced by (a) an independent re-derivation of the published Sharpe from the record, (b) the production-gate equality check (unchanged), (c) a 449-session reference-sample anchor; the "N failing windows" label is now derived instead of frozen |
| `research/rebalance_schedule_audit.py` | the incumbent invariant is asserted on the 8487-session reference sample; the full-sample numbers and the raw-cache fingerprint are reported next to it |
| `research/long_sample_overlay_attribution.py` | the committed artifact is compared on its 8487-session reference sample, and the Cycle 862 continuity check uses the 63-session window Cycle 862 published (2026-07-21..2026-10-16) instead of the current trailing window |
| `research/trailing_window_attribution.py` | the "449-session / 444-session record" labels are derived from the record instead of frozen |
| `tests/test_rebalance_schedule.py` | the incumbent constants are split into reference-sample and current-sample pins, and `test_incumbent_reference_sample_numbers_have_not_moved` asserts the reference-sample invariant directly |

## 3. What did not change

No gate threshold, gate table, candidate configuration, cost model, universe,
Sharpe convention, promotion decision or committed metric was changed.

* Paper-trading record: decision **NO-GO**, failed gates `['rolling_63d_sharpe', 'psr']`,
  rolling 63d Sharpe -0.448918, PSR 0.695606.
* Candidate backtest: decision **NO-GO**, failed gates
  `['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown', 'psr']`.
* The state file and the raw cache are byte-identical before and after every
  tool run (the read-only proof inside each tool).

## 4. Reproduction

```
python research/rolling_63d_gate_refresh.py        # OVERALL: PASS, 12/12 checks, decision NO-GO
python research/rebalance_schedule_audit.py        # OVERALL: PASS, 12/12 checks
python research/long_sample_overlay_attribution.py # OVERALL: PASS
python research/promotion_feasibility_backtest.py  # OVERALL: PASS, decision=NO-GO
python -m pytest -q                                # full suite
```

## 5. Residual finding (not fixed here): the backtest window is not honoured

`run_backtest(symbols, start_date, end_date, ...)` does not honour the
requested window when the data comes from the committed cache:
`src/data/yfinance_fetcher.py:YFinanceFetcher._load_cached` returns the whole
parquet and `src/backtest/engine.py:run_backtest` never slices it. Measured
consequences:

* `research/promotion_feasibility_backtest.py` prints `SAMPLE: 2004-11-18..2026-10-19 (8488 sessions)`,
  but the realized sample starts **1993-01-29** (the union calendar of the seven
  symbols) and has 8488 sessions: the published sample definition does not
  describe the sample it was computed on.
* `run_backtest(..., end_date="2026-10-16")` returns the 8488-session series,
  i.e. `end_date` is silently ignored.
* `research/long_sample_overlay_attribution.py` prints the same mismatch
  ("label start 2004-11-18, realized start 1993-01-29").

This is left as the next cycle's task: it is a research decision (correct the
label, or truncate the sample and restate every published number), not a
mechanical fix, and the published numbers must not move without an explicit,
recorded decision.
