# Next Agent Task: Cycle 862 - Attribute the trailing-63-session underperformance and the PSR shortfall (read-only diagnosis, one settled Sharpe convention)

## Context

Cycle 861 closed the measurement-consistency defect that Cycle 860 found. The repository now uses **one**
documented Sharpe convention for every promotion-gate, drift-flag and PSR quantity:

| | |
|---|---|
| id | `arithmetic_annualized_rf0` |
| formula | `mean(r) * 252 / (std(r, ddof=1) * sqrt(252))`, zero risk-free rate |
| implementation | `src.evaluation.sharpe.sharpe_ratio` |
| declaration | `config/promotion_gates.yaml` → `sharpe_convention` (checked against the code; the evaluation fails closed on a mismatch) |
| applies to | gate `full_period_sharpe`, gate `rolling_63d_sharpe`, PSR numerator **and** PSR bootstrap distribution, drift flag `state.drift_flags.low_rolling_sharpe` |

The separate *backtest-baseline* scale (`src.evaluation.sharpe.backtest_sharpe_ratio`, CAGR-based, rf 2%) is
kept, named and confined to backtest research metrics, because the recorded backtest baseline 1.4178 and the
published backtest artifacts are on that scale.

Current state of the record (449 sessions through 2026-10-16), gate-complete and reproducible
(`evaluation_deterministic: True`):

| Gate | Value | Threshold | Result |
|---|---|---|---|
| `track_record_length` | 449 | ≥ 126 | PASS |
| `full_period_sharpe` | 1.748401 | ≥ 0.9 | PASS |
| `rolling_63d_sharpe` | **-0.211884** | ≥ 0.9 | **FAIL** |
| `max_drawdown` | -0.049857 | ≥ -0.15 | PASS |
| `rolling_63d_max_dd` | -0.038564 | ≥ -0.15 | PASS |
| `regime_flips` | 6 | ≥ 1 | PASS |
| `psr` | **0.684041** | ≥ 0.95 | **FAIL** (grey zone 0.5–0.95) |

**Decision: NO-GO. Live deployment remains unsupported.** The `low_rolling_sharpe` drift flag persists
(-0.21188351222842883, 5 consecutive sessions below 0.5, 2026-10-12 → 2026-10-16).

The full-period Sharpe (1.748401) passes comfortably while the trailing 63 sessions fail badly. **The reason
for that divergence has never been investigated** — Cycle 860 and Cycle 861 deliberately deferred it until the
measurement convention was settled, so that the analysis would not be run on two definitions of "rolling
Sharpe". That condition is now met, so the diagnosis is the next cycle.

Cycle 861 evidence: `research/reports/monitoring_cycle_861.md`; dated addenda in
`research/reports/go_no_go_evaluation_002.md`, `research/reports/deployment_dossier_001.md` and
`research/reports/paper_trading_validation_002.md`; `research/sharpe_convention_audit.py` (read-only audit that
reproduces every number from the committed state); `tests/test_go_no_go_evaluation.py` (61 tests).

## Objective

Establish, with numbers and from the committed data alone, **what made the trailing 63 sessions of the paper
record fail the promotion gate**, and state which mechanism dominates. This is a *diagnosis* cycle: it must
identify the cause of the observed -0.211884 trailing Sharpe and of the PSR shortfall, so that any later
decision (fix, re-fit or abandon) is made on evidence instead of on a number that moved because a definition
changed.

## Precondition checks (cheap, do them first)

1. Check whether a **completed** US session beyond 2026-10-16 is now available (raw parquet index max dates for
   SPY, QQQ, IWM, TLT, GLD, EFA, EEM, ^VIX; `python research/refresh_raw_cache.py --dry-run`; `python
   research/extend_paper_trading_state.py --dry-run`). If a completed session exists, extend the state **once**
   with the session-safe tools and run the diagnosis on the extended record; otherwise stay verification-only.
2. Record the state/raw SHA-256 set before and after the cycle; the committed artifacts must stay byte-identical
   unless the extension path legitimately appended a completed session.
3. Re-derive the current numbers with the settled convention (`python research/sharpe_convention_audit.py`) so
   the diagnosis is anchored on the same numbers the gate uses.

## Acceptance Criteria

1. **A decomposition that reconciles.** A report `research/reports/trailing_window_attribution_001.md` that
   decomposes the trailing-63-session return of the committed record into *gross signal return*, *cost drag*
   (turnover × the 3 bp committed cost model), *overlay effect* (vol-scale and drawdown-scale reductions) and
   *filter effect* (SPY-trend regime exposure), with an explicit residual. The decomposition must sum to the
   observed compounded return of the window to within a stated tolerance (≤ 1e-6 in return terms), and the
   residual must be explained, not left over.
2. **Per-asset attribution of the deterioration.** The 63-session window that ended 2026-10-16 compounded
   **-0.5175%** while the 63-session window that ended 2026-10-09 compounded **+1.7469%**; the difference is
   concentrated in the last five sessions (2026-10-12 → 2026-10-16, compounded **-2.6549%**, all with
   `regime_exposure = 1.0`, `dd_scale = 1.0`, `vol_scale` 0.63–0.65). The report must attribute those five
   sessions (and the full window) per asset and per mechanism, using a **scratch** copy of the state — the
   canonical `data/processed/paper_trading_state.yaml` must never be written.
3. **A stated dominant mechanism.** The report must say, with numbers, which of signal decay / filter timing /
   overlay scaling / cost drag dominates the window, and must state the **falsification condition**: what
   observation would refute that conclusion, and what would refute the alternative explanations.
4. **The connection to the PSR shortfall** must be stated: the PSR is 0.684041 because the trailing window
   dominates the bootstrap, or for another reason, with the numbers that support it (e.g. the PSR recomputed on
   the record truncated to 2026-10-09 is 0.762425, and the canonical trailing Sharpe of the two windows is
   0.935578 vs -0.211884).
5. **Read-only.** No change to the strategy, the universe, the cost model, the parameters, the promotion
   thresholds or the promotion-gate table; no change to the committed state, the raw cache or any committed
   artifact. A new read-only script (`research/trailing_window_attribution.py`) must reproduce every number in
   the report, and `python -m pytest -q` must still pass (61 tests at the end of Cycle 861).
6. **The report must not recommend a re-fit.** It may state what a follow-up experiment would have to show,
   but it must not tune parameters against the current record.

## Validation Commands

- `python -m pytest -q`
- `python research/go_no_go_evaluation.py` (must print `side_effect_free: True` and `evaluation_deterministic: True`)
- `python research/drift_persistence_report.py` (must report `stored == recomputed: True`)
- `python research/sharpe_convention_audit.py`
- `python research/trailing_window_attribution.py` (new; reproduces the report's numbers)
- `python research/_tmp_cycle77_verify.py`
- `python .github/scripts/test_kilo_supervisor_loop.py`
- `git status --porcelain data/` must be empty (byte-identical committed artifacts)

## Scope Boundaries

- **No threshold values may change** (0.9 Sharpe target, 15% max DD, PSR 0.5/0.95 boundaries, 126-day minimum,
  1 regime flip). No strategy, config, cost-model, universe or parameter changes. No live trading, no new
  dependencies, no schedule/workflow changes.
- **No re-optimisation and no re-selection against the current record.** This cycle measures and explains; it
  does not search.
- Do not change the drift-flag threshold (0.5) or its persistence definition.
- Do not restate the PSR target (1.4178) on the canonical scale in this cycle: that needs a backtest baseline
  re-run and is a separate measurement task (see "Out of scope").
- Any scratch state used for the per-asset attribution must live outside `data/processed` and must be deleted
  or left untracked; the committed state file must stay byte-identical.
- If a completed session is not available, the cycle must not fabricate one.

## Evidence to Carry Forward

- Current decision: **NO-GO** (gate-complete). `psr_normal` 0.684041 (grey zone), `psr_empirical` 0.741000,
  `sharpe_se` 0.690150, 95% CI [0.536027, 3.216373], bootstrap mean 1.877745. Gate values:
  `track_record_length` 449 (PASS), `full_period_sharpe` 1.748401 (PASS), `rolling_63d_sharpe` **-0.211884
  (FAIL)**, `max_drawdown` -0.049857 (PASS), `rolling_63d_max_dd` -0.038564 (PASS), `regime_flips` 6 (PASS),
  `psr` **0.684041 (FAIL)**. Drift flag `low_rolling_sharpe` = -0.21188351222842883, persistence 5 trading days
  (2026-10-12 → 2026-10-16), 21 of 33 sessions below threshold in the trailing 46 calendar days. Max DD
  -4.9857%. NAV $133,729.22.
- **The rolling 63d Sharpe series (canonical)** for the last sessions: 2026-10-05 0.9920, 2026-10-06 0.9994,
  2026-10-07 0.4728, 2026-10-08 0.1902, 2026-10-09 0.9356, 2026-10-12 0.4892, 2026-10-13 0.3669, 2026-10-14
  0.1133, 2026-10-15 0.3249, 2026-10-16 -0.2119. The window passed the gate (0.9356) up to 2026-10-09.
- **Window composition (from `run_history`, canonical convention):** trailing 63 sessions (2026-08-21 →
  2026-10-16) compounded **-0.5175%**, **0 risk-off sessions** (`regime_exposure = 1.0` throughout),
  `dd_scale = 1.0` throughout, mean `vol_scale` 0.5238 (min 0.4373), cumulative turnover 3.3102 → cost drag
  ≈ 0.0993% at 3 bp. The preceding 63 sessions (through 2026-10-09) compounded **+1.7469%** with the same
  zero-risk-off / no-drawdown-cut profile, mean `vol_scale` 0.5084, turnover 3.2969.
- **The last five sessions** (2026-10-12 → 2026-10-16): daily returns -0.3431%, -0.2272%, -1.1352%, +0.1383%,
  -1.1099% (compounded -2.6549%), all `regime_exposure = 1.0`, `dd_scale = 1.0`, `vol_scale` 0.6526 / 0.6517 /
  0.6461 / 0.6484 / 0.6313, turnover 0.0049 / 0.0009 / 0.0056 / 0.0023 / 0.0170.
  → the deterioration is **not** explained by the trend filter switching off or by the drawdown overlay cutting;
  the strategy was invested and lost money. The open question this cycle must answer is *which positions and
  which mechanism* produced the loss, and whether it is a signal failure, a regime-timing failure, an overlay
  failure or plain cost drag.
- 444-session record (through 2026-10-09) under the settled convention: `full_period_sharpe` 1.934100 (PASS),
  `rolling_63d_sharpe` 0.935578 (PASS), `psr` 0.762425 (FAIL, grey zone) → **INCONCLUSIVE**, still not
  promotable. The 449-session record is NO-GO.
- **Out of scope for this cycle (deliberate):** restating the PSR target 1.4178 on the canonical scale. It is a
  fixed external reference on the backtest-baseline scale; converting it needs the backtest return series (a
  backtest baseline re-run) and is a separate, bounded measurement task. The quantified effect of the
  mismatch is in `research/reports/monitoring_cycle_861.md` §3.3 (the PSR would be 0.625165 instead of 0.684041
  if the target carried the paper series' own scale offset) — it changes no verdict.
- Environment note: the runner image ships without the Python dependencies (`numpy`, `pandas`, `pyyaml`,
  `pytest`, `scipy`, `statsmodels`, `yfinance`, `pyarrow`, `arch`); install them before running the validation
  commands. `requirements.txt` already lists them and must not be modified.
