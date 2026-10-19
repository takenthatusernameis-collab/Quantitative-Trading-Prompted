# NEXT AGENT TASK — Cycle 880

## Context

Cycles 878 and 879 established two facts that change how the loop must read
its own gates (reports `research/reports/long_sample_overlay_attribution_001.md`
and `research/reports/gate_false_negative_rate_001.md`):

1. The incumbent's trailing 63-session promotion-gate failure is an
   **overlay-timing** outcome, not signal decay: the raw signal was profitable
   in the same window (L0-net Sharpe +0.307230 vs -0.211884 executed).
2. The gate statistic is **noisy**: over the incumbent's own 8,425 rolling-63
   windows the executed path fails the >= 0.9 gate in **39.16%** of them, and
   the current window sits at the 11.13th percentile — an ordinary failure.

Meanwhile the repository's own inventory contains exactly **one family that
has never been tested as a candidate**: the *overnight session* effect.
`research/experiments/overnight_drift_exploratory_001.md` (exploratory
diagnostic, no alpha claim) measures it on the committed cache:

| Asset (full history) | Overnight ann. mean | Overnight Sharpe | Intraday Sharpe |
|---|---|---|---|
| SPY | 8.37% | 0.790 | 0.122 |
| QQQ | 13.40% | 0.939 | -0.004 |
| IWM | 12.14% | 0.916 | -0.123 |

with the 2020+ sub-period still positive (SPY 8.37%, QQQ 12.40%, IWM 15.91%
annualized overnight). The mechanism is documented and distinct from every
candidate in the repository (retail open-of-session buying, institutional flow
timing, delayed price discovery); every candidate evaluated so far is a
close-to-close momentum or rotation signal. The turn-of-month candidate
(`calendar_effects_001`) was tested and rejected (WF mean OOS Sharpe -0.0254),
so the calendar/session-timing space is not exhausted.

## Objective

Pre-register and evaluate **one** new candidate — the overnight-session
capture candidate `overnight_001` — under the repository's hypothesis-first,
walk-forward, cost-aware discipline, and label it.

Pre-registration file (write it BEFORE running anything):
`research/hypotheses/overnight_capture_001.md`.

## Method (fixed by this task; do not re-choose)

- **Universe**: SPY, QQQ, IWM (the three most liquid US equity ETFs — the same
  choice as `research/hypotheses/calendar_effects_001.md`). No in-sample asset
  selection; no other symbol may enter the candidate. Common sample from IWM's
  inception (2000-05-26) to 2026-10-16.
- **Signal**: deterministic session timing. Hold a 1/3 equal-weight basket from
  the previous close to the next open; flat during the day. The overnight
  return of session *t* is `Open_t / Close_{t-1} - 1`; the position is
  established at the *previous* close and liquidated at the open, so the
  standing rule requires no price-based decision and cannot look ahead.
- **Costs**: the repository's model, 3 bp per unit of weight change, applied to
  the **actual** daily turnover (sell at the open, buy back at the close = 2x
  gross exposure per session => ~504 units of annual turnover => ~1.51%/yr of
  cost). Pre-register 5 bp and 10 bp per unit as a *cost-sensitivity row*
  (the documented "hidden cost of buying at the open"), never as a selection
  grid; the decision uses the 3 bp configuration. Multiple-testing count
  **N = 3** (the three cost levels).
- **Walk-forward**: `src/evaluation/walkforward.py:generate_walkforward_splits`
  with 10-year train, 12-month test, 6-month step, 21-day purge and 21-day
  embargo, exactly as the calendar-effects candidate did. The strategy has no
  fitted parameter, so the train window only bounds each fold; the per-fold
  statistic is the **test-period net Sharpe**. The script MUST assert the
  generated fold count and print the first and last fold.
- **Gates (pre-registered, repository convention)**: WF mean OOS Sharpe
  >= 0.9; positive fold rate >= 50%; pooled OOS trades > 100; plus the
  Deflated Sharpe Ratio at N = 3 and a block-bootstrap 95% CI
  (`src/evaluation/statistics.py`).
- **Benchmarks (evaluated on the identical folds)**: (a) the same basket held
  close-to-close (buy-and-hold), (b) the intraday-only leg (open to close).
  The overnight leg must beat the close-to-close benchmark **after costs**,
  otherwise the effect is equity beta, not an edge.
- **Data-integrity pre-check (do this first and publish it)**: confirm whether
  the committed cache stores **raw or dividend-adjusted** OHLC (the fetcher
  calls yfinance with `auto_adjust=False`, so the cache is expected to be raw
  — the exploratory diagnostic's caveat #5 asserts the opposite and must be
  checked, not assumed); state the ex-dividend implication for an overnight
  holder (the overnight leg does not receive dividends, so raw-price overnight
  returns are biased *downward* — conservative); confirm Open/Close alignment
  and count sessions with a missing Open.
- **Carry the Cycle 879 finding into the report**: whenever a rolling-63-day
  gate statistic is quoted for this candidate, report the statistic's own
  dispersion (or the false-negative rate measured on the candidate's own
  history) next to it. Do not change any gate.

## Falsification conditions (pre-registered)

The candidate is **Rejected/Failed** if ANY of:
1. WF mean OOS Sharpe < 0.9;
2. positive fold rate < 50%;
3. pooled OOS trades <= 100;
4. the net WF Sharpe does not exceed the same-fold close-to-close benchmark's;
5. the edge does not survive the 10 bp-per-unit cost row.

It is a **credible candidate for further validation** only if all of 1-5 hold
and the DSR does not reject.

## Acceptance criteria

1. `research/hypotheses/overnight_capture_001.md` exists, is committed with the
   cycle, and contains the mechanism, expected direction and magnitude, the
   data-integrity expectation, the execution convention, the cost model, the
   walk-forward design, the gates, the benchmarks and the falsification
   conditions — written **before** the backtest was run.
2. New read-only script `research/overnight_capture_backtest.py` (or a new
   candidate config `config/overnight_capture_001.yaml` plus script) that
   prints every number in the report and exits 0 with `OVERALL: PASS`.
3. New report `research/reports/overnight_capture_backtest_001.md` with: the
   data-integrity pre-check, the full-sample net metrics (Sharpe, CAGR, max
   drawdown, turnover, cost drag, trade count) for the 3 bp configuration, the
   per-fold walk-forward table, the pooled OOS statistics, the DSR and
   block-bootstrap CI, the cost-sensitivity row (3 / 5 / 10 bp), both
   benchmarks on identical folds, the gate outcomes and the falsification
   verdicts.
4. New experiment record `research/experiments/overnight_capture_backtest_001.md`
   in the repository format (hypothesis reference, data, point-in-time
   treatment, configuration, splits, results, trials = 3 cost levels,
   reproduction commands, decision label).
5. New offline tests in `tests/test_overnight_capture_backtest.py` (no network,
   no data mutation) for the pure helpers (overnight return computation,
   turnover/cost application, walk-forward fold count, the benchmark).
6. `python -m pytest -q` passes (95 existing + the new tests) and
   `git status --porcelain data/ config/` shows **no modification** to an
   existing file under `data/` or `config/` (a new candidate config file is
   allowed; no existing config may be edited).
7. The incumbent's decision is unchanged: **NO-GO**, live deployment
   unsupported; `python research/go_no_go_evaluation.py` still prints NO-GO
   with `side_effect_free: True`.

## Validation commands

- `python research/overnight_capture_backtest.py`
- `python research/go_no_go_evaluation.py`
- `python -m pytest -q`
- `git status --porcelain data/ config/`

## Scope boundaries

- Research/backtesting only. No live trading, no credential access, no
  scheduled jobs, no new dependencies.
- Do not modify existing files under `config/` or `data/`, the paper-trading
  state, the promotion gates, the incumbent configuration or the deployment
  decision. Do not modify `src/` (the shared engine is shared infrastructure;
  put candidate-specific code in `research/`).
- Do not re-optimize the incumbent and do not propose a variant of it; this
  cycle tests a **different** family.
- Do not dispatch this workflow or start additional agent sessions.

## Known pending item (deliberately not bundled with this cycle)

The 2026-10-19 US session is published by the provider but only becomes
*eligible* under the repository's own completeness rule
(`research/extend_paper_trading_state.py:session_is_complete`, `close_hour + 1`
= 17:00 ET = 21:00 UTC). Once that time has passed, the paper-trading record
can be extended from 449 to 450 sessions with the existing session-safe tool
(`python research/extend_paper_trading_state.py`, then
`python research/go_no_go_evaluation.py` and
`python research/drift_persistence_report.py`). Keep it separate from
candidate-evaluation cycles so the measured samples stay fixed.
