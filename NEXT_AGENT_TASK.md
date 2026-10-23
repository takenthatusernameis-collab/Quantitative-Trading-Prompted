# Cycle 955 — Bounded incumbent improvement: SPY SMA 175 phase-stable variant

## Context
- Cycle 954 closed the C4 sector-rotation line; remaining shortlist candidates are
  data-blocked or already rejected.
- Credible incumbent `tsmomentum_spytrend_001` (226d lookback, 21d skip, top-50%,
  vol-target 10%, DD control 15%, SPY 200d SMA filter) is phase-unstable: Phase A
  mean 1.385, Phase B mean 0.510 (gate-1 FAIL).
- `tsmomentum_phase_stability_fix_audit` found a single bounded tweak — SPY SMA
  window 200 -> 175 — that restores phase stability (Phase A 1.539, Phase B 1.541,
  both gate-1 PASS) as a read-only sensitivity. No promotion or re-fit has occurred.

## Objective
Promote the phase-stable SPY SMA 175 variant from sensitivity finding to a
documented, reproducible experiment artifact under the existing hypothesis line,
without changing parameters, gates, cost model, or protocol beyond the single
window change. No new backtest execution; reuse the committed cached data and
read-only audit machinery.

## Acceptance criteria
1. `research/experiments/tsmomentum_spy_sma175_phase_stable_001.md` records the
   determination, referencing `tsmomentum_phase_stability_fix_001.md` and the
   tweak evidence (windows 200 vs 175, phase means, gate outcomes).
2. `python -m pytest -q tests/test_tsmomentum_phase_stability_fix_audit.py`
   passes.
3. `python research/tsmomentum_phase_stability_fix_audit.py` runs and reports the
   phase-stable PASS for the SMA 175 tweak.
4. `python -c "import yaml; print('ok')"` and `python research/commoditytrend_001_evaluation.py`
   (OVERALL: PASS) still pass.
5. No new backtest executed; no data fetched.

## Scope boundaries
- Single-parameter change only (SPY SMA window 200 -> 175); no re-tuning, no
  additional tweaks, no gate or cost-model changes.
- Reuse cached data and existing audit machinery only.
- Do not promote the variant to production/paper-trading state in this cycle.

## Verification
- `python -m pytest -q tests/test_tsmomentum_phase_stability_fix_audit.py`
- `python research/tsmomentum_phase_stability_fix_audit.py`
- `python -c "import yaml; print('ok')"`
- `python research/commoditytrend_001_evaluation.py`