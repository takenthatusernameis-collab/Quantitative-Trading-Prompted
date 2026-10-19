# Next Agent Task: Refresh Go/No-Go Evaluation and Deployment Decision Against the Current Paper Record (Cycle 858)

## Context

Cycle 857 (2026-10-19) executed the assigned post-gate monitoring (no new completed US session; canonical cache still pinned at 2026-10-16) and then implemented the evidence-based follow-up: a deterministic `low_rolling_sharpe` persistence counter (`src/evaluation/drift.py`, `research/drift_persistence_report.py`, `tests/test_drift_persistence.py`). The tool reproduces the escalation report's independent finding exactly — persistence = **5 consecutive trading days** below the 0.5 threshold (2026-10-12 → 2026-10-16), 21 of 33 sessions below threshold in the trailing 46 calendar days, recomputed rolling 63d Sharpe -0.21188351222842883 == stored drift-flag value.

**The promotion record is now stale relative to the committed paper record:**

| Source | Record used | Stated verdict |
|---|---|---|
| `research/reports/go_nogo_evaluation_001.md:158` | 444 days, through 2026-10-09, rolling 63d Sharpe 0.9356 | **GO** for live deployment |
| `research/reports/deployment_dossier_001.md:6` and §8.3 | same | **GO** for live deployment / "PROCEED with live deployment" |
| `research/reports/paper_trading_validation_002.md` gate table | 444 days, through 2026-10-09 | "Rolling 63d Sharpe ≥ 0.9 → PASSED" |
| `evaluate_go_no_go(state, config)` on the **current** committed state (449 days, through 2026-10-16) | paper Sharpe 1.6380, ann. return 17.72%, ann. vol 9.59%, max DD -4.99%, PSR(normal) 0.6168, Sharpe SE 0.7413 | **INCONCLUSIVE** (PSR grey zone 0.5–0.95) |
| report-level rolling 63d Sharpe gate on the current state | -0.21188351222842883 | **FAILS** the ≥ 0.9 target |

No report records this transition, and the two go/no-go documents in the repository disagree with each other (`research/reports/go_no_go_evaluation_001.md` = INCONCLUSIVE on a 5-day record, 2026-10-12; `research/reports/go_nogo_evaluation_001.md` = GO on a 444-day record, 2026-10-14).

## Objective

Produce an offline, reproducible go/no-go re-evaluation of the **current** paper record and reconcile the two gate definitions (the code-level full-period PSR decision in `src/simulation/evaluation.py` vs the report-level rolling-63-day-Sharpe gate), so the stated deployment decision matches the data that is actually in the repository. No strategy, cost-model, universe or configuration change; research only, no live trading.

## Acceptance Criteria

1. `python -m pytest -q` passes (42 tests: 27 pre-existing + 15 drift-persistence).
2. A new read-only, offline script (e.g. `research/go_no_go_evaluation.py`) regenerates the evaluation from `data/processed/paper_trading_state.yaml` and prints: track-record length, paper Sharpe, annualized return/volatility, Sortino, profit factor, max DD, trade count, annualized turnover, PSR (normal + empirical), Sharpe SE and 95% CI, regime flips/persistence, drift flags, and the decision from `evaluate_go_no_go(state, config)`.
3. The script is proven side-effect free: `data/processed/paper_trading_state.yaml` and `data/raw/*.parquet` are byte-identical (sha256) before and after the run; a test asserts this.
4. A dated report (e.g. `research/reports/go_no_go_evaluation_002.md`) states, with numbers computed from the state file:
   - the code-level decision and the report-level rolling 63d Sharpe gate, side by side;
   - an explicit decision label (GO / INCONCLUSIVE / NO-GO) and the conditions for re-evaluation;
   - why the earlier "GO for live deployment" statement no longer holds, or why it still holds.
5. `research/reports/deployment_dossier_001.md` and `research/reports/go_nogo_evaluation_001.md` are reconciled with the new verdict (append a dated addendum or amend the decision line). No unqualified "GO for live deployment" claim may remain that is contradicted by the current record.
6. `python research/drift_persistence_report.py` still reports persistence 5 trading days and `stored == recomputed: True`; `python research/_tmp_cycle77_verify.py` prints OVERALL: PASS; `python .github/scripts/test_kilo_supervisor_loop.py` prints OK.
7. `.kilo-runtime/worker-disposition.json` updated (verified).

## Precondition (data freshness)

If a **completed** US session is available when you start (the 2026-10-19 session closes 20:00Z), run these **once**, in order, before the evaluation, and record the resulting `last_run_date` in the report:

```
python research/refresh_raw_cache.py
python research/extend_paper_trading_state.py
```

The go/no-go numbers must be computed from the state as it stands after that step (450 sessions instead of 449). If no completed session is available, proceed with the 449-session state and say so explicitly.

## Validation Commands

- python -m pytest -q
- python research/go_no_go_evaluation.py
- python research/drift_persistence_report.py
- python research/_tmp_cycle77_verify.py
- python .github/scripts/test_kilo_supervisor_loop.py

## Scope Boundaries

- Offline evaluation only: no strategy parameter, cost model, universe, or `config/*.yaml` threshold may be changed — the purpose is to measure the current record against the *existing* gates.
- No data refresh, no state extension beyond the single session allowed in the precondition, no live trading, no account/credential access.
- Do not re-optimize the strategy because of the rolling-window degradation; the degradation is already documented as sampling variation in `research/reports/drift_flag_escalation_001.md` §4–5. This task is about the *decision record*, not about re-tuning.
- Keep the reporting path deterministic: the same state file must always produce the same numbers.

## Evidence to Carry Forward

- `python -c` on the current state (Cycle 857): `evaluate_go_no_go` → decision `INCONCLUSIVE`, `psr_normal 0.6167938439140701`, `paper_sharpe 1.6380093192847855`, `paper_max_dd -0.04985740111232129`, `paper_days 449`, `drift_flags_count 1` (the `low_rolling_sharpe` flag).
- `research/drift_persistence_report.py` → persistence 5 trading days; first flagged session 2025-02-27; 109 of 430 evaluated sessions below threshold over the full history.
