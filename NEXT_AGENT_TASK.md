# NEXT AGENT TASK — Cycle 878

## Context

Cycle 877 confirmed NO-GO stability on an unchanged record: rolling 63d Sharpe
-0.21188351222842883, PSR 0.684041 (grey zone), max DD -4.99%, 107 trades, 449
sessions through 2026-10-16; `low_rolling_sharpe` drift flag persists (5
consecutive trading days below 0.5). Evidence:
`research/reports/monitoring_cycle_877.md`.

Cycle 862 (`research/reports/trailing_window_attribution_001.md`) localised the
trailing-window failure to the **volatility-targeting overlay** (-1.497444% over
the trailing 63 sessions against a +1.078731% raw signal) and explicitly left the
question open: *"it localises the loss; it does not establish that the signal has
decayed, and it recommends no re-fit."* That question has never been answered
with long-sample evidence: the committed long-sample artifact
(`research/reports/promotion_feasibility_backtest_001.md`, 8,487 sessions
2004-11-18..2026-10-16, canonical Sharpe 0.5646255767978904, max DD -0.6224126346564325)
is produced by `src/backtest/engine.py:run_backtest`, which has **no risk
overlays**, while the paper record is produced by
`src/simulation/engine.py:run_simulation`, which **has** the SPY-trend filter,
the 10%/63d volatility target, the 15% drawdown cut and the gross-exposure cap.
The overlays' long-run net contribution has therefore never been measured.

## Objective

Measurement-only, pre-registered diagnostic (no strategy, universe, cost model,
gate, threshold, config, state or candidate change): decompose the incumbent's
**long-sample** record into its mechanisms and decide, from pre-registered
falsification conditions, whether the volatility overlay is a structural drag and
whether the trailing 63-session failure is overlay mechanics or signal decay.

Pre-registration file (write it BEFORE running anything):
`research/hypotheses/overlay_mechanism_long_sample_001.md`.

## Method (fixed by this task; do not re-choose)

- Sample: 2004-11-18 .. 2026-10-16 (the published long-sample window, 8,487
  sessions), universe = the 7 paper-trading assets, configuration = the frozen
  `config/simulation_candidate_001.yaml` (226/21 momentum, top 50%, 10% vol
  target on 63d, dd cut to 0.5 below -15%, SPY-200d trend filter, 3 bp round
  trip, close execution, 1-day signal lag).
- Engine: `src/simulation/engine.py:run_simulation` (the pipeline that produced
  the paper record). Reuse `research/trailing_window_attribution.py:build_layers`
  and `decompose_window` by import — do not re-implement the layer chain.
- Counterfactual layers: L0 base signal -> L1 x SPY-trend filter -> L2 x
  vol_scale -> L3 x dd_scale -> L4 gross-exposure cap -> L5 net of the executed
  costs. For every layer, also compute that layer's **own** turnover cost
  (3 bp x |dW|_1) so each layer has a fair net-of-cost path (Cycle 862's
  counterfactuals were gross, which overstates the cost of the uncosted layers).
- Rolling 63-session distribution of each mechanism's contribution (mean, median,
  p05, p95, min, max, and the percentile rank of the trailing-63 window
  2026-07-21..2026-10-16), plus the trailing-63 canonical Sharpe of L0-net and
  L5-net (signal-only vs fully overlaid) to separate decay from overlay effect.
- Reconciliation: reproduce the committed long-sample artifact exactly
  (`python research/promotion_feasibility_backtest.py` -> canonical Sharpe
  0.5646255767978904, max DD -0.6224126346564325, decision NO-GO), and quantify
  the difference between the backtest engine's net path and the simulation
  engine's L0-net-of-base-costs path (warm-up window and cost base differ by
  construction; the deviation must be measured, not assumed).

## Falsification conditions (pre-registered; evaluate all three)

- F1 (overlay is a structural drag): the full-sample net-of-cost canonical
  Sharpe of L2-net is **not** greater than L0-net, or the full-sample vol-overlay
  contribution is negative. => The overlay must be dropped in any future
  candidate; do not re-tune the incumbent.
- F2 (trailing window is an overlay anomaly): the trailing-63 vol-overlay
  contribution ranks **below the 50th percentile** of all rolling-63 vol-overlay
  contributions. => Overlay timing explains a material part of the trailing
  failure; a different risk treatment is warranted and its expected benefit is
  pre-quantified by this measurement.
- F3 (signal decayed): the trailing-63 canonical Sharpe of **L0-net** (raw
  signal, no overlays) is negative. => The failure is in the signal, not in the
  overlay; the incumbent's edge is not robust and the next candidate must be a
  structurally different family (not a variant of this one).

Decision rule (fixed in advance): report F1/F2/F3 as PASS/FAIL each with its
numbers and state which of the three conclusions the evidence supports. A
candidate is **not** proposed, tuned or promoted in this cycle.

## Acceptance criteria

1. `research/hypotheses/overlay_mechanism_long_sample_001.md` exists and contains
   the mechanism, expected direction, falsification conditions (F1-F3), the
   decision rule and the fixed method **before** the script is run (it is
   committed in the same cycle).
2. New read-only script `research/long_sample_overlay_attribution.py` exists,
   imports the shared layer helpers, reads only the committed cache, writes
   nothing under `data/`, `config/` or `data/processed/`, prints every number
   that appears in the report, and exits 0 with `OVERALL: PASS`.
3. The script reconciles to the committed long-sample artifact: canonical Sharpe
   0.5646255767978904 and max DD -0.6224126346564325 reproduced (or the deviation
   measured and explained), and the 449-session paper window still reproduces the
   committed record (max |net_return - committed| = 0 over 449 sessions).
4. New report `research/reports/long_sample_overlay_attribution_001.md` contains:
   the full-sample decomposition with a telescoping residual <= 1e-12, the
   canonical Sharpe of every layer (gross and net of its own costs), the
   rolling-63 distribution of every mechanism's contribution, the trailing-63
   L0-net vs L5-net Sharpe, the reconciliation table, and the F1/F2/F3 verdicts.
5. New experiment record `research/experiments/long_sample_overlay_attribution_001.md`
   follows the repository format (hypothesis reference, data, point-in-time
   treatment, configuration, splits, results, number of trials = 1, reproduction
   commands, decision label).
6. New offline tests in `tests/test_long_sample_overlay_attribution.py` (no
   network, no data mutation) for the pure helpers (e.g. telescoping residual is
   zero, percentile rank, own-turnover cost of a layer).
7. `python -m pytest -q` passes (82 existing + the new tests) and
   `git status --porcelain data/ config/` is empty.
8. The deployment decision is unchanged: **NO-GO**, live deployment unsupported;
   `research/go_no_go_evaluation.py` still prints NO-GO with
   `side_effect_free: True`.

## Validation commands

- `python research/long_sample_overlay_attribution.py`
- `python research/promotion_feasibility_backtest.py`
- `python research/go_no_go_evaluation.py`
- `python -m pytest -q`
- `git status --porcelain data/ config/`

## Scope boundaries

- Research/backtesting only. No live trading, no credential access, no
  scheduled jobs, no new dependencies.
- Do not modify `config/`, `data/`, `src/`, the paper-trading state, the
  promotion gates, the incumbent configuration or the deployment decision.
- Do not re-fit, re-optimize or promote the incumbent; this cycle measures.
- Do not dispatch this workflow or start additional agent sessions.
