# Experiment: Fold regime attribution for `tsmomentum_spytrend_001` (tsmomentum_fold_regime_attribution_001, Cycle 923)

## Hypothesis reference

- Candidate hypothesis: `research/hypotheses/tsmomentum_004.md` (incumbent)
- Published walk-forward record: `research/experiments/tsmomentum_regime_filter_wf_001.md` (resolved by content)
- Frozen candidate definition: `research/run_cycle6.py` (the script that produced the published record; read, never changed)

## Objective

Attribute the incumbent's published 48-fold walk-forward outcome to pre-specified observable state buckets (F1 calendar phase, F2 SPY trend state, F3 SPY trailing 12-month return sign, F4 training-window 63-day realised volatility tercile), test whether the phase-A / phase-B weakness is an observable regime state or a calendar/protocol artefact, and publish a monitoring statement. Descriptive only: the published protocol, gates, verdict and every committed artifact are unchanged.

## Data

- Source: committed raw cache `data/raw/*.parquet` (cache-only; the fetcher is never called)
- Universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- Date range: 1993-01-01 to 2026-10-09
- Point-in-time treatment: signals use only data available at formation; SPY SMA and trailing returns computed point-in-time at each fold's test-window start; F4 tercile boundaries computed from each fold's training window only.
- Cost model: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip; risk-free rate 0.02 annual

## Configuration (consumed as-is, never inferred)

- Signal: TSMOM lookback 226, skip 21, top_fraction 0.5
- Risk overlay: vol-target 0.1 (lookback 63) + drawdown control 0.15
- Regime filter: SPY 200-day SMA trend filter
- Walk-forward: train 10.0y / test 12m / step 6m, purge 21d, embargo 21d (the published design)
- Bucket families: F1_calendar_phase, F2_spy_trend_state, F3_spy_12m_return_sign, F4_train_63d_realvol_tercile (pre-specified; no fifth family)
- Permutation control: 10000 permutations, fixed seed 923

## Splits

- Published design: 48 folds; phase A = folds 1, 3, 5, ...; phase B = folds 2, 4, 6, ...

## Results

- Recomputed aggregate: 48 folds, mean OOS Sharpe 0.947307, median 1.293299, positive 0.9167, pooled OOS trades 6013

### Phase decomposition

- Phase A: 24 folds, mean OOS Sharpe 1.385035; phase B: 24 folds, mean OOS Sharpe 0.509580; gap (A - B): +0.875454

### Dispersion share and permutation p-value by family

| Family | Dispersion share (eta^2) | Permutation p-value |
|---|---|---|
| F1 calendar phase | 0.016160 | 0.634937 |
| F2 SPY trend state at test-window start | 0.064618 | 0.127087 |
| F3 SPY trailing 12-month return sign at test-window start | 0.066018 | 0.141386 |
| F4 training-window 63-day realised volatility tercile | 0.023240 | 0.877812 |

### State-vs-calendar conclusion

Mixed evidence: the phase gap shrinks inside some state buckets but persists inside others, so the weakness is only partially explained by the observable states tested here; treat the monitorable signal as tentative.

## Monitoring statement

No observable state among F2/F3/F4 is wired into any gate or decision. If monitored on the live stance, the candidate input would be: watch the SPY trend state (F2), the trailing 12-month return sign (F3) and the training-window realised volatility tercile (F4). The phase-A / phase-B gap collapses to about zero in risk-on and up-trend buckets (both phases ~1.4, no calendar weakness), while it persists in risk-off and down-trend buckets (phase B far weaker than phase A) -- so the phase-B weakness concentrates in observable risk-off/down states, albeit with small fold counts (11 risk-off, 10 down) and no dispersion share reaching conventional significance. Treat the monitorable signal as tentative. This attribution does not select, re-rank or re-fit anything and does not change the incumbent's published verdict.

## Trial count

- 1 attribution on the published 48 folds; 4 pre-specified bucket families; 10000 permutations per family; fixed parameters, no per-fold re-optimisation, no candidate selection.

## Reproduction

```bash
python research/tsmomentum_fold_regime_attribution.py
python -m pytest -q tests/test_tsmomentum_fold_regime_attribution.py
python -m pytest -q
git status --porcelain data/ config/
```
