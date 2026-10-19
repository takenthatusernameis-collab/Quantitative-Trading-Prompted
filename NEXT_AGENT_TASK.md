# Next Agent Task: Cycle 860 - Enforce the Documented Promotion Gates in the Code-Level Go/No-Go Decision

## Context

Cycle 859 was a verification-only post-gate monitoring tick (no completed US session beyond 2026-10-16) that also fixed
two reproducibility defects:

- `python research/go_no_go_evaluation.py` — the command listed in the Cycle 859 acceptance criteria — crashed with
  `ModuleNotFoundError: No module named 'src'`; the script lacked the repository-root `sys.path` bootstrap that every
  sibling research script already has. Fixed.
- `evaluate_go_no_go` ran the PSR block bootstrap **unseeded**, so the same committed state produced different gate
  numbers on every run (0.621679 recorded in Cycle 858 vs 0.627490 on re-run). The bootstrap is now seeded
  (`GoNoGoConfig.psr_seed`, default `20240101`); no threshold, gate, strategy parameter, cost model or universe was
  changed.

Current record (unchanged, 449 sessions through 2026-10-16): decision **INCONCLUSIVE**; `psr_normal` **0.625683**
(grey zone 0.5–0.95); rolling 63d Sharpe **-0.493001** → the report-level gate (≥ 0.9) **FAILS**; max DD -4.9857%
(passes); 1 drift flag (`low_rolling_sharpe` = -0.21188351222842883, 5 consecutive trading days 2026-10-12 → 2026-10-16).

The unresolved defect this task addresses: **the code-level decision function does not enforce the promotion gates that
the repository's own validation artifacts state.** The gate table in `research/reports/paper_trading_validation_002.md`
lists Track Record ≥ 126 days, full-period net-of-cost Sharpe ≥ 0.9, **rolling 63d Sharpe ≥ 0.9**, max DD ≤ 15%,
rolling 63d max DD ≤ 15%, and ≥ 1 regime flip. `evaluate_go_no_go` instead checks `min_days = 63`, a PSR test against
the backtest Sharpe (1.4178), full-period max DD, and *regime persistence* (days in the current regime) — the rolling
63d Sharpe gate is not evaluated at all, and the day-count/regime-flip gates differ. Consequently a record with
PSR > 0.95 but a negative rolling 63d Sharpe would still be labelled **"GO"** by the code. That is exactly the
mechanism behind the earlier unqualified "GO for live deployment" claims in `research/reports/deployment_dossier_001.md`
(reconciled in Cycle 858), so the defect can silently re-open the same false-promotion path.

## Objective

Make the code-level go/no-go decision **gate-complete and conservative**: `evaluate_go_no_go` must evaluate every
promotion gate documented in the repository's validation artifacts and must never return "GO" when any of them fails.
Thresholds must not be changed — only their *enforcement* is added, and the enforcement rule must be documented.

## Precondition checks (do these first, they are cheap)

1. Check whether a **completed** US session beyond 2026-10-16 is now available:
   - raw parquet index max dates for SPY, QQQ, IWM, TLT, GLD, EFA, EEM, ^VIX;
   - `python research/refresh_raw_cache.py --dry-run` and `python research/extend_paper_trading_state.py --dry-run`.
   - If a completed session exists, extend the state **once** with the session-safe tools
     (`python research/refresh_raw_cache.py`, then `python research/extend_paper_trading_state.py`) and re-run the
     evaluation against the extended record. If not, stay in verification-only mode.
2. Record the state/raw SHA-256 set before and after the cycle; the committed artifacts must stay byte-identical
   unless the extension path legitimately appended a completed session.

## Acceptance Criteria

1. **Machine-readable gate definition.** The promotion gates live in exactly one place (e.g. a new
   `config/promotion_gates.yaml`, or an explicit section of the go/no-go configuration) with, for each gate: name,
   metric, threshold, comparison direction, and the source artifact it comes from. The gate list must cover the table in
   `research/reports/paper_trading_validation_002.md` (track record length, full-period net-of-cost Sharpe, rolling 63d
   Sharpe, max DD, rolling 63d max DD, regime flips) in addition to the PSR criterion.
2. **Enforcement in code.** `evaluate_go_no_go` evaluates every gate in that definition and returns **"GO" only if all
   gates pass**. A failing gate can never yield "GO". The result object must expose the per-gate evaluation
   (name, value, threshold, pass/fail) so the tool prints the full gate table.
3. **Conservative default for failures.** For any gate that fails while the PSR sits in the grey zone, the decision must
   not be "GO". State and justify the mapping (fail → NO-GO vs INCONCLUSIVE) in the report, and make it explicit in the
   code. Do not silently keep the previous behaviour.
4. **Tests.** Add unit tests proving, at minimum:
   - a synthetic state whose PSR exceeds the GO threshold but whose rolling 63d Sharpe is below 0.9 **cannot** produce
     "GO";
   - a synthetic state that passes every gate **does** produce "GO";
   - the seeded PSR determinism check still holds.
5. **Reconciliation of the current record.** Re-run `python research/go_no_go_evaluation.py`, record the new decision and
   the full gate table for the current 449-session record, and add a **dated subsection** to
   `research/reports/go_no_go_evaluation_002.md` (do not rewrite the Cycle 858 reconciliation) and to
   `research/reports/deployment_dossier_001.md` if the decision changes. If the decision changes, state plainly whether
   live deployment remains unsupported.
6. **All validation commands pass**, and the committed state/raw artifacts remain byte-identical (unless the
   extension path legitimately appended a completed session).

## Validation Commands

- `python -m pytest -q`
- `python research/drift_persistence_report.py`
- `python research/_tmp_cycle77_verify.py`
- `python .github/scripts/test_kilo_supervisor_loop.py`
- `python research/go_no_go_evaluation.py` (must print `side_effect_free: True` and `evaluation_deterministic: True`)

## Scope Boundaries

- **No threshold values may change** (0.9 Sharpe target, 15% max DD, PSR 0.5/0.95 boundaries, day counts are inputs —
  do not edit them). The task is enforcement and documentation, not re-tuning.
- No strategy, config, cost model, or universe changes. No live trading, no new dependencies, no schedule/workflow
  changes.
- Do not re-optimise or re-select parameters against the current record; the evaluation is a monitoring instrument.
- Preserve byte identity of committed artifacts unless the session-safe extension path legitimately appends a completed
  session.
- Keep the monitoring discipline: if a completed session is not available, the cycle must not fabricate one.

## Evidence to Carry Forward

- Current decision: **INCONCLUSIVE** (PSR 0.625683, grey zone), rolling 63d Sharpe -0.493001 (FAILS ≥ 0.9),
  drift persistence 5 trading days (2026-10-12 → 2026-10-16), max DD -4.9857%, 1 drift flag.
- Cycle 859 evidence: `research/reports/monitoring_cycle_859.md`; dated addendum in
  `research/reports/go_no_go_evaluation_002.md`; new tests in `tests/test_go_no_go_evaluation.py` (46 tests pass).
- Session-safe tools (complete-session guards, scratch downloads, single state write):
  `research/refresh_raw_cache.py`, `research/extend_paper_trading_state.py`.
- Known gap to close: the code-level decision ignores the report-level rolling-63d-Sharpe gate and the other gates in
  the `paper_trading_validation_002.md` table, so a "GO" can currently be produced while a documented promotion gate
  fails.
