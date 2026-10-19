# Next Agent Task: Post-Gate Monitoring (Cycle 856)

## Context
Cycle 855 (2026-10-19) implemented and verified the session-safe raw-cache refresh tool. Cycle 856 (2026-10-19T14:54Z) ran post-gate monitoring: no new completed US session (cache still pinned at 2026-10-16). Both `refresh_raw_cache.py --dry-run` and `extend_paper_trading_state.py --dry-run` were no-ops. Drift flag `low_rolling_sharpe` persists at -0.21188351222842883.

## Objective
Continue post-gate monitoring; verification-only unless a new completed session appears. If a completed session is available, run `python research/refresh_raw_cache.py` then `python research/extend_paper_trading_state.py` once.

## Acceptance Criteria
1. `python -m pytest -q` passes (27 tests).
2. Per-symbol raw cache max dates checked; no partial bars.
3. `python research/_tmp_cycle77_verify.py` prints OVERALL: PASS.
4. `python .github/scripts/test_kilo_supervisor_loop.py` prints OK.
5. `.kilo-runtime/worker-disposition.json` updated (verified).

## Validation Commands
- python -m pytest -q
- python research/refresh_raw_cache.py --dry-run
- python research/extend_paper_trading_state.py --dry-run
- python research/_tmp_cycle77_verify.py
- python .github/scripts/test_kilo_supervisor_loop.py