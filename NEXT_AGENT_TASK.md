# NEXT_AGENT_TASK.md

## Cycle 902 — Publish the sample that was actually computed (and remove the last two frozen Sharpe literals)

### Context

Cycle 901 (see `research/reports/reference_sample_invariance_001.md`) made every
record-length-specific invariant **append-proof**: the canonical Sharpe of the
paper record, the incumbent backtest artifact and the Cycle 862 trailing-window
decomposition are now asserted on a *reference sample* (a fixed date boundary)
instead of on a frozen constant, so the 2026-10-19 session append could no
longer turn three read-only evidence tools and two tests red. All gates,
thresholds, decisions and metrics were left untouched.

Cycle 901 verification (exact commands and results):

```
python research/rolling_63d_gate_refresh.py      -> exit 0, OVERALL: PASS, 12/12 checks, NO-GO
python research/rebalance_schedule_audit.py      -> exit 0, OVERALL: PASS, 12/12 checks
python research/long_sample_overlay_attribution.py -> exit 0, OVERALL: PASS
python research/promotion_feasibility_backtest.py -> exit 0, OVERALL: PASS, decision=NO-GO
python -m pytest -q                              -> 234 passed in 321.77s
git status --porcelain data/ config/              -> empty
```

Two defects found while doing that work remain open:

1. **The published sample definition does not describe the sample.**
   `src/backtest/engine.py:run_backtest` does not slice the price frame it
   loads, and `src/data/yfinance_fetcher.py:YFinanceFetcher._load_cached`
   returns the whole parquet, so the *realized* sample of every committed
   backtest artifact is the union calendar of the universe from 1993-01-29
   (8,488 sessions), not the labelled common inception 2004-11-18.
   `research/promotion_feasibility_backtest.py` publishes
   `sample.start_date: 2004-11-18` together with `session_count: 8488` and
   prints `SAMPLE: 2004-11-18..2026-10-19 (8488 sessions)` — a label and a
   count that describe two different samples. The property is documented in
   `README.md` (Cycle 878 entry) but is not visible in the artifact itself.
   `run_backtest(..., end_date="2026-10-16")` also returns the 8488-session
   series: the requested window is silently ignored.
2. **Two published evidence generators still print frozen numbers** that the
   2026-10-19 append invalidated:
   `research/psr_continuation_horizon.py:93` ("current observed Sharpe
   1.748401") and `research/rolling_63d_rolloff_projection.py:179`
   ("Current observed Sharpe (full period): 1.748401"), while the same
   scripts compute the live value (1.771084 for the 450-session record).

### Objective

Make the published sample definition describe the sample that was actually
computed, and remove the last two frozen Sharpe literals — **without changing
any computed metric, gate, threshold, decision or committed number**.

### Acceptance criteria

1. The `sample` block of `research/promotion_feasibility_backtest.py` publishes
   both the label and the realized window: the label dates (common inception),
   the realized first/last session of the run and the realized session count,
   and the realized values equal the price-frame index of that run. The
   realized window must be derived **independently** from the `data/raw/*.parquet`
   union index (not from the engine's loader), and the block should also carry
   the per-symbol first/last date and row count, so that the ragged edge of the
   union calendar is visible in the artifact.
2. No metric moves: the canonical metrics, gate table, decision, failed gates
   and the reference-sample invariants stay bit-identical. The current-sample
   expectations are expressed as **reference-sample anchors plus a cache
   fingerprint**, not as values that the next session append invalidates:
   * reference-sample anchors (exact): the 8,487 sessions through 2026-10-16
     reproduce Sharpe 0.5646255767978904 / max DD -0.6224126346564325 /
     PSR 2.2219753177036448e-08, and the first 449 sessions of the paper record
     reproduce the canonical Sharpe 1.748401;
   * cache fingerprint: the per-symbol row count, last date and SHA-256 of the
     raw cache that the numbers were computed on (SPY 8488 rows through
     2026-10-19, sha256 971d02284b9790df...) are published with them, so a
     later append is visible as a fingerprint change instead of an unexplained
     number change;
   * decision and failed gates stay **NO-GO** and
     `['full_period_sharpe', 'rolling_63d_sharpe', 'max_drawdown', 'psr']`.
3. The two frozen literals are replaced by the live computed value, and the
   reports those scripts write
   (`research/reports/psr_continuation_horizon_001.md`,
   `research/reports/rolling_63d_rolloff_projection_001.md` if it exists) are
   regenerated and committed.
4. A test asserts that the published realized window equals the independently
   computed union index of the raw cache (no new stale literal; the test must
   survive the next data append).
5. The reference-sample invariants of Cycle 901 still hold: the 449-session
   reference sample of the paper record still reproduces 1.748401, the
   8,487-session reference sample of the incumbent still reproduces
   0.5646255767978904 / -0.6224126346564325 / 2.2219753177036448e-08.

### Validation commands

```
python research/promotion_feasibility_backtest.py     # OVERALL: PASS, decision=NO-GO, failed gates unchanged
python research/rolling_63d_gate_refresh.py           # OVERALL: PASS, 12/12 checks, decision NO-GO
python research/rebalance_schedule_audit.py           # OVERALL: PASS, 12/12 checks
python research/long_sample_overlay_attribution.py    # OVERALL: PASS
python research/psr_continuation_horizon.py           # prints the live observed Sharpe
python research/rolling_63d_rolloff_projection.py     # prints the live observed Sharpe
python research/go_no_go_evaluation.py                # decision NO-GO, failed gates ['rolling_63d_sharpe', 'psr']
python -m pytest -q                                  # whole suite green
git status --porcelain data/ config/                  # empty
```

### Scope boundaries

* Do **not** refresh the raw cache, extend the paper record, or change any
  file under `data/` or `config/`.
* Do **not** change the window semantics of `run_backtest` (making it slice the
  price frame would restate every published number — that is a separate,
  explicitly recorded research decision, not this task).
* Do **not** change a gate, a threshold, the decision mapping, a candidate
  configuration, a universe, the cost model or the Sharpe convention.
* Do **not** re-optimize or re-fit the incumbent, and do not start a new
  candidate family; this task is evidence hygiene.
* If a metric turns out to move, stop and report it instead of regenerating
  the published artifacts around the new value.
