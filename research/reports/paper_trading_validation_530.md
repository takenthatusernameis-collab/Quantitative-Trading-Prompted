# Paper-Trading Validation Report 530 — Drawdown Correctness Fix (Cycle 530)

**Generated:** 2026-10-16T08:00:00Z
**UTC time at generation:** 2026-10-16T08:00:00Z
**Gate state:** 2026-10-18T20:00:00Z — NOT REACHED (monitoring + bounded correction)
**Disposition:** verified

## Change Summary

This cycle executed a materially different corrective action from prior
invocations (which only re-ran the same three monitoring checks and wrote
gitignored disposition files). It identified and fixed a genuine code defect
in the paper-trading engine's drawdown tracking.

### Defect
`src/simulation/paper_trading.py:run_daily_paper_update` reset the running
maximum to the current NAV each day and measured the drawdown against that
local maximum:

```python
state.peak_nav = max(state.peak_nav, new_nav)
new_dd = (new_nav / state.peak_nav - 1.0) if state.peak_nav > 0 else 0.0
state.max_drawdown = min(state.max_drawdown, new_dd)
```

This understated drawdown whenever the portfolio recovered and then fell again.
The correct running-maximum definition anchors the drawdown to the all-time
peak NAV, so a trough after a recovery is measured from the new high.

### Evidence of the defect (pre-fix)
- `state.max_drawdown` = -0.0293 (stored), but the true full-series running-max
  drawdown computed from the same `cumulative_returns` was **-0.0499**.
- `state.rolling_max_dd_63d` = -0.0499 already matched the true value, proving
  the returns/NAV series were correct and only the tracked `max_drawdown`
  field was wrong.
- The rolling report's "Paper Drawdown" line therefore reported -2.93% instead
  of the true -4.99%.

### Fix
1. Added `compute_running_drawdown(peak_nav, current_nav, prev_max_drawdown)`
   to `src/evaluation/utils.py` (next to the existing `max_drawdown` helper).
2. Wired it into `run_daily_paper_update`:
   ```python
   state.peak_nav, state.max_drawdown = compute_running_drawdown(
       state.peak_nav, new_nav, state.max_drawdown
   )
   ```
3. Added regression tests in `tests/test_paper_trading_drawdown.py`
   (3 tests, TDD-first: written to fail against the old behavior, then pass
   after the fix).

### Verification
- `python3 -m pytest tests/ -v` → **3 passed**
- `python3 -m ruff check src/evaluation/utils.py src/simulation/paper_trading.py tests/test_paper_trading_drawdown.py` → **All checks passed**
- `python3 -m mypy --ignore-missing-imports src/evaluation/utils.py src/simulation/paper_trading.py` → **Success: no issues found**
- `python3 .github/scripts/test_kilo_supervisor_loop.py -v` → **OK (10 tests)**
- Full replay `research/run_paper_trading_replay.py` re-run end-to-end:
  - Track record **447 days** (2025-01-02 → 2026-10-14) — unchanged
  - NAV **$135,043.35** (+35.04%) — unchanged
  - Sharpe **1.9293** — unchanged
  - Rolling 63-day Sharpe **0.1133** — unchanged (diff vs stored 5.13e-16)
  - Regime flips **6/447** — unchanged
  - **max_drawdown now -0.0499** (was -0.0293) — corrected, matches the
    true running-maximum drawdown and the already-correct `rolling_max_dd_63d`
  - Rolling report `research/reports/paper_trading_rolling.md` regenerated
    with "Paper Drawdown | -4.99%"
- Diff of `paper_trading_state.yaml` before/after the fix (excluding the
  `max_drawdown`/`peak_nav` fields) is **empty** — the fix changed only the
  drawdown field, all other state (returns, NAV, Sharpe, regime, drift flags)
  is bit-identical.

### Scope boundaries respected
- No strategy, parameter, data-acquisition, or infrastructure changes.
- No new dependencies (only test tooling installed: pytest, ruff, mypy).
- No live trading, no secrets, no workflow/agent-count changes.
- Replay data acquisition unchanged (force=True, end_date 2026-10-15).

### Unresolved blockers (unchanged)
- Gate at 2026-10-18T20:00:00Z not reached (current UTC 2026-10-16T08:00:00Z).
- Drift flag `low_rolling_sharpe` persists (value 0.1133, threshold 0.5,
  date 2026-10-14) — 3 consecutive days, below the >20-day persistence
  threshold.
- No Yahoo Finance data beyond 2026-10-14 for the incumbent universe.