# Long-Sample Mechanism Decomposition of the Incumbent's Risk Overlays

Cycle 878 — measurement-only, pre-registered in
`research/hypotheses/overlay_mechanism_long_sample_001.md` before execution.
No strategy, universe, cost model, gate, threshold, configuration, state or
candidate was changed; the incumbent's promotion decision (**NO-GO**) is unchanged.

## 0. Sample and integrity

| Item | Value |
|---|---|
| Sample (simulation engine) | 1993-01-29 .. 2026-10-19 (8488 sessions) |
| Universe | SPY, QQQ, IWM, TLT, GLD, EFA, EEM |
| Cost model | 3.0 bp per unit of weight change |
| Configuration | `config/simulation_candidate_001.yaml` (frozen, unmodified) |
| Engine | `src/simulation/engine.py:run_simulation` |
| Layer construction | `research/trailing_window_attribution.py:build_layers` (imported) |
| Paper record reproduced | True (max diff 0.000e+00) |
| Cycle 862 trailing window reproduced | True (max diff 4.587e-07 pp) |
| Committed backtest artifact reproduced | True |
| Read-only (data/, config/, state) | True |

## 1. Reconciliation with the committed long-sample artifact

| Quantity | Committed artifact | This run | Difference |
|---|---|---|---|
| Canonical Sharpe | 0.5646255767978904 | 0.5657179297830458 | 1.092e-03 |
| Max drawdown | -0.6224126346564325 | -0.6224126346564325 | 0.000e+00 |
| Sessions | 8487 | 8488 | 1 |
| Realized first session | labelled 2004-11-18 | 1993-01-29 | — |

The committed artifact publishes two windows side by side: `label_start_date` is
the **common** (max of per-symbol) inception, and `realized_start_date` (published
as `start_date`) is the sample the backtest actually computed.
`src/backtest/engine.py:run_backtest` does not slice the price frame to the common
inception, so the realized sample is the union calendar from SPY's inception
(1993-01-29), i.e. 8488 sessions, and the
published metrics reproduce bit-exactly. This measurement uses the same realized sample.

Engine agreement on the raw signal: max |backtest net − L0 net| = 5.421e-20 over 8488 common sessions
(compounded +1563.921225% vs +1563.921225%).

## 2. Full-sample decomposition (each layer net of its own cost)

| Layer | Compounded | Canonical Sharpe | Max drawdown | Annualised turnover |
|---|---|---|---|---|
| L0 raw signal | +1563.921225% | +0.565718 | -62.2413% | 9.213x |
| L1 + SPY-trend filter | +20810.559505% | +1.338415 | -16.0189% | 13.508x |
| L2 + volatility overlay | +6774.281690% | +1.486941 | -9.9349% | 12.157x |
| L3 + drawdown overlay | +6774.281690% | +1.486941 | -9.9349% | 12.157x |
| L4 + gross-exposure cap (executed) | +6774.281690% | +1.486941 | -9.9349% | 12.157x |

| Mechanism contribution (telescoping, compounded) | Value |
|---|---|
| filter_effect | +19246.638280% |
| vol_overlay_effect | -14036.277815% |
| drawdown_overlay_effect | +0.000000% |
| gross_exposure_cap_effect | +0.000000% |
| telescoping residual | 0.000e+00 (tol 1e-12) |

**Scale caveat (important).** A telescoping *difference of compounded*
returns is not scale-free: on this sample the trend filter's own compounded
effect is of the order of 10^4 percentage points, so every later difference
is dominated by that number and cannot be read as an economic contribution.
The interpretable readings of the same measurement are the risk-adjusted
columns (canonical Sharpe, max drawdown) and the rolling-window distribution
in section 3, where the window returns are of order 1%.

| Isolated comparison (same sample, same costs) | Sharpe | Max drawdown |
|---|---|---|
| L1 (filter only) -> L2 (+ volatility overlay) | +1.338415 -> +1.486941 | -16.0189% -> -9.9349% |
| L0 (raw signal) -> L4 (executed) | +0.565718 -> +1.486941 | -62.2413% -> -9.9349% |

The drawdown overlay and the gross-exposure cap are **inert** on this sample
(`dd_scale < 1` on 0 of 8488 sessions, maximum gross exposure exactly
1.000000), so the incumbent's entire overlay stack is the SPY-trend filter plus the
volatility scaler.

## 3. Rolling 63-session distribution of each mechanism's contribution

8426 overlapping rolling-63 windows over the
full sample. `trailing` is the 2026-07-21..2026-10-16 window (the gate window).

| Mechanism | trailing | rank | mean | median | p05 | p95 | min | max | windows < 0 |
|---|---|---|---|---|---|---|---|---|---|
| filter_effect | +0.000000% | 55.35% | +1.800243% | +0.000000% | -2.752103% | +12.957195% | -26.682491% | +32.709840% | 30.23% |
| vol_overlay_effect | -0.559135% | 34.73% | -0.914204% | -0.019173% | -4.742999% | +0.492748% | -25.358671% | +4.749315% | 56.98% |
| drawdown_overlay_effect | +0.000000% | 100.00% | +0.000000% | +0.000000% | +0.000000% | +0.000000% | +0.000000% | +0.000000% | 0.00% |
| gross_exposure_cap_effect | +0.000000% | 100.00% | +0.000000% | +0.000000% | +0.000000% | +0.000000% | +0.000000% | +0.000000% | 0.00% |

## 4. Trailing 63 sessions: signal-only vs fully overlaid

| Layer | Compounded | Canonical Sharpe |
|---|---|---|
| L0 raw signal | -0.421198% | -0.034252 |
| L1 + SPY-trend filter | -0.421198% | -0.034252 |
| L2 + volatility overlay | -0.980333% | -0.448918 |
| L3 + drawdown overlay | -0.980333% | -0.448918 |
| L4 + gross-exposure cap (executed) | -0.980333% | -0.448918 |
| executed (paper record path) | -0.980333% | -0.448918 |

## 5. Pre-registered falsification conditions

| Condition | Statement | Verdict |
|---|---|---|
| F1 | L2-net Sharpe <= L0-net Sharpe **or** full-sample vol-overlay contribution < 0 | **PASS** |
| F2 | trailing-63 vol-overlay contribution ranks below the 50th percentile | **PASS** |
| F3 | trailing-63 L0-net (raw signal) Sharpe < 0 | **PASS** |

- F1 detail: L2-net Sharpe +1.486941 vs L0-net +0.565718; vol-overlay effect -14036.277815%.
- F2 detail: trailing-63 vol-overlay contribution -0.559135%, rank 34.73% of 8426 windows (median -0.019173%, p05 -4.742999%).
- F3 detail: trailing-63 L0-net Sharpe -0.034252; executed-net Sharpe -0.448918.

### 5.1 Qualification of the literal verdicts (mandatory)

**F1 is triggered by its second clause only** (the full-sample *compounded*
vol-overlay contribution is negative, -14036.28%),
not by its first clause: the canonical Sharpe of L2-net (+1.486941) is **higher** than L0-net (+0.565718).
The same measurement shows the isolated overlay comparison (L1 -> L2) as
Sharpe +1.338415 -> +1.486941 and max
drawdown -16.0189% ->
-9.9349%, i.e. the volatility overlay
**improves** both risk-adjusted readings on the long sample and costs compounded
return instead. The literal F1 verdict is reported as pre-registered, but its
mechanism-level wording ("the overlay is a structural drag") is **not** supported by
the risk-adjusted readings of the same run; the compounded-difference clause
is dominated by the trend filter's very large compounded effect (scale caveat
in section 2).

**F2 is true but modest**: the trailing window's overlay damage sits at the
34.7th percentile of
8426 windows, i.e. worse than typical but
far from the p05 of -4.7430%; the
median window is approximately flat (-0.0192%).

**F3 is false and is the most decision-relevant reading of this cycle**: over the
trailing 63 sessions the *raw signal* was profitable (L0-net Sharpe
-0.034252, compounded
-0.421198%) while the executed path lost money
(-0.448918). The trailing-window NO-GO is therefore an
**overlay-timing** outcome, not evidence that the momentum signal decayed.

**Decision (pre-registered rule):** The overlay is a drag and the raw signal also failed in the trailing window: retire the incumbent; the next candidate must be a structurally different family.

### 5.2 What this measurement does and does not establish

It establishes:

1. The committed long-sample artifact (canonical Sharpe 0.5646255767978904, max drawdown -0.6224126346564325) is the **raw signal net of costs, without any overlay**, over the union calendar from 1993-01-29; the two engines agree on that path to 5.4e-20 per session.
2. On the same sample the full overlay stack lifts the canonical Sharpe from +0.565718 to +1.486941 and the max drawdown from -62.24% to -9.93%; the drawdown cut and the gross-exposure cap never bind.
3. The trailing 63-session failure of the promotion gate is an overlay-timing outcome: the same window's raw signal was profitable.

It does **not** establish:

1. Any new candidate, parameter, universe or deployment decision (the incumbent stays **NO-GO**; no re-fit is proposed).
2. That the overlay is or is not a drag in the risk-adjusted sense — the pre-registered F1 statistic is not scale-free, and the scale-free readings (Sharpe, max drawdown) point the other way.
3. Whether the rolling-63-day gate itself is a statistically informative promotion criterion or a noisy one; the empirical distribution of that statistic over the long sample is not measured here.

## 6. Reproduction

```bash
python research/long_sample_overlay_attribution.py
python research/promotion_feasibility_backtest.py
python research/go_no_go_evaluation.py
python -m pytest -q
git status --porcelain data/ config/
```
