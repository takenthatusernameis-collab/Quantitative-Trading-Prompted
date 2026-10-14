#!/usr/bin/env python3
"""Versioned Kilo supervisor/worker message protocol and evidence-gated completion checks."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
DIRECTIONS = {"supervisor_to_worker", "worker_to_supervisor", "controller_internal"}
STAGES = {
    "message_written", "message_delivered", "worker_acknowledged",
    "worker_processed", "message_superseded", "completion_gate_evaluated",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TEXT_LIMIT = 12000
LIST_LIMIT = 64


class ProtocolError(ValueError):
    """The append-only communication record is malformed or unsafe to extend."""


def _redact(value: str) -> str:
    value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    value = re.sub(r"(?i)(authorization\s*:\s*bearer)\s+[A-Za-z0-9._~+/\-=]+", r"\1 [REDACTED]", value)
    value = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b", "[REDACTED_GITHUB_TOKEN]", value)
    value = re.sub(r"\bsk-[A-Za-z0-9_-]{20,}\b", "[REDACTED_API_KEY]", value)
    value = re.sub(r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]", value)
    return value[:TEXT_LIMIT]


def _text(value: Any, limit: int = 2000) -> str:
    return _redact(value if isinstance(value, str) else "")[:limit]


def _list(value: Any, *, item_limit: int = 500) -> list:
    if not isinstance(value, list):
        return []
    clean = []
    for item in value[:LIST_LIMIT]:
        if isinstance(item, str):
            clean.append(_redact(item)[:item_limit])
        elif isinstance(item, dict):
            safe_item = {}
            for key, val in list(item.items())[:16]:
                key = str(key)[:80]
                if isinstance(val, str):
                    safe_item[key] = _redact(val)[:item_limit]
                elif isinstance(val, (int, float, bool)) or val is None:
                    safe_item[key] = val
                else:
                    safe_item[key] = _redact(str(val))[:item_limit]
            clean.append(safe_item)
    return clean


def make_event(
    *,
    stage: str,
    direction: str,
    role: str,
    message_id: str,
    message: str,
    task_id: str = "",
    run_id: str = "",
    session_id: str = "",
    message_type: str = "",
    priority: str = "normal",
    scope_boundaries: Any = None,
    acceptance_criteria: Any = None,
    correlation_id: str = "",
    delivery_state: str = "not_applicable",
    acknowledgement_state: str = "pending",
    disposition: str = "",
    reason: str = "",
    evidence: str = "",
    verification: str = "",
    work_performed: str = "",
    blockers: Any = None,
    changed_files: Any = None,
    commit_sha: str = "",
    checkpoint_sha: str = "",
    commands_executed: Any = None,
    test_outcomes: Any = None,
    artifact_refs: Any = None,
    outstanding_work: Any = None,
    event_id: str = "",
) -> dict:
    """Build one complete versioned event. Empty evidence remains explicit, not inferred."""
    safe_message = _text(message, TEXT_LIMIT)
    effective_run_id = _text(run_id or os.environ.get("GITHUB_RUN_ID", ""), 100)
    effective_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    effective_task_id = task_id or (f"{effective_run_id}-attempt-{effective_attempt}" if effective_run_id else "unscoped-task")
    values = {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id or str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "direction": direction,
        "role": role,
        "message_id": _text(message_id, 180),
        "task_id": _text(effective_task_id, 220),
        "run_id": effective_run_id,
        "session_id": _text(session_id or os.environ.get("KILO_WORKER_SESSION_ID", ""), 220),
        "message_type": _text(message_type, 100),
        "priority": _text(priority, 30) or "normal",
        "scope_boundaries": _list(scope_boundaries),
        "acceptance_criteria": _list(acceptance_criteria),
        "correlation_id": _text(correlation_id or message_id, 220),
        "delivery_state": _text(delivery_state, 40),
        "acknowledgement_state": _text(acknowledgement_state, 40),
        "disposition": _text(disposition, 80),
        "reason": _text(reason),
        "evidence": _text(evidence),
        "verification": _text(verification),
        "work_performed": _text(work_performed),
        "blockers": _list(blockers),
        "changed_files": _list(changed_files, item_limit=500),
        "commit_sha": _text(commit_sha, 80),
        "checkpoint_sha": _text(checkpoint_sha, 80),
        "commands_executed": _list(commands_executed),
        "test_outcomes": _list(test_outcomes),
        "artifact_refs": _list(artifact_refs),
        "outstanding_work": _list(outstanding_work),
        "message": safe_message,
    }
    key_material = "\0".join((
        values["direction"], values["stage"], values["message_id"],
        values["correlation_id"], values["message"], values["disposition"],
    ))
    values["event_key"] = hashlib.sha256(key_material.encode("utf-8")).hexdigest()
    validate_event(values)
    return values


def validate_event(value: Any) -> None:
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise ProtocolError("event must be a JSON object with schema_version=2")
    string_fields = (
        "event_id", "timestamp_utc", "stage", "direction", "role", "message_id",
        "task_id", "run_id", "session_id", "message_type", "priority", "correlation_id",
        "delivery_state", "acknowledgement_state", "disposition", "reason", "evidence",
        "verification", "work_performed", "commit_sha", "checkpoint_sha", "message", "event_key",
    )
    for key in string_fields:
        if not isinstance(value.get(key), str):
            raise ProtocolError(f"event field {key!r} must be a string")
    for key in ("event_id", "timestamp_utc", "stage", "direction", "role", "message_id", "task_id", "correlation_id", "message", "event_key"):
        if not value[key].strip():
            raise ProtocolError(f"event field {key!r} must be a non-empty string")
    if value["direction"] not in DIRECTIONS:
        raise ProtocolError("event direction is not recognized")
    if value["stage"] not in STAGES:
        raise ProtocolError("event stage is not recognized")
    if len(value["message"]) > TEXT_LIMIT:
        raise ProtocolError("event message exceeds the size limit")
    for key in ("scope_boundaries", "acceptance_criteria", "blockers", "changed_files", "commands_executed", "test_outcomes", "artifact_refs", "outstanding_work"):
        if not isinstance(value.get(key), list) or len(value[key]) > LIST_LIMIT:
            raise ProtocolError(f"event field {key!r} must be a bounded list")
    if not re.fullmatch(r"[0-9a-f]{64}", value["event_key"]):
        raise ProtocolError("event_key must be a SHA-256 hex digest")


def append_event(path: Path, event: dict) -> bool:
    """Append one event once, under a file lock; never silently truncate a partial/corrupt log."""
    validate_event(event)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if path.exists():
            content = path.read_bytes()
            if content and not content.endswith(b"\n"):
                raise ProtocolError(f"{path} has an incomplete trailing record; refusing to append")
            for index, raw in enumerate(content.splitlines(), start=1):
                try:
                    old = json.loads(raw)
                    validate_event(old)
                except (json.JSONDecodeError, ProtocolError) as exc:
                    raise ProtocolError(f"{path} record {index} is malformed; refusing to append") from exc
                if old.get("event_key") == event["event_key"]:
                    return False
        payload = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        try:
            written = os.write(fd, payload)
            if written != len(payload):
                raise ProtocolError("short append while writing dialogue event")
            os.fsync(fd)
        finally:
            os.close(fd)
        return True
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def read_events(path: Path) -> tuple[list[dict], list[str]]:
    """Read a transcript without disguising missing, malformed, or partial records."""
    path = Path(path)
    if not path.is_file():
        return [], [f"missing transcript: {path.name}"]
    try:
        content = path.read_bytes()
    except OSError as exc:
        return [], [f"cannot read transcript {path.name}: {type(exc).__name__}"]
    if content and not content.endswith(b"\n"):
        return [], [f"incomplete trailing record: {path.name}"]
    events = []
    errors = []
    for index, raw in enumerate(content.splitlines(), start=1):
        try:
            event = json.loads(raw)
            validate_event(event)
            events.append(event)
        except (json.JSONDecodeError, ProtocolError) as exc:
            errors.append(f"{path.name}:{index}: {type(exc).__name__}")
    return events, errors


def _verified_checklist(items: Any, kind: str) -> bool:
    if not isinstance(items, list) or not items:
        return False
    for item in items:
        if not isinstance(item, dict) or item.get("verified_by") != "controller":
            return False
        if not isinstance(item.get("evidence_ref"), str) or not item["evidence_ref"].strip():
            return False
        if kind == "criterion" and item.get("status") != "passed":
            return False
        if kind == "test" and (item.get("status") != "passed" or item.get("exit_code") != 0):
            return False
        if kind == "artifact" and item.get("verified") is not True:
            return False
    return True


def evaluate_completion(
    *,
    dialogue_path: Path,
    communication_path: Path,
    verification_path: Path | None,
    task_id: str,
    checkpoint_sha: str = "",
    checkpoint_persisted: bool = False,
) -> dict:
    """Return verified completion only with a correlated worker response and independent evidence."""
    dialogue, dialogue_errors = read_events(dialogue_path)
    communication, communication_errors = read_events(communication_path)
    errors = dialogue_errors + communication_errors
    non_missing_errors = [item for item in errors if not item.startswith("missing transcript:")]
    task_events = [e for e in communication if e.get("task_id") == task_id]
    dialogue_task = [e for e in dialogue if e.get("task_id") == task_id]
    written_ids = {
        e["message_id"] for e in task_events
        if e["direction"] == "supervisor_to_worker" and e["stage"] == "message_written"
    }
    delivered_ids = {
        e["message_id"] for e in task_events
        if e["direction"] == "supervisor_to_worker"
        and e["stage"] == "message_delivered"
        and e["message_id"] in written_ids
    }
    replies = [
        e for e in task_events
        if e["direction"] == "worker_to_supervisor"
        and e["stage"] == "worker_processed"
        and e.get("correlation_id") in delivered_ids
    ]
    status = "awaiting_independent_verification"
    reasons: list[str] = []
    if non_missing_errors:
        status = "incomplete_evidence"
        reasons.extend(non_missing_errors)
    elif not delivered_ids:
        status = "awaiting_worker_response"
        reasons.append("No delivered supervisor message linked to a recorded written message exists for this task.")
    elif not replies:
        status = "awaiting_worker_response"
        reasons.append("No correlated worker response is recorded; recommendation text is not a reply.")
    else:
        response = replies[-1]
        if response.get("disposition") in {"blocked", "rejected_with_reason", "superseded"}:
            status = "blocked"
            reasons.append("The correlated worker response records a blocker, rejection, or superseded task.")
        elif response.get("blockers") or response.get("outstanding_work"):
            status = "blocked"
            reasons.append("Worker response reports blockers or outstanding work.")
        elif response.get("disposition") != "verified":
            status = "awaiting_independent_verification"
            reasons.append("Worker has not reported a verified disposition.")
        elif not response.get("work_performed") or not response.get("verification"):
            status = "awaiting_independent_verification"
            reasons.append("Worker response lacks work performed or verification details.")
        else:
            reasons.append("Worker completion claim is present but is not independent verification.")

    manifest = None
    if verification_path and Path(verification_path).is_file():
        try:
            manifest = json.loads(Path(verification_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            status = "incomplete_evidence"
            reasons.append("Controller verification manifest is unreadable or malformed.")
    if manifest is None:
        reasons.append("No controller-owned task-acceptance verification manifest was supplied.")
    else:
        manifest_ok = (
            isinstance(manifest, dict)
            and manifest.get("schema_version") == 1
            and manifest.get("verifier") == "controller"
            and manifest.get("task_id") == task_id
        )
        criteria_ok = manifest_ok and _verified_checklist(manifest.get("acceptance_criteria"), "criterion")
        tests_ok = manifest_ok and _verified_checklist(manifest.get("tests"), "test")
        artifacts_ok = manifest_ok and _verified_checklist(manifest.get("artifacts"), "artifact")
        remote = manifest.get("remote_checkpoint", {}) if manifest_ok else {}
        manifest_sha = remote.get("sha", "") if isinstance(remote, dict) else ""
        remote_ok = (
            manifest_ok
            and isinstance(remote, dict)
            and remote.get("verified") is True
            and isinstance(manifest_sha, str)
            and bool(SHA_RE.fullmatch(manifest_sha))
            and checkpoint_persisted
            and bool(SHA_RE.fullmatch(checkpoint_sha or ""))
            and manifest_sha == checkpoint_sha
        )
        no_open_work = not manifest.get("blockers") and not manifest.get("outstanding_work") if manifest_ok else False
        if not manifest_ok:
            reasons.append("Verification manifest must be version 1, controller-issued, and scoped to this task.")
        if not criteria_ok:
            reasons.append("Every acceptance criterion needs controller-verified pass status and an evidence reference.")
        if not tests_ok:
            reasons.append("At least one independently verified test result with exit code 0 is required.")
        if not remote_ok:
            reasons.append("Exact remote checkpoint SHA was not independently confirmed against controller persistence state.")
        if not artifacts_ok:
            reasons.append("At least one required artifact must be independently verified and referenced.")
        if not no_open_work:
            reasons.append("Controller verification manifest reports blockers or outstanding work.")
        if manifest_ok and criteria_ok and tests_ok and artifacts_ok and remote_ok and no_open_work and not non_missing_errors and replies and replies[-1].get("disposition") == "verified" and not replies[-1].get("blockers") and not replies[-1].get("outstanding_work") and replies[-1].get("work_performed") and replies[-1].get("verification"):
            status = "verified_completion"
            reasons = ["Worker response, task-scoped acceptance criteria, tests, artifacts, and exact remote checkpoint passed independent controller verification."]

    if errors:
        reasons.extend(errors)
    last_reply = replies[-1] if replies else None
    return {
        "schema_version": 1,
        "task_id": task_id,
        "status": status,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "worker_response_captured": bool(last_reply),
        "worker_disposition": last_reply.get("disposition") if last_reply else None,
        "remote_checkpoint_sha": checkpoint_sha or None,
        "remote_checkpoint_verified": bool(checkpoint_persisted and SHA_RE.fullmatch(checkpoint_sha or "")),
        "acceptance_criteria_verified": bool(manifest and _verified_checklist(manifest.get("acceptance_criteria"), "criterion")),
        "tests_verified": bool(manifest and _verified_checklist(manifest.get("tests"), "test")),
        "artifacts_verified": bool(manifest and _verified_checklist(manifest.get("artifacts"), "artifact")),
        "dialogue_events": len(dialogue_task),
        "communication_events": len(task_events),
        "transcript_errors": errors,
        "reasons": list(dict.fromkeys(reasons)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gate = sub.add_parser("completion-status")
    gate.add_argument("--dialogue", type=Path, required=True)
    gate.add_argument("--communication", type=Path, required=True)
    gate.add_argument("--verification", type=Path, default=None)
    gate.add_argument("--task-id", required=True)
    gate.add_argument("--checkpoint-sha", default="")
    gate.add_argument("--checkpoint-persisted", choices=("0", "1"), default="0")
    gate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = evaluate_completion(
        dialogue_path=args.dialogue,
        communication_path=args.communication,
        verification_path=args.verification,
        task_id=args.task_id,
        checkpoint_sha=args.checkpoint_sha,
        checkpoint_persisted=args.checkpoint_persisted == "1",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    event = make_event(
        stage="completion_gate_evaluated",
        direction="controller_internal",
        role="controller",
        message_id=f"{args.task_id}-completion-gate",
        correlation_id=args.task_id,
        task_id=args.task_id,
        message=f"Task completion gate result: {result['status']}.",
        disposition=result["status"],
        evidence="; ".join(result["reasons"][:8]),
        verification=f"Transcript events={result['communication_events']}; transcript errors={len(result['transcript_errors'])}.",
        checkpoint_sha=args.checkpoint_sha,
        delivery_state="not_applicable",
        acknowledgement_state="not_applicable",
    )
    try:
        append_event(args.communication, event)
    except (OSError, ProtocolError) as exc:
        print(f"warning: completion status written but lifecycle event could not be appended: {type(exc).__name__}", file=sys.stderr)
    print(json.dumps({"status": result["status"], "reasons": result["reasons"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
