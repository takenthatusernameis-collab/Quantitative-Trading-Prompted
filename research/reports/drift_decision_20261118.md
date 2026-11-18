# Drift Decision Record — 2026-11-18 session (post-gate)

**Generated:** 2026-11-18T22:10Z
**Scope:** read-only re-derivation of the four stored drift flags, one explicit
`observe`/`mitigate` decision per flag. No strategy, gate, threshold, cost,
universe, or `data/raw` change.
**State:** `bed3b2363a50d51bf059a27b2ca369d4b5480ada8ad01fe0e89756035720b750`
(`last_run_date 2026-11-18`, NAV `130307.21196257228`, 472 sessions).

## 1. The four stored flags

| flag | stored value | threshold | threshold source |
|---|---|---|---|
| `high_turnover` | 0.5132058911351663 | 0.5 | `config/paper_trading_config.yaml:22` (`signal_turnover_pct`), applied at `src/simulation/paper_trading.py:374` |
| `regime_flip` | from 1.0 → to 0.0 | any change | `config/paper_trading_config.yaml:19` (`regime_flip: true`), applied at `src/simulation/paper_trading.py:404-414` |
| `low_rolling_sharpe` | -1.9744867954469325 (persistence 16) | 0.5 | `src/evaluation/drift.py:39` (`DEFAULT_SHARPE_THRESHOLD`), min periods `:38`, applied at `paper_trading.py:416-427` |
| `regime_persistence_low` | 1 | 5 | hard-coded `src/simulation/paper_trading.py:439` |

## 2. Independent reproduction from committed data

All four reproduce exactly from `data/processed/paper_trading_state.yaml`:

| quantity | recomputed | stored |
|---|---|---|
| rolling 63d Sharpe (`src/evaluation/sharpe.sharpe_ratio` over last 63 returns) | `-1.9744867954469325` | `-1.9744867954469325` |
| Sharpe persistence streak (`src/evaluation/drift.sharpe_persistence`) | `16` sessions, start `2026-10-28`, end `2026-11-18` | `16` |
| 2026-11-18 turnover vs 2026-11-17 weights | `sum |w_prev| = sum |delta| = 0.5132058911351663` | `0.5132058911351663` |
| regime exposure 2026-11-17 → 2026-11-18 | `1.0 → 0.0` (`run_history[-2]`, `[-1]`) | flag `from 1.0, to 0.0` |
| regime persistence | reset to `1` on flip (`paper_trading.py:352-353`) | `1` |

`research/drift_persistence_report.py` rerun agrees: last ten evaluated sessions
end `2026-11-18 -1.9745`; `stored == recomputed` (the script asserts this).

## 3. Reconciliation of the `regime_flip` vs `regime_exposure` question

A supervisor hypothesis stated that `run_history` for 2026-11-18 shows
`regime_exposure: 1.0` while the flag says `to: 0.0`. **This is falsified.** The
committed state contains:

- `run_history[-1]` (2026-11-18): `regime_exposure 0.0`, `n_positions 0`, `turnover 0.5132`
- `run_history[-2]` (2026-11-17): `regime_exposure 1.0`, `n_positions 4`
- `state.previous_regime_exposure`: `0.0` (written after the update, `paper_trading.py:469`)
- `data/processed/paper_trading/regime_20261118.parquet`: `regime_exposure 0.0`
- `data/processed/paper_trading/positions_20261118.parquet`: all 7 weights `0.0`

The `1.0` in the flag is the *previous* session's exposure (the `from` side), not
today's. Flag, applied exposure, and stored artifact come from one and the same
column: `latest["regime_exposure"]` (`paper_trading.py:278`) feeds the flag
(`:404-414`), the run-history row, and the persisted regime artifact. They are
consistent; there is no mismatch to fix.

Note: `regime_20261118.spy_price` is `NaN` by construction
(`paper_trading.py:508` needs a `price_SPY` column that `engine.py:500-513` never
creates); it is a reporting artifact and was not used in any flag.

## 4. Structural interpretation (why these four fired together)

- **The regime filter de-risked 100%.** `_regime_exposure` (`src/simulation/engine.py:207-219`)
  sets exposure to `exposure_below = 0.0` when SPY < its 200-day SMA
  (`config/simulation_candidate_001.yaml:34-38`). On 2026-11-18 the simulated
  close crossed below the SMA, so the book went from 4×0.1283 to all cash.
- **`high_turnover` is the arithmetic consequence of that liquidation**, not
  independent drift: `turnover = sum |Δw| = 0.5132058911351663`. In the whole
  472-session record every day with `turnover > 0.5` (7 days) is a regime
  transition day, and every one of the 7 regime transitions has
  `turnover > 0.5`. Median turnover is `0.00148`; annualized turnover `12.44`.
- **`regime_flip` is the filter working as designed**, and it is what the
  promotion gate `regime_flips` (threshold ≥1) asks to observe. That gate now
  counts 7 transitions and passes.
- **`regime_persistence_low = 1` is definitional**: persistence is reset to
  exactly 1 on every flip (`paper_trading.py:352-353`), so it always co-fires
  with `regime_flip` and carries no additional information.
- **`low_rolling_sharpe` is not a new event**: the streak is 16 sessions old
  (started `2026-10-28`) and its value is exactly the `rolling_63d_sharpe`
  promotion gate metric, which is already failing (`-1.9745 < 0.9`). Record-wide
  Sharpe remains `1.4709` (passes), and full-period/rolling max drawdown are
  `-0.0656 / -0.0654` (both pass at `-0.15`).

Current production verdict (`research/go_no_go_evaluation.py`, read-only):
`NO-GO`, `failed_gates = ['rolling_63d_sharpe', 'psr']`, `psr 0.5304` in the
grey zone.

## 5. Decision per flag (no new thresholds introduced)

| flag | decision | rule that justifies it |
|---|---|---|
| `high_turnover` 0.5132 | **observe** | `signal_turnover_pct: 0.5` (`paper_trading_config.yaml:22`) is a per-day alert, not a remediation trigger; the value is fully explained by the regime liquidation (all 7 such days in the record are transition days). No documented rule prescribes action. |
| `regime_flip` 1.0→0.0 | **observe** | `alert_regime_flip: true` (`paper_trading_config.yaml:19`) plus the `regime_flips` promotion gate (`config/promotion_gates.yaml`, threshold ≥1) treat a flip as *expected* filter behaviour to be recorded, not suppressed. |
| `low_rolling_sharpe` -1.9745 | **observe** | Same metric as the `rolling_63d_sharpe` gate (`config/promotion_gates.yaml`), already reflected in the NO-GO verdict. The gate table / decision mapping define the consequence (no promotion), not a code mitigation. |
| `regime_persistence_low` 1 | **observe** | Threshold 5 with reset-to-1 on flip (`paper_trading.py:352-353,439`); informational and fully redundant with `regime_flip`. |

No flag warrants mitigation: none contradicts the recorded state, none indicates
a data or accounting defect, and no predefined rule maps any of them to an
action other than recording. Introducing an action (e.g. a new turnover
threshold or a re-entry override) would be a strategy change and is out of
scope.

## 6. Verification actually run

```
/tmp/kilo-venv/bin/python research/drift_persistence_report.py            # tail ends 2026-11-18 -1.9745
/tmp/kilo-venv/bin/python research/rolling_63d_gate_refresh.py            # OVERALL: PASS, checks passed: 12/12
/tmp/kilo-venv/bin/python research/go_no_go_evaluation.py                 # decision NO-GO, failed ['rolling_63d_sharpe','psr']
/tmp/kilo-venv/bin/python -m pytest -q tests/test_drift_persistence.py \
    tests/test_rolling_63d_gate_refresh.py                                # 30 passed in 6.88s
/tmp/kilo-venv/bin/ruff check research/drift_persistence_report.py \
    research/rolling_63d_gate_refresh.py                                  # All checks passed!
git status --porcelain -- data/raw                                        # empty
sha256sum data/processed/paper_trading_state.yaml                         # bed3b236… (unchanged)
```

`rolling_63d_gate_refresh.py` also proves read-only behaviour: state file and raw
cache byte-identical before/after.

## 7. What would change this decision

Only evidence, not tuning:

- a `turnover > 0.5` session **without** a regime transition (would indicate
  unintended trading rather than filter-driven rebalancing);
- a stored flag that does not reproduce from the state (would indicate a defect);
- a recorded regime exposure that disagrees with the persisted regime artifact
  (would indicate a write-order/accounting bug).

None of these is present for 2026-11-18.
