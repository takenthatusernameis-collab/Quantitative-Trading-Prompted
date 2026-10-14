#!/usr/bin/env python3
"""Fail-open, 150-second-cadence Kilo supervisor for the active worker invocation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from kilo_dialogue_protocol import ProtocolError, append_event as append_protocol_event, make_event as make_protocol_event, read_events as read_protocol_events

STOP_REQUESTED = False
ACTIVE_REVIEW: Optional[subprocess.Popen[str]] = None

MAX_LOG_CHARS = 5_500
MAX_OBJECTIVE_CHARS = 2_500
MAX_REPORT_CHARS = 3_200
MAX_PREVIOUS_FEEDBACK_CHARS = 12_000
MAX_REVIEW_OUTPUT_CHARS = 1_200
MAX_CLI_TRANSCRIPT_CHARS = 24_000
MAX_WORKER_DISPOSITION_CHARS = 6_000
DIALOGUE_PROTOCOL_SCHEMA_VERSION = 1
VALID_WORKER_DISPOSITIONS = {
    "accepted", "in_progress", "verified", "blocked", "rejected_with_reason", "superseded",
}


def redact_sensitive_text(text: str) -> str:
    """Redact common credentials and terminal controls before sharing text."""
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    patterns = [
        (r"(?i)(authorization\s*:\s*bearer)\s+[A-Za-z0-9._~+/\-=]+", r"\1 [REDACTED]"),
        (r"(?i)\bbearer\s+[A-Za-z0-9._~+/\-=]{8,}", "Bearer [REDACTED]"),
        (r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b", "[REDACTED_GITHUB_TOKEN]"),
        (r"\bsk-[A-Za-z0-9_-]{20,}\b", "[REDACTED_API_KEY]"),
        (r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]"),
        (
            r"(?im)^(\s*(?:export\s+)?(?:GITHUB_TOKEN|GH_TOKEN|KILO_API_KEY|API_KEY|ACCESS_TOKEN|SECRET_KEY|CLIENT_SECRET|PASSWORD)\s*=\s*)\S.*$",
            r"\1[REDACTED]",
        ),
        (r"(?i)(https?://[^:/\s]+:)[^@/\s]+(@)", r"\1[REDACTED]\2"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def read_bounded(path: Path, maximum: int) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-maximum:]
    except (OSError, UnicodeError):
        return ""


def within_directory(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def safe_runtime_path(raw_path: str, runtime_root: Path) -> Optional[Path]:
    try:
        path = Path(raw_path).resolve()
        return path if within_directory(path, runtime_root) else None
    except (OSError, ValueError):
        return None


def read_active_worker_log(pointer_file: Path, runtime_root: Path) -> str:
    pointer_value = read_bounded(pointer_file, 4_000).strip()
    if not pointer_value:
        return ""
    log_path = safe_runtime_path(pointer_value, runtime_root)
    if log_path is None or not log_path.is_file():
        return ""
    return redact_sensitive_text(read_bounded(log_path, MAX_LOG_CHARS))


def read_git_snapshot(repo_root: Path) -> str:
    sections = []
    commands = (
        ("status", ["git", "status", "--short", "--branch"]),
        ("unstaged diff summary", ["git", "diff", "--stat"]),
        ("staged diff summary", ["git", "diff", "--cached", "--stat"]),
        ("recent checkpoint", ["git", "log", "-2", "--oneline"]),
    )
    for label, command in commands:
        try:
            result = subprocess.run(
                command, cwd=repo_root, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=4, check=False,
            )
            value = result.stdout.strip() or "(none)"
            if result.returncode:
                value = f"(unavailable; exit {result.returncode})"
            if label == "status" and value:
                # Supervisor report files are diagnostic output created by this monitor,
                # not changes made by the worker; exclude them to prevent self-triggered review loops.
                value = "\n".join(
                    line for line in value.splitlines()
                    if not re.match(r"^\?\?\s+\.kilo/supervisor-reports(?:/|$)", line)
                ) or "(no worker-visible repository status changes)"
            sections.append(f"{label}:\n{value}")
        except (OSError, subprocess.TimeoutExpired):
            sections.append(f"{label}:\n(unavailable)")
    return redact_sensitive_text("\n\n".join(sections))[-2_500:]


def build_review_prompt(
    objective: str,
    log_delta: str,
    git_snapshot: str,
    previous_feedback: str,
    report_relative_path: str,
    cycle: int,
    cadence_seconds: float,
    require_initial_recommendation: bool = False,
) -> str:
    if not log_delta.strip():
        log_delta = "(No new worker output since the previous review; assess repository/task state without inventing progress.)"
    if not previous_feedback.strip():
        previous_feedback = "(No previous supervisor recommendation.)"
    if require_initial_recommendation:
        bootstrap_instruction = """BOOTSTRAP REQUIREMENT:
No valid recommendation has yet been published. The initial recommendation is mandatory before worker startup in this bounded run. Produce one concise, evidence-based initial recommendation using only the supplied objective and repository snapshot. Do not invent defects, failures, or results. If evidence is insufficient to justify a code change, recommend the narrowest safe evidence-gathering step or explicitly recommend keeping completion blocked until evidence exists. For this required initial exchange, do not return NO_NEW_DIALOGUE."""
        no_new_dialogue_rule = "5. This is the required initial recommendation; do not return NO_NEW_DIALOGUE. If evidence is insufficient, issue STATUS: ATTENTION and state the missing evidence and safe next step."
    else:
        bootstrap_instruction = ""
        no_new_dialogue_rule = "{no_new_dialogue_rule}"
    return f"""CONTINUOUS KILO WORKER REVIEW — CYCLE {cycle}

You are the supervisor role in a two-role dialogue with an active worker. Review only new evidence, material repository-state changes, or a new worker disposition. Do not restate files, snapshots, old recommendations, or unchanged observations. If nothing material warrants a new worker message, write exactly NO_NEW_DIALOGUE on one line and do not produce the standard report. Never invent novelty just to fill a review cycle.

CURRENT WORKER OBJECTIVE / INSTRUCTIONS (redacted, truncated):
{objective[-MAX_OBJECTIVE_CHARS:]}

{bootstrap_instruction}

NEW OR MOST RELEVANT WORKER OUTPUT (redacted, truncated):
{log_delta[-MAX_LOG_CHARS:]}

CURRENT REPOSITORY STATE:
{git_snapshot}

PREVIOUS SUPERVISOR MESSAGE (context only; the worker receives only the latest pending message):
{previous_feedback[-MAX_PREVIOUS_FEEDBACK_CHARS:]}

REQUIRED ACTION — REPORT-FIRST, BOUNDED REVIEW:
1. Treat the supplied worker log delta, objective, repository snapshot, and prior advice as your primary evidence. Do not rebuild inventories, run backtests, install dependencies, or inspect unrelated files.
2. If one relevant detail is needed, make no more than two targeted read/search calls. Mark anything else unverified instead of continuing exploration.
3. Write the report to this exact path on your first available write operation, no later than your fourth tool call:
REPORT_PATH: {report_relative_path}
4. The report's first line must be exactly one of `STATUS: CONTINUE`, `STATUS: ATTENTION`, or `STATUS: CRITICAL`. Do not add a title. Then use plain, unnumbered headings with colons in this order: `Observed evidence:`, `Previous approaches:`, `Likely cause:`, `Different next step:`, `Verification:`, and `Limitations:`. Do not number or bold headings. Keep the report concise (about 150–250 words). `Alternative:` is optional only when the main step is blocked or materially uncertain.
5. If no new action or materially changed recommendation is warranted, write exactly NO_NEW_DIALOGUE with no other text; the controller will not send or record a duplicate message.
6. Do not tell the worker to restart, stop the workflow, weaken checks, or alter the existing 355-minute cutoff-only policy. Separate facts from hypotheses and do not claim unverified tests or file state.
7. Do not include credentials, tokens, passwords, timestamps, or cycle counters in the report unless materially necessary. Your permissions remain read/search plus report-path-scoped edit/write only; do not execute commands, browse the web, delegate, or control workflows.
8. If you cannot write the report or are about to exhaust the eight-step limit, return the same concise report in your final response prefixed by a standalone “REPORT_FALLBACK:” line. Include one evidence-supported next action and a focused verification check so the controller can recover it safely.

Review cadence target: {cadence_seconds} seconds. Your feedback is advisory. The worker must independently verify it and retains responsibility for all changes.
"""


def atomic_write(path: Path, content: str, *, ensure_newline: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            if ensure_newline and not content.endswith("\n"):
                handle.write("\n")
        os.replace(temporary_path, path)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def read_protocol_json(path: Optional[Path], maximum: int = MAX_WORKER_DISPOSITION_CHARS) -> Optional[dict]:
    """Read one bounded JSON protocol record; malformed/stale records never block the worker."""
    if path is None:
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        if len(raw) > maximum:
            return None
        value = json.loads(raw)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def read_worker_disposition(protocol_dir: Optional[Path], recommendation: Optional[dict] = None) -> Optional[dict]:
    """Read one correlated worker disposition; a verified claim is not task completion."""
    if protocol_dir is None:
        return None
    value = read_protocol_json(protocol_dir / "worker-disposition.json")
    if not value or value.get("schema_version") not in {1, 2}:
        return None
    recommendation_id = value.get("recommendation_id")
    disposition = value.get("disposition")
    reason = value.get("reason")
    if not isinstance(recommendation_id, str) or not recommendation_id.strip() or len(recommendation_id) > 180:
        return None
    if recommendation is not None and recommendation_id != recommendation.get("recommendation_id"):
        return None
    task_id = value.get("task_id", "")
    session_id = value.get("session_id", "")
    if value.get("schema_version") == 2:
        if not isinstance(task_id, str) or not task_id.strip() or len(task_id) > 220:
            return None
        if not isinstance(session_id, str) or not session_id.strip() or len(session_id) > 220:
            return None
        if recommendation is not None and task_id != recommendation.get("task_id"):
            return None
    if disposition not in VALID_WORKER_DISPOSITIONS:
        return None
    if not isinstance(reason, str) or len(reason.strip()) < 8:
        return None
    verification = value.get("verification", "")
    evidence = value.get("evidence", "")
    if not isinstance(verification, str) or not isinstance(evidence, str):
        return None
    if disposition == "verified" and not verification.strip():
        return None
    list_fields = ("acceptance_criteria", "blockers", "changed_files", "commands_executed", "test_outcomes", "artifact_refs", "outstanding_work")
    for field in list_fields:
        if field in value and not isinstance(value[field], list):
            return None
    # Do not infer an acknowledgement from a disposition: these are distinct states.
    acknowledgement = value.get("acknowledgement_state")
    if acknowledgement not in {"acknowledged", "rejected", "pending"}:
        return None
    return {
        "schema_version": 2,
        "recommendation_id": recommendation_id.strip(),
        "task_id": task_id[:220] if isinstance(task_id, str) else "",
        "session_id": session_id[:220] if isinstance(session_id, str) else "",
        "acknowledgement_state": acknowledgement,
        "disposition": disposition,
        "reason": redact_sensitive_text(reason)[:1_200],
        "evidence": redact_sensitive_text(evidence)[:1_200],
        "verification": redact_sensitive_text(verification)[:1_200],
        "work_performed": redact_sensitive_text(str(value.get("work_performed", "")))[:2_000],
        "blockers": value.get("blockers", [])[:64],
        "changed_files": value.get("changed_files", [])[:64],
        "commit_sha": str(value.get("commit_sha", ""))[:80],
        "checkpoint_sha": str(value.get("checkpoint_sha", ""))[:80],
        "commands_executed": value.get("commands_executed", [])[:64],
        "test_outcomes": value.get("test_outcomes", [])[:64],
        "artifact_refs": value.get("artifact_refs", [])[:64],
        "acceptance_criteria": value.get("acceptance_criteria", [])[:64],
        "outstanding_work": value.get("outstanding_work", [])[:64],
        "updated_at": str(value.get("updated_at", ""))[:80],
    }


def read_current_recommendation(protocol_dir: Optional[Path]) -> Optional[dict]:
    """Read controller-owned recommendation state and its correlation metadata."""
    if protocol_dir is None:
        return None
    value = read_protocol_json(protocol_dir / "current-supervisor-recommendation.json", maximum=12_000)
    if not value or value.get("schema_version") not in {1, 2}:
        return None
    recommendation_id = value.get("recommendation_id")
    report = value.get("report")
    if not isinstance(recommendation_id, str) or not recommendation_id.strip() or len(recommendation_id) > 180:
        return None
    if not isinstance(report, str) or len(report.strip()) < 80 or len(report) > MAX_REPORT_CHARS + 200:
        return None
    task_id = value.get("task_id", "")
    session_id = value.get("session_id", "")
    scopes = value.get("scope_boundaries", [])
    criteria = value.get("acceptance_criteria", [])
    if not isinstance(task_id, str) or not isinstance(session_id, str):
        return None
    if not isinstance(scopes, list) or not isinstance(criteria, list):
        return None
    return {
        "schema_version": value.get("schema_version", 1),
        "recommendation_id": recommendation_id.strip(),
        "task_id": task_id[:220],
        "session_id": session_id[:220],
        "message_type": str(value.get("message_type", "advisory_recommendation"))[:100],
        "priority": str(value.get("priority", "normal"))[:30],
        "scope_boundaries": scopes[:64],
        "acceptance_criteria": criteria[:64],
        "review_cycle": value.get("review_cycle") if isinstance(value.get("review_cycle"), int) else 0,
        "source_worker_state_sha256": str(value.get("source_worker_state_sha256", ""))[:64],
        "report": redact_sensitive_text(report).strip(),
        "created_at": str(value.get("created_at", ""))[:80],
    }


def append_dialogue_event(
    transcript_dir: Path,
    direction: str,
    role: str,
    message_id: str,
    message: str,
    *,
    stage: str = "message_delivered",
    task_id: str = "",
    run_id: str = "",
    session_id: str = "",
    message_type: str = "",
    priority: str = "normal",
    scope_boundaries=None,
    acceptance_criteria=None,
    correlation_id: str = "",
    delivery_state: str = "delivered",
    acknowledgement_state: str = "pending",
    disposition: str = "",
    reason: str = "",
    evidence: str = "",
    verification: str = "",
    work_performed: str = "",
    blockers=None,
    changed_files=None,
    commit_sha: str = "",
    checkpoint_sha: str = "",
    commands_executed=None,
    test_outcomes=None,
    artifact_refs=None,
    outstanding_work=None,
) -> bool:
    """Record an actual role-boundary message using the versioned v2 event schema."""
    path = (transcript_dir / "agent-dialogue.jsonl").resolve()
    if not within_directory(path, transcript_dir):
        log("refusing dialogue event path outside the configured transcript directory")
        return False
    try:
        event = make_protocol_event(
            stage=stage, direction=direction, role=role, message_id=message_id,
            message=message, task_id=task_id, run_id=run_id, session_id=session_id,
            message_type=message_type, priority=priority, scope_boundaries=scope_boundaries,
            acceptance_criteria=acceptance_criteria, correlation_id=correlation_id,
            delivery_state=delivery_state, acknowledgement_state=acknowledgement_state,
            disposition=disposition, reason=reason, evidence=evidence, verification=verification,
            work_performed=work_performed, blockers=blockers, changed_files=changed_files,
            commit_sha=commit_sha, checkpoint_sha=checkpoint_sha, commands_executed=commands_executed,
            test_outcomes=test_outcomes, artifact_refs=artifact_refs, outstanding_work=outstanding_work,
        )
        for attempt in range(3):
            try:
                return append_protocol_event(path, event)
            except (OSError, ProtocolError) as exc:
                if attempt == 2:
                    log(f"could not record role dialogue ({type(exc).__name__}); evidence remains incomplete")
                    return False
                time.sleep(0.05 * (attempt + 1))
    except (OSError, ProtocolError, TypeError, ValueError) as exc:
        log(f"could not construct role dialogue event ({type(exc).__name__}); evidence remains incomplete")
        return False
    return False


def append_communication_event(transcript_dir: Path, **fields) -> bool:
    """Append lifecycle state transitions separately from human-readable role dialogue."""
    path = (transcript_dir / "agent-communication.jsonl").resolve()
    if not within_directory(path, transcript_dir):
        log("refusing communication lifecycle path outside the configured transcript directory")
        return False
    try:
        event = make_protocol_event(**fields)
        for attempt in range(3):
            try:
                return append_protocol_event(path, event)
            except (OSError, ProtocolError) as exc:
                if attempt == 2:
                    log(f"communication lifecycle persistence failed ({type(exc).__name__})")
                    return False
                time.sleep(0.05 * (attempt + 1))
    except (OSError, ProtocolError, TypeError, ValueError) as exc:
        log(f"could not construct communication lifecycle event ({type(exc).__name__})")
        return False
    return False


def format_worker_disposition(recommendation: Optional[dict], disposition: Optional[dict]) -> str:
    """Format a worker response only when it correlates to the active recommendation."""
    if recommendation is None or disposition is None:
        return ""
    recommendation_id = recommendation.get("recommendation_id")
    if not isinstance(recommendation_id, str) or not recommendation_id.strip():
        return ""
    if disposition.get("recommendation_id") != recommendation_id:
        return ""
    lines = [
        f"Disposition: {disposition['disposition']}",
        f"Reason: {disposition['reason']}",
        f"Evidence: {disposition['evidence'] or '(none supplied)'}",
        f"Verification: {disposition['verification'] or '(not supplied)'}",
        f"Work performed: {disposition['work_performed'] or '(not supplied)'}",
        f"Acknowledgement: {disposition['acknowledgement_state']}",
        f"Changed files: {json.dumps(disposition['changed_files'], ensure_ascii=False)}",
        f"Tests: {json.dumps(disposition['test_outcomes'], ensure_ascii=False)}",
        f"Artifacts: {json.dumps(disposition['artifact_refs'], ensure_ascii=False)}",
        f"Blockers: {json.dumps(disposition['blockers'], ensure_ascii=False)}",
        f"Outstanding work: {json.dumps(disposition['outstanding_work'], ensure_ascii=False)}",
    ]
    if disposition["commit_sha"] or disposition["checkpoint_sha"]:
        lines.append(f"Commit/checkpoint: {disposition['commit_sha'] or '(none)'} / {disposition['checkpoint_sha'] or '(none)'}")
    return "\n".join(lines)


def dialogue_protocol_observation(protocol_dir: Optional[Path]) -> str:
    """Return a compact audit view; worker claims must be checked against independent evidence."""
    recommendation = read_current_recommendation(protocol_dir)
    disposition = read_worker_disposition(protocol_dir, recommendation)
    if recommendation is None:
        return "No valid current recommendation has been published to the file-backed dialogue protocol."
    matched = bool(disposition and disposition["recommendation_id"] == recommendation["recommendation_id"])
    lines = [
        f"Current recommendation ID: {recommendation['recommendation_id']}",
        f"Task ID: {recommendation['task_id'] or '(not supplied)'}",
        f"Source worker-state SHA-256: {recommendation['source_worker_state_sha256'] or '(not recorded)'}",
        f"Worker disposition status: {disposition['disposition'] if matched else 'UNACKNOWLEDGED_OR_STALE'}",
    ]
    if matched and disposition:
        lines.extend([
            f"Worker acknowledgement: {disposition['acknowledgement_state']}",
            f"Worker reason: {disposition['reason']}",
            f"Worker evidence: {disposition['evidence'] or '(none supplied)'}",
            f"Worker verification claim: {disposition['verification'] or '(not supplied)'}",
            f"Worker work performed: {disposition['work_performed'] or '(not supplied)'}",
            f"Worker blockers: {json.dumps(disposition['blockers'], ensure_ascii=False)}",
            f"Worker outstanding work: {json.dumps(disposition['outstanding_work'], ensure_ascii=False)}",
        ])
    lines.append("A worker disposition is a claim, not proof of task completion; the completion gate requires controller-verified acceptance criteria, passing tests, verified artifacts, and the exact remote checkpoint.")
    return "\n".join(lines)


def publish_current_recommendation(
    protocol_dir: Optional[Path],
    run_id: str,
    run_attempt: str,
    cycle: int,
    report: str,
    source_worker_state: str,
    transcript_dir: Optional[Path] = None,
) -> Optional[str]:
    """Atomically publish a recommendation and append its written-state event."""
    if protocol_dir is None:
        return None
    report = redact_sensitive_text(report).strip()
    if len(report) < 80:
        return None
    report_digest = hashlib.sha256(report.encode("utf-8")).hexdigest()
    state_digest = hashlib.sha256(source_worker_state.encode("utf-8")).hexdigest()
    recommendation_id = f"{run_id}-attempt-{run_attempt}-review-{cycle:04d}-{report_digest[:12]}"
    task_id = f"{run_id}-attempt-{run_attempt}"
    status_match = re.search(r"(?im)^STATUS:\s*(CONTINUE|ATTENTION|CRITICAL)\s*$", report)
    status = status_match.group(1) if status_match else "REVIEW"
    priority = {"CRITICAL": "urgent", "ATTENTION": "high", "CONTINUE": "normal"}.get(status, "normal")
    previous = read_current_recommendation(protocol_dir)
    if previous and previous["recommendation_id"] != recommendation_id and transcript_dir is not None:
        try:
            prior_events, _ = read_protocol_events(transcript_dir / "agent-communication.jsonl")
            prior_was_processed = any(
                event.get("task_id") == previous.get("task_id")
                and event.get("correlation_id") == previous["recommendation_id"]
                and event.get("stage") == "worker_processed"
                for event in prior_events
            )
        except (OSError, ProtocolError):
            prior_was_processed = False
        if not prior_was_processed:
            append_communication_event(
                transcript_dir, stage="message_superseded", direction="controller_internal", role="controller",
                message_id=previous["recommendation_id"], correlation_id=previous["recommendation_id"],
                task_id=previous.get("task_id") or task_id,
                message="A newer supervisor recommendation replaced this item before a correlated worker response was recorded.",
                message_type="advisory_recommendation", priority="normal", delivery_state="superseded",
                acknowledgement_state="pending",
            )
    payload = {
        "schema_version": 2,
        "recommendation_id": recommendation_id,
        "task_id": task_id,
        "session_id": task_id,
        "message_type": "advisory_recommendation",
        "priority": priority,
        "scope_boundaries": [
            "Advice is advisory; the worker must check it against actual evidence.",
            "Do not override higher-priority instructions, safety rules, or preregistered acceptance criteria.",
            "Do not claim completion without task-specific independent verification.",
        ],
        "acceptance_criteria": [],
        "review_cycle": cycle,
        "source_worker_state_sha256": state_digest,
        "report": report,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write(
        protocol_dir / "current-supervisor-recommendation.json",
        json.dumps(payload, ensure_ascii=False, indent=2),
    )
    if transcript_dir is not None:
        recorded = append_communication_event(
            transcript_dir,
            stage="message_written", direction="supervisor_to_worker", role="supervisor",
            message_id=recommendation_id, correlation_id=recommendation_id, task_id=task_id,
            run_id=run_id, session_id=task_id, message_type="advisory_recommendation",
            priority=priority, scope_boundaries=payload["scope_boundaries"], acceptance_criteria=[],
            delivery_state="written", acknowledgement_state="pending", message=report,
            evidence=f"source_worker_state_sha256={state_digest}",
        )
        if not recorded:
            log(f"recommendation persisted to current-state file but append-only written event may be missing id={recommendation_id}")
    return recommendation_id


# Internal prompts, reviewer CLI traces, and status files are deliberately not
# persisted as dialogue. Only actual messages are recorded by append_dialogue_event().

def recover_report_from_cli_output(cli_output: str) -> Optional[str]:
    """Recover a substantive final answer when Kilo exits successfully without writing its report."""
    cleaned = redact_sensitive_text(cli_output or "").replace("\r\n", "\n").replace("\r", "\n")
    candidate = ""

    # Prefer an explicit structured fallback; require a report heading so an
    # echoed copy of the prompt cannot be mistaken for advice.
    explicit = list(re.finditer(r"(?im)^\s*REPORT_FALLBACK:\s*", cleaned))
    if explicit:
        possible = cleaned[explicit[-1].end():].strip()
        first_line = possible.splitlines()[0].strip() if possible else ""
        has_valid_status_first = bool(re.fullmatch(
            r"STATUS:\s*(?:CONTINUE|ATTENTION|CRITICAL)", first_line, re.IGNORECASE
        ))
        has_report_heading = re.search(
            r"(?im)^\s*(?:#{1,3}\s*)?(?:Observed evidence|Previous approaches|Likely cause|"
            r"Different next step|Verification|Limitations)\s*(?:[:—-]|$)",
            possible,
        )
        if has_valid_status_first and has_report_heading:
            candidate = possible

    # Older Kilo runs can exhaust the agent step budget yet still return a
    # substantive final answer with a stable summary heading.
    if not candidate:
        summaries = list(re.finditer(r"(?im)^\s*Summary of work done:\s*", cleaned))
        if summaries:
            possible = cleaned[summaries[-1].end():].strip()
            if re.search(
                r"(?i)(recommendations? for next steps|recommended next action|"
                r"different next step|verification needed|next task)",
                possible,
            ):
                candidate = possible

    # Some CLI versions omit the summary heading but expose a final recommendation section.
    if not candidate:
        recommendations = list(re.finditer(
            r"(?im)^\s*Recommendations for next steps:\s*$", cleaned
        ))
        if recommendations:
            candidate = cleaned[recommendations[-1].start():].strip()

    candidate = redact_sensitive_text(candidate).strip()
    if len(candidate) < 120:
        return None
    if not re.search(
        r"(?i)\b(recommend\w*|next step|next action|should|must|verify|verification|"
        r"priority|check|continue|proceed|blocked|task)\b",
        candidate,
    ):
        return None

    # Preserve the actionable tail if the CLI response is unusually verbose.
    candidate = candidate[-(MAX_REPORT_CHARS - 650):]
    return (
        "STATUS: ATTENTION\n\n"
        "## Report recovery\n"
        "The reviewer CLI exited successfully but did not create the required report file. "
        "The content below was recovered from its final response; it remains advisory and "
        "must be verified independently before action.\n\n"
        "## Recovered reviewer response\n"
        + candidate
    )


def terminate_process_group(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        try:
            process.terminate()
        except OSError:
            pass
    try:
        process.wait(timeout=3)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def handle_signal(_signum: int, _frame: object) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True
    if ACTIVE_REVIEW is not None:
        terminate_process_group(ACTIVE_REVIEW)


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[loop-supervisor] {stamp} {message}", flush=True)


def run_review(
    args: argparse.Namespace,
    cycle: int,
    objective: str,
    log_delta: str,
    git_snapshot: str,
    previous_feedback: str,
    repo_root: Path,
    report_dir: Path,
    require_initial_recommendation: bool = False,
) -> Optional[str]:
    global ACTIVE_REVIEW
    report_name = f"run-{args.run_id}-attempt-{args.run_attempt}-review-{cycle:04d}.md"
    report_path = (report_dir / report_name).resolve()
    if not within_directory(report_path, report_dir):
        log("refusing report path outside the configured report directory")
        return None
    try:
        report_path.unlink(missing_ok=True)
    except OSError:
        pass
    report_relative_path = report_path.relative_to(repo_root).as_posix()
    prompt = redact_sensitive_text(build_review_prompt(
        objective, log_delta, git_snapshot, previous_feedback,
        report_relative_path, cycle, args.interval_seconds,
        require_initial_recommendation=require_initial_recommendation,
    ))
    # The generated prompt is reviewer input, not a message from either agent.
    # Keep it in memory for the model call only; do not write or echo it.
    
    output = ""
    env = os.environ.copy()
    env["KILO_SUPERVISOR_MODE"] = "1"
    env.pop("KILO_SUPERVISOR_FEEDBACK_FILE", None)
    command = [
        str(args.kilo), "run", "--agent", "loop-supervisor",
        "--model", args.model, "--auto", prompt,
    ]
    try:
        ACTIVE_REVIEW = subprocess.Popen(
            command, cwd=repo_root, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", start_new_session=True,
        )
        try:
            output, _ = ACTIVE_REVIEW.communicate(timeout=args.review_timeout_seconds)
        except subprocess.TimeoutExpired:
            terminate_process_group(ACTIVE_REVIEW)
            output, _ = ACTIVE_REVIEW.communicate(timeout=2)
            log(f"review {cycle} timed out; no role message was produced; worker remains unaffected")
            return None
        rc = ACTIVE_REVIEW.returncode
        if rc != 0:
            log(f"review {cycle} returned exit {rc}; no role message was produced; prior advice remains active")
            return None
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"review {cycle} failed to launch or complete ({type(exc).__name__}); no role message produced; worker continues")
        return None
    finally:
        ACTIVE_REVIEW = None

    try:
        report = report_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        report = ""

    if not report:
        recovered = recover_report_from_cli_output(output or "")
        if recovered:
            report = recovered
            try:
                atomic_write(report_path, report)
                log(f"review {cycle} recovered a substantive final response into the report file")
            except OSError as exc:
                # The in-memory advice can still be published to the worker journal
                # when the diagnostic report file cannot be persisted.
                log(f"review {cycle} recovered advice but report-file persistence failed ({type(exc).__name__}); attempting journal delivery")
        else:
            log(f"review {cycle} produced no report file or recoverable final response; previous advice retained")
            return None

    report = redact_sensitive_text(report).strip()
    if report == "NO_NEW_DIALOGUE":
        return "NO_NEW_DIALOGUE"
    if len(report) > MAX_REPORT_CHARS:
        head = (MAX_REPORT_CHARS - 140) // 2
        tail = MAX_REPORT_CHARS - head - 100
        report = report[:head] + "\n\n...[middle of report truncated for bounded delivery]...\n\n" + report[-tail:]
    if not report:
        log(f"review {cycle} report was empty after sanitization; previous advice retained")
        return None

    try:
        atomic_write(report_path, report)
    except OSError as exc:
        # Report files are diagnostic; the sanitized in-memory response is enough
        # to continue through the append-only journal and delivery plugin.
        log(f"review {cycle} could not persist sanitized report file ({type(exc).__name__}); continuing with in-memory advice")

    # Caller publishes a new report as advice; the feedback plugin records the
    # exact supervisor-to-worker message only when it is injected into a worker tool result.
    return report


def initial_recommendation_is_ready(
    protocol_dir: Optional[Path],
    transcript_dir: Optional[Path],
    recommendation: Optional[dict],
    run_id: str,
    run_attempt: str,
) -> bool:
    """Require both a run-scoped v2 recommendation and its matching durable written event."""
    if protocol_dir is None or transcript_dir is None or recommendation is None:
        return False

    task_id = f"{run_id}-attempt-{run_attempt}"
    recommendation_id = recommendation.get("recommendation_id")
    report = recommendation.get("report")
    if (
        recommendation.get("schema_version") != 2
        or recommendation.get("task_id") != task_id
        or recommendation.get("session_id") != task_id
        or not isinstance(recommendation_id, str)
        or not recommendation_id.startswith(task_id + "-review-")
        or not isinstance(report, str)
        or len(report.strip()) < 80
    ):
        return False

    first_line = report.splitlines()[0] if report.splitlines() else ""
    if not re.fullmatch(r"STATUS: (?:CONTINUE|ATTENTION|CRITICAL)\\s*", first_line):
        return False

    events, errors = read_protocol_events(Path(transcript_dir) / "agent-communication.jsonl")
    if errors:
        return False
    return any(
        event.get("task_id") == task_id
        and event.get("run_id") == run_id
        and event.get("session_id") == task_id
        and event.get("direction") == "supervisor_to_worker"
        and event.get("role") == "supervisor"
        and event.get("stage") == "message_written"
        and event.get("message_id") == recommendation_id
        and event.get("correlation_id") == recommendation_id
        and event.get("delivery_state") == "written"
        and event.get("message") == report
        for event in events
    )


def should_run_review(
    *,
    has_new_worker_output: bool,
    repository_changed: bool,
    require_initial_recommendation: bool,
    recommendation_ready: bool,
) -> bool:
    """Keep bootstrapping until the run-scoped recommendation and written event both exist."""
    return bool(
        has_new_worker_output
        or repository_changed
        or (require_initial_recommendation and not recommendation_ready)
    )


def main_with_args(argv: list[str]) -> int:
    """Testable entry point for deterministic CI tests."""
    global STOP_REQUESTED
    STOP_REQUESTED = False
    original_argv = sys.argv
    sys.argv = [original_argv[0], *argv]
    try:
        return main()
    finally:
        sys.argv = original_argv
        STOP_REQUESTED = False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--runtime-root", type=Path, default=Path(os.environ.get("RUNNER_TEMP", "/tmp")))
    parser.add_argument("--active-log-pointer", type=Path, required=True)
    parser.add_argument("--objective-file", type=Path, required=True)
    parser.add_argument("--feedback-file", type=Path, required=True)
    parser.add_argument("--transcript-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, default=Path(".kilo/supervisor-reports"))
    parser.add_argument("--kilo", type=Path, required=True)
    parser.add_argument("--model", default="kilo/kilo-auto/free")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    parser.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    parser.add_argument("--interval-seconds", type=float, default=150.0)
    parser.add_argument("--review-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--max-reviews", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument(
        "--require-initial-recommendation",
        action="store_true",
        help="Retry bootstrap reviews without new worker output until an initial recommendation is published.",
    )
    args = parser.parse_args()

    if args.interval_seconds <= 0 or args.review_timeout_seconds <= 0:
        parser.error("interval and review timeout must be positive")
    if args.review_timeout_seconds >= args.interval_seconds and args.max_reviews == 0:
        args.review_timeout_seconds = max(1.0, args.interval_seconds - 5.0)

    repo_root = args.repo_root.resolve()
    runtime_root = args.runtime_root.resolve()
    report_dir = (repo_root / args.report_dir).resolve() if not args.report_dir.is_absolute() else args.report_dir.resolve()
    pointer_file = safe_runtime_path(str(args.active_log_pointer), runtime_root)
    objective_file = safe_runtime_path(str(args.objective_file), runtime_root)
    feedback_file = safe_runtime_path(str(args.feedback_file), runtime_root)
    transcript_dir = safe_runtime_path(str(args.transcript_dir), runtime_root)
    kilo_path = args.kilo.resolve()

    if not repo_root.is_dir():
        parser.error("repository root is not a directory")
    if not within_directory(report_dir, repo_root / ".kilo" / "supervisor-reports"):
        parser.error("report directory must be under .kilo/supervisor-reports")
    if pointer_file is None or objective_file is None or feedback_file is None or transcript_dir is None:
        parser.error("active log pointer, objective file, feedback file, and transcript directory must be under runtime root")
    if not kilo_path.is_file():
        log("pinned Kilo executable is missing; supervisor monitor will exit fail-open")
        return 0

    report_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)
    protocol_dir: Optional[Path] = repo_root / ".kilo-runtime"
    if not within_directory(protocol_dir, repo_root / ".kilo-runtime"):
        log("file-backed dialogue protocol path escapes .kilo-runtime; protocol disabled fail-open")
        protocol_dir = None
    else:
        try:
            protocol_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log(f"file-backed dialogue protocol unavailable ({type(exc).__name__}); worker continues fail-open")
            protocol_dir = None
    previous_feedback = read_bounded(feedback_file, MAX_PREVIOUS_FEEDBACK_CHARS).strip()
    active_recommendation_at_start = read_current_recommendation(protocol_dir)
    previous_report = (
        active_recommendation_at_start["report"]
        if active_recommendation_at_start is not None else ""
    )
    previous_log = ""
    previous_git_digest: Optional[str] = None
    previous_worker_disposition_digest: Optional[str] = None
    quiet_notice_logged = False
    no_new_dialogue_count = 0
    consecutive_unusable_reviews = 0
    circuit_breaker_threshold = 3
    cycle = 0
    next_due = time.monotonic()
    log(f"started; review runs only on new worker output, repository changes, or a changed worker reply; cadence {args.interval_seconds:g}s")

    while not STOP_REQUESTED:
        cycle += 1
        objective = redact_sensitive_text(read_bounded(objective_file, MAX_OBJECTIVE_CHARS))
        current_log = read_active_worker_log(pointer_file, runtime_root)
        if current_log.startswith(previous_log):
            log_delta = current_log[len(previous_log):]
        else:
            log_delta = current_log
        previous_log = current_log
        git_snapshot = read_git_snapshot(repo_root)
        git_digest = hashlib.sha256(git_snapshot.encode("utf-8")).hexdigest()
        repository_changed = previous_git_digest is None or git_digest != previous_git_digest
        previous_git_digest = git_digest

        current_recommendation = read_current_recommendation(protocol_dir)
        current_disposition = read_worker_disposition(protocol_dir, current_recommendation)
        worker_reply = format_worker_disposition(current_recommendation, current_disposition)
        if worker_reply:
            disposition_digest = hashlib.sha256(
                json.dumps(
                    [
                        current_recommendation["recommendation_id"],
                        current_disposition["disposition"],
                        current_disposition["reason"],
                        current_disposition["evidence"],
                        current_disposition["verification"],
                    ],
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()
            if disposition_digest != previous_worker_disposition_digest:
                recommendation_id = current_recommendation["recommendation_id"]
                task_id = current_recommendation.get("task_id") or f"{args.run_id}-attempt-{args.run_attempt}"
                response_fields = {
                    "task_id": task_id,
                    "run_id": args.run_id,
                    "session_id": current_disposition.get("session_id") or current_recommendation.get("session_id") or task_id,
                    "message_type": "worker_response",
                    "priority": "normal",
                    "correlation_id": recommendation_id,
                    "acknowledgement_state": current_disposition["acknowledgement_state"],
                    "disposition": current_disposition["disposition"],
                    "reason": current_disposition["reason"],
                    "evidence": current_disposition["evidence"],
                    "verification": current_disposition["verification"],
                    "work_performed": current_disposition["work_performed"],
                    "blockers": current_disposition["blockers"],
                    "changed_files": current_disposition["changed_files"],
                    "commit_sha": current_disposition["commit_sha"],
                    "checkpoint_sha": current_disposition["checkpoint_sha"],
                    "commands_executed": current_disposition["commands_executed"],
                    "test_outcomes": current_disposition["test_outcomes"],
                    "artifact_refs": current_disposition["artifact_refs"],
                    "acceptance_criteria": current_disposition["acceptance_criteria"],
                    "outstanding_work": current_disposition["outstanding_work"],
                }
                recorded = append_dialogue_event(
                    transcript_dir, "worker_to_supervisor", "worker", recommendation_id, worker_reply,
                    stage="worker_processed", **response_fields, delivery_state="delivered",
                )
                ack_message = f"Worker {current_disposition['acknowledgement_state']} recommendation {recommendation_id}."
                acknowledged = append_communication_event(
                    transcript_dir, stage="worker_acknowledged", direction="worker_to_supervisor", role="worker",
                    message_id=recommendation_id, message=ack_message, **response_fields,
                    delivery_state="received",
                )
                processed = append_communication_event(
                    transcript_dir, stage="worker_processed", direction="worker_to_supervisor", role="worker",
                    message_id=recommendation_id, message=worker_reply, **response_fields,
                    delivery_state="processed",
                )
                previous_worker_disposition_digest = disposition_digest
                if recorded or processed:
                    log(f"worker replied to supervisor recommendation={recommendation_id} disposition={current_disposition['disposition']}")
                    print("::group::LIVE AGENT DIALOGUE BOX — WORKER → SUPERVISOR", flush=True)
                    for message_line in worker_reply.splitlines() or ["(empty worker reply)"]:
                        print("[agent-dialogue] " + message_line, flush=True)
                    print("::endgroup::", flush=True)
                    log_delta = (log_delta.rstrip() + "\n\nNEW WORKER-TO-SUPERVISOR MESSAGE\n" + worker_reply).strip()
                if not acknowledged or not processed or not recorded:
                    log(f"worker disposition persistence incomplete for recommendation={recommendation_id}; dialogue={recorded} acknowledged={acknowledged} processed={processed}")
        else:
            previous_worker_disposition_digest = None

        has_new_worker_output = bool(log_delta.strip())
        recommendation_ready = initial_recommendation_is_ready(
            protocol_dir, transcript_dir, current_recommendation, args.run_id, args.run_attempt,
        )
        needs_initial_recommendation = bool(
            args.require_initial_recommendation and not recommendation_ready
        )
        review_required = should_run_review(
            has_new_worker_output=has_new_worker_output,
            repository_changed=repository_changed,
            require_initial_recommendation=args.require_initial_recommendation,
            recommendation_ready=recommendation_ready,
        )
        if not review_required:
            if not quiet_notice_logged:
                log("review skipped: no new worker output, repository change, or role dialogue; no duplicate message recorded")
                quiet_notice_logged = True
            report = "NO_NEW_DIALOGUE"
        else:
            quiet_notice_logged = False
            if needs_initial_recommendation:
                log(f"review {cycle} started; required initial recommendation is still missing")
            else:
                log(f"review {cycle} started; new worker/repository evidence available")
            report = run_review(
                args, cycle, objective, log_delta, git_snapshot,
                previous_feedback, repo_root, report_dir,
                require_initial_recommendation=needs_initial_recommendation,
            )
            if needs_initial_recommendation and report == "NO_NEW_DIALOGUE":
                log(f"review {cycle} returned NO_NEW_DIALOGUE before the required initial recommendation; treating it as unusable")
                report = None
        if report == "NO_NEW_DIALOGUE":
            consecutive_unusable_reviews = 0
            no_new_dialogue_count += 1
            if no_new_dialogue_count == 1:
                log("no new actionable supervisor message; existing advice remains unchanged")
        elif report is None:
            no_new_dialogue_count = 0
            consecutive_unusable_reviews += 1
            log(
                f"review {cycle} produced no usable report "
                f"(consecutive unusable reviews: {consecutive_unusable_reviews}/"
                f"{circuit_breaker_threshold}); worker continues independently"
            )
        elif report == previous_report and not needs_initial_recommendation:
            no_new_dialogue_count += 1
            consecutive_unusable_reviews = 0
            if no_new_dialogue_count == 1:
                log("review output matches the active supervisor message; duplicate delivery and recording suppressed")
        else:
            no_new_dialogue_count = 0
            entry = (
                f"--- SUPERVISOR ADVICE ENTRY cycle={cycle:04d} ---\n"
                "CURRENT SUPERVISOR MESSAGE — this file contains only the latest undelivered recommendation. "
                "Older messages are kept in the role-dialogue record only. Verify recommendations independently before changing code.\n\n"
                + report.strip()
                + f"\n--- END SUPERVISOR ADVICE ENTRY cycle={cycle:04d} ---\n"
            )
            try:
                # Replace the queue with the latest message; never replay a cumulative history to the worker.
                atomic_write(feedback_file, entry)
            except OSError as exc:
                consecutive_unusable_reviews += 1
                log(
                    f"review {cycle} feedback journal publication failed ({type(exc).__name__}); "
                    f"advice was not delivered (consecutive unusable reviews: "
                    f"{consecutive_unusable_reviews}/{circuit_breaker_threshold}); worker continues"
                )
            else:
                consecutive_unusable_reviews = 0
                previous_report = report
                previous_feedback = read_bounded(feedback_file, MAX_PREVIOUS_FEEDBACK_CHARS).strip()
                try:
                    recommendation_id = publish_current_recommendation(
                        protocol_dir,
                        args.run_id,
                        args.run_attempt,
                        cycle,
                        report,
                        "\n".join((objective, log_delta, git_snapshot)),
                        transcript_dir=transcript_dir,
                    )
                    if recommendation_id:
                        log(f"file-backed recommendation published id={recommendation_id}; worker disposition required")
                except OSError as exc:
                    log(f"file-backed recommendation publication failed ({type(exc).__name__}); journal delivery remains enabled")
                status_match = re.search(r"(?im)^STATUS:\s*(CONTINUE|ATTENTION|CRITICAL)\s*$", report)
                status = status_match.group(1) if status_match else "REVIEW"
                log(f"review {cycle} issued a new supervisor recommendation status={status}; exact advice is recorded only on delivery")
                log(f"review {cycle} completed with usable report")
        if consecutive_unusable_reviews >= circuit_breaker_threshold:
            log(
                f"SUPERVISOR_CIRCUIT_BREAKER_OPEN: {consecutive_unusable_reviews} consecutive "
                "reviews produced no usable report; no further reviewer model calls will be launched "
                "in this run; the worker remains unaffected"
            )
            # Keep the health/status process alive for the controller heartbeat, but stop
            # consuming provider capacity on a persistently failing reviewer. Deterministic
            # test runs may request a finite review count; honor that cap instead of waiting
            # for an external signal that CI tests do not send.
            if args.max_reviews and cycle >= args.max_reviews:
                break
            while not STOP_REQUESTED:
                time.sleep(0.25)
            break
        if args.max_reviews and cycle >= args.max_reviews:
            break
        next_due += args.interval_seconds
        now = time.monotonic()
        if next_due <= now:
            next_due = now + args.interval_seconds
        while not STOP_REQUESTED and time.monotonic() < next_due:
            time.sleep(min(0.25, max(0.01, next_due - time.monotonic())))
    log("stopped; worker execution was not controlled by the supervisor monitor")
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:
        log(f"unexpected monitor failure ({type(exc).__name__}); worker remains independent")
        raise SystemExit(0)
