# Monitoring Cycle 860 — gate-complete promotion-gate enforcement

- **Cycle:** 860 (enforcement cycle for the promotion gates; verification-only with respect to market data)
- **Run date:** 2026-10-19 (UTC 16:03–16:25Z)
- **Mode:** verification-only — **no new completed US trading session** existed beyond 2026-10-16, so the paper-trading
  state was **not** extended. The cycle changed **code, tests and reports only**.
- **State touched:** none. `data/processed/paper_trading_state.yaml` and every `data/raw/*.parquet` file are
  byte-identical before and after the cycle (SHA-256 compared over 1832 files under `data/processed` + `data/raw`).
- **Decision before this cycle:** INCONCLUSIVE (Cycle 858/859 reconciliation, PSR in the grey zone).
- **Decision after this cycle:** **NO-GO** (the code-level decision is now gate-complete; two documented gates fail).

## 1. Precondition check (was a new completed session available?)

| Check | Result |
|---|---|
| Raw cache index max date (SPY, QQQ, IWM, TLT, GLD, EFA, EEM, ^VIX) | **2026-10-16** for all 8 symbols (row counts 8487 / 6945 / 6637 / 6094 / 5512 / 6322 / 5916 / 451) |
| `python research/refresh_raw_cache.py --dry-run` | `no-op: no completed sessions to append` — 0 rows appended for every symbol |
| `python research/extend_paper_trading_state.py --dry-run` | `no new completed session`; sessions extended 0; state write count 0; NAV before = NAV after = 133,729.224310211 |

**Conclusion:** no completed session beyond 2026-10-16 → verification-only mode. The extension path was **not** taken.
The evaluation therefore runs against the same 449-session record (2025-01-02 → 2026-10-16) that Cycles 858 and 859
used, which makes the before/after decision comparison apples-to-apples.

## 2. Defect closed: the code-level decision ignored the documented promotion gates

`evaluate_go_no_go` (src/simulation/evaluation.py) evaluated a `min_days = 63` day-count, a PSR test against the
backtest Sharpe, the full-period max drawdown and *regime persistence*. It never evaluated the **rolling 63d Sharpe**
gate, the full-period net-of-cost Sharpe gate, the rolling 63d max-DD gate or the regime-flip gate — all four of which
are stated in the repository's own gate table (`research/reports/paper_trading_validation_002.md`, "Go/No-Go
Assessment"). A record with PSR > 0.95 but a negative rolling 63d Sharpe could therefore be labelled **"GO"** by the
code. That is the mechanism behind the earlier unqualified "GO for live deployment" claims in
`research/reports/deployment_dossier_001.md` (reconciled in Cycle 858): the false-promotion path could silently re-open.

### 2.1 Single source of truth

`config/promotion_gates.yaml` is now the only place where the promotion gates live. For every gate it records the
name, the metric, the threshold, the comparison direction, the formula used to compute the metric
(`metric_definition`) and the source artifact the gate comes from. The gate list covers the complete
`paper_trading_validation_002.md` table plus the PSR criterion:

| Gate | Metric | Threshold | Source |
|---|---|---|---|
| `track_record_length` | `paper_days` | ≥ 126 | paper_trading_validation_002.md |
| `full_period_sharpe` | `paper_sharpe` | ≥ 0.9 | paper_trading_validation_002.md |
| `rolling_63d_sharpe` | `rolling_sharpe_63d` | ≥ 0.9 | paper_trading_validation_002.md |
| `max_drawdown` | `paper_max_dd` | ≥ -0.15 | paper_trading_validation_002.md |
| `rolling_63d_max_dd` | `rolling_max_dd_63d` | ≥ -0.15 | paper_trading_validation_002.md |
| `regime_flips` | `regime_flips` | ≥ 1 | paper_trading_validation_002.md |
| `psr` | `psr_normal` | ≥ 0.95 | go_no_go_evaluation_002.md |

**No threshold value changed.** The values above are the ones already documented in the artifacts; Cycle 860 added
enforcement, not re-tuning.

### 2.2 Enforcement

`evaluate_go_no_go` now evaluates **every** gate in the definition and exposes the per-gate outcome
(`GateEvaluation`: name, metric, value, threshold, comparison, pass/fail, source) on the result object
(`result.gates`, also surfaced as `result.gate_table`). "GO" is returned only when every gate passes.

The decision mapping is now read from the same YAML file (`decision_mapping`), so the documented policy and the
executed policy cannot drift apart, and a missing mapping key is a hard error rather than a silent default:

| Situation | Decision | Rationale |
|---|---|---|
| Track record shorter than the `track_record_length` gate | **INCONCLUSIVE** | too few observations to judge |
| Every gate passes | **GO** | — |
| Only the PSR gate fails and the PSR sits in the grey zone [0.5, 0.95) | **INCONCLUSIVE** | statistically indistinguishable from the backtest baseline and every economic/risk gate is satisfied, so more observations are needed |
| Any other gate fails | **NO-GO** | a record that violates a documented promotion criterion is not promotable, regardless of how uncertain its Sharpe estimate is |

**Why fail → NO-GO rather than INCONCLUSIVE.** The Cycle 858/859 code returned INCONCLUSIVE whenever the PSR was in
the grey zone, which meant a record that *violated* a documented promotion gate (rolling 63d Sharpe -0.493) was
reported as merely "undecided". The gate table and the drift flag disagree with that framing: the strategy's own
promotion criteria are not satisfied, and statistical uncertainty about the Sharpe is not a licence to ignore a
failed economic gate. The one case that stays INCONCLUSIVE is the case where the *only* failing gate is the PSR
itself — there the evidence really is indeterminate, and no economic or risk gate is violated.

**A failing gate can never yield "GO"** in any of the four cases. This is enforced in code
(`map_decision`, src/simulation/evaluation.py) and pinned by a test that fails each gate in turn and asserts that
the decision is never "GO".

### 2.3 Fail-closed behaviour

The gate evaluation previously used `metric_values.get(metric, 0.0)`, so a typo in the gate table would have silently
substituted 0.0 for a missing metric. It now raises `ValueError` naming the unknown metric, and a missing
`decision_mapping` key or a missing `psr_grey_zone` block is likewise a hard error. A malformed gate table can no
longer change a promotion verdict silently.

## 3. Reconciliation of the current record (449 sessions through 2026-10-16)

`python research/go_no_go_evaluation.py` (read-only, seeded bootstrap, `evaluation_deterministic: True`):

| Gate | Value | Threshold | Result |
|---|---|---|---|
| `track_record_length` | 449 | ≥ 126 | PASS |
| `full_period_sharpe` | 1.638009 | ≥ 0.9 | PASS |
| `rolling_63d_sharpe` | **-0.493001** | ≥ 0.9 | **FAIL** |
| `max_drawdown` | -0.049857 | ≥ -0.15 | PASS |
| `rolling_63d_max_dd` | -0.038564 | ≥ -0.15 | PASS |
| `regime_flips` | 6 | ≥ 1 | PASS |
| `psr` | **0.625683** | ≥ 0.95 | **FAIL** |

- `psr_zone`: **grey_zone** (0.625683 ∈ [0.5, 0.95))
- `failed_gates`: `['rolling_63d_sharpe', 'psr']`
- **decision: NO-GO** (was INCONCLUSIVE in Cycles 858/859)
- Supporting metrics: `psr_empirical` 0.654000, `sharpe_se` 0.687208, 95% CI [0.344994, 2.998531], ann. return
  0.177184, ann. vol 0.095853, Sortino 2.442582, profit factor 1.357463, 107 trades, ann. turnover 12.594489,
  regime persistence 134 days, 1 drift flag (`low_rolling_sharpe` = -0.21188351222842883, 2026-10-16).

**Live deployment remains unsupported.** The decision changed from INCONCLUSIVE to NO-GO, not because any gate value
changed (they are identical to Cycle 859) but because the decision function now enforces the gates that the
artifacts document. The `deployment_dossier_001.md` "GO for live deployment" / "PROCEED with live deployment"
statements remain unsupported by the current record and are now contradicted by a gate-complete NO-GO.

## 4. Estimator discrepancy (found this cycle; not a decision-changing defect)

The **code-level** rolling 63d Sharpe and the **report-level** rolling 63d Sharpe are computed with two different
formulas, and both are reproducible:

| Estimator | Formula | 444-day record (2026-10-09) | Current 449-day record |
|---|---|---|---|
| code-level gate value (`src/evaluation/utils.py:sharpe_ratio`) | (CAGR − 2% rf) / annualised vol | 0.670178 | **-0.493001** |
| report convention (`src/evaluation/drift.py:annualized_sharpe`) | mean(r) / std(r, ddof=1) · √252 | **0.9356** (the value documented in the artifacts) | **-0.211884** (= the stored drift flag) |

Evidence that the report convention is the one used by the artifacts: `research/drift_persistence_report.py`
reproduces the stored drift flag exactly (`stored == recomputed: True`, -0.21188351222842883) and its rolling series
reproduces the values quoted in the validation reports (0.9920, 0.9994, 0.4728, 0.1902, 0.9356, 0.4892, 0.3669,
0.1133, 0.3249, -0.2119).

Consequences:

- **The decision is unaffected.** Both estimators fail the ≥ 0.9 gate on the current record (-0.493 and -0.212), so
  the NO-GO holds under either convention.
- **The historical reading changes.** On the 444-day record the code-level estimator (0.670178) *fails* the gate
  while the documented report value (0.9356) *passes* it. The code-level gate is therefore the more conservative of
  the two, and the two conventions would have produced different verdicts on the same data.
- The gate value was **not** changed in this cycle: switching estimators mid-record would silently re-write the
  instrument's history (a monitoring instrument must not change its own measurement definition under the record it
  is monitoring). The discrepancy is instead documented in the gate table (`metric_definition`) and reported as a
  diagnostic (`rolling_sharpe_63d_report_convention`) next to the gate value, and it is the substance of the next task.

## 5. Tests added (`tests/test_go_no_go_evaluation.py`, 46 → 54 tests)

| Test | What it pins |
|---|---|
| `test_promotion_gate_table_matches_documented_gates` | the gate table still carries exactly the documented thresholds, sources, comparisons and metric definitions |
| `test_gate_evaluation_fails_closed_on_unknown_metric` | a typo in the gate table raises instead of silently defaulting to 0.0 |
| `test_psr_above_go_threshold_with_failing_rolling_sharpe_cannot_yield_go` | **a synthetic state whose PSR (0.9999999999999992) clears the GO threshold but whose rolling 63d Sharpe (0.1144) is below 0.9 cannot produce "GO"** — every other gate passes, so the verdict is driven purely by the rolling-Sharpe failure; the decision is NO-GO |
| `test_synthetic_state_passing_every_gate_yields_go` | the enforcement is not vacuous: a state that passes every gate **does** produce "GO" |
| `test_decision_never_go_when_any_single_gate_fails` | failing each of the 7 gates in turn never yields "GO"; all-passing yields "GO" |
| `test_insufficient_track_record_is_inconclusive_not_go` | a short record is INCONCLUSIVE, never GO |
| `test_only_psr_gate_failing_in_grey_zone_is_inconclusive_not_go` | the documented grey-zone branch behaves as specified |
| `test_committed_record_is_not_promoted` | regression guard for the false-promotion path: the committed record must not be labelled GO |

The pre-existing seeded-PSR determinism test (`test_psr_is_deterministic_for_the_committed_state`) still passes, and
the tool's own self-check now also compares the gate table, the PSR zone and the failed-gate list between the two
evaluations.

## 6. Verification (commands run in this cycle)

| Command | Result |
|---|---|
| `python -m pytest -q` | **54 passed** in 80.66s (46 pre-existing + 8 new) |
| `python research/go_no_go_evaluation.py` | exit 0 — `side_effect_free: True`, `evaluation_deterministic: True`, decision **NO-GO** |
| `python research/drift_persistence_report.py` | exit 0 — persistence 5 trading days (2026-10-12 → 2026-10-16), `stored == recomputed: True` |
| `python research/_tmp_cycle77_verify.py` | exit 0 — OVERALL: PASS (regime flips 6/6, NAV $133,729.22, max DD -4.9857%) |
| `python .github/scripts/test_kilo_supervisor_loop.py` | exit 0 — OK (10 tests) |
| SHA-256 over `data/processed` + `data/raw` (1832 files), before vs after | **identical** |

Note on the environment: the runner image had no Python dependencies installed (`numpy`, `pandas`, `pyyaml`, `pytest`,
`scipy`, `statsmodels`, `yfinance`, `pyarrow`, `arch` were all missing, which is why `python -m pytest -q` and
`python research/go_no_go_evaluation.py` aborted with `ModuleNotFoundError` before the install). The install is
environment-only and is **not** a repository change; `requirements.txt` already lists these packages and was not
modified.

## 7. What this cycle did not do

- No threshold value was changed (0.9 Sharpe target, 15% max DD, PSR 0.5/0.95 boundaries, 126-day minimum, 1 regime
  flip) — enforcement and documentation only.
- No strategy, config, cost-model or universe change; no live trading; no new dependency, service or schedule.
- No re-optimisation or re-selection of parameters against the current record.
- No extension of the paper-trading state: no completed session was available.
- The root cause of the 63-day underperformance and the PSR shortfall was **not** investigated: Cycle 860 is an
  enforcement cycle, and the task file explicitly forbids re-optimising against the current record. That
  investigation is the next task.

## 8. Handoff

- Decision: **NO-GO**. Promotion to live trading is **not** supported by the current record.
- Next task: reconcile the two Sharpe estimators (code-level vs report convention) so the gate value and the
  documented drift flag use one convention, then investigate the 63-day underperformance as a separate,
  evidence-based step — see `NEXT_AGENT_TASK.md` (Cycle 861).
