# Next Agent Task: Cycle 19 — Execute C5 (Macro Regime Overlay Extension, 24/35)

## Context

Cycle 18 completed execution of the pre-registered C6 (calendar_effects_001)
evaluation: TOM window exposure on SPY/QQQ/IWM, 33-fold walk-forward,
18-config grid. Results: WF mean OOS Sharpe -0.0254 < 0.9, positive-fold
rate 42.4% < 50%, plateau 1/3 — **Rejected/Failed**. Artifacts and record:
- `research/experiments/calendar_effects_baseline_wf_001.md`
- `data/processed/*_calendar_effects_001.parquet`
- `research/run_cycle18.py` (new, implements C6 per pre-registration)
- `research/reports/cross_momentum_consolidation.md` updated with C6 note
- `README.md` Current Status updated

C6 is a distinct mechanism (calendar-based) from the momentum family (C3/C4)
which was archived in Cycle 17. The cross-momentum family remains rejected
on two valid tests.

Per the pre-registered decision tree in the original Cycle 18/C6 spec and
the Cycle 11 shortlist: if C6 is rejected, the next untested candidate is
**C5 — Macro Regime Overlay Extension (24/35)**, noting its overlay-only
constraint.

## Objective

Execute the pre-registered C5 evaluation (if it exists as a frozen hypothesis
and config) following the repository’s evaluation discipline. If C5 is not
yet frozen/pre-registered in the expected files, inspect the codebase to
locate the correct C5 hypothesis/config and execute it as specified. Treat
C5 as a bounded task with honest reporting regardless of outcome.

## Evidence References

- `research/experiments/calendar_effects_baseline_wf_001.md` (Cycle 18 C6 outcome)
- `research/reports/opportunity_shortlist.md` (C5 = 24/35, C6 = 26/35)
- `AGENTS.md` (research loop, promotion gates, baseline-before-complexity)
- Existing run scripts as structural templates (`research/run_cycle15_c4_corrected.py`,
  `research/run_cycle18.py`) for discipline (splits, grid/multiple-testing
  as applicable, benchmarks, provenance)

## Acceptance Criteria

- Locate and respect any frozen pre-registration for C5 (hypothesis + config).
  Do not modify frozen files.
- Create/run an evaluation script mirroring existing discipline (deterministic,
  cache-only data, pre-execution assertions, full provenance in experiment record).
- Produce required artifacts (simulation/trades/weights) and experiment record
  with 33-fold dates matching the repo’s walk-forward convention for that
  candidate (or the pre-registered split spec). If no pre-registered split
  spec exists, follow the standard 10y/1y/6m with purge/embargo used
  elsewhere and document the choice.
- Compute promotion gates honestly from results; label as Rejected/Failed,
  Exploratory signal, or Credible candidate per pre-committed decision discipline.
- Update `README.md` Current Status with C5 outcome.
- Prepare `NEXT_AGENT_TASK.md` for Cycle 20 based on C5 outcome (if C5
  rejected, move to next untested shortlist candidate; if passes, follow
  post-gate guidance in its pre-registration).

## Scope Boundaries

- Research/backtesting only. No live trading, no credentials, no scheduled jobs.
- Cache-only data access; no new dependencies unless necessary and justified.
- Do not modify C3/C4/C6 artifacts, hypotheses, configs, or scripts.
- Baseline-before-complexity; do not weaken gates.
