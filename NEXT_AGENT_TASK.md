# Next Agent Task: Gate-Met Protocol — Cycle 522

## Context
Cycle 521 completed at 2026-10-16T05:38:30Z (UTC). Gate is 2026-10-18T20:00:00Z. All verifications passed: rolling 63d Sharpe diff 5.13e-16, regime flips 6/447, supervisor loop tests 10/10. Report written at research/reports/paper_trading_validation_521.md. Worker disposition recorded as "verified" for recommendation_id 38817660960-attempt-1-review-0003-2ac0cb7d6609.

Track record: 447 days (2025-01-02 → 2026-10-14), current_nav $135,043.35, max DD -2.93%, rolling 63d Sharpe 0.11333. Drift flag `low_rolling_sharpe` persists in state; below the >20-day persistence threshold.

## Objective
1. Record UTC time (TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ).
2. If < 2026-10-18T20:00:00Z: continue monitoring only (same minimal verifications as Cycle 520).
3. If >= 2026-10-18T20:00:00Z: proceed with the gate-met protocol per Cycle 486:
    - Re-attempt data acquisition from Yahoo Finance (force=True, end_date 2026-11-30) for the incumbent 7-ETF universe (SPY, QQQ, IWM, TLT, GLD, EFA, EEM) plus SPY and ^VIX.
    - Verify per-symbol max dates and confirm real (nonzero volume) data for each incumbent ETF; note ^VIX placeholder rows (Volume=0) are expected.
    - Re-run `research/run_paper_trading_replay.py` with appropriate end_date (yfinance exclusive-end semantics).
    - Confirm state: track record length/dates, NAV metrics, Sharpe, max DD, rolling 63d Sharpe, regime flips (expect 6), drift flag status.
    - Write research/reports/paper_trading_validation_522.md with UTC time, gate state, verification results, and data-acquisition outcome.
4. Update .kilo-runtime/worker-disposition.json per protocol (schema_version 1) within the next two tool calls; use recommendation_id from current-supervisor-recommendation.json if present, else "38817660960-attempt-1-review-0003-2ac0cb7d6609". Set disposition to "verified" with concrete reason/evidence/verification/updated_at (ISO-8601 UTC).

## Validation Commands
```bash
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ
python3 <<'PY'
import yaml, math
d = yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
ret = d['cumulative_returns'][-63:]
if len(ret) > 1:
    m = sum(ret) / len(ret); v = sum((r - m) ** 2 for r in ret) / (len(ret) - 1)
    s = (m * 252) / (math.sqrt(v) * math.sqrt(252)) if v > 0 else 0
else:
    s = ret[0] if ret else 0
stored = d['drift_flags']['low_rolling_sharpe']['value']
print('diff', abs(s - stored))
PY
python3 <<'PY'
import yaml
d = yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
rh = d['run_history']
t = 0
if rh:
    prev = rh[0]['regime_exposure']
    for i in range(1, len(rh)):
        if rh[i]['regime_exposure'] != prev: t += 1; prev = rh[i]['regime_exposure']
print('flips', t, 'len', len(rh))
PY
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries
- No commits unless explicitly requested.
- No strategy or data-acquisition changes before the gate; after the gate, only the Cycle 486 gate-met data acquisition/replay protocol.