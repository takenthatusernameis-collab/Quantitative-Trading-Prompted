# Next Agent Task — Verify paper trading state after extension

## Context
- Current state: last processed session `2026-10-23` in `data/processed/paper_trading_state.yaml`. The extension task is waiting for `2026-10-26 17:00 ET` (Monday).
- After `extend_paper_trading_state.py` successfully extends by >=1 session, we need to verify integrity and produce a concise validation report.
- Prior verification: `python research/drift_persistence_report.py` shows `stored == recomputed: True`; all `tests/test_paper_trading_extend.py tests/test_drift_persistence.py` pass (29 passed).

## Objective
If `data/processed/paper_trading_state.yaml` has been extended beyond `2026-10-23` (new latest session date exists), verify integrity and write a validation report. If not yet extended (still at `2026-10-23`), do not extend - just confirm readiness state unchanged and report.

## Acceptance criteria
1. Read latest session date from `data/processed/paper_trading_state.yaml` (`run_history[-1].date` or equivalent).
2. If latest > `2026-10-23`:
   - Run `python research/drift_persistence_report.py` -> must show `stored == recomputed: True`
   - Run `python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q` -> all pass
   - `git status --porcelain data/` must be empty (or only intentional changes if committed per rules)
   - Write `research/reports/paper_trading_validation_post_extend_<YYYYMMDD>.md` with UTC timestamp, old/new latest dates, NAV change, rolling 63d Sharpe, drift status, and verification commands/results
3. If latest == `2026-10-23`: report "not yet extended; awaiting gate (2026-10-26 17:00 ET)" with readiness summary from `python research/extend_paper_trading_state.py` output; no data changes.
4. Never fabricate sessions; no strategy/gate/config changes.

## Validation commands
```bash
python3 -c "
import yaml
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
print(d['run_history'][-1]['date'])
"
python research/drift_persistence_report.py | tail -2
python -m pytest tests/test_paper_trading_extend.py tests/test_drift_persistence.py -q
git status --porcelain data/
```

## Scope boundaries
- No strategy/gate/threshold/config changes. Do not commit unless explicitly requested. Raw cache untouched. Research/backtesting only.
