# Bounded Kilo dual-track end-to-end verification task

This activation is a live protocol test, not a general research session. Use only the checked-out non-default infra branch and work within the 10-minute controller cutoff.

## One bounded deliverable

Create exactly this durable report: `docs/verification/kilo-e2e-run-__RUN_ID__-attempt-__RUN_ATTEMPT__.md`.

The report must begin with the exact marker `KILO_E2E_TASK_REPORT_V1` and include:
- the run ID and attempt-derived task ID (`__RUN_ID__-attempt-__RUN_ATTEMPT__`);
- the exact target branch and original checked-out HEAD;
- the recommendation ID and the recommendation's own `session_id` from the actual `.kilo-runtime/current-supervisor-recommendation.json` received in this run;
- the actual worker invocation's `session_id` from the live `KILO_WORKER_SESSION_ID` environment/runtime evidence; include it separately from the recommendation's session ID and never substitute one for the other;
- the worker disposition actually written to `.kilo-runtime/worker-disposition.json`;
- the actual focused commands run and their observed exit codes;
- a clear statement of any missing acknowledgement, processed response, event-correlation problem, test failure, or other blocker.

Do not fabricate, edit, or synthesize dialogue events, worker replies, artifact IDs, verification manifests, remote checkpoint SHAs, or controller verification results. The controller and verifier own those records. If the live recommendation or its correlated acknowledgement/processed response is missing, state that honestly; do not claim that the end-to-end test passed.

## Required execution behavior

1. The controller now gates this E2E activation until a valid recommendation with the same run/task ID and its append-only `message_written` event exist. Immediately read `.kilo-runtime/current-supervisor-recommendation.json`; verify its `task_id` matches this run, acknowledge or explicitly reject that actual recommendation, and write `.kilo-runtime/worker-disposition.json` promptly with its exact `recommendation_id` and `task_id`. Set the disposition `session_id` to this worker invocation's actual `KILO_WORKER_SESSION_ID` (obtain the value from live runtime evidence); do not copy the recommendation's `session_id` into this field merely because it is available. Include `recommendation_session_id` and actual worker `session_id` as separate report fields. The disposition must also include `acknowledgement_state`, `disposition`, `reason`, `evidence`, `verification`, `work_performed`, `blockers`, `changed_files`, `commands_executed`, `test_outcomes`, `artifact_refs` and `outstanding_work`. Never treat your own disposition as independent proof. If the recommendation is unexpectedly missing or mismatched, stop the test task, report it as blocked, and do not claim verified completion.
2. Inspect the existing protocol implementation and actual runtime records. Do not edit controller-owned trace files.
3. Run `bash -n .github/scripts/kilo-controller.sh`, `python3 .github/scripts/test_kilo_dialogue_protocol.py`, and `python3 .github/scripts/test_kilo_supervisor_loop.py`. Record actual exit codes; fix only a demonstrated task-scoped defect if necessary.
4. Write the report with evidence observed in this session. Include no credentials, tokens, secrets, or unrelated repository changes.
5. Before reporting a verified disposition, ensure the report exists, focused checks actually passed, no blockers remain, and the worker disposition accurately reflects the task. If any required check is blocked, set an appropriate blocked/rejected disposition and document why.
6. Do not merge, change workflow definitions, modify research datasets/registries, push to `main`, remove control markers, or broaden the task. The controller will persist work only to the selected infra branch; independent verification runs after your session.

The controller enforces a 10-minute hard cutoff and a one-session target for this run. References in the generic prompt to the normal 355-minute workflow do not override this cutoff.