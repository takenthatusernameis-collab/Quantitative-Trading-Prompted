# Next Agent Task: Cycle 861 - Adopt ONE documented Sharpe convention across the promotion gates, the drift flag and the PSR bootstrap

## Context

Cycle 860 closed the false-promotion path: `evaluate_go_no_go` now evaluates **every** gate defined in
`config/promotion_gates.yaml` and returns "GO" only if all of them pass, so a failing gate can never yield "GO".
The decision for the current 449-session record (through 2026-10-16) is now **NO-GO** (previously INCONCLUSIVE in
Cycles 858/859); no gate value changed, the decision moved because the documented gates are now enforced.

While doing that, Cycle 860 found and documented a **measurement-consistency defect** that it deliberately did not
fix (fixing it mid-record would rewrite the history of a monitoring instrument). Three different Sharpe estimators
are in simultaneous use in this repository:

| # | Estimator | Formula | Where it is used |
|---|---|---|---|
| 1 | `src/evaluation/utils.py:sharpe_ratio` | (CAGR − 2% rf) / ann_vol | `paper_sharpe` (promotion gate `full_period_sharpe`), the **PSR numerator** `sr_obs` in `compute_psr`, and the backtest baseline 1.4178 (`src/backtest/engine.py:compute_metrics` uses the same geometric definition) |
| 2 | `src/evaluation/drift.py:annualized_sharpe` | mean(r)·252 / (std(r, ddof=1)·√252), rf = 0 | the stored `low_rolling_sharpe` drift flag, `research/drift_persistence_report.py`, and every "Rolling 63d Sharpe" number quoted in the validation artifacts |
| 3 | `src/evaluation/statistics.py:_safe_sharpe` | (mean(r) − rf_daily)·252 / (std(r, ddof=1)·√252) | the **moving-block bootstrap distribution** and therefore the PSR standard error |

Consequences, all reproducible on the committed state:

- The **promotion gate value** for `rolling_63d_sharpe` is **-0.493001** (estimator 1) while the **report-level**
  value — the one in `paper_trading_validation_002.md`, in the drift flag and in every monitoring report — is
  **-0.211884** (estimator 2). On the 444-day record (through 2026-10-09) the same window is **0.670178** (estimator 1,
  gate FAIL) versus the documented **0.9356** (estimator 2, gate PASS): the two conventions disagree on the *verdict*
  for the same data.
- The **PSR mixes estimators**: the numerator `sr_obs` uses estimator 1 (geometric, rf 2%) while the SE comes from
  the estimator-3 bootstrap distribution. On the current record: PSR = **0.625683** as computed today, **0.570557**
  with an estimator-3 numerator, **0.684770** with an arithmetic rf=0 numerator. All three are inside the grey zone
  [0.5, 0.95), so the current NO-GO does not change — but the reported PSR is not an apples-to-apples number.

Cycle 860 evidence: `research/reports/monitoring_cycle_860.md`; dated addenda in
`research/reports/go_no_go_evaluation_002.md` and `research/reports/deployment_dossier_001.md`;
`tests/test_go_no_go_evaluation.py` (54 tests).

## Objective

Make the repository use **one documented Sharpe convention** for every promotion-gate, drift-flag and PSR quantity,
so that a gate value, the stored drift flag and the validation artifacts can be compared directly, and so that the PSR
numerator and the bootstrap distribution measure the same statistic. The convention must be **chosen and documented**,
not tuned: the task is measurement consistency, not re-tuning, and the promotion thresholds (0.9, 15%, 0.5/0.95,
126 days, 1 flip) must not change.

## Precondition checks (do these first, they are cheap)

1. Check whether a **completed** US session beyond 2026-10-16 is now available:
   - raw parquet index max dates for SPY, QQQ, IWM, TLT, GLD, EFA, EEM, ^VIX;
   - `python research/refresh_raw_cache.py --dry-run` and `python research/extend_paper_trading_state.py --dry-run`.
   - If a completed session exists, extend the state **once** with the session-safe tools and re-run the evaluation
     against the extended record. If not, stay in verification-only mode.
2. Record the state/raw SHA-256 set before and after the cycle; the committed artifacts must stay byte-identical
   unless the extension path legitimately appended a completed session.
3. Re-derive the three estimator values for **both** the 444-day record (through 2026-10-09) and the current
   449-day record, so the historical verdict impact of the convention choice is on the table before it is made.

## Acceptance Criteria

1. **One documented convention, used everywhere.** A short "Sharpe conventions" section (in
   `config/promotion_gates.yaml` and/or `src/evaluation/utils.py`) names the single convention that the promotion
   gates, the drift flag and the PSR use, and states why. The code must then actually use it — no estimator may be
   left in a gate path that is not the documented one.
2. **The drift flag and the gate agree.** After the change, the rolling 63d Sharpe computed for the promotion gate
   must equal the value stored in `state.drift_flags.low_rolling_sharpe` for the committed record
   (-0.21188351222842883) and must reproduce the series quoted in the validation artifacts
   (…, 0.4892, 0.3669, 0.1133, 0.3249, -0.2119 for 2026-10-12 → 2026-10-16). `research/drift_persistence_report.py`
   must still report `stored == recomputed: True`.
3. **The PSR measures one statistic.** The PSR numerator and the bootstrap distribution must use the same estimator
   (either both geometric, matching the backtest baseline 1.4178, or both arithmetic). The change must be applied
   without re-tuning: keep the seeded bootstrap (`psr_seed = 20240101`) and the same block size.
4. **Historical verdicts are re-verified, not silently rewritten.** The report must state, with numbers, what the
   convention change does to (a) the current 449-day decision, (b) the 444-day record's `rolling_63d_sharpe` gate
   outcome (0.670178 FAIL vs 0.9356 PASS today) and (c) the PSR value. If the convention change flips any historical
   promotion verdict, that must be called out explicitly in `research/reports/go_no_go_evaluation_002.md` and
   `research/reports/deployment_dossier_001.md` — including the statement of whether live deployment remains
   unsupported (it does today: decision **NO-GO**, gates `rolling_63d_sharpe` and `psr` failing).
5. **The gate table stays gate-complete.** `config/promotion_gates.yaml` keeps exactly the documented thresholds and
   all seven gates; `tests/test_go_no_go_evaluation.py` keeps passing (54 tests at the end of Cycle 860) and gains
   at least one test that pins the chosen convention (e.g. the gate value equals the stored drift flag value) and one
   that the PSR numerator and the bootstrap distribution share an estimator.
6. **All validation commands pass** and the committed state/raw artifacts remain byte-identical (unless the
   extension path legitimately appended a completed session).

## Validation Commands

- `python -m pytest -q`
- `python research/go_no_go_evaluation.py` (must print `side_effect_free: True` and `evaluation_deterministic: True`)
- `python research/drift_persistence_report.py` (must report `stored == recomputed: True`)
- `python research/_tmp_cycle77_verify.py`
- `python .github/scripts/test_kilo_supervisor_loop.py`

## Scope Boundaries

- **No threshold values may change** (0.9 Sharpe target, 15% max DD, PSR 0.5/0.95 boundaries, 126-day minimum,
  1 regime flip). No strategy, config, cost-model or universe changes. No live trading, no new dependencies, no
  schedule/workflow changes.
- **Do not re-optimise or re-select parameters against the current record.** The evaluation is a monitoring
  instrument; this task changes how a number is *defined*, not what the strategy does.
- Do not "fix" the drift by changing the drift threshold; the drift flag threshold (0.5) and its persistence
  definition are unchanged.
- If a convention change would flip a historical promotion verdict, report it — do not quietly adopt the convention
  that produces the prettier history.
- Preserve byte identity of committed artifacts unless the session-safe extension path legitimately appends a
  completed session. If a completed session is not available, the cycle must not fabricate one.

## Evidence to Carry Forward

- Current decision: **NO-GO** (gate-complete). `psr_normal` 0.625683 (grey zone), `psr_empirical` 0.654000,
  `sharpe_se` 0.687208, 95% CI [0.344994, 2.998531]; gate values: `track_record_length` 449 (PASS),
  `full_period_sharpe` 1.638009 (PASS), `rolling_63d_sharpe` **-0.493001 (FAIL)**, `max_drawdown` -0.049857 (PASS),
  `rolling_63d_max_dd` -0.038564 (PASS), `regime_flips` 6 (PASS), `psr` **0.625683 (FAIL)**.
  Drift flag `low_rolling_sharpe` = -0.21188351222842883, persistence 5 trading days (2026-10-12 → 2026-10-16),
  21 of 33 sessions below threshold in the trailing 46 calendar days. Max DD -4.9857%. NAV $133,729.22.
- Estimator values measured in Cycle 860 (reproduce them before changing anything):
  - 449-day record: estimator 1 = **-0.493001**, estimator 2 = **-0.211884** (= stored drift flag), estimator 3
    numerator-equivalent arithmetic rf=2% = 1.539981, arithmetic rf=0 = 1.748401, bootstrap mean 1.667394,
    bootstrap SE 0.687208 → PSR 0.625683 (today) / 0.570557 (arithmetic rf=2%) / 0.684770 (arithmetic rf=0).
  - 444-day record (through 2026-10-09): estimator 1 = **0.670178** (gate FAIL), estimator 2 = **0.9356**
    (documented PASS) — the two conventions disagree on the verdict.
- The NO-GO does **not** depend on the convention: both estimators fail the ≥ 0.9 gate on the current record, and all
  three PSR variants stay inside the grey zone.
- **Not yet done (deliberately, and the reason this task exists):** the root cause of the 63-day underperformance and
  the PSR shortfall has not been investigated. That investigation must be a separate cycle, and it should start only
  after the measurement convention is settled — otherwise the analysis would be run on two different definitions of
  "rolling Sharpe". Do not fold it into this task.
- Environment note: the runner image ships without the Python dependencies (`numpy`, `pandas`, `pyyaml`, `pytest`,
  `scipy`, `statsmodels`, `yfinance`, `pyarrow`, `arch`); install them before running the validation commands.
  `requirements.txt` already lists them and must not be modified.
