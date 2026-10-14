# Dual-track Kilo agent communication protocol

## Purpose

Kilo's supervisor and research worker communicate through two complementary records:

- `agent-dialogue.jsonl` is the readable, chronological role-boundary transcript. It records messages actually injected into the worker and correlated worker replies observed by the supervisor.
- `agent-communication.jsonl` is the append-only lifecycle ledger. It separates writing a message, delivering it, worker acknowledgement, worker processing, superseding an unanswered message, and evaluating completion.

Both records use version 2 event records produced by `.github/scripts/kilo_dialogue_protocol.py`. Each event has a UUID event id, UTC timestamp, direction, role, task/run/session/message IDs, correlation ID, message type, priority, scope boundaries, acceptance-criteria references, delivery/acknowledgement state, reason/evidence/verification, work performed, blockers, changed files, commit/checkpoint SHAs, commands, tests, artifact references, outstanding work, a redacted message, and an idempotency digest. Sensitive values are redacted before the record is written.

## Worker response contract

The controller owns `.kilo-runtime/current-supervisor-recommendation.json`; the worker must not overwrite it. The worker records acknowledgement/disposition and task evidence in `.kilo-runtime/worker-disposition.json`. The worker response copies the exact current recommendation ID and task ID. Stale or unmatched responses are not associated with the active message.

Runtime state files remain out of Git. Actual role-boundary messages and lifecycle transitions are saved into the run's `kilo-progress-trace-<run_id>` artifact. The plugin injects newly journaled advice at the next Kilo tool-result boundary; this avoids claiming the model can be interrupted mid-tool-call. A cutoff preserves the artifacts for review, but this implementation does not automatically replay an earlier run's communication into a new run.

## Completion gate

The CLI command `completion-status` evaluates a task-scoped communication history and writes `task-completion-status.json`. It does not infer completion from supervisor advice, delivery, acknowledgement, a worker's `verified` disposition, a green workflow, or a local commit. Verified completion requires:

1. A supervisor message recorded as written and delivered, plus a correlated worker-processed response.
2. A controller-owned version-1 verification manifest scoped to the exact task.
3. Controller-verified acceptance criteria, each with passing status and an evidence reference.
4. Independently verified passing test results with exit code 0 and references.
5. Independently verified artifacts with evidence references.
6. An exact 40-character remote checkpoint SHA that matches the controller's verified persistence result.
7. No outstanding work or blockers.

The current workflow runs the gate in report-only mode and does **not** automatically issue a positive controller-verification manifest. In the absence of independent verification, the status remains `awaiting_worker_response`, `awaiting_independent_verification`, `blocked`, or `incomplete_evidence`. A maintainer or a separately trusted controller verification step must validate the evidence before positive completion can be recorded.

## Reliability properties and limits

- JSONL appends are serialized with an OS file lock, deduplicated by event digest, flushed, and fsynced. A malformed or incomplete trailing record is reported and not silently overwritten.
- Retries are bounded; the transcript write failures stay visible. The workflow's existing cadence, session target, concurrency controls, and 355-minute cutoff are unchanged.
- Unit/integration tests use local temporary files and local Git-like evidence; they do not prove that a hosted Kilo worker replied during a production run.
- CI success verifies the implementation and test cases, not the success of a research task. Check both tracks and the completion-status artifact for each run.
