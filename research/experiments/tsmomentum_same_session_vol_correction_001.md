# Experiment: Same-session volatility estimate -- opt-in correction and side-by-side re-derivation for `tsmomentum_spytrend_001` (tsmomentum_same_session_vol_correction_001, Cycle 926)

## Hypothesis reference

- Incumbent hypothesis: `research/hypotheses/tsmomentum_004.md`
- Prior cycles reused: Cycle 866 (rolling-gate base rate), Cycle 910 (fold design), Cycle 921 (PSR target), Cycle 925 (the rolling-63d diagnosis and the discovery of the same-session measurement defect)

## Objective

Make the same-session volatility estimate correctable behind a default-off, opt-in switch, and re-derive the incumbent's published record on the corrected path in a new artifact. Measurement and remediation planning only: no gate, threshold, universe, cost model, Sharpe convention, parameter, hypothesis or drift flag is changed, and no candidate is promoted, re-fit or re-ranked.

## Data

- Committed paper-trading record: 450 sessions (2025-01-02 .. 2026-10-19)
- Price panel: committed parquet cache `data/raw/*.parquet` (cache-only; the fetcher is never called)
- Universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- Cost model: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip
- Point-in-time treatment: momentum weights shifted one session; the SPY SMA filter and the trailing volatility window are computed on the cached panel; the published walk-forward design (10y train / 12m test / 6m step, 21d purge, 21d embargo) is reused unchanged

## Configuration

- Signal: TSMOM lookback 226, skip 21, top_fraction 0.5
- Overlay: vol-target 0.1 (lookback 63) + drawdown control 0.15 + SPY 200-day SMA filter
- Switch: `lag_vol_estimate`, default **off**; the corrected path sets it to True in the research path (`research/run_cycle6.py::_apply_overlay`) and in the shared engine (`src/simulation/engine.py::SimulationConfig.lag_vol_estimate`)
- PSR: target 1.4178, `n_bootstrap=1000`, `block_size=22`, `seed=20240101` (the repository's own settings)
- Gates read from `config/promotion_gates.yaml`: `rolling_63d_sharpe` >= 0.9, `psr` >= 0.95

## Results

### Anchor (fail closed)

- Published 48-fold walk-forward mean OOS Sharpe reproduced: **0.947307** (published 0.947307); the published machinery reproduces **0.947307**
- Committed record's 450 sessions reproduced with max |diff| = 5.421e-20
- Default path bit-identical to the pre-change implementation: research path 0.0e+00, simulation path 0.0e+00, risk overlays 0.0e+00

### Side by side

- Walk-forward mean OOS Sharpe: 0.947307 -> 1.318605 (all folds); excluding each path's own worst fold: 1.431928 -> 1.357135
- Record canonical Sharpe: 1.771084 -> 1.635705
- Trailing 63-session Sharpe (`rolling_63d_sharpe`): -0.448918 -> -0.515807
- PSR vs 1.4178: 0.695606 -> 0.623929
- Promotion decision: NO-GO -> NO-GO (failed gates: rolling_63d_sharpe, psr)

## Trial count

- 1 anchor reproduction (published machinery, 48 folds) + 2 paths (default, corrected) + 1 frozen-implementation bit-identity comparison per code path; no per-fold re-optimisation, no candidate selection, no configuration search.

## Verdict

**1. The defect is real, quantified and now correctable, but it is not a cause of the gate failure and it does not rescue anything.** The same-session volatility estimate (session *t*'s own return moves session *t*'s exposure) is present in the published research path, in the shared simulation / live paper-trading path and in both overlay helpers of `src/evaluation/risk.py`. With the estimate lagged one session the committed record's canonical Sharpe moves from 1.771084 to 1.635705, its trailing 63-session Sharpe from -0.448918 to -0.515807 and its PSR against the fixed backtest baseline 1.4178 from 0.695606 to 0.623929. The corrected path is **worse on every record-level statistic** and the promotion decision stays **NO-GO** (failed gates: rolling_63d_sharpe, psr).

**2. The corrected 48-fold walk-forward mean looks better only because a numerical artefact disappears.** On the default path the published mean OOS Sharpe is 0.947307 and it contains one pathological fold (fold 12, -21.829879: 242 of 244 flat sessions, so the backtest-scale estimator divides a near-zero numerator by a near-zero dispersion, Cycle 925 section 5). Excluding that fold the default path's mean is 1.431928. On the corrected path the same segment is entirely flat, so the estimator returns 0.000000 instead of a pathology, the mean over all 48 folds is 1.318605, and the strictest comparable statistic - both paths with fold 12 excluded - is **lower** on the corrected path (1.346660 vs 1.431928); excluding each path's own worst fold it is also lower (1.357135 vs 1.431928). The corrected path is not a recovery, and the higher headline mean must never be quoted without the fold-level table.

**3. The default path is unchanged, bit-for-bit.** The opt-in switch (`lag_vol_estimate`, default off) is available in all three code paths; every default-path comparison in this report is a max |diff| of exactly 0.0 against a frozen copy of the pre-change implementation (research path, simulation path and both risk-overlay helpers). No gate, threshold, universe, cost model, Sharpe convention, parameter, hypothesis or drift flag was changed, the published walk-forward record and the committed paper-trading state were **not** overwritten, and `data/` and `config/` are byte-identical before and after the run.

**4. Decision recommendation: adopt only for new live paper-trading records.** The defect is a genuine point-in-time error in the **live** path (the exposure for session *t* is set with information that is only fully observable after session *t*'s close, at the price the trade is executed at), so a **new** live record must not be produced with it. But the published backtest artefacts are frozen, are quoted by 69 committed files, and the correction **lowers** every record-level statistic of the only credible candidate in the repository while leaving the decision NO-GO: adopting it everywhere would invalidate a large body of published evidence in exchange for no decision-relevant gain. The published record therefore stays as it is, and a clearly labelled successor record is the right vehicle for the corrected backtest (plan in section 7, not executed here). Two consequences must be stated. (i) A corrected live record is measured on a different path from the published backtest baseline 1.4178, so its PSR comparison against that unchanged reference is **conservative**: the corrected path's own 2018-2026 test-period Sharpe is 1.335983 against the published 1.417752. (ii) A corrected live record must be **started fresh** rather than appended to the committed one, because a record that mixes the two paths measures neither; the `track_record_length` gate needs 126 sessions, so the promotion evidence would restart from zero while the committed record stays published and NO-GO.

**5. The incumbent's published verdict is unchanged.** It remains a **Credible Candidate** by its published verdict and **NO-GO** for promotion, live deployment remains unsupported, and this cycle publishes a measurement and a plan - not an edge, not a recovery and not a promotion.

## Reproduction

```bash
python research/tsmomentum_same_session_vol_correction.py
python -m pytest -q tests/test_tsmomentum_same_session_vol_correction.py
```
