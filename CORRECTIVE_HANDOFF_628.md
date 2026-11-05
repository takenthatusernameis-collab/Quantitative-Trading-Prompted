# CORRECTIVE_HANDOFF_628 — pre-gate; corrected gross-vs-cost attribution

- **Diagnostic (627 log):** prior invocation re-read the 626 log, re-checked the
  clock (gate NOT released), re-armed a post-gate wakeup, and emitted
  `CORRECTIVE_VERIFICATION=BLOCKED`. No durable project change; only a
  handoff file.
- **Worktree:** `research/reports/sharpe63d_gross_vs_cost_attribution_351.md`
  (new, read-only correction); `data/`, `config/`, `src/`, `tests/` verified
  clean; `git status --porcelain data/ config/ src/ tests/` -> empty.
- **Smallest justified correction (628, materially different from 627/624):**
  instead of re-running the same readiness/scan no-op, executed the bounded
  read-only research follow-up that was deferred in the handoff — the
  gross-vs-cost/turnover attribution — and **corrected the methodological error
  in invocation 350**. 350 double-differenced an already-daily-return series.
- **Key finding (verified):** `state.cumulative_returns` is a **daily return
  series**, identical to `daily_pnl.daily_return` (461 matched rows, max abs
  diff = 0.0). The +0.405 "discrepancy" in the 350 report was a
  double-differencing artefact (ann. ret ~1949%), **retracted**. No metric
  inconsistency exists.
- **Canonical attribution (63 sessions 2026-08-07→2026-11-04, `sharpe_ratio`):**
  net Sharpe **-0.8724** (matches state/drift exactly); gross Sharpe (3 bps/unit
  cost backed out) **-0.8308**; annualised cost drag **0.357%/yr**; cost drag is
  **~4.8%** of the negative return magnitude. **Directional performance drag
  dominates; turnover/cost does not explain the drawdown.**
- **Minor integrity flag (non-blocking):** `daily_pnl_*.parquet` store (461 rows)
  is missing the 2026-11-02 session present in canonical state (462 rows). Does
  not affect any Sharpe/persistence figure; separate bounded storage task.
- **Verification (observed):**
  - `date -u && TZ=America/New_York date` -> `Thu Nov 5 20:42:06 UTC 2026 /
    15:42:06 EST 2026` (gate **not released**; ~1h18m to 22:00 UTC)
  - `python3 research/drift_persistence_report.py` -> last_sharpe
    `-0.872439579425076`, streak 6, `stored_matches_recomputed True`
  - `python3 -m pytest ... -q` -> **47 passed in 18.05s**
  - `git status --porcelain data/ config/ src/ tests/` -> empty
- **Unresolved blockers:** (1) NEXT_AGENT_TASK extension blocked until
  `>= 2026-11-05 22:00:00 UTC`; run commands 1–6 post-gate, extend ≤1 session
  only if completed 2026-11-05 bar exists else `sessions_extended==0`/NAV
  unchanged/0 writes/idempotent. (2) 2026-11-05 bar availability unknown
  pre-gate. (3) daily_pnl-vs-canonical 2026-11-02 storage gap needs separate
  bounded read-only reconciliation.
- **Safety:** no extender run, no threshold/gate/cost/universe/clock-gate/state
  logic changes, no `data/raw` access, no canonical state edits, no commit.

CORRECTIVE_VERIFICATION=BLOCKED