# Corrective Handoff inv 473

## Blocker diagnosis (materially different from prior failed invocations)
- inv 472 log (5 lines): `Error: Sign up for free to continue and explore 500 other models.` — a model-provider registration/credential error, not a code defect.
- inv 473 log (698 lines): re-ran the same Read + ls probe and hit the identical wall. No prior invocation made any durable change; the working tree still carried only the inv-230 handoff.
- This invocation's different approach: skip the failed probe, inspect the tree directly, and fix the two documented residual full-suite failures rather than re-running the pre-gate loop (which deterministically exits 0/STOP ~2 days before the gate).

## Changes made (all durable, all verified)
1. tests/test_shortlist_gross_edge_001.py — test_writes_nothing_outside_research was a test-fragility: it never ran the harness (despite its own "after running harness" comment) and asserted git diff --name-only subset of research/,tests/ against the whole working tree, so it failed whenever anything outside those dirs was uncommitted. Rewritten to snapshot git status --porcelain before and after the harness and diff only the harness's own changes; the harness runs once via a module-scoped harness_run fixture shared with test_determinism_two_runs_byte_identical.
2. research/reports/tsmomentum_same_session_vol_correction_001.md — refreshed from the tool's own PASS output (python research/tsmomentum_same_session_vol_correction.py, RC=0, OVERALL: PASS). The working-tree copy had carried an orphaned committed_artifacts_unchanged: FAIL / overall: FAIL written by a concurrent session; the tool computes PASS. Report now matches HEAD.

## Verification (exact commands and observed outputs)
- pytest -q tests/test_shortlist_gross_edge_001.py -> 5 passed (was 1 failed).
- pytest -q tests/test_tsmomentum_same_session_vol_correction.py -> 28 passed (was 3 failed).
- pytest -q tests/test_shortlist_gross_edge_001.py tests/test_tsmomentum_same_session_vol_correction.py -> 33 passed in 403.90s.
- pytest -q tests/test_shortlist_gross_edge_001.py tests/test_tsmomentum_same_session_vol_correction.py tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py tests/test_csmomentum_sample_gate_audit.py tests/test_go_no_go_evaluation.py -> 117 passed in 449.75s (no regression; inv-230 go_no_go parser fix holds).
- GATE_EPOCH=1794866400 STATE_SHA256=c438cd71785459e2612e2dda3425d670de920a62de532c0dff2da6fe332b6365 bash scripts/pre_gate_check.sh -> PRE-GATE OK: now=1794692472 (2026-11-14T21:41:12Z) < gate 1794866400 (2026-11-16T22:00:00Z); T-173928s remaining; state sha256 matches; data/raw clean. STOP EXIT=0.
- git status --porcelain -- data/raw -> 0 lines. State SHA256 c438cd71... == HEAD. git status --porcelain research/reports/tsmomentum_same_session_vol_correction_001.md -> empty (matches HEAD).
- Bare harness timing: research/shortlist_gross_edge_001.py -> rc 0 time 3.9, OVERALL: PASS.

## Scope discipline
- No production code, thresholds, gates, cost model, universe, or clock-gate values changed. Test-only fix plus one stale report refreshed from the tool's own PASS output. No commit (not requested).

## Residual blocker (deterministic, not a failure loop)
- Gate (2026-11-16T22:00:00Z) is ~2.02 days / T-173928s out. This controller envelope ends before the gate; the run active at/after the gate must execute Step 2.
- The model-provider registration error that blocked inv 472/473 is an environment/credential issue, not a repo defect — verify provider reachability before Step 2.