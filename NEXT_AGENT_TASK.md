# NEXT_AGENT_TASK — Paper-trading extension gate check (2026-11-04 post-close)

## Context
- Verified 2026-11-04 ~10:43 UTC (05:43 EST, Wednesday): last processed session 2026-11-03, NAV 132866.0435881768, sessions_extended 0, 0 writes.
- Clock gate NOT released at run time; candidate session 2026-11-04 has not closed.
  - Reason: `next session 2026-11-04 has not closed yet (today and still in progress); no completed candidate bar exists to extend into`
- Gate releases at 17:00 ET / 22:00 UTC on 2026-11-04 (Wednesday) — i.e. once the local ET clock passes 17:00 on the 2026-11-04 session date.
- drift_persistence_report: stored == recomputed True (rolling 63d Sharpe -1.3997 at 2026-11-03).
- Idempotency confirmed (2nd invocation: 0 writes, NAV unchanged).
- `git status --porcelain data/ config/` -> empty (clean). Only non-data/config artifact: `research/reports/paper_trading_rolling.md` git_sha provenance line bumps whenever `drift_persistence_report.py` runs — expected, self-generated report metadata, documented in README.md; left as-is.
- Supervisor recommendation cycle 0008 (advisory) verified and dispositioned: the only unstaged change is the self-generated git_sha line in `paper_trading_rolling.md` (d619202 -> 770d0ff, current HEAD); no code change warranted.
- **Provider data lag (confirmed, Cycle 566 + re-verified this cycle):** an exhaustive scan of every `.parquet` under `data/` (raw + processed, 30+ files) finds **no** 2026-11-04 (or later) bar anywhere; the latest bar in the entire committed dataset is 2026-10-23 (^VIX). The live yfinance provider has not served a 2026-11-04 bar at any simulated gate-release time. So even after the clock gate releases there may be no completed candidate bar to extend into. This is a data-availability blocker, not a code defect.

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

## Handoff notes (this session, corrective invocation 971)
- This session verified the pre-close baseline only: gate NOT released, sessions_extended 0, NAV unchanged, idempotent, drift stored==recomputed True, data/config clean. No state was written; no commit made.
- **Durable change made this cycle:** prepended a new Cycle 1115 entry to README.md documenting this session's verification run and the resolution of supervisor recommendation cycle 0008 (the git_sha-only diff in `paper_trading_rolling.md` was verified as self-generated provenance metadata, not a substantive change). No source, data, config, test, gate, threshold, or cost-model content changed.
- The real extension cannot run until the gate releases at ~22:00 UTC on 2026-11-04. The global workflow cutoff (~10:20 UTC) precedes gate release, so no extension can complete in this session.
- If yfinance does not return a completed 2026-11-04 bar at 22:00 UTC, expect sessions_extended==0 with an explicit reason and state unchanged; record exactly what the script prints.
- **Next distinct investigation if provider remains lagged past gate release:** inventory alternate in-repo data sources for the paper-trading universe. This cycle's exhaustive `data/**/*.parquet` scan (the investigation handoff 758 asked for) confirms NO in-repo source — raw or processed — carries a 2026-11-04 bar; the latest committed bar is 2026-10-23. The blocker is therefore external data availability, not an in-repo feed choice.

(End of file - total 45 lines)