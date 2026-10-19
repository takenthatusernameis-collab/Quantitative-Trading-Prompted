# Experiment: Empirical Null Distribution of the Promotion Gate's Rolling-63-Day Sharpe (gate_false_negative_rate_001)

**Cycle**: 879
**Type**: read-only, pre-registered measurement of a *criterion* (not of a strategy). No gate, threshold, configuration, state, candidate or deployment decision was changed.
**Hypothesis**: `research/hypotheses/promotion_gate_false_negative_001.md` (v001, pre-registered 2026-10-19, code revision 8fefeb7, before execution; with a **disclosed** Cycle 878 feasibility probe — see "Disclosure" below)
**Report**: `research/reports/gate_false_negative_rate_001.md` (+ machine-readable `research/reports/gate_false_negative_rate_001.json`)
**Script**: `research/gate_false_negative_rate.py` (read-only; prints every number in the report; exits 0 with `OVERALL: PASS`)

---

## Hypothesis Reference

The promotion gate in `config/promotion_gates.yaml` tests the incumbent's trailing 63-session Sharpe against 0.9. The sampling distribution of that statistic **for the same strategy** had never been measured, so the loop was reading a single trailing-window value (-0.211884) as if it were a stable property of the strategy. Cycle 878 had just established that the trailing failure is an overlay-timing outcome (the raw signal was profitable in the same window: L0-net Sharpe +0.307230) and left the informativeness of the gate itself open (report §5.2 item 3).

Pre-registered conditions:

- **G1** — the executed path fails the >= 0.9 gate in **>= 10%** of rolling-63 windows -> the gate has a high false-negative rate and a single trailing-window NO-GO must not be read as evidence that the edge decayed.
- **G2** — the current trailing value is **below the 1st percentile** -> the current window is an extreme drawdown of the statistic.
- **G3** — *the overlay causes gate failures* (the executed path fails in more windows than the raw-signal path).

Decision rule (fixed in advance): report G1/G2/G3, state the false-negative rate, and state what it implies for reading a trailing-window NO-GO and for the next candidate family's evaluation protocol. **No gate may be changed**; a criterion is not relaxed because it failed.

---

## Disclosure (recorded here because the hypothesis file records it)

The pre-registration is **not blind**: a feasibility probe of the same computation was executed in Cycle 878 while designing the mechanism measurement. The probe established only that the statistic is computable for all 8,425 windows, that its dispersion is of the order of 1.7-1.8 Sharpe units, and that the current trailing window is not the extreme of the distribution. It produced no report, record or test, and none of its numbers was written into the Cycle 878 artifacts. The thresholds (10%, 1st percentile) are round values tied to the repository's own gates and were not tuned to the outcome. No candidate decision may depend on this measurement.

---

## Data Used

- **Source**: committed cache `data/raw/*.parquet` (read-only; no download, no write).
- **Sample**: 1993-01-29 .. 2026-10-16, **8,487 sessions** (the same realized long sample as the Cycle 878 measurement; 8,425 complete 63-session windows).
- **Paths**: the long-sample executed path (L4) and the raw-signal path (L0) produced by `research/long_sample_overlay_attribution.py` (Cycle 878), each net of its **own** 3 bp turnover cost.
- **Universe**: SPY, QQQ, IWM, TLT, GLD, EFA, EEM (frozen). `^VIX` cached but unused.
- **Point-in-time treatment**: unchanged; nothing is fitted and no parameter is selected. The measurement is the distribution of an already-fixed statistic over history.
- **Missing data**: the fetcher's union-calendar forward fill, unchanged.

---

## Configuration (unchanged, frozen)

| Item | Value | Source |
|---|---|---|
| Candidate | `tsmomentum_spytrend_001` | `config/simulation_candidate_001.yaml` |
| Costs | 1 bp commission + 2 bp slippage = 3 bp per unit of weight change, charged per path on its own turnover | same |
| Statistic | rolling-63-session canonical Sharpe, `arithmetic_annualized_rf0` | `src/evaluation/drift.py:rolling_sharpe_series` (the live `low_rolling_sharpe` estimator) |
| Zero-dispersion convention | a window without return dispersion scores **0.0** | `src/evaluation/sharpe.py:sharpe_ratio` |
| Thresholds | 0.9 (promotion gate), 0.5 (live drift threshold), 0.0 | `config/promotion_gates.yaml`, `src/evaluation/drift.py` |

**Number of trials: 1.** One deterministic measurement of one frozen configuration; no bootstrap, no fitted parameter, no selection, no candidate.

---

## Splits

None (nothing was fitted). The only structure is the long-sample history and the 8,425 overlapping rolling-63 windows over it.

---

## Method

1. Rebuild the long-sample paths with the Cycle 878 helpers (`long_sample_layers`, `layer_net_paths`).
2. Compute the rolling-63 canonical Sharpe with the live drift estimator `src/evaluation/drift.py:rolling_sharpe_series`, and cross-check it against an independent vectorised recomputation.
3. Report the distribution, the failure rates at 0.9 / 0.5 / 0.0 with an independent-window standard error, the zero-dispersion window count, the current trailing window's value and percentile rank.
4. Evaluate G1-G3 and apply the pre-registered decision rule.

**Integrity checks performed (all inside the script):**

| Check | Result |
|---|---|
| Long-sample trailing window reproduces the live gate value | **9.437e-15** (executed path -0.21188351222843826 vs committed -0.21188351222842883) |
| Live drift estimator vs vectorised recomputation | executed 2.420e-10, raw 1.302e-12 (tol 1e-9; different accumulation order) |
| Read-only | SHA-256 of all 19 raw parquet files, all `config/*.yaml` and the paper-trading state unchanged before/after |

---

## Results

### 1. Distribution of the rolling-63 canonical Sharpe (8,425 windows)

| Statistic | Executed path (L4) | Raw signal (L0) |
|---|---|---|
| mean | +1.498806 | +0.993137 |
| standard deviation | 1.723200 | 1.823348 |
| minimum | -4.372613 | -5.590810 |
| p01 | -2.537441 | -3.234474 |
| p05 | -0.945845 | -2.023419 |
| p25 | +0.003880 | -0.184999 |
| median | +1.351557 | +1.006243 |
| p75 | +2.510136 | +2.199143 |
| p95 | +4.618149 | +4.069824 |
| p99 | +5.919156 | +5.136948 |
| maximum | +9.668564 | +7.604644 |
| zero-dispersion windows | 965 (11.45%) | 186 |

### 2. Failure rates

| Threshold | Executed path | Raw signal | Independent-window SE (executed) |
|---|---|---|---|
| rolling Sharpe < 0.9 (promotion gate) | **39.16%** | 47.31% | +/- 4.22 pp |
| rolling Sharpe < 0.5 (drift threshold) | 32.09% | 38.93% | +/- 4.04 pp |
| rolling Sharpe < 0 | 13.51% | 28.27% | +/- 2.96 pp |

**Dependence**: consecutive windows share up to 62 of their 63 sessions, so the effective number of independent windows is approximately **134**, not 8,425. The standard errors use the independent-window approximation and are therefore **optimistic**; the failure rates themselves are unaffected.

**Zero-dispersion windows** are scored 0.0 by the repository's canonical convention and therefore mechanically fail the 0.9 gate. They are the cash periods created by the SPY-trend filter (the filter is flat on 2,270 of 8,487 sessions), i.e. part of the strategy's behaviour rather than an artefact of this cycle.

### 3. The current trailing window

| Item | Value |
|---|---|
| Executed path trailing value | -0.21188351222843826 (live gate value -0.21188351222842883) |
| Percentile rank in the distribution | **11.13%** |
| Raw-signal trailing value | +0.307230 |

### 4. Pre-registered conditions

| Condition | Verdict | Numbers |
|---|---|---|
| G1 (gate has a high false-negative rate) | **PASS** | 39.16% of windows fail the >= 0.9 gate (+/- 4.22 pp) |
| G2 (current window is extreme) | **FAIL** | rank 11.13%, far above the 1st percentile (-2.537441) |
| G3 (the overlay causes gate failures) | **FAIL** | raw signal fails in 47.31% of windows vs 39.16% executed: the overlay **reduces** gate failures by 8.15 pp |

**Decision (pre-registered rule):** *"The rolling-63-day gate fails on a large fraction of the strategy's own history, the current window is an ordinary failure rather than an extreme one, and the overlay does not cause gate failures (it reduces them). A trailing-window NO-GO is therefore weak evidence about the edge and must be reported together with this false-negative rate."*

### 5. Wording defect in the pre-registered G3 (disclosed, not silently repaired)

The G3 condition sentence ("the raw-signal path fails in materially more windows than the executed path -> the overlay causes gate failures") contradicts its own falsification clause ("falsified if the executed path fails *less* often: the overlay then **helps** the gate"), which is also what the hypothesis's prior table states. Both clauses describe the same event with opposite labels. The measured event is that the raw-signal path fails in more windows (47.31%) than the executed path (39.16%), i.e. the overlay **reduces** gate failures. G3 is therefore reported as the proposition it names ("the overlay causes gate failures"), which is **FALSE**, and the decision rule is applied on that reading. The pre-registered file was left unedited so the audit trail shows what was actually written before execution.

---

## What the measurement establishes

1. The gate statistic is far noisier than its full-sample mean suggests: with a full-sample Sharpe of +1.4988 the rolling-63 statistic has a standard deviation of **1.7232**, and **39.16%** of the strategy's own 63-day windows fail the >= 0.9 gate.
2. The current trailing window is an **ordinary** failure (11.13th percentile), not an extreme one.
3. The overlay **reduces** the gate's failure rate (47.31% -> 39.16%); it does not cause gate failures. This is the counter-evidence that must accompany Cycle 878's overlay-timing reading: the overlay made *this* window fail, but it makes fewer windows fail on average.

## What it does not establish

1. That the gate should be changed. `config/promotion_gates.yaml` is the incumbent's frozen contract; a criterion is not relaxed because it failed. The measured rate is a reason to **report the gate's informativeness alongside every gate decision**, not to ignore the gate.
2. Anything about a different candidate: the distribution is the statistic's distribution *for this strategy on this history*.
3. That the incumbent's edge is intact. The measurement says the trailing NO-GO is weak evidence, not that the edge is good.

---

## Reproduction

```bash
python research/gate_false_negative_rate.py      # OVERALL: PASS (exit 0)
python research/long_sample_overlay_attribution.py
python research/go_no_go_evaluation.py             # decision unchanged (NO-GO)
python research/drift_persistence_report.py        # stored == recomputed
python -m pytest -q                               # 95 tests (89 pre-existing + 6 new)
git status --porcelain data/ config/              # must be empty
```

---

## Decision label

**Methodological / diagnostic** — a statement about a criterion, not about a strategy. The incumbent's promotion decision is unchanged: **NO-GO**, live deployment unsupported; `sectorrotation_001`, `csmomentum_001` and `macroregime_001` remain rejected/failed; the drift flag `low_rolling_sharpe` (-0.21188351222842883, 5 consecutive trading days below 0.5) is unchanged; no candidate was proposed, promoted or rejected, and no gate was changed.
