# Hypothesis: Empirical Null Distribution of the Promotion Gate's Rolling-63-Day Sharpe (promotion_gate_false_negative_001)

## Version History

- v001 (promotion_gate_false_negative_001, 2026-10-19): Initial pre-registered
  hypothesis for Cycle 879. Parent cycle: Cycle 878 (long-sample mechanism
  decomposition of the incumbent's risk overlays). Code revision: 8fefeb7.

---

## Disclosure (mandatory; read before using this file)

**This pre-registration is not blind.** In Cycle 878, while designing the
mechanism measurement, a *feasibility probe* of this exact computation was
executed: the rolling-63-session canonical Sharpe of the incumbent's
long-sample executed path and of its raw-signal path. The probe established
that

- the statistic is computable for all 8,425 overlapping windows of the
  8,487-session sample,
- its dispersion is of the order of 1.7-1.8 Sharpe units (not the ~0.25 that a
  normal approximation would suggest from the full-sample Sharpe alone),
- the current trailing window's value (-0.211884) is not the extreme of the
  distribution.

The probe was a feasibility check, not the measurement: it produced no
report, no experiment record and no test, and none of its numbers was written
into the Cycle 878 artifacts. The decision rule and the interpretation
thresholds below are therefore **not independent of the probe**, and this file
says so. Two consequences are accepted as the price of the disclosure:

1. The thresholds (10%, 1st percentile, "materially more") are stated as round,
   pre-specified-style values tied to the repository's own gate values, and are
   **not** tuned to the outcome.
2. **No candidate, promotion, rejection, re-fit or deployment decision may
   depend on this measurement.** It is a statement about the *criterion*, not
   about a strategy. The incumbent's decision (**NO-GO**) stands whatever the
   numbers are.

---

## Mechanism Description

The promotion gate in `config/promotion_gates.yaml` contains two statistics
computed on the incumbent's paper record: a `rolling_63d_sharpe` gate (>= 0.9)
and a `psr` gate (>= 0.95), plus a `full_period_sharpe` gate. The rolling gate
is a **63-session window statistic of a path-dependent, vol-targeted,
daily-rebalanced strategy**. Its sampling distribution under the *same
strategy* has never been measured, so the loop currently reads a single
trailing-window value (-0.211884) as if it were a stable property of the
strategy.

The structural reason a 63-day rolling Sharpe is noisy is well known and
applies here with particular force:

1. **Estimation error.** A 63-session Sharpe has a standard error of roughly
   `sqrt((1 + SR^2/2) / 63)` in annualised units, i.e. of order 0.2-0.3 for a
   strategy with a full-sample Sharpe near 1.5, before any non-normality.
2. **The overlay's own path dependence.** The volatility scaler is
   pro-cyclical (Cycle 878 §2): it reduces exposure after volatility has
   risen, which is when the signal loses money, and restores exposure after
   volatility has fallen. This adds a *negative* serial correlation between
   the scaled exposure and the realised signal return, which is precisely the
   mechanism that makes the window statistic more volatile than its long-run
   mean suggests, and makes the window statistic's *tails* fat.
3. **Regime clustering.** Window statistics are not independent: consecutive
   windows share up to 62 of their 63 sessions, so the effective number of
   independent observations is roughly `n / 63`, not `n`.

**Consequence if the hypothesis holds:** a trailing-window NO-GO is weak
evidence about the strategy's edge, and the research loop's decision rule must
be read accordingly — including the incumbent's current NO-GO, which Cycle 878
showed is an overlay-timing outcome rather than signal decay.

---

## Expected direction and magnitude (Pre-Specified Prior)

| Quantity | Prior (non-binding) |
|---|---|
| Fraction of rolling-63 windows of the executed path failing the >= 0.9 gate | **materially above 10%** (the 63-day statistic is noisy; the prior is that a single window is a weak test) |
| Fraction of windows with rolling-63 Sharpe < 0.5 (the drift threshold) | of the order of 10-30% |
| Dispersion (sd) of the rolling-63 Sharpe | **of the order of 1.5-2.0**, i.e. much larger than the ~0.25 implied by the full-sample Sharpe alone |
| Effect of the overlay on the gate failure rate | **the executed path fails less often than the raw signal** (Cycle 878 showed the overlay improves both the full-sample Sharpe and the max drawdown; the same overlay made the *current* window fail, which is the exception, not the rule) |
| Current trailing window (-0.211884) | **not** in the extreme tail (its damage was an overlay-timing accident inside an ordinary window) |

---

## Holding horizon

The 63-session window of the promotion gate, evaluated over every trailing
window of the incumbent's long-sample history (8,425 overlapping windows of
8,487 sessions, 1993-01-29 .. 2026-10-16).

---

## Asset Universe

The frozen paper-trading universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM),
unchanged. `^VIX` is cached but unused.

---

## Features and Data Sources

| Item | Value | Source |
|---|---|---|
| Prices | daily OHLCV, close execution | committed cache `data/raw/*.parquet` (read-only) |
| Paths | long-sample executed path (L4) and raw-signal path (L0) | `research/long_sample_overlay_attribution.py` (Cycle 878) |
| Costs | 3 bp per unit of weight change, charged on each path's own turnover | frozen config `cost_model` |
| Statistic | rolling-63-session canonical Sharpe, `arithmetic_annualized_rf0` | `src/evaluation/drift.py:rolling_sharpe_series` (the live drift-flag estimator) |
| Zero-dispersion convention | a window with no return dispersion yields Sharpe **0.0** (the repository's `sharpe_ratio` convention) | `src/evaluation/sharpe.py` |
| Gate thresholds used for the failure rates | 0.9 (promotion gate), 0.5 (drift threshold), 0.0 | `config/promotion_gates.yaml`, `config/paper_trading_config.yaml` |

**Point-in-time treatment**: unchanged; nothing is fitted and no parameter is
selected. The measurement is a distribution of an already-fixed statistic over
history, not a test on a held-out sample.

---

## Measurement Rules (fixed by this hypothesis)

1. Two paths only: the executed path (L4) and the raw-signal path (L0), each
   net of its own 3 bp turnover cost, over the same 8,487 sessions.
2. The rolling statistic is computed with
   `src/evaluation/drift.py:rolling_sharpe_series` (the same estimator the
   live `low_rolling_sharpe` drift flag uses), window 63.
3. Report for each path: window count, mean, sd, min, p01, p05, p25, median,
   p75, p95, p99, max; the failure rates at < 0.9, < 0.5 and < 0.0; the
   number of zero-dispersion windows; the value and the percentile rank of the
   current trailing window.
4. **Dependence**: overlapping windows share up to 62 of 63 sessions. Report
   the effective number of independent windows (`n / 63`) and the standard
   error of each failure rate under the independent-window approximation
   (`sqrt(p(1-p) / n_eff)`), and state that the approximation is optimistic
   because the windows are positively autocorrelated in their failures.
5. **Trials: 1.** No bootstrap, no fitted parameter, no selection, no
   candidate. One deterministic measurement of one frozen configuration.

---

## Pre-Registered Conditions

- **G1 (gate informativeness)**: the executed path fails the >= 0.9 rolling-63
  gate in **>= 10%** of windows -> the gate has a high false-negative rate and
  a single trailing-window NO-GO must not be read as evidence that the edge
  decayed. *Falsified if* the rate is < 10% (the gate is a low-false-negative
  criterion and the current NO-GO is informative).
- **G2 (is the current window extreme?)**: the current trailing value
  (-0.211884) is **below the 1st percentile** -> the current window is an
  extreme drawdown of the statistic. *Falsified if* it is at or above the 1st
  percentile (an ordinary window failure).
- **G3 (does the overlay cause gate failures?)**: the raw-signal path fails
  the >= 0.9 gate in **materially more** windows than the executed path -> the
  overlay causes gate failures. *Falsified if* the executed path fails *less*
  often: the overlay then **helps** the gate on average, and the Cycle 878
  reading of the trailing failure as a pure overlay-timing accident must be
  stated together with that counter-evidence.

**Decision rule (fixed in advance)**: report G1/G2/G3 as PASS/FAIL with their
numbers; state the gate's false-negative rate in percent and in words; state
what that implies for how the loop reads a trailing-window NO-GO (including the
incumbent's current NO-GO) and for the evaluation protocol of the next
candidate family. **Do not change the gates**; `config/promotion_gates.yaml`
is the incumbent's frozen contract and a criterion may not be relaxed because
it failed. A measured high false-negative rate is a reason to *report the
gate's informativeness alongside every future gate decision*, not a reason to
ignore the gate.

---

## Known Confounders

1. **Overlapping windows**: failure rates are not based on 8,425 independent
   observations (see rule 4).
2. **Same path, same strategy**: the distribution is the statistic's
   distribution *for this strategy*. It says nothing about a different
   candidate; a different strategy may have a much tighter distribution.
3. **The statistic is the gate**: the failure rate is measured against the
   same threshold the gate uses, so the measurement is a property of the
   (statistic, threshold) pair, not of the strategy alone.
4. **Historical regimes**: 1993-2026 contains one 1998, one 2000-2002, one
   2008 and one 2020 crisis; the distribution of 63-day statistics is
   therefore estimated from a handful of independent crisis episodes and the
   tails are thinly sampled.
5. **Cash windows**: the strategy is in cash when the SPY-trend filter is off;
   186 raw-signal and 965 executed windows have zero dispersion and are
   scored 0.0 by the repository convention, which mechanically fails the
   0.9 gate. This is the repository's own convention, not a modelling choice
   of this cycle, but it inflates the failure rate and must be reported
   separately.
6. **Non-blind pre-registration**: see the Disclosure section.

---

## Cost Model Assumptions

Unchanged: 1.0 bp commission + 2.0 bp slippage = 3.0 bp per unit of weight
change, charged on each path's own turnover; canonical Sharpe with a 0%
risk-free rate. Documented gaps: no spread, impact, borrow or latency model.

---

## Reproduction

```bash
python research/gate_false_negative_rate.py   # the measurement (exit 0, OVERALL: PASS)
python research/long_sample_overlay_attribution.py
python research/go_no_go_evaluation.py          # decision unchanged (NO-GO)
python -m pytest -q
git status --porcelain data/ config/             # must be empty
```

---

## Decision Discipline (Pre-Commitment)

This cycle produces a **methodological / diagnostic** label about a
criterion. It does not produce, change or reverse any candidate's status, and
it does not change any gate.

---

## References

- `research/reports/long_sample_overlay_attribution_001.md` (Cycle 878) — the
  long-sample paths and the trailing-window mechanism finding.
- `research/experiments/long_sample_overlay_attribution_001.md` (Cycle 878).
- `research/reports/monitoring_cycle_877.md` (Cycle 877) — current NO-GO
  decision and drift-flag status.
- `config/promotion_gates.yaml` — the gate table being characterised.
- `src/evaluation/drift.py:rolling_sharpe_series` — the live drift estimator.
- AGENTS.md: "Honest accounting", "Statistical testability", "Hypothesis
  first", "Independent evaluation".

---

*Created: 2026-10-19*
*Code revision: 8fefeb7*
*Status: PRE-REGISTERED (with disclosed Cycle 878 feasibility probe) — measurement not yet run.*
