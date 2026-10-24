# State Aggregate Integrity Audit — Cycle 870

**Generated:** 2026-10-24T21:40Z (17:40 ET, Saturday)
**Tool:** `research/audit_state_aggregates.py`
**Tests:** `tests/test_state_aggregate_audit.py` (7 new tests)

## Scope

Prior corrective cycles verified only two state properties:

1. The `low_rolling_sharpe` drift flag (`research/drift_persistence_report.py`,
   `tests/test_drift_persistence.py`).
2. The extension clock gate (`research/extend_paper_trading_state.py`,
   `tests/test_paper_trading_extend.py`).

The remaining eleven stored aggregate fields were never independently
recomputed from the per-session record. This audit closes that gap.

## Method

Recomputes every stored aggregate in `data/processed/paper_trading_state.yaml`
solely from `run_history`, using the exact update formulas in
`src/simulation/paper_trading.run_daily_paper_update`:

| Field | Formula (from run_history) |
|---|---|
| `rolling_sharpe_63d` | `sharpe_ratio(last 63 daily_returns)` (canonical convention) |
| `rolling_max_dd_63d` | `min(cumprod(1+r) / maximum.accumulate(cumprod(1+r)) - 1)` |
| `regime_persistence_days` | trailing count of identical `regime_exposure` |
| `vol_scale_min/max` | `min/max` of `vol_scale` over all sessions |
| `dd_scale_min/max` | `min/max` of `dd_scale` over all sessions |
| `turnover_median/p95` | `median/percentile(95)` of `turnover` over all sessions |
| `peak_nav` | `max(nav)` over the NAV series |
| `max_drawdown` | running-max drawdown over the NAV series |

`run_history[].nav` is converted to daily returns via
`ret[0] = nav[0]/100000 - 1`, `ret[i] = nav[i]/nav[i-1] - 1`.

## Result

```
state sessions: 454  date_range: 2025-01-02 -> 2026-10-23
aggregate fields audited: 11
all_match: True
OK: every stored aggregate matches its recomputation from run_history
```

All 11 aggregates match to within float tolerance. No drift between the
per-session record and the stored summary fields.

## Additional invariant checks (ad-hoc, all pass)

- `cumulative_pnl` chain reproduces `run_history[].nav` exactly (max abs diff 0.0).
- `run_history[].daily_pnl` == `cumulative_pnl` elementwise (max abs diff 0.0).
- `previous_regime_exposure` == last `run_history[].regime_exposure` (1.0 == 1.0).
- `peak_nav` == `max(nav)` (139120.07235486925).
- `max_drawdown` recomputed == stored (-0.049857401112321176).
- `low_rolling_sharpe` flag date (2026-10-23) == `last_run_date`.
- `current_positions` sum (0.6449193851213544) == last `vol_scale`
  (0.6449193851213544) — consistent with the risk overlay's effective
  exposure, and `n_positions` = 4 matches the four non-zero weights.

## Tests

```
python -m pytest tests/test_state_aggregate_audit.py \
              tests/test_paper_trading_extend.py \
              tests/test_drift_persistence.py \
              tests/test_refresh_raw_cache.py -q
-> 49 passed in 3.15s
```

The new test file also includes a negative control (`test_audit_flags_injected_mismatch`)
that injects an impossible `rolling_sharpe_63d = 999.0` and asserts the audit
reports a mismatch — proving the check can fail, not just pass.

## Data integrity

- `git status --porcelain data/` -> empty (DATA_TREE_CLEAN=yes).
- The audit is read-only: it opens the committed state, recomputes, and
  asserts; it writes nothing and never touches the network or the raw cache.
- The extension gate remains unchanged: `session already complete: False` for
  2026-10-26, 0 sessions extended, NAV unchanged at 133634.38193355838,
  0 state writes. This is a live-clock condition, not a code defect.

## Files added

- `research/audit_state_aggregates.py` — reusable, importable audit function
  (`audit(state=None) -> dict`) plus `main()` CLI.
- `tests/test_state_aggregate_audit.py` — 7 offline, read-only tests.

## Reproduction

```bash
python research/audit_state_aggregates.py
python -m pytest tests/test_state_aggregate_audit.py -q
```