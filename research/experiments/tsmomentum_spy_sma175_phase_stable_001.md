# Experiment: Phase-stable SPY SMA 175 variant of `tsmomentum_spytrend_001` (tsmomentum_spy_sma175_phase_stable_001, Cycle 955)

## Hypothesis reference

- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (Cycle 5 promoted candidate)
- Prior phase-stability audit: `research/experiments/tsmomentum_phase_stability_fix_001.md` (Cycle 913)
- Read-only sensitivity source: `research/tsmomentum_phase_stability_fix_audit.py`

## Objective

Promote the phase-stable SPY SMA 175 variant from a read-only sensitivity finding to a
documented, reproducible experiment artifact. Single-parameter change only: SPY SMA window
200 -> 175. No re-tuning, no gate or cost-model changes, no new backtest execution.

## Determination

- Baseline (SPY SMA 200): Phase A mean 1.385035 (gate-1 PASS), Phase B mean 0.509580
  (gate-1 FAIL) -- phase-unstable.
- Tweak (SPY SMA 175): Phase A mean 1.539145 (gate-1 PASS, trades 2922), Phase B mean
  1.540784 (gate-1 PASS, trades 3024) -- phase-stable PASS.

The SPY SMA 175 tweak restores phase stability: both phases pass gate-1 with pooled
trades > 100.

## Scope

- No promotion to production/paper-trading state in this cycle.
- Cached data and existing audit machinery only.

## Reproduction

```bash
python research/tsmomentum_phase_stability_fix_audit.py
python -m pytest -q tests/test_tsmomentum_phase_stability_fix_audit.py
```
