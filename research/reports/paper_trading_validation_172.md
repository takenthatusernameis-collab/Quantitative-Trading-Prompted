# Paper Trading Validation — Cycle 172 (Gate Pending)

**Session UTC:** 2026-10-15T17:46:07Z
**Post-close gate:** 2026-10-18T20:00:00Z UTC
**Gate status:** NOT MET (session_time < gate_time)
**Action:** No fetch, no replay — minimal verification only.

---

## State Snapshot (from `data/processed/paper_trading_state.yaml`)

- **Track record length:** 447 days (2025-01-02 → 2026-10-14)
- **Last run date:** 2026-10-14
- **Run history records:** 447
- **Current NAV:** $135,043.35
- **Peak NAV:** $139,120.07
- **Max drawdown:** -2.93%
- **Full-period Sharpe:** 1.8170
- **Rolling 63d Sharpe (stored drift flag):** 0.11333136870186329
- **Regime flips (stored):** 6
- **Drift flag:** `low_rolling_sharpe` active (3 consecutive days: 2026-10-12, 2026-10-13, 2026-10-14)
- **Current regime:** Risk-on (exposure=1.0), 132 days

---

## Independent Verification

### Rolling 63-day Sharpe Recomputation
```
Recomputed: 0.11333136870186278
Stored:     0.11333136870186329
Diff:       5.13e-16  (within float precision)
```
✅ **MATCH** — drift flag value verified.

### Regime Flips Recomputation
```
Recomputed flips: 6
Run history length: 447
```
✅ **MATCH** — 6 regime flips confirmed.

---

## Supervisor Loop Tests
```
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```
**Result:** 10/10 tests PASSED (0.658s)

```
test_agent_and_runner_share_recoverable_report_contract ... ok
test_failed_review_keeps_feedback_without_transcript_dumps ... ok
test_file_backed_dialogue_protocol_rejects_stale_or_malformed_dispositions ... ok
test_missing_report_without_actionable_final_response_is_not_published ... ok
test_report_fallback_requires_status_on_first_line ... ok
test_report_missing_recovers_final_response_and_publishes_advice ... ok
test_role_dialogue_log_records_only_distinct_messages_in_both_directions ... ok
test_secret_redaction_before_model_input ... ok
test_single_timeout_does_not_repeat_without_new_evidence ... ok
test_two_cycles_preserve_feedback_without_recording_internal_prompts ... ok
```

---

## Gate Enforcement

- Session time: 2026-10-15T17:46:07Z
- Post-close gate: 2026-10-18T20:00:00Z
- **No fetch/replay performed** — gate not met per protocol.
- Git working tree: no changes to data or source files (clean except for this report).

---

## Go/No-Go Gate Status

| Gate | Value | Threshold | Status |
|------|-------|-----------|--------|
| Track record length | 447 days | > 126 days | ✅ PASS |
| Net-of-cost Sharpe | 1.8170 | >= 0.9 | ✅ PASS |
| Max drawdown | -2.93% | < 15% | ✅ PASS |
| Regime flips | 6 | > 1 | ✅ PASS |
| Rolling 63d Sharpe | 0.1133 | drift flag active | ⚠️ MONITOR |

All primary go/no-go gates pass. The drift flag (low rolling 63d Sharpe) persists at 3 consecutive days, below the >20-day persistence threshold for concern. Strategy remains frozen pending post-close gate.

---

## Summary

Session time 2026-10-15T17:46:07Z is before the post-close gate (2026-10-18T20:00:00Z). No fetch or replay was performed. All verifications pass independently: rolling 63d Sharpe recomputed = 0.11333136870186278 (matches stored 0.11333136870186329 within 5.13e-16), regime flips recomputed = 6 (matches stored 6 over 447 entries), supervisor loop tests 10/10 passed. Strategy frozen, state unchanged from Cycle 171. Next cycle should re-evaluate gate status at session time.

---

## Reproduction Commands

```bash
TZ=UTC date -u +%Y-%m-%dT%H:%M:%SZ
python3 -c "
import yaml,math
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
ret=d['cumulative_returns'][-63:]
m=sum(ret)/len(ret); v=sum((r-m)**2 for r in ret)/(len(ret)-1)
s=(m*252)/(math.sqrt(v)*math.sqrt(252)) if v>0 else 0
print('sharpe',s,d['drift_flags']['low_rolling_sharpe']['value'], abs(s-d['drift_flags']['low_rolling_sharpe']['value']))
"
python3 -c "
import yaml
d=yaml.safe_load(open('data/processed/paper_trading_state.yaml'))
rh=d['run_history']; t=0; prev=rh[0]['regime_exposure']
for i in range(1,len(rh)):
  if rh[i]['regime_exposure']!=prev: t+=1; prev=rh[i]['regime_exposure']
print('flips',t,len(rh))
"
python3 .github/scripts/test_kilo_supervisor_loop.py -v
```
