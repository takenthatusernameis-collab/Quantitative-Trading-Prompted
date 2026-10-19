# Empirical Null Distribution of the Promotion Gate's Rolling-63-Day Sharpe

Cycle 879 — measurement-only, pre-registered in
`research/hypotheses/promotion_gate_false_negative_001.md` before execution
(with a disclosed Cycle 878 feasibility probe; see the hypothesis file).
No gate, threshold, configuration, state, candidate or deployment decision
was changed; the incumbent's decision (**NO-GO**) is unchanged.

## 0. Sample and integrity

| Item | Value |
|---|---|
| Sample | 1993-01-29 .. 2026-10-16 (8487 sessions) |
| Paths | executed (L4) and raw signal (L0), each net of its own 3 bp turnover cost |
| Statistic | rolling-63-session canonical Sharpe (`arithmetic_annualized_rf0`) |
| Estimator | `src/evaluation/drift.py:rolling_sharpe_series` (the live drift-flag estimator) |
| Cross-check vs vectorised recomputation | executed 2.420e-10, raw 1.302e-12 (tol 1e-09; the vectorised path accumulates in a different order, so the difference is floating-point noise) |
| Trailing window reproduces the live gate value | True (diff 9.437e-15) |
| Read-only (data/, config/, state) | True |

## 1. Distribution of the gate statistic

| Statistic | Executed path (L4) | Raw signal (L0) |
|---|---|---|
| windows | 8425 | 8425 |
| mean | 1.498806 | 0.993137 |
| standard deviation | 1.723200 | 1.823348 |
| minimum | -4.372613 | -5.590810 |
| p01 | -2.537441 | -3.234474 |
| p05 | -0.945845 | -2.023419 |
| p25 | 0.003880 | -0.184999 |
| median | 1.351557 | 1.006243 |
| p75 | 2.510136 | 2.199143 |
| p95 | 4.618149 | 4.069824 |
| p99 | 5.919156 | 5.136948 |
| maximum | 9.668564 | 7.604644 |
| zero-dispersion windows | 965 | 186 |

### Failure rates

| Threshold | Executed path | Raw signal | Independent-window SE (executed) |
|---|---|---|---|
| rolling Sharpe < 0.9 (promotion gate) | 39.16% | 47.31% | +/- 4.22 pp |
| rolling Sharpe < 0.5 (drift threshold) | 32.09% | 38.93% | +/- 4.04 pp |
| rolling Sharpe < 0 | 13.51% | 28.27% | +/- 2.96 pp |

**Dependence.** Consecutive windows share up to 62 of their 63 sessions, so the effective number of independent windows is approximately 134, not 8425. The standard errors above use the independent-window approximation and are therefore **optimistic**; the failure rates themselves are not affected.

**Zero-dispersion windows** are scored 0.0 by the repository's canonical convention (`src/evaluation/sharpe.py:sharpe_ratio`), which mechanically fails the 0.9 gate. There are 965 such windows on the executed path (11.45% of all windows) and 186 on the raw-signal path. They are the cash periods created by the SPY-trend filter, and they are part of the strategy's behaviour, not a modelling artefact of this cycle.

## 2. The current trailing window

| Item | Value |
|---|---|
| Executed path trailing value | -0.211883512228 |
| Live gate value (committed record) | -0.211883512228 |
| Percentile rank in the distribution | 11.13% |
| Raw-signal trailing value | +0.307230 |

## 3. Pre-registered conditions

| Condition | Statement | Verdict |
|---|---|---|
| G1 | executed path fails the >= 0.9 gate in >= 10% of windows | **PASS** |
| G2 | current trailing value is below the 1st percentile | **FAIL** |
| G3 | the overlay causes gate failures (executed path fails in more windows than the raw-signal path) | **FAIL** |

- G1 detail: executed failure rate 39.16% (+/- 4.22 pp).
- G2 detail: trailing rank 11.13% of 8425 windows; the p01 of the distribution is -2.537441.
- G3 detail: raw-signal failure rate 47.31% vs executed 39.16% (difference 8.15 pp).

### 3.1 Wording defect in the pre-registered G3 (disclosed, not silently fixed)

The G3 condition sentence in the pre-registration ("the raw-signal path fails the
gate in materially more windows than the executed path -> the overlay causes gate
failures") contradicts its own falsification clause ("falsified if the executed path
fails *less* often: the overlay then **helps** the gate"), which is also what the
hypothesis's prior table states. The two clauses describe the same event with opposite
labels. The measured event is that the raw-signal path fails in **more** windows
(47.31%) than the executed path
(39.16%), i.e. the overlay **reduces** gate
failures by 8.15 pp. G3 is
therefore reported as the proposition it names — *the overlay causes gate failures* —
which is **FAIL** — and the decision rule is applied on
that reading, which is the reading stated in the hypothesis's prior table and in its
falsification clause. The wording defect is recorded here rather than repaired
in the pre-registered file, so the audit trail shows what was actually
written before execution.

**Decision (pre-registered rule):** The rolling-63-day gate fails on a large fraction of the strategy's own history, the current window is an ordinary failure rather than an extreme one, and the overlay does not cause gate failures (it reduces them). A trailing-window NO-GO is therefore weak evidence about the edge and must be reported together with this false-negative rate.

## 4. What this measurement does and does not establish

It establishes the sampling distribution of the gate statistic **for this
strategy on this history**, and therefore the false-negative rate of a
single trailing-window gate read.

It does not establish that the gate should be changed: the gate table in
`config/promotion_gates.yaml` is the incumbent's frozen contract, and a
criterion is not relaxed because it failed. The measured rate is a reason to
**report the gate's informativeness alongside every gate decision**, not to
ignore the gate.

## 5. Reproduction

```bash
python research/gate_false_negative_rate.py
python research/long_sample_overlay_attribution.py
python research/go_no_go_evaluation.py
python -m pytest -q
git status --porcelain data/ config/
```
