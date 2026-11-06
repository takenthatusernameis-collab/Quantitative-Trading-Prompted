# CORRECTIVE_HANDOFF_INVOCATION_515 — pre-gate; rolling_max_dd_63d producer defect corrected

- **Diagnostic (514 log):** prior invocation re-read the 513 log, re-checked the
  clock (gate NOT released), re-armed a post-gate wakeup, and emitted
  `CORRECTIVE_VERIFICATION=BLOCKED`. No durable project change; only a handoff
  file.
- **Worktree changes (first durable change in this corrective cycle):**
  - `src/simulation/paper_trading.py:340-342` — `rolling_max_dd` now measured on
    the trailing-63 `recent_returns` window (matching `rolling_sharpe_63d` and
    the gate definition), instead of the full history.
  - `research/audit_state_aggregates.py:60-64` — offline audit mirrors the same
    trailing-63 definition so stored and recomputed agree.
  - `tests/test_state_aggregate_audit.py` — added
    `test_rolling_max_dd_is_trailing_63d_not_full_history`; fixed
    `test_audit_sessions_span_a_real_history` (stale hard-coded date
    `2026-10-23` replaced by an invariant against the live last session).
  - `data/processed/paper_trading_state.yaml` — single field rewritten
    (`-0.06562469374042079` -> `-0.06544463769225417`); sha256
    `f9572aed...` -> `60b16fb4...`; `git diff` shows exactly one line.
  - `research/correct_rolling_max_dd_field.py` — new idempotent, dry-run-capable,
    field-only correction tool.
  - `README.md` — Cycle 1140 entry; `NEXT_AGENT_TASK.md` — handoff updated.
- **Smallest justified correction (515, materially different from 514/513/512):**
  instead of re-running the same readiness/scan no-op, re-read the *producer*
  source (`src/simulation/paper_trading.py`) and found a real, clock-gate-independent
  defect: `rolling_max_dd_63d` was the all-time drawdown stored under a
  trailing-63d name. Fixed the producer, mirrored the audit, added a discriminating
  regression test, and rewrote only the one stale canonical field.
- **Key finding (verified).** Stored `-0.06562469374042079` == full-history
  `cumprod(1+r)/maximum.accumulate-1` min; trailing-63 value is
  `-0.06544463769225417`. Gate 5 threshold `-0.15` passes under both, so the
  promotion verdict is unchanged — this is a definitional integrity defect, not
  a performance claim. Sibling `rolling_sharpe_63d` already used the trailing 63
  sessions (`-2.1202794870108126`).
- **Integrity re-checks (both prior flagged items CLOSED, verified fresh):**
  (a) `cumulative_returns` vs `daily_pnl` "Sharpe discrepancy" from
  `research/reports/sharpe63d_gross_vs_cost_attribution_350.md` is a `np.diff()`
  double-differencing artefact: `cumulative_returns` is a daily return series,
  identical to `daily_pnl.daily_return` (463 rows, max abs diff 0.0, Sharpe
  -2.1203 on both). Already retracted in `CORRECTIVE_HANDOFF_628.md`; re-derived
  here to close the loop. (b) `daily_pnl` 2026-11-02 storage gap closed: 463 store
  rows == 463 canonical dates, zero missing/extra, last NAV `129990.36021343581`
  matches state.
- **Verification (observed):**
  - `date -u && TZ=America/New_York date` -> Fri Nov 6 00:51:04 UTC 2026 /
    Thu Nov 5 19:51:04 EST 2026 (gate **not released**)
  - `python3 research/correct_rolling_max_dd_field.py` -> stored == full-history
    True, stored == trailing-63 False; rewrote one field; sha256
    `f9572aed...` -> `60b16fb4...`
  - `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py
    tests/test_verify_monday_extension_path.py tests/test_real_extension_path.py
    tests/test_state_aggregate_audit.py tests/test_rolling_63d_gate_refresh.py -q`
    -> **61 passed in 36.38s**
  - `python3 research/drift_persistence_report.py` -> `stored == recomputed: True`,
    rolling 63d Sharpe `-2.1202794870108126` at 2026-11-05, persistence 7
  - `python3 research/extend_paper_trading_state.py` -> clock gate NOT released,
    next expected session 2026-11-06 (Friday), candidate available: no (in the
    future), `sessions extended: 0`, NAV `129990.36021343581` unchanged, state
    write count 0, raw cache scratch
  - `git status --porcelain data/ config/` -> only
    `M data/processed/paper_trading_state.yaml` (the single-field correction)
- **Unresolved blockers:** (1) NEXT_AGENT_TASK extension blocked until
  `>= 2026-11-06 22:00:00 UTC`; run commands 1–6 post-gate, extend <=1 session
  only if a completed 2026-11-06 bar exists else `sessions_extended==0`/NAV
  unchanged/0 writes/idempotent. (2) 2026-11-06 bar availability unknown pre-gate.
- **Safety:** no extender run, no threshold/gate/cost/universe/clock-gate/state
  logic changes, no `data/raw` access, no canonical state hand-edit (rewritten
  only by the idempotent field-only tool, verified to change exactly one line),
  no commit.

CORRECTIVE_VERIFICATION=PASS