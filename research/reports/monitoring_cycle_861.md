# Monitoring Cycle 861 — One Sharpe convention (2026-10-19)

**Scope:** measurement consistency. Cycle 860 left three different Sharpe estimators in simultaneous use and
deferred their reconciliation. This cycle adopts **one** documented convention for every promotion-gate,
drift-flag and PSR quantity, re-verifies the historical verdicts it touches, and keeps the 63-day
underperformance investigation as a separate cycle.

**Mode:** verification-only with respect to market data. No completed US session beyond 2026-10-16 exists
(`python research/refresh_raw_cache.py --dry-run` → `no-op: no completed sessions to append`;
`python research/extend_paper_trading_state.py --dry-run` → `no new completed session`, state write count 0,
NAV 133,729.224310211 unchanged), so the paper-trading state was **not** extended. `data/processed` and
`data/raw` are byte-identical to `HEAD` (verified with `git status --porcelain data/` → empty).

---

## 1. The convention

| | |
|---|---|
| **id** | `arithmetic_annualized_rf0` |
| **formula** | `mean(r) * 252 / (std(r, ddof=1) * sqrt(252))` |
| **risk-free rate** | 0 (the return series is already net of costs) |
| **implementation** | `src.evaluation.sharpe.sharpe_ratio` |
| **declaration** | `config/promotion_gates.yaml` → `sharpe_convention` (machine-readable, checked against the code) |
| **applies to** | gate `full_period_sharpe`, gate `rolling_63d_sharpe`, PSR numerator **and** PSR bootstrap distribution, drift flag `state.drift_flags.low_rolling_sharpe` |

**Why this one.** It is the formula the live paper-trading update already used for the `low_rolling_sharpe`
drift flag, and therefore the scale of every rolling Sharpe quoted in the validation artifacts
(`research/reports/paper_trading_validation_002.md`: 0.9356 for the 444-day record). After the change a gate
value, the stored drift flag and the artifacts are *the same measurement* and can be compared directly. It is
arithmetic, so it compounds no wealth path and cannot overflow on a bootstrap resample with a non-positive
growth factor — the failure mode the old geometric bootstrap estimator needed a log-mean-exp guard for. It uses
a zero risk-free rate because the recorded drift flag and every quoted rolling Sharpe do; a risk-free rate is
an assumption, not a property of the strategy, and restating it would have invalidated every stored value.

**The second scale, named and confined.** The recorded backtest baseline (Sharpe 1.4178) and the published
backtest research artifacts are on the *backtest-baseline* scale
(`((1+r).prod() ** (252/n) - 1 - 0.02) / (std(r, ddof=1) * sqrt(252))`, CAGR-based). That scale is kept as
`src.evaluation.sharpe.backtest_sharpe_ratio` and is used for **backtest research metrics only** (parameter
plateau, PBO/FDR, benchmark statistics), so that the published artifacts stay reproducible. It is not used in
any gate, in the drift flag or in the PSR.

---

## 2. What changed in code

| File | Change |
|---|---|
| `src/evaluation/sharpe.py` | **new** — `sharpe_ratio` (canonical) and `backtest_sharpe_ratio` (backtest-baseline scale), plus the convention constants |
| `src/evaluation/utils.py` | the old geometric `sharpe_ratio` is removed; the canonical one is re-exported (backward-compatible import path) |
| `src/evaluation/drift.py` | `annualized_sharpe` now delegates to the canonical estimator (same numbers, one formula) |
| `src/evaluation/statistics.py` | `_safe_sharpe` (bootstrap distribution) and the `compute_psr` numerator both use the canonical estimator; `_evaluate_config` (parameter plateau / PBO / FDR) uses the backtest-baseline scale, so the published backtest artifacts stay reproducible |
| `src/evaluation/benchmark.py` | benchmark statistics use the backtest-baseline scale (unchanged numbers) |
| `src/simulation/evaluation.py` | `paper_sharpe` and the rolling 63d gate use the canonical estimator; the diagnostic `rolling_sharpe_63d_report_convention` is replaced by `rolling_sharpe_63d_backtest_scale`; the evaluation **fails closed** when `config/promotion_gates.yaml` declares a different convention id |
| `src/simulation/paper_trading.py` | the live drift flag uses the canonical estimator (same numbers) |
| `config/promotion_gates.yaml` | new `sharpe_convention` block (the declaration, the rationale, the backtest-baseline scale and its PSR-target note); the `metric_definition` of the three affected gates now names the canonical implementation |
| `research/go_no_go_evaluation.py` | prints `sharpe_convention` and the renamed diagnostic |
| `research/run_cycle3.py`, `run_cycle13.py`, `run_cycle15.py`, `run_cycle15_c4_corrected.py`, `run_cycle19.py` | the legacy calls are renamed to `backtest_sharpe_ratio` so the historical scripts keep producing exactly the numbers their artifacts record |
| `research/sharpe_convention_audit.py` | **new** — read-only audit that reproduces every number in this report from the committed state alone |
| `tests/test_go_no_go_evaluation.py` | **7 new tests** (see §5) |

No threshold, gate, strategy parameter, cost model or universe was changed. The only behavioural change in the
promotion path is the *measurement definition* the gates were always documented with.

---

## 3. The numbers

Reproduce with `python research/sharpe_convention_audit.py`.

### 3.1 Committed record — 449 sessions through 2026-10-16

| Quantity | Canonical (new) | Backtest-baseline scale (the old gate estimator) |
|---|---|---|
| full-period Sharpe | **1.748401** | 1.638009 |
| trailing 63d Sharpe | **-0.211884** | -0.493001 |
| stored `low_rolling_sharpe` flag | **-0.21188351222842883** | (identical to the canonical value) |
| PSR (numerator + bootstrap, same estimator) | **0.684041** (SE 0.690150, empirical 0.741, 95% CI [0.536027, 3.216373]) | 0.625683 (SE 0.687208, empirical 0.654) — the old *mixed* pairing |
| scale offset (canonical − backtest-baseline) | +0.110392 | — |

Gate table and decision (`evaluation_deterministic: True`):

| Gate | Value | Threshold | Result |
|---|---|---|---|
| `track_record_length` | 449 | ≥ 126 | PASS |
| `full_period_sharpe` | 1.748401 | ≥ 0.9 | PASS |
| `rolling_63d_sharpe` | **-0.211884** | ≥ 0.9 | **FAIL** |
| `max_drawdown` | -0.049857 | ≥ -0.15 | PASS |
| `rolling_63d_max_dd` | -0.038564 | ≥ -0.15 | PASS |
| `regime_flips` | 6 | ≥ 1 | PASS |
| `psr` | **0.684041** | ≥ 0.95 | **FAIL** |

`psr_zone: grey_zone`; `failed_gates: ['rolling_63d_sharpe', 'psr']`; **decision: NO-GO** — *unchanged* from
Cycle 860. The gate values moved (they are now on the canonical scale), the decision did not.

### 3.2 The 444-session record through 2026-10-09 — **historical verdict flip**

| Quantity | Canonical (new) | Backtest-baseline scale (the old gate estimator) |
|---|---|---|
| full-period Sharpe | **1.934100** | 1.857060 |
| trailing 63d Sharpe | **0.935578 → PASS** | 0.670178 → **FAIL** |
| PSR (numerator + bootstrap, same estimator) | **0.762425** (SE 0.722984, empirical 0.763) | 0.729085 (the old mixed pairing) |
| scale offset | +0.077040 | — |

| Gate | Value | Threshold | Result |
|---|---|---|---|
| `track_record_length` | 444 | ≥ 126 | PASS |
| `full_period_sharpe` | 1.934100 | ≥ 0.9 | PASS |
| `rolling_63d_sharpe` | **0.935578** | ≥ 0.9 | **PASS** (was FAIL: 0.670178) |
| `max_drawdown` | -0.049857 | ≥ -0.15 | PASS |
| `rolling_63d_max_dd` | -0.019998 | ≥ -0.15 | PASS |
| `regime_flips` | 6 | ≥ 1 | PASS |
| `psr` | **0.762425** | ≥ 0.95 | **FAIL** (grey zone) |

`failed_gates: ['psr']`; `psr_zone: grey_zone`; **decision: INCONCLUSIVE** (previously NO-GO, because the
rolling gate also failed under the old estimator).

**This is a flip of a historical verdict, and it is only a measurement fix, not new evidence.** Under the
canonical convention the rolling 63d gate on the 444-day record passes — exactly the value the validation
artifact already quoted (0.9356) — but the record still fails the PSR gate and therefore is still **not
promotable**. Live deployment remains unsupported: the *current* record (449 sessions) is NO-GO with two
failing gates.

### 3.3 What the change does to the PSR — and what it does not

The PSR target is the recorded backtest baseline **1.4178**, which is on the backtest-baseline scale; the
paper Sharpe is now on the canonical scale. The target is documented as a fixed external reference and is
**not** restated, because the backtest return series needed to restate it is not in the repository and
re-running the backtest baseline is outside the scope of a measurement-consistency change.

The residual mismatch is quantified. If the target carried the paper series' own scale offset (+0.110392), the
target would be 1.528192 and the PSR would be **0.625165** — i.e. essentially the pre-change value
(0.625683). The entire apparent PSR improvement (0.625683 → 0.684041) therefore comes from the *scale of the
target*, not from new evidence about the strategy. For the 444-day record the same sensitivity gives 0.728262
against the pre-change 0.729085. All variants stay inside the grey zone, so no verdict changes because of it.

**Residual known limitation (carried forward):** the PSR compares a canonical-scale numerator with a
backtest-baseline-scale target. Converting the target needs the backtest return series, i.e. a re-run of the
backtest baseline — a separate, bounded task, not a silent restatement.

### 3.4 The validation artifact's full-period number is on a *third* scale

`research/reports/paper_trading_validation_002.md` quotes "Net-of-Cost Sharpe (444d) = 2.0548". That number
is `annualized return / annualized volatility` with no risk-free subtraction (the formula printed by
`research/run_paper_trading_replay.py`), a third scale. Recomputing that scale on the committed 444-day slice
gives 2.066310 (the artifact predates the last state refresh: it quotes a total return of 37.11% against
37.3764% in the committed state). The artifact's **rolling** 63d value (0.9356) is already on the canonical
scale and is reproduced exactly. The artifact is therefore left in place with a dated addendum; its gate
verdicts (all six passed) do not change under the canonical convention.

---

## 4. Why the change is a measurement fix and not re-tuning

* No threshold changed: 126 days, 0.9 Sharpe (×2), 15% max DD (×2), 1 regime flip, PSR 0.5/0.95 grey zone.
* No strategy, universe, cost model or parameter changed.
* The convention was **chosen from the existing evidence**, not fitted: it is the formula of the live drift
  flag and of every rolling Sharpe in the artifacts, i.e. the scale on which the record was already being
  described.
* The two scales are named, documented and confined, so the remaining backtest-baseline usages are visible
  rather than accidental.

---

## 5. Verification

| Command | Result |
|---|---|
| `python -m pytest -q` | **61 passed** (54 pre-existing + 7 new) |
| `python research/go_no_go_evaluation.py` | exit 0; `side_effect_free: True`; `evaluation_deterministic: True`; decision **NO-GO**; failed gates `['rolling_63d_sharpe', 'psr']`; `sharpe_convention: arithmetic_annualized_rf0`; gate value `rolling_63d_sharpe = -0.21188351222842883`, identical to the stored drift flag |
| `python research/drift_persistence_report.py` | persistence 5 (2026-10-12 → 2026-10-16); `stored == recomputed: True`; series tail 0.4892 / 0.3669 / 0.1133 / 0.3249 / -0.2119 |
| `python research/_tmp_cycle77_verify.py` | **OVERALL: PASS** (rolling Sharpe match True, regime flips 6/6, NAV $133,729.22, max DD -4.9857%) |
| `python .github/scripts/test_kilo_supervisor_loop.py` | OK (10 tests) |
| `python research/sharpe_convention_audit.py` | the tables of §3, from the committed state alone |
| `python research/refresh_raw_cache.py --dry-run` | `no-op: no completed sessions to append` |
| `python research/extend_paper_trading_state.py --dry-run` | `no new completed session`, state write count 0, NAV unchanged |
| `git status --porcelain data/` | empty → `data/processed` and `data/raw` byte-identical to `HEAD` |

The seven new tests in `tests/test_go_no_go_evaluation.py`:

1. `test_documented_convention_matches_the_implementation` — the declared convention in
   `config/promotion_gates.yaml` is the one the code implements.
2. `test_gate_rolling_sharpe_equals_the_stored_drift_flag_value` — the gate value and
   `state.drift_flags.low_rolling_sharpe` are the same number (-0.21188351222842883), and it is *not* the
   backtest-baseline value.
3. `test_rolling_sharpe_series_reproduces_the_validation_artifact_values` — the rolling series tail equals
   the artifact values 0.4892 / 0.3669 / 0.1133 / 0.3249 / -0.2119.
4. `test_psr_numerator_uses_the_canonical_estimator` — the PSR numerator is the canonical Sharpe and not the
   backtest-baseline one.
5. `test_psr_bootstrap_uses_the_canonical_estimator` — a fixed bootstrap resample is scored with the canonical
   estimator.
6. `test_evaluation_fails_closed_when_the_declared_convention_differs` — a gate table that declares another
   convention is a hard error, not a silent evaluation.
7. `test_444_session_record_verdict_under_the_canonical_convention` — the 444-session record passes the
   rolling gate (0.935578), fails only the PSR gate in the grey zone, and the decision is INCONCLUSIVE, never
   GO.

**One pre-existing test was re-specified** (not weakened): the synthetic record of
`test_psr_above_go_threshold_with_failing_rolling_sharpe_cannot_yield_go` used a series that cleared the PSR
GO threshold under the old *mixed* estimator (0.975) but not under the canonical one (0.797), so its premise
had become void. The series was re-specified (strong first half, weak trailing 63-day window) and now yields
`psr_normal = 0.9849` with a rolling 63d Sharpe of 0.25, i.e. the premise — PSR gate passes, rolling gate
fails — is preserved. The test's *assertions* are unchanged.

---

## 6. Decision status

* **Current record (449 sessions through 2026-10-16): NO-GO.** Two documented promotion gates fail
  (`rolling_63d_sharpe` -0.211884 < 0.9 and `psr` 0.684041 < 0.95, grey zone). Live deployment remains
  unsupported.
* **444-day record: INCONCLUSIVE** (was NO-GO) — the flip is a measurement fix, and the record still fails the
  PSR gate, so it is still not promotable.

## 7. Not done (deliberately)

* The root cause of the 63-day underperformance and of the PSR shortfall is **not** investigated here. That
  investigation now starts from a single, settled definition of "rolling Sharpe" and is the next cycle.
* The PSR target is not restated on the canonical scale (needs a backtest baseline re-run; see §3.3).
* The `low_rolling_sharpe` drift flag still persists (5 consecutive sessions below 0.5); the drift-flag
  escalation path is unchanged.
