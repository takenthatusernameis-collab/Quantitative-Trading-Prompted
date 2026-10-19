# Next Agent Task: Incremental Paper-Trading State Extension + Extension-Safe Verification (Cycle 853)

## Context

Cycle 852 completed post-gate monitoring with **no new trading days**: `data/raw/*.parquet` index max is
`2026-10-16` for every monitored universe symbol (SPY, QQQ, IWM, TLT, GLD, EFA, EEM, ^VIX); non-universe
symbols (DBC/VNQ/XLB/XLE/XLF/XLI/XLK/XLP/XLU/XLV/XLY) max `2026-10-08`. All three verification commands passed
(pytest 7 passed in 118.96s; `research/_tmp_cycle77_verify.py` OVERALL PASS; supervisor-loop tests OK 10/10).
Drift flag `low_rolling_sharpe` persists (rolling 63d Sharpe `-0.21188351222842883`). No state was changed.

The monitoring loop has now been in verification-only mode for many consecutive cycles because **no script in
this repository can incorporate a new trading day into the paper-trading state**, and the repository's own
verification command is hard-frozen to the current state length. This task removes that blocker. It is a
tooling/verification task: the frozen strategy, candidate configuration, cost model, and data sources are
untouched.

### Evidence (verified in Cycle 852, 2026-10-19T14:22Z)

1. **No incremental extension path exists.**
   - `src/simulation/paper_trading.py:216-226` — `run_daily_paper_update(config, state)` with `market_data=None`
     calls `fetch_universe(config.universe, config.history_start, end_date)`. `src/data/yfinance_fetcher.py:193-206`
     defines `fetch_universe(..., force: bool = False)`, so this path is **cache-only** and can never observe a new
     session. This is the only single-step update call site outside a replay (`research/run_cycle9.py:83`).
   - `research/run_paper_trading_replay.py:46` hard-codes `end_date = "2026-10-17"` and line 53 filters
     `replay_dates ... <= "2026-10-16"`; line 77 calls `state.to_yaml(state_path)` **inside** the day loop
     (449 writes for a full replay, not the "deterministic, single state save" the monitoring contract requires).
2. **Partial-bar hazard is live, not hypothetical.** A Yahoo Finance probe at `2026-10-19T14:21Z` (network
   access works from this environment) already returns a **partial** `2026-10-19` row: SPY volume `6,508,028`
   versus 40–65M on completed sessions. The US session opened 13:30Z and closes 20:00Z. A naive force-fetch
   today would write an incomplete intraday bar into the paper-trading state and corrupt the track record.
3. **The verification harness is frozen to the current state.** `research/_tmp_cycle77_verify.py:83` asserts
   `len(run_history) == 449` and `flips == 6`. A legitimate one-session extension to 450 days would make the
   repository's own verification command fail.
4. **Extension-safe integrity invariants exist and hold on today's state** (independently recomputed in Cycle 852):
   - `100000 + cumsum(cumulative_pnl)[-1] == current_nav` → `133729.22` ✓
   - `100000 + max(cumsum(cumulative_pnl)) == peak_nav` → `139120.07` ✓
   - `len(cumulative_pnl) == len(cumulative_returns) == len(run_history) == len(cumulative_dates) == 449` ✓
   - `cumulative_dates == [r['date'] for r in run_history]`, strictly increasing and unique ✓
   - `previous_regime_exposure == run_history[-1]['regime_exposure']` → `1.0` ✓
   - stored `drift_flags.low_rolling_sharpe.value` == independently recomputed rolling 63d Sharpe → `-0.21188351222842883` ✓
   These are strictly stronger checks than the frozen `449` / `6` literals, and they survive a legitimate extension.

## Objective

Build a deterministic, session-safe, **incremental** paper-trading state extension tool, and make the
verification harness validate *state integrity* instead of a frozen state length. Then use the tool exactly once
if (and only if) a completed trading session is available.

## Acceptance Criteria

1. **New tool** `research/extend_paper_trading_state.py` exists, has a docstring stating its contract
   (incremental, single state write, idempotent, no strategy change), and supports:
   - `--dry-run` — report what would be extended; **must not write any file**;
   - `--through YYYY-MM-DD` — optional explicit upper bound on the last session to incorporate;
   - no-argument invocation — real extension.
2. **Session-completion guard.** The tool incorporates a bar dated `d` only when that US session is known to be
   complete, using `config.data_refresh.timezone` (`America/New_York`) and `config.data_refresh.market_close_hour`
   (16): accept when the current ET date is strictly later than `d`, or the current ET time is at or after
   `market_close_hour + 1` (a 1-hour settle buffer). Any bar for an open or partially-elapsed session must be
   rejected with an explicit message. The guard is a pure function of (bar date, current ET timestamp) and is
   unit-tested offline.
3. **yfinance exclusive-end handling.** Because `yfinance` treats `end` as exclusive
   (see `research/run_paper_trading_replay.py:43-45`), the tool must request `end = last_session + 1 day` so the
   target session is actually captured, and must assert the captured index max equals the intended session.
4. **Incremental extension semantics.** Starting from the existing `data/processed/paper_trading_state.yaml`
   (`last_run_date = 2026-10-16`), the tool appends exactly one `run_history` entry, one `cumulative_return`,
   one `cumulative_pnl`, and one `cumulative_date` per newly completed session, in date order, while preserving
   every invariant listed in Evidence item 4. It must call `run_daily_paper_update` with market data sliced to the
   target session date, exactly as `research/run_paper_trading_replay.py:66-69` does.
5. **Single state write.** The tool writes `paper_trading_state.yaml` exactly **once** per invocation (plus a
   `.backup` copy of the pre-run state before the overwrite), then regenerates
   `research/reports/paper_trading_rolling.md` via `generate_paper_report`. It must print a machine-checkable
   summary: sessions extended, NAV before/after, new/changed drift flags, state write count.
6. **Idempotency.** Running the tool twice in a row with no new completed session must leave the state logically
   unchanged (same `last_run_date`, same series lengths, same `current_nav`), perform **zero** state writes, and
   report "no new completed session". This must be demonstrated by the offline test and by the no-argument run.
7. **Extension-safe verification.** `research/_tmp_cycle77_verify.py` must drop the frozen `449` / `6` literals
   and instead assert the invariants from Evidence item 4 (series-length equality, date ordering/uniqueness,
   `last_run_date` equality, NAV and peak reconstruction, `previous_regime_exposure` consistency, and the
   independent recomputation of the rolling 63d Sharpe against the stored drift flag). The script must still print
   `OVERALL: PASS` and exit 0 against the **current, unmodified** 449-day state.
8. **Offline tests.** `tests/test_paper_trading_extend.py` covers, with synthetic data and temporary directories
   and **no network access**: the session guard accepting a completed session and rejecting an open session; a
   one-session extension appending exactly one entry and preserving all invariants; a second run being a no-op;
   and the state file being written exactly once per extending invocation.
9. **Real run, conditional and recorded.** If, at execution time, a completed session exists beyond `2026-10-16`
   (i.e. the guard accepts it), run the tool once without `--dry-run`, re-run all verification commands, and
   document the before/after state summary. If no completed session is available (e.g. the cycle runs while the US
   market is open), do **not** force a partial bar: run the tool with no arguments, confirm it reports "no new
   completed session" with zero state writes, and record that outcome. Either outcome is acceptable provided it is
   reported with evidence.
10. **Scope of data.** Only the `config.universe` symbols (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) plus the `^VIX`
    regime series may be refreshed. `DBC/VNQ/XLB/XLE/XLF/XLI/XLK/XLP/XLU/XLV/XLY` are outside the candidate
    universe and must not be written by this task.
11. **Handoff.** Record current UTC in the documentation and in `.kilo-runtime/worker-disposition.json`
    (disposition `verified` only if every command below actually ran and passed; otherwise `blocked` with the
    exact failure). Write ONE bounded NEXT_AGENT_TASK.md for the next cycle.

## Validation Commands

- `python -m pytest -q`
- `python research/_tmp_cycle77_verify.py`
- `python .github/scripts/test_kilo_supervisor_loop.py`
- `python research/extend_paper_trading_state.py --dry-run` — must report the target session(s) and write nothing
- `python research/extend_paper_trading_state.py` — the real (or no-op) run; re-run the three commands above afterwards

## Scope Boundaries

- **Monitoring/tooling only.** Do not modify strategy logic, `src/simulation/engine.py` signal or risk code,
  `config/simulation_candidate_001.yaml`, the universe, the cost model, or any data source. The candidate stays frozen.
- **No re-optimization.** Monitor the `low_rolling_sharpe` drift flag; do not retune the strategy because of it.
  The current streak below the 0.5 threshold is **5 consecutive trading days** (2026-10-12 → 2026-10-16), and
  21 of the last 46 calendar days — see `research/reports/drift_flag_escalation_001.md` §3. Do not restate the
  unreproducible "88 days" / ">20 consecutive days" figures in new documentation.
- **No new dependencies** (numpy/pandas/pyyaml/yfinance are already present), no services, no workflow or
  scheduling changes, no new agents.
- **Research/paper only.** Never place live trades or enable live trading; never touch credentials.
- **Do not commit.** The controller creates checkpoints. `src/**/__pycache__/*.pyc` files are tracked in git and
  show as modified on every run — do not stage them deliberately and do not delete them as part of this task.
- Do not rewrite the historical `research/reports/paper_trading_*.md` validation records; only
  `research/reports/paper_trading_rolling.md` is regenerated by the tool.

## Known State

- Data ends `2026-10-16` for the monitored universe; `last_run_date = 2026-10-16`; `current_nav = 133729.22`;
  `peak_nav = 139120.07`; `max_drawdown = -0.049857`; 449 `run_history` entries; 6 regime flips;
  stored `low_rolling_sharpe = -0.21188351222842883` (date `2026-10-16`), equal to the independent recomputation.
- `^VIX` has 451 rows ending `2026-10-16`; Yahoo returns `^VIX` with zero volume (expected).
- Yahoo Finance network access is functional from this environment; a partial `2026-10-19` bar is already being
  served while the US session is open (opened 13:30Z, closes 20:00Z).
- Cycle 852 verification (2026-10-19T14:22:44Z): pytest 7 passed in 118.96s; `_tmp_cycle77_verify.py` OVERALL PASS;
  supervisor-loop tests OK 10/10 in 0.497s.
