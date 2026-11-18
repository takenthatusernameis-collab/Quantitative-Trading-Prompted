# Corrective invocation 382 — durable handoff (2026-11-18T23:23Z)

## Situation

- Assigned task in `NEXT_AGENT_TASK.md`: the **2026-11-19 gate cycle**, pre-gate first.
- `GATE_EPOCH=1795125600 STATE_SHA256=bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750 bash scripts/pre_gate_check.sh`
  → `PRE-GATE OK: now=1795044174 (2026-11-18T23:22:54Z) < gate 1795125600 (2026-11-19T22:00:00Z); T-81426s remaining. state sha256 matches; data/raw clean. STOP`
  → `EXIT=0`. No mutating cycle is permitted for ~22.6 h.
- The previous invocations (380/381) re-ran that same check and stopped, which produced no
  durable project change. This invocation therefore did **not** repeat a bare re-verification.

## Change made

Audited, quantified and persisted a **previously undocumented measurement defect**, following the
repository's own precedent for the analogous volatility-estimate defect
(`research/reports/tsmomentum_same_session_vol_correction_001.md`):

The SPY 200-session SMA regime factor is **same-session**:

- `src/simulation/engine.py::_regime_exposure` — `sma = spy.rolling(200).mean()` includes session `t`
  and sets `exposure[spy < sma] = 0.0`;
- `src/simulation/engine.py:450-452` — `gated = base_weights.mul(regime…)` on the *same* index row;
- `src/simulation/engine.py::_finalize` — `gross_ret = (scheduled * asset_ret)` with
  `asset_ret = close.pct_change()`, so the weight recorded at `t` earns `close[t]/close[t-1]-1`;
- `research/run_cycle6.py::_apply_overlay` — identical (`weights.mul(ef, axis=0)`);
- `src/simulation/paper_trading.py:288-296` — the live record uses that `net_return`.

The momentum signal is correctly lagged (`src/features/momentum.py:105`, `weights.shift(1)`), so the
regime factor is the only same-session input on the execution path. Two committed documents assert
the opposite (`research/reports/deployment_dossier_001.md:279`,
`research/reports/go_nogo_evaluation_001.md:75`).

### Artifacts added (new files only)

| File | Purpose |
| --- | --- |
| `research/tsmomentum_regime_lookahead_audit_001.py` | Read-only audit tool (committed vs `shift(1)` exposure; fails closed if the published anchor does not reproduce; hashes `data/` + `config/` before/after) |
| `research/reports/tsmomentum_regime_lookahead_audit_001.md` | Generated evidence report |
| `tests/test_tsmomentum_regime_lookahead_audit_001.py` | 5 regression tests pinning the exposure semantics, the read-only digest and the anchor constant |

### Result

| Quantity | Committed (same-session) | Point-in-time (`shift(1)`) |
| --- | --- | --- |
| 48-fold mean OOS Sharpe | **0.947307** (reproduces published anchor) | **0.153040** |
| Folds worsened by the lag | — | 43 of 48 |
| Post-2017 Sharpe | 1.333367 | 0.555815 |
| Post-2017 max drawdown | -7.7940% | -15.4646% |
| Post-2017 trades | 1218 | 1247 |
| Avg daily turnover | 0.052496 | 0.052496 (unchanged) |

Live record: 472 sessions, 55 at zero exposure, 25 of those 55 with a negative base-portfolio return
(mean base return on cash-out sessions `+0.00053990`, sum `+0.02969435`).

## What was deliberately not done

- No production code change, no opt-in switch, no config/threshold/universe/cost/gate change, no
  state write, no promotion, no re-ranking. A corrected path needs a default-path bit-identity proof
  and a full re-derivation, which is bounded as a deferred task in `NEXT_AGENT_TASK.md`.
- No commit (task scope: do not commit manually).
- Promotion verdict unchanged: `research/go_no_go_evaluation.py` → **NO-GO**
  (`rolling_63d_sharpe`, `psr`).

## Verification (exact commands and observed output)

```
$ GATE_EPOCH=1795125600 STATE_SHA256=bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750 bash scripts/pre_gate_check.sh
PRE-GATE OK: now=1795044174 (2026-11-18T23:22:54Z) < gate 1795125600 (2026-11-19T22:00:00Z); T-81426s remaining.
  state sha256 matches (bed3b236…20b750); data/raw clean. STOP — do not re-run the cycle.
EXIT=0

$ /tmp/kilo-venv/bin/python research/tsmomentum_regime_lookahead_audit_001.py
sessions loaded:      8504 (1993-01-29 -> 2026-11-10)
cash-out sessions:    2270
sessions affected by the one-session lag: 223
anchor 48-fold mean OOS Sharpe: 0.947307 (published 0.947307)
point-in-time 48-fold mean OOS Sharpe: 0.153040
read-only (data/ + config/ byte-identical): True
report written -> research/reports/tsmomentum_regime_lookahead_audit_001.md
EXIT=0

$ diff <(grep -v "Generated:" <first run report>) <(grep -v "Generated:" <second run report>)
DETERMINISTIC: reports identical apart from timestamp

$ /tmp/kilo-venv/bin/python -m pytest -q tests/test_tsmomentum_regime_lookahead_audit_001.py \
    tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py \
    tests/test_post_gate_handoff_consistency.py tests/test_drift_persistence.py
102 passed, 1 skipped in 11.92s

$ /tmp/kilo-venv/bin/ruff check research/tsmomentum_regime_lookahead_audit_001.py tests/test_tsmomentum_regime_lookahead_audit_001.py
All checks passed!

$ git status --porcelain -- data/raw      # (empty)
$ sha256sum data/processed/paper_trading_state.yaml
bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750  (unchanged)
$ git status --porcelain
?? research/reports/tsmomentum_regime_lookahead_audit_001.md
?? research/tsmomentum_regime_lookahead_audit_001.py
?? tests/test_tsmomentum_regime_lookahead_audit_001.py
```

## Unresolved blocker

The 2026-11-19 gate cycle cannot run before 2026-11-19T22:00:00Z; that is a clock precondition, not a
failure. The next invocation at/after the gate must follow the unchanged task in `NEXT_AGENT_TASK.md`;
the regime-lag correction is queued as the deferred bounded task in the same file.
