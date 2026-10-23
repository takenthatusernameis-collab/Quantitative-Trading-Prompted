# Experiment: Rolling 63d Sharpe weakness diagnosis for `tsmomentum_spytrend_001` (tsmomentum_rolling63_weakness_diagnosis_001, Cycle 925)

## Hypothesis reference

- Incumbent hypothesis: `research/hypotheses/tsmomentum_004.md`
- Prior cycles reused: Cycle 866 (rolling-gate base rate), Cycle 899 (window attribution), Cycle 923/924 (fold regime buckets and bootstrap CIs)

## Objective

Diagnose the `rolling_63d_sharpe` promotion-gate failure on the committed paper-trading record: reproduce it, characterise its distribution and its worst windows, test whether the weakness concentrates in the published observable-state buckets, and test in isolation whether any minimal overlay change clears the gate. Descriptive only: no selection, re-ranking, re-fit, gate change or verdict change.

## Data

- Committed paper-trading record: 450 sessions, 2025-01-02 .. 2026-10-19
- Price panel: committed parquet cache `data/raw/*.parquet` (cache-only; the fetcher is never called)
- Universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- Cost model: 1.0 bps commission + 2.0 bps slippage = 3.0 bps round-trip
- Point-in-time treatment: momentum weights shifted one session; SPY SMA and trailing returns computed on the cached panel; fold buckets reused from the Cycle-923 publication

## Configuration

- Signal: TSMOM lookback 226, skip 21, top_fraction 0.5
- Overlay: vol-target 0.1 (lookback 63) + drawdown control 0.15 + SPY 200-day SMA filter
- Window: 63 sessions; gate threshold 0.9 (read from `config/promotion_gates.yaml`)
- Controls: 10000 permutations (seed 925); 2000 moving-block bootstrap resamples (seed 925): blocks of 21 windows over the rolling-window series (base rate, percentile rank, bucket gaps) and blocks of 63 sessions over the joint (return, market-state) rows (correlations)

## Results

- Trailing 63d Sharpe: **-0.448918** (gate 0.9, FAIL); production decision NO-GO (unchanged)
- Rolling windows: 388; base rate 73.9691% (bootstrap 95% CI [59.5361%, 92.7835%]); current value at percentile 6.44%
- Distribution: min -1.809887, p10 -0.089883, p25 0.746583, median 1.946854, p75 3.715701, max 6.144063
- Current failing run: 6 window(s); last passing window ended 2026-10-09
- F1 calendar phase (published fold parity): eta^2 0.353830, permutation p 0.000100, bucket gap -2.919032 (bootstrap 95% CI [-4.506950, +1.061537])
- F2 SPY trend state at the fold's test-window start: eta^2 0.000000, permutation p 1.000000, bucket gap not estimable (one bucket absent in the record period)
- F3 SPY trailing 12-month return sign at the fold's test-window start: eta^2 0.000000, permutation p 1.000000, bucket gap not estimable (one bucket absent in the record period)
- F4 training-window 63-day realised-volatility tercile: eta^2 0.353830, permutation p 0.000100, bucket gap +2.919032 (bootstrap 95% CI [-1.061537, +4.506950])
- Spearman(rolling Sharpe, spy_ret_12m) = -0.0694
- Spearman(rolling Sharpe, spy_rv_63) = -0.4523
- Spearman(rolling Sharpe, spy_sma_gap) = 0.4313
- Spearman(rolling Sharpe, strategy_window_realised_vol) = -0.1574
- V0_baseline: trailing 63d -0.448918, record 1.771084, full path 1.486763, WF mean OOS 0.947307
- V1_no_vol_target: trailing 63d -0.034252, record 1.359084, full path 1.342495, WF mean OOS 0.930602
- V2_vol_estimate_lagged_1d: trailing 63d -0.515807, record 1.635705, full path 1.413566, WF mean OOS 1.318605
- V3_no_drawdown_control: trailing 63d -0.448918, record 1.771084, full path 1.486763, WF mean OOS 0.947307
- V4_no_overlay: trailing 63d -0.034252, record 1.359084, full path 1.338256, WF mean OOS 0.930602

## Trial count

- 1 diagnosis on the committed record; 4 pre-specified bucket families; 10000 permutations per family; 5 isolated overlay variants; no per-fold re-optimisation and no candidate selection.

## Verdict

**1. The failing gate value is a tail state of the record's own rolling-window distribution, not a new level.** The trailing 63-session Sharpe -0.448918 sits at the 6.44% percentile of the 388 rolling windows the record has produced; the gate passes in 73.97% of them (bootstrap 95% CI [59.54%, 92.78%]). The current failing run covers 2026-10-12 .. 2026-10-19 (6 window(s)), and the record has produced longer failing runs before (the longest: 36 windows).

**2. The weakness does not cluster in any published observable-state bucket.** The families F2_spy_trend_state, F3_spy_12m_return_sign are one-sided inside the record period (the risk-off / down-trend / high-volatility states that Cycle 923 flagged never occur in the committed record), so their bucket gaps are **not estimable** from this record and are reported as absent rather than imputed; the two-sided F1_calendar_phase, F4_train_63d_realvol_tercile partition the record identically (the published folds that cover it are contiguous in time), i.e. they are a time split of the record rather than an independent state, and their bucket gap CI includes zero. The apparent concentration is therefore consistent with sampling noise at this record's effective sample size -- the same conclusion Cycle 924 reached for the fold-level buckets.

**3. No permitted change clears the gate.** The strongest isolated overlay variant (`V1_no_vol_target`, volatility target disabled (vol_scale == 1)) lifts the trailing window from -0.448918 to -0.034252, still far below the 0.9 gate, and every other variant is below that. The weakness is an overlay-timing outcome -- the volatility target de-risks into the high-volatility sessions that dominate the window -- not evidence that the momentum edge has decayed, and not something a threshold, universe, cost-model or parameter change may fix.

**4. The gate is a symptom, not the binding constraint.** Per Cycle 866, clearing `rolling_63d_sharpe` alone cannot yield GO on this record: the PSR gate is decisive and the decision stays NO-GO (failed gates: rolling_63d_sharpe, psr).

**5. Separate measurement defect found and quantified (not a fix).** The volatility estimate sets session t's exposure from a trailing window that includes session t itself (same-session feedback, in `research/run_cycle6.py`, `src/simulation/engine.py` and `src/evaluation/risk.py`). Lagging the estimate one session changes the committed record's Sharpe from 1.771084 to 1.635705, the full-path Sharpe from 1.486763 to 1.413566 and the failing window from -0.448918 to -0.515807: it makes the failing window slightly worse, so it is **not** the cause of the gate failure, but it does flatter the published Sharpe statistics of this candidate (the headline walk-forward mean moves the other way only because of the one numerical-artifact fold documented in section 5). It is handed off as a separate, explicitly scoped re-derivation task -- **no production code is changed by this cycle**.

## Reproduction

```bash
python research/tsmomentum_rolling63_weakness_diagnosis.py
python -m pytest -q tests/test_tsmomentum_rolling63_weakness_diagnosis.py
```
