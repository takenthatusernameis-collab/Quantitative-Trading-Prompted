# Paper-trading record vs daily-artifact reconciliation

Read-only audit produced by
`research/paper_trading_artifact_reconciliation_audit.py`.
No file under `data/` or `config/` is written; every artifact field is
re-derived from the committed state and compared with the committed
per-session parquet.

## Coverage

| quantity | value |
|---|---|
| universe checked | `SPY`, `QQQ`, `IWM`, `TLT`, `GLD`, `EFA`, `EEM` |
| record window | `2025-01-02` .. `2026-11-18` |
| record sessions | `472` |
| sessions with a mismatch | `1` |
| mismatches attested (known defects) | `1` |
| mismatches unattested | `0` |
| verdict | `PASS` |

## Checks applied per session

- `daily_pnl`: single row dated to the session; `daily_return`, `daily_pnl`
  and `nav` equal the state row; `daily_pnl == nav - previous nav`.
- `risk_state`: `vol_scale` and `dd_scale` equal the state row;
  `exposure == vol_scale * regime_exposure`; `drawdown` equals the running
  maximum drawdown of the record NAV series up to that session.
- `regime`: `regime_exposure` equals the state row.
- `positions`: exactly the configured universe, dated to the session; the
  nonzero-weight count equals `n_positions`; gross exposure is at most 1;
  `sum |w_t - w_{t-1}|` equals the state row's `turnover` (from session 2).

## Known defects (attested)

- `2026-11-02` `drawdown`: artifact `-0.06562469374042057`, expected `-0.049857401112321176`.
  risk_state_20261102.parquet reconstructed by research/repair_missing_paper_trading_artifacts_868.py using drawdown = state.max_drawdown (all-time max at repair time) instead of the session's running max drawdown.

## Unattested mismatches

- (none)

A defect is only exempted when both its session/field key and its exact
observed value match the pinned registry entry; any drift in either fails
the audit. Known defects are documented, not repaired by rewriting the
committed artifacts.
