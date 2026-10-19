# Next Agent Task: Cycle 863 — Quantify the mechanical roll-off of the 63-session window (read-only projection, no forecast)

## Context

Cycle 862 attributed the trailing-63-session failure and the PSR shortfall from the committed
record alone (`research/reports/trailing_window_attribution_001.md`,
`research/experiments/trailing_window_attribution_001.md`,
`research/trailing_window_attribution.py`). The record is unchanged: 449 sessions through
2026-10-16, gate-complete, decision **NO-GO** (`evaluation_deterministic: True`).

What Cycle 862 established, with numbers:

| Window | gross signal return (unscaled) | vol overlay | filter | drawdown overlay | cost | observed net | canonical 63d Sharpe |
|---|---|---|---|---|---|---|---|
| trailing 63 (2026-07-21 → 2026-10-16) | **+1.078731%** | **-1.497444%** | 0.000000% | 0.000000% | -0.098798% | **-0.517510%** | **-0.211884** |
| previous 63 (2026-07-14 → 2026-10-09) | +4.393818% | -2.546287% | 0.000000% | 0.000000% | -0.100635% | +1.746896% | +0.935578 |
| tail 5 (2026-10-12 → 2026-10-16) | **-4.120856%** | +1.466867% | 0.000000% | 0.000000% | -0.000903% | **-2.654892%** | — |

- The trailing-window shortfall is dominated by the **volatility-targeting overlay** (pro-cyclical
  with a lag: it de-risked the sessions where the signal was making money — signal sum
  +6.625738% on the low-`vol_scale` half of the window, -5.244338% on the high half), against a
  *positive* raw signal (+1.078731%). The filter, the drawdown overlay and the gross-exposure cap
  contributed exactly 0.000000% each; cost drag was -0.098798% (window) and -0.000903% (tail).
- The window-to-window deterioration is a **signal failure** in the five sessions that entered the
  window: -4.120856% unscaled, cushioned to -2.654892% by the overlay. Two sessions
  (2026-10-14, 2026-10-16) carry 84.2% of it, in the four assets the momentum signal held
  (SPY, QQQ, IWM, EEM).
- The **PSR shortfall is not** caused by the trailing window: the five new sessions are 1.11% of the
  record, the bootstrap SE *fell* (0.722984 → 0.690150), and the PSR change of -0.078384 is 110%
  numerator-driven (observed Sharpe 1.934100 → 1.748401). At SE 0.690150 the record would need an
  observed Sharpe of **2.552996** (or an SE of **0.200991**) to reach PSR 0.95; the PSR gate was
  already failing before the tail (0.762425 < 0.95).

**The question this cycle answers**: the 63-session window is a *rolling* measurement, and the five
crash sessions will mechanically leave it after 63 further sessions. What does the gate table look
like on the way out, and what would actually have to happen for the record to be promotable again?
Without this, a future agent risks reading a mechanical window effect as a recovery — or reading a
still-failing gate as a strategy failure.

## Precondition checks (cheap, do them first)

1. Check whether a **completed** US session beyond 2026-10-16 is now available
   (`research/refresh_raw_cache.py --dry-run`, `research/extend_paper_trading_state.py --dry-run`,
   raw parquet index max dates). If a completed session exists, extend the state **once** with the
   session-safe tools and run the projection on the extended record; otherwise stay verification-only
   and project from the 449-session record.
2. Record the state/raw SHA-256 set before and after the cycle; committed artifacts must stay
   byte-identical unless the extension path legitimately appended a completed session.
3. Re-derive the current numbers with the settled convention
   (`python research/sharpe_convention_audit.py`, `python research/trailing_window_attribution.py`)
   so the projection is anchored on the same numbers the gate uses.

## Objective

Produce a **read-only, deterministic projection** of the `rolling_63d_sharpe` gate as the window
rolls forward over the next 63 sessions, under explicitly stated continuation assumptions, together
with the *requirement* (not a forecast) that has to be met at every projected window. The output must
make it impossible to confuse a mechanical window effect with a performance recovery.

## Acceptance Criteria

1. **A projection script.** New read-only `research/rolling_63d_rolloff_projection.py` that, from the
   committed record alone, prints:
   - the canonical rolling 63d Sharpe series for the record (and the sessions currently in the window
     with the date each one leaves the window);
   - a projected rolling 63d Sharpe path for the next 63 sessions under **at least two** clearly
     labelled continuation assumptions — (a) *flat*: every future session earns exactly 0.00%
     net of cost, and (b) *record-average*: every future session earns the arithmetic mean daily net
     return of the committed record (0.00066578, i.e. +16.77% annualised);
   - for every projected window: the realised window mean, the window dispersion, the resulting
     canonical Sharpe, the gate verdict, and the **mean daily net return required** for that
     window to reach Sharpe 0.9 at its own dispersion;
   - the first session on which the projected `rolling_63d_sharpe` would be ≥ 0.9 under each
     assumption, or an explicit statement that it never is within the 63-session horizon.
2. **A report** `research/reports/rolling_63d_rolloff_001.md` containing those numbers, the
   interpretation, and an explicit **interpretation guard**: the projection is a conditional
   calculation on the committed record, not a forecast, and it must not be presented as evidence
   that the strategy has recovered. The report must state what the projection *does* and *does not*
   establish.
3. **A statement on the PSR gate's reachability**, using the Cycle 862 numbers: at the current SE
   (0.690150) the observed Sharpe would have to reach 2.552996, or the SE 0.200991. If an
   approximate scaling of the block-bootstrap SE with record length is used (state the assumption
   explicitly and label it an approximation), state the approximate record length at which PSR 0.95
   could be reached at the *unchanged* observed Sharpe — and say plainly that the alternative route
   (a higher observed Sharpe) is the only one the strategy controls.
4. **Read-only.** No change to the strategy, the universe, the cost model, the parameters, the
   promotion thresholds or the promotion-gate table; no change to the committed state, the raw cache
   or any committed artifact. `python -m pytest -q` must still pass (61 tests at the end of Cycle 862)
   and `git status --porcelain data/` must be empty.
5. **No forecast and no re-fit.** The cycle must not project market returns from a model, must not
   tune anything against the current record, and must not restate the promotion decision: the current
   decision stays **NO-GO** and the drift flag `low_rolling_sharpe` (-0.21188351222842883, 5
   consecutive trading days below 0.5, 2026-10-12 → 2026-10-16) is unchanged. If a completed
   session becomes available, the *realised* record must be reported alongside the projection, never
   merged into it.

## Validation Commands

- `python -m pytest -q`
- `python research/go_no_go_evaluation.py` (must print `side_effect_free: True` and `evaluation_deterministic: True`)
- `python research/drift_persistence_report.py` (must report `stored == recomputed: True`)
- `python research/sharpe_convention_audit.py`
- `python research/trailing_window_attribution.py` (Cycle 862 script; must still print `OVERALL: PASS`)
- `python research/rolling_63d_rolloff_projection.py` (new; reproduces the report's numbers)
- `python research/_tmp_cycle77_verify.py`
- `python .github/scripts/test_kilo_supervisor_loop.py`
- `git status --porcelain data/` must be empty (byte-identical committed artifacts)

## Scope Boundaries

- **No threshold values may change** (0.9 Sharpe target, 15% max DD, PSR 0.5/0.95 boundaries, 126-day
  minimum, 1 regime flip). No strategy, config, cost-model, universe or parameter changes. No live
  trading, no new dependencies, no schedule/workflow changes.
- **No re-optimisation and no re-selection against the current record.** This cycle projects and
  quantifies requirements; it does not search.
- **No fabricated market data.** The flat and record-average continuations are assumptions, must be
  labelled as such in the script output and in the report, and must never be stored in the state file
  or in `data/`.
- Do not change the drift-flag threshold (0.5) or its persistence definition.
- Do not restate the PSR target (1.4178) on the canonical scale: that needs a backtest baseline re-run
  and remains a separate measurement task.
- The projection must not be used to justify any deployment action; live deployment remains
  unsupported while any gate fails.

## Evidence to Carry Forward

- Current decision: **NO-GO** (gate-complete). `psr_normal` 0.684041 (grey zone), `psr_empirical`
  0.741000, `sharpe_se` 0.690150, 95% CI [0.536027, 3.216373], bootstrap mean 1.877745. Gate values:
  `track_record_length` 449 (PASS), `full_period_sharpe` 1.748401 (PASS), `rolling_63d_sharpe`
  **-0.211884 (FAIL)**, `max_drawdown` -0.049857 (PASS), `rolling_63d_max_dd` -0.038564 (PASS),
  `regime_flips` 6 (PASS), `psr` **0.684041 (FAIL)**. Drift flag `low_rolling_sharpe` =
  -0.21188351222842883, persistence 5 trading days (2026-10-12 → 2026-10-16). Max DD -4.9857%.
  NAV $133,729.22.
- **The rolling 63d Sharpe series (canonical)** for the last sessions: 2026-10-05 0.9920, 2026-10-06
  0.9994, 2026-10-07 0.4728, 2026-10-08 0.1902, 2026-10-09 0.9356, 2026-10-12 0.4892, 2026-10-13
  0.3669, 2026-10-14 0.1133, 2026-10-15 0.3249, 2026-10-16 -0.2119. The window passed the gate
  (0.9356) up to 2026-10-09.
- **Window composition (canonical convention)**: the trailing 63 sessions are **2026-07-21 →
  2026-10-16** and compounded **-0.5175%**; 0 risk-off sessions, `dd_scale = 1.0` throughout, mean
  `vol_scale` 0.5238 (min 0.4373), cumulative turnover 3.3102 → cost drag ≈ 0.0993% at 3 bp. The
  preceding 63 sessions (**2026-07-14 → 2026-10-09**) compounded **+1.7469%** with the same
  zero-risk-off / no-drawdown-cut profile, mean `vol_scale` 0.5084, turnover 3.2969. (Cycle 861's
  handoff labelled the trailing window "2026-08-21 → 2026-10-16"; that range holds only 40
  sessions — Cycle 862 resolved the label, the -0.5175% figure was the 63-session number.)
- **Cycle 862 attribution (read-only, `research/reports/trailing_window_attribution_001.md`)**:
  trailing 63 = signal +1.078731% + filter 0.000000% + vol overlay -1.497444% + drawdown overlay
  0.000000% + cap 0.000000% + cost -0.098798% = observed -0.517510% (residual 0.000e+00). Tail 5 =
  signal -4.120856% + overlay +1.466867% + cost -0.000903% = -2.654892%. Per asset over the trailing
  63 (session-summed, bp): IWM -117.40, GLD +99.26, EEM -39.09, QQQ +16.37, SPY +11.13, EFA -13.81,
  TLT 0.00; total -43.56 bp = the window's arithmetic sum. Tail 5: EEM -97.38, QQQ -90.10, IWM -48.71,
  SPY -31.50; total -267.69 bp.
- **Overlay mechanics**: trailing 63 corr(`vol_scale`, signal return) -0.2197, mean/median
  `vol_scale` 0.5238/0.4661, implied realised vol of the raw signal portfolio 19.50% annualised;
  previous 63: -0.1007, 0.5084/0.4642, 20.02%; tail 5: +0.6799, 0.6460/0.6484, 15.48%.
- **Sharpe level**: trailing 63 mean -0.6914 bp/day (-1.7424% annualised), std 51.8011 bp/day
  (8.2232% annualised), Sharpe -0.211884; mean required for Sharpe 0.9 at that dispersion
  +2.9368 bp/day (+7.4009% annualised) → gap -9.1432 pp annualised. Previous 63: mean +2.8656 bp/day,
  std 48.6225 bp/day, Sharpe 0.935578; gap +0.2746 pp annualised.
- **PSR reachability**: at SE 0.690150 the observed Sharpe must be ≥ 2.552996 for PSR 0.95; at the
  observed 1.748401 the SE must be ≤ 0.200991.
- **Precondition (2026-10-19T16:42Z)**: no completed US session beyond 2026-10-16
  (`refresh_raw_cache.py --dry-run` no-op for all 8 symbols; `extend_paper_trading_state.py --dry-run`
  "no new completed session", 0 sessions extended, 0 state writes; raw cache pinned at 2026-10-16:
  SPY 8487, QQQ 6945, IWM 6637, TLT 6094, GLD 5512, EFA 6322, EEM 5916 rows; ^VIX 451).
- Environment note: the runner image ships without the Python dependencies (`numpy`, `pandas`,
  `pyyaml`, `pytest`, `scipy`, `statsmodels`, `yfinance`, `pyarrow`, `arch`); install them before
  running the validation commands. `requirements.txt` already lists them and must not be modified.
