# Paper Trading Validation Report - Cycle 111

## UTC Session Time
2026-10-15T13:44:03Z

## Post-Close Gate Evaluation
Gate time: 2026-10-17T20:00:00Z
Comparison: session_time (2026-10-15T13:44:03Z) < gate_time (2026-10-17T20:00:00Z)
Result: **Gate not met**. No fetch or replay performed.

## Verification Steps (Performed Despite Gate Not Being Met)

### 3. Independent Rolling-63-Day Sharpe Verification
- Computed from last 63 cumulative returns: 0.11333136870186278
- Stored value in state.drift_flags.low_rolling_sharpe.value: 0.11333136870186329
- Difference: ~5.3e-16 (within float precision)
- Status: **PASS**

### 4. Regime Flip Verification
- Recomputed regime flips from run_history.regime_exposure transitions: 6
- Stored value (from context): 6
- Status: **PASS**

### 5. Supervisor Loop Tests
- Command: `python3 .github/scripts/test_kilo_supervisor_loop.py -v`
- Result: All 10 tests passed (see detailed output below)
- Status: **PASS**

## Test Output Summary
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

## Track Record (Unchanged)
- Track record days: 447 (2025-01-02 → 2026-10-14)
- NAV: $135,043.35
- Sharpe: 1.9272
- Max drawdown: -2.93%
- Rolling 63-day Sharpe: 0.11333136870186278
- Drift flag: Persists (3 consecutive days, not yet >20d threshold)

## Notes
- No new real trading day data was fetched due to gate not being met.
- The post-close gate is preserved and will be re-evaluated in the next cycle.
- This report documents the gate not being met for Cycle 111.

## Next Task
The same gate enforcement task is left for the next cycle (Cycle 112), with the gate unchanged at 2026-10-17T20:00:00Z.