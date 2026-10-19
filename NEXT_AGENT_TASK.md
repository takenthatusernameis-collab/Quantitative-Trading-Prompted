# NEXT AGENT TASK — Cycle 879

## Context

Cycle 878 measured the incumbent's long-sample mechanism decomposition
(pre-registered in `research/hypotheses/overlay_mechanism_long_sample_001.md`;
report `research/reports/long_sample_overlay_attribution_001.md`). Three
results matter for the research process:

1. The trailing 63-session promotion-gate failure is an **overlay-timing**
   outcome, not signal decay: in the same window the raw signal was
   profitable (L0-net Sharpe +0.307230) while the executed path lost money
   (-0.211884).
2. On the full 8,487-session sample the overlay stack *improves* both risk
   readings (canonical Sharpe +0.564626 -> +1.485591, max drawdown -62.24%
   -> -9.93%) and costs compounded return instead.
3. The report explicitly leaves one question open (§5.2 item 3): **whether the
   rolling-63-day promotion gate is statistically informative or noisy.** The
   empirical distribution of that gate statistic over the incumbent's own
   long-sample history has never been measured, so a single trailing-window
   NO-GO is currently interpreted without any knowledge of how often the same
   statistic fails on the same strategy in other periods.

## Objective

Measurement-only, pre-registered: quantify the **empirical null distribution
of the promotion gate's rolling-63-day Sharpe statistic** on the incumbent's
own long-sample paths, and state the gate's false-negative rate, so that the
loop can interpret trailing-window NO-GOs correctly.

Pre-registration file (write it BEFORE running the measurement):
`research/hypotheses/promotion_gate_false_negative_001.md`.

**Disclosure requirement (honesty, not optional):** a feasibility probe of this
exact computation was already run in Cycle 878 (the rolling-63 Sharpe
distribution of the long-sample executed path), so the pre-registration is
*not* blind. The hypothesis file must state this explicitly and fix the
decision rule and the interpretation thresholds in advance, and must record
that **no candidate, promotion or rejection decision may depend on this
measurement** — it is a statement about a gate, not about a strategy.

## Method (fixed by this task; do not re-choose)

- Paths: the long-sample paths produced by
  `research/long_sample_overlay_attribution.py` (executed path L4 and raw
  signal L0), each net of its own 3 bp turnover cost. Reuse that script's
  helpers (`own_cost_net_path`, `annualised_turnover`) and
  `research/trailing_window_attribution.py:build_layers`; do not re-implement
  the layer chain.
- Statistic: the rolling-63-session canonical Sharpe, computed with the
  **live drift-flag estimator** `src/evaluation/drift.py:rolling_sharpe_series`
  (canonical `arithmetic_annualized_rf0`; zero-dispersion windows return 0.0
  by the repository convention). Report the number of zero-dispersion windows
  explicitly.
- Report for the executed path (and, for the overlay's effect on the gate,
  the raw-signal path): n windows, mean, sd, min, p01, p05, p25, median, p75,
  p95, p99, max; failure rates at the gate thresholds (< 0.9 promotion gate,
  < 0.5 drift threshold, < 0); the value and percentile rank of the current
  trailing window (2026-07-21..2026-10-16, value -0.211884).
- **Overlapping windows are not independent.** Report the effective number of
  independent windows (approximately n / 63), and a standard error for each
  failure rate, so the rates are not over-read. State the dependence
  explicitly.
- No bootstrap, no parameter fitting, no selection: one deterministic
  measurement of one frozen configuration (**trials = 1**).

## Pre-registered conditions (evaluate all three)

- **G1 (gate informativeness)**: if the executed path fails the >= 0.9
  rolling-63 gate in **>= 10%** of windows, the gate has a high
  false-negative rate and a single trailing-window NO-GO must not be read as
  evidence that the strategy's edge decayed. If the rate is < 10%, the gate
  is a low-false-negative criterion and the current NO-GO is informative.
- **G2 (is the current window extreme?)**: if the current trailing value is
  below the **1st percentile** of the distribution, the current window is an
  extreme drawdown of the statistic; otherwise it is an ordinary window
  failure.
- **G3 (does the overlay cause gate failures?)**: if the raw-signal path fails
  the >= 0.9 gate in **materially more** windows than the executed path, the
  overlay is a cause of gate failures; if the executed path fails *less*
  often, the overlay **helps** the gate and the Cycle 878 reading of the
  trailing failure as a pure overlay-timing accident must be stated with that
  counter-evidence.

Decision rule (fixed in advance): report G1/G2/G3 as PASS/FAIL with their
numbers, state the gate's false-negative rate in words and in percent, and
state what that implies for how the loop reads a trailing-window NO-GO and for
the evaluation protocol of the next candidate family.

**Not allowed in this cycle**: changing `config/promotion_gates.yaml`, changing
the incumbent's decision (**NO-GO** stands), re-fitting or re-optimizing the
incumbent, promoting or rejecting any candidate, or writing to `data/`,
`config/` or the paper-trading state.

## Acceptance criteria

1. `research/hypotheses/promotion_gate_false_negative_001.md` exists, is
   committed with the cycle, contains the mechanism, the disclosure of the
   Cycle 878 feasibility probe, the fixed method, the three conditions and the
   decision rule, and was written before the measurement script was run.
2. New read-only script `research/gate_false_negative_rate.py` exists, reuses
   the shared helpers, reads only the committed cache, writes nothing under
   `data/`, `config/` or `data/processed/`, prints every number that appears
   in the report, and exits 0 with `OVERALL: PASS`.
3. New report `research/reports/gate_false_negative_rate_001.md` contains: the
   two path distributions (executed and raw signal) with all the statistics
   above, the failure rates at 0.9 / 0.5 / 0 with their standard errors, the
   current trailing window's value and rank, the zero-dispersion window count,
   the overlap-dependence statement, and the G1/G2/G3 verdicts with the
   decision-rule output.
4. New experiment record `research/experiments/gate_false_negative_rate_001.md`
   in the repository format (hypothesis reference, data, point-in-time
   treatment, configuration, splits, results, trials = 1, reproduction
   commands, decision label).
5. New offline tests in `tests/test_gate_false_negative_rate.py` (no network,
   no data mutation) for the pure helpers (e.g. the zero-dispersion
   convention, the failure-rate computation, the effective-independent-window
   estimate).
6. `python -m pytest -q` passes (89 existing + the new tests) and
   `git status --porcelain data/ config/` is empty.
7. `python research/go_no_go_evaluation.py` still prints **NO-GO** with
   `side_effect_free: True`; the deployment decision is unchanged.

## Validation commands

- `python research/gate_false_negative_rate.py`
- `python research/long_sample_overlay_attribution.py`
- `python research/go_no_go_evaluation.py`
- `python -m pytest -q`
- `git status --porcelain data/ config/`

## Scope boundaries

- Research/backtesting only. No live trading, no credential access, no
  scheduled jobs, no new dependencies.
- Do not modify `config/`, `data/`, `src/`, the paper-trading state, the
  promotion gates, the incumbent configuration or the deployment decision.
- Do not dispatch this workflow or start additional agent sessions.

## Known pending item (deliberately not bundled with this cycle)

The 2026-10-19 US session is published by the provider but only becomes
*eligible* under the repository's own completeness rule
(`research/extend_paper_trading_state.py:session_is_complete`, `close_hour + 1`
= 17:00 ET = 21:00 UTC). Once that time has passed, the paper-trading record
can be extended from 449 to 450 sessions with the existing session-safe tool
(`python research/extend_paper_trading_state.py`, then
`python research/go_no_go_evaluation.py` and
`python research/drift_persistence_report.py`). Keep this separate from
measurement cycles so the measured sample stays fixed.
