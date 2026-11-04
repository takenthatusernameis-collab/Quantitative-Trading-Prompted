# NEXT_AGENT_TASK — Paper-trading extension gate check (2026-11-04 post-close)

## Context
- Verified 2026-11-04 ~04:40 UTC (Tue 2026-11-03 23:40 EST): last processed session 2026-11-03, NAV 132866.0435881768, sessions_extended 0, 0 writes.
- Clock gate NOT released at run time; candidate session 2026-11-04 has not closed.
  - Reason: `next session 2026-11-04 has not closed yet (in the future (today is 2026-11-03)); no completed candidate bar exists to extend into`
- Gate releases at 17:00 ET / 22:00 UTC on 2026-11-04 (Wednesday) — i.e. once the local ET clock passes 17:00 on the 2026-11-04 session date. Current time is ~04:40 UTC, so the gate will not release until ~22:00 UTC today.
- drift_persistence_report: stored == recomputed True (rolling 63d Sharpe -1.3997 at 2026-11-03).
- Idempotency confirmed (2nd invocation: 0 writes, NAV unchanged).
- `git status --porcelain data/ config/` -> empty (clean). Only non-data/config artifact: `research/reports/paper_trading_rolling.md` git_sha provenance line bumps from d9a4045 -> 618fb91 whenever `drift_persistence_report.py` runs — expected, self-generated report metadata, documented in README.md; left as-is.
- No supervisor recommendation pending (`.kilo-runtime/current-supervisor-recommendation.json` absent).

## Objective
At/after 22:00 UTC on 2026-11-04, run real extension and persistence checks. Extend by at most one session to 2026-11-04 if a completed bar exists; otherwise sessions_extended==0 with explicit reason and state unchanged.

## Acceptance criteria
- Run `python3 research/extend_paper_trading_state.py`; record gate/candidate/sessions_extended/last_run_date/NAV and reason if 0.
- If completed 2026-11-04 session exists: sessions_extended==1, last_run_date advances to 2026-11-04, NAV changes, state write count 1, raw cache scratch.
- If not: sessions_extended==0 with explicit reason, NAV unchanged, 0 writes.
- Second invocation idempotent: sessions_extended==0, write count 0, NAV unchanged.
- `python3 research/drift_persistence_report.py` reports stored == recomputed: True.
- `git status --porcelain data/ config/` shows only expected state update (no unintended changes).

## Scope boundaries
- Do not change thresholds/gates/cost model/universe/clock-gate logic.
- Do not commit unless asked.
- Do not modify data/raw/.
- Do not hand-edit canonical state.
- Do NOT run before 22:00 UTC on 2026-11-04 (gate not released; would be a premature no-op).

## Verification commands (exact, in order)
1. `date -u && TZ=America/New_York date`
2. `python3 research/extend_paper_trading_state.py 2>&1 | tail -25`
3. `python3 research/drift_persistence_report.py 2>&1 | tail -4`
4. `python3 research/extend_paper_trading_state.py 2>&1 | tail -6`
5. `git status --porcelain data/ config/`

## Handoff notes (this session)
- This session verified the pre-close baseline only: gate NOT released, sessions_extended 0, NAV unchanged, idempotent, drift stored==recomputed, data/config clean. No state was written; no commit made.
- The real extension cannot run until the gate releases at ~22:00 UTC on 2026-11-04 (~17.5 hours after this session). The next agent must run the verification commands at/after that time.
- If yfinance does not return a completed 2026-11-04 bar at 22:00 UTC, expect sessions_extended==0 with an explicit reason and state unchanged; record exactly what the script prints.