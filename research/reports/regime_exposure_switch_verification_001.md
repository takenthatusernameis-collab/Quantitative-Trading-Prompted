# Regime exposure lag switch — verification report (2026-11-19 pre-gate session)

## Context

`NEXT_AGENT_TASK.md` (2026-11-19 cycle) listed the opt-in
`lag_regime_exposure` switch as a **deferred, not-yet-implemented** task to be
done after the 2026-11-19 gate cycle. A previous invocation (corrective 264,
2026-11-19T00:15Z) reverted working-tree changes to that switch as
out-of-scope. At the current HEAD (`5363746`) the switch is nevertheless
**present and committed**:

- `src/simulation/engine.py:96` (config field), `:236` (`exposure.shift(1).fillna(exposure_below)`)
- `research/run_cycle6.py:114,134` (parameter + `ef.shift(1).fillna(0.0)`)
- `src/simulation/paper_trading.py:103` (threaded from `SimulationConfig`)

No shipped YAML config sets the switch, so the default path is unchanged.
Before this session there was **no test coverage** pinning that invariant.
This report records the verification performed (read-only) and the small
regression test added. No defaults, thresholds, configs, state or committed
artifacts were modified.

## Evidence

Production research path (`research/run_cycle6.py::run_walkforward`), cached
`data/raw` prices, 1993-01-01 … 2026-10-09, 48 folds:

| Path | Mean OOS Sharpe | % positive | Pooled trades |
|---|---|---|---|
| default (`lag_regime_exposure=False`) | `0.947307` | `0.9167` | `6013` |
| lagged (`lag_regime_exposure=True`) | `0.153040` | `0.7083` | `6060` |

These match the published anchor `0.947307` and the audit's lagged result
`0.153040` (`research/reports/tsmomentum_regime_lookahead_audit_001.md`) to six
decimals, i.e. the committed switch reproduces both sides of the audit through
the production module rather than only through the audit's reimplementation.

Simulation engine (`run_simulation`, 1993-01-01 … 2026-11-18, 8504 sessions,
`config/simulation_candidate_001.yaml`):

- default path vs a frozen copy of `engine.py` with the `if
  config.lag_regime_exposure:` branch deleted: **daily frame byte-identical**
  (`check_exact=True`) and identical metrics — the switch is default-neutral.
- `lag_regime_exposure=True` exposure equals the audit's committed rule
  shifted one session (`exposure_committed(...).shift(1).fillna(0.0)`),
  asserted exactly on the real SPY series.
- Whole-history max drawdown: `-9.9349%` (default) → `-16.4972%` (lagged),
  consistent with the same-session rule flattering drawdowns by dodging
  same-day closes.

## Added

- `tests/test_regime_exposure_lag_switch.py` — 5 hermetic tests: default
  switch off; default exposure equals the same-session rule; lagged exposure
  is exactly `shift(1)` with `exposure_below` fill; the crash session flips
  from cash to invested; no `config/*.y*ml` enables the switch.
- Verification run: `pytest -q tests/test_regime_exposure_lag_switch.py
  tests/test_tsmomentum_regime_lookahead_audit_001.py` → **10 passed**;
  `ruff check tests/test_regime_exposure_lag_switch.py` → clean.

## Integrity

- `data/processed/paper_trading_state.yaml` sha256
  `bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750`
  unchanged; `last_run_date 2026-11-18`; `git status --porcelain -- data/raw`
  empty.
- Pre-gate check: `EXIT=0` at `2026-11-19T01:13:25Z`, gate
  `2026-11-19T22:00:00Z` (T-74796s). No mutating cycle was run.

## Remaining (post-gate)

The switch is implemented and now tested. The deferred task's documentation
deliverable is complete: `research/reports/deployment_dossier_001.md:279-280`
and `research/reports/go_nogo_evaluation_001.md:75-76` no longer assert the
regime factor is point-in-time — both carry an explicit "Correction
(2026-11-19)" annotation stating the default path is *not* point-in-time, the
regime factor is same-session, the audit reference, and the default vs lagged
metrics. What remains is downstream re-derivation only (no record changes).
