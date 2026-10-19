# Next Agent Task: Session-Safe Raw-Cache Refresh Tool (Cycle 855)

## Context
Cycle 854 (2026-10-19) completed post-extension verification. Findings:

- Verification suite green: `pytest -q` 15 passed; `research/_tmp_cycle77_verify.py` OVERALL: PASS (rolling 63d Sharpe -0.21188351222842883, regime flips 6/6, 449 run_history entries, NAV $133,729.22, max DD -4.9857%); `.github/scripts/test_kilo_supervisor_loop.py` OK 10/10.
- `research/extend_paper_trading_state.py` was a correct no-op: the 2026-10-19 US session had not closed (10:32 ET, close 16:00 ET), so `sessions extended: 0`, `state write count: 0`, state byte-identical (sha256 e291d0d3...).
- **Defect found and fixed (Cycle 854)**: the extension tool called `fetch_universe(..., force=True)` with the default `raw_dir`, so every monitoring/no-op run rewrote 7 canonical `data/raw/*.parquet` files and appended a *partial* 2026-10-19 bar (SPY volume 6,623,724 vs 64,035,200 typical) into the committed dataset that `src/backtest/engine.py` and `src/simulation/engine.py` read with `force=False` (cache-only). The tool now downloads into a scratch dir, drops in-session bars, and refuses to write state unless the update lands exactly on the target session. The canonical cache was restored to the last completed session (2026-10-16).
- Side effect: nothing in the repo refreshes `data/raw` any more (the tool is deliberately read-only there), so the canonical dataset is pinned at 2026-10-16 while wall-clock advances.

## Objective
Build a deterministic, session-safe **raw-cache refresh tool** that appends only *completed* sessions to the canonical `data/raw` cache, is idempotent, and records an integrity manifest. Then, if a completed session is available, extend the paper-trading state once with the (now read-only) extension tool.

## Acceptance Criteria
1. `python -m pytest -q` passes (current baseline: 15 tests, ~116s).
2. New tool `research/refresh_raw_cache.py` exists and:
   - downloads the universe into a scratch dir, keeps only sessions whose local close has passed (no partial bar can ever enter `data/raw`);
   - merges new complete sessions into `data/raw/<symbol>.parquet` for the paper-trading universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) and `^VIX`, appending only rows newer than the cached max date (idempotent: re-running with no new session writes 0 rows and reports "no-op");
   - refuses to write a bar whose session is not complete (assertion/failure with a clear message);
   - writes an integrity manifest (per symbol: row count, max date, sha256 of the parquet, timestamp) under `research/reports/` and/or `data/processed/`, and prints a before/after summary.
3. Offline unit tests for the new tool (no network): completeness filter, merge/no-op behaviour, refusal of incomplete bars, manifest content. Tests must not require network access.
4. `python research/refresh_raw_cache.py --dry-run` reports the sessions it would append (today: none, cache already at the last completed session 2026-10-16).
5. `python research/refresh_raw_cache.py` real run; document before/after row counts and max dates for every symbol, and prove no partial bar is present.
6. `python research/extend_paper_trading_state.py --dry-run` and the real run: if a completed session is available, extend once and document NAV before/after; otherwise record the no-op. After the refresh, `data/raw` must still contain only complete sessions.
7. `python research/_tmp_cycle77_verify.py` prints OVERALL: PASS and `python .github/scripts/test_kilo_supervisor_loop.py` prints OK.
8. Write `.kilo-runtime/worker-disposition.json` (verified/blocked) and update `README.md` + this file.

## Validation Commands
- python -m pytest -q
- python research/refresh_raw_cache.py --dry-run
- python research/refresh_raw_cache.py
- python research/extend_paper_trading_state.py --dry-run
- python research/extend_paper_trading_state.py
- python research/_tmp_cycle77_verify.py
- python .github/scripts/test_kilo_supervisor_loop.py

## Evidence Anchors
- Canonical cache state to preserve: universe symbols max 2026-10-16 (SPY 8487, QQQ 6945, IWM 6637, TLT 6094, GLD 5512, EFA 6322, EEM 5916 rows), `^VIX` 451 rows max 2026-10-16, non-universe symbols (DBC, VNQ, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY) max 2026-10-08.
- Session-completeness rule (already implemented and unit-tested in `research/extend_paper_trading_state.py`): a session is complete once the following local (America/New_York) day has started, or once the local clock passes `market_close_hour + 1` on the session date. Reuse `session_is_complete` / `complete_session_view` instead of re-implementing.
- `config/paper_trading_config.yaml` holds `data_refresh.timezone: America/New_York` and `data_refresh.market_close_hour: 16`; `config/settings.yaml` holds `data.raw_dir: data/raw`.
- Bar timestamps are UTC midnight of the *session date* (2026-10-16 bar -> index 2026-10-16 00:00:00+00:00); never convert them to ET to obtain the session date.
- Drift flag `low_rolling_sharpe` (-0.21188351222842883, 5 consecutive trading days below the 0.5 threshold as of 2026-10-16) persists; see `research/reports/drift_flag_escalation_001.md`. Monitoring alone has not moved it for 88+ days.

## Scope Boundaries
- Monitoring/tooling/data-refresh only. No strategy, config, cost-model, or universe changes; no new dependencies.
- Never write a partial (in-session) bar into `data/raw`; never delete existing history from the canonical cache.
- `data/raw` writes are only allowed from the new refresh tool and must be append-only.
- Do not fabricate data, metrics, or results; record exact commands and observed output.
