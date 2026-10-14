#!/usr/bin/env python3
"""Independently verify real Kilo E2E dialogue, recoverable artifacts, tests, and remote SHA."""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
import kilo_dialogue_protocol as protocol

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_RAW = {"agent-dialogue.jsonl", "agent-communication.jsonl", "worker-disposition.json"}

def isolated_target_branch(target: str, default: str) -> bool:
    return target.startswith("infra/") and target != default

def disposition_matches(disposition: Any, events: list[dict], task_id: str) -> tuple[bool, str, str]:
    if not isinstance(disposition, dict) or disposition.get("schema_version") != 2:
        return False, "missing or unsupported worker-disposition schema", ""
    if disposition.get("task_id") != task_id:
        return False, "worker disposition task_id mismatch", ""
    session = disposition.get("session_id")
    recommendation = disposition.get("recommendation_id")
    if not isinstance(session, str) or not session or not isinstance(recommendation, str) or not recommendation:
        return False, "worker disposition lacks session_id or recommendation_id", ""
    if disposition.get("acknowledgement_state") not in {"acknowledged", "rejected"}:
        return False, "explicit acknowledgement/rejection missing", session
    if disposition.get("disposition") != "verified" or not disposition.get("work_performed") or not disposition.get("verification"):
        return False, "worker disposition is not a complete verified claim", session
    if disposition.get("blockers") or disposition.get("outstanding_work"):
        return False, "worker disposition reports blockers or outstanding work", session
    processed = [e for e in events if e.get("task_id") == task_id and e.get("session_id") == session
        and e.get("direction") == "worker_to_supervisor" and e.get("stage") == "worker_processed"
        and e.get("correlation_id") == recommendation]
    if not processed:
        return False, "no processed response matches recommendation/session", session
    reply = processed[-1]
    for field in ("disposition", "work_performed", "verification"):
        if reply.get(field) != disposition.get(field):
            return False, f"disposition differs from processed {field}", session
    ack = [e for e in events if e.get("task_id") == task_id and e.get("session_id") == session
        and e.get("direction") == "worker_to_supervisor" and e.get("stage") == "worker_acknowledged"
        and e.get("correlation_id") == recommendation and e.get("acknowledgement_state") in {"acknowledged", "rejected"}]
    if not ack:
        return False, "separate acknowledgement/rejection event missing", session
    if ack[-1].get("acknowledgement_state") != disposition.get("acknowledgement_state"):
        return False, "acknowledgement differs from lifecycle evidence", session
    return True, "worker disposition matches correlated lifecycle records", session

def run_check(name: str, command: list[str], log_dir: Path) -> dict:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{name}.log"
    try:
        proc = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True, timeout=180)
        log_path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
        code = int(proc.returncode)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        code = 124 if isinstance(exc, subprocess.TimeoutExpired) else 127
    return {"name": name, "status": "passed" if code == 0 else "failed", "exit_code": code,
        "verified_by": "controller", "evidence_ref": f"workflow-run:{os.environ.get('RUN_ID', 'unknown')}#test-{name}",
        "command": " ".join(command), "log_file": str(log_path)}

def find_one(root: Path, basename: str) -> Path | None:
    found = list(root.rglob(basename)) if root.exists() else []
    return found[0] if len(found) == 1 else None

def main() -> int:
    run_id = os.environ.get("RUN_ID", os.environ.get("GITHUB_RUN_ID", ""))
    attempt = os.environ.get("RUN_ATTEMPT", os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    task_id = f"{run_id}-attempt-{attempt}"
    target = os.environ.get("TARGET_BRANCH", os.environ.get("GITHUB_REF_NAME", ""))
    default = os.environ.get("REPOSITORY_DEFAULT_BRANCH", "main")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    temp = Path(os.environ.get("RUNNER_TEMP", "/tmp"))
    transcripts = Path(os.environ.get("SUPERVISOR_TRANSCRIPT_DIR", str(temp / "missing-transcripts")))
    dialogue = transcripts / "agent-dialogue.jsonl"
    communication = transcripts / "agent-communication.jsonl"
    status_path = transcripts / "task-completion-status.json"
    report_path = f"docs/verification/kilo-e2e-run-{run_id}-attempt-{attempt}.md"
    manifest_path = temp / f"kilo-task-verification-{run_id}-attempt-{attempt}.json"
    summary_path = temp / f"kilo-e2e-verification-summary-{run_id}-attempt-{attempt}.json"
    artifact_id = os.environ.get("RAW_ARTIFACT_ID", "")
    artifact_name = f"kilo-progress-trace-{run_id}"
    raw_upload_ok = os.environ.get("RAW_ARTIFACT_UPLOAD_OUTCOME") == "success"
    controller_ok = os.environ.get("CONTROLLER_OUTCOME") == "success"
    terminal_ok = os.environ.get("CONTROLLER_TERMINAL_STATUS") == "verified_progress"
    try:
        persisted_count = int(os.environ.get("PERSISTED_CHECKPOINTS", "0"))
    except ValueError:
        persisted_count = 0
    checkpoint = os.environ.get("LAST_VERIFIED_CHECKPOINT_SHA", "")
    test_dir = temp / "kilo-e2e-independent-tests"
    tests = [
        run_check("controller-bash-syntax", ["bash", "-n", ".github/scripts/kilo-controller.sh"], test_dir),
        run_check("dialogue-protocol-regressions", ["python3", ".github/scripts/test_kilo_dialogue_protocol.py"], test_dir),
        run_check("supervisor-regressions", ["python3", ".github/scripts/test_kilo_supervisor_loop.py"], test_dir),
        run_check("e2e-verifier-regressions", ["python3", ".github/scripts/test_kilo_e2e_verification.py"], test_dir),
    ]
    blockers: list[str] = []
    criteria: list[dict] = []
    target_ok = isolated_target_branch(target, default)
    if not target_ok:
        blockers.append("target is not a non-default infra/* branch")
    criteria.append({"id": "branch_isolation", "status": "passed" if target_ok else "blocked",
        "verified_by": "controller", "evidence_ref": f"target={target}; default={default}"})

    remote_sha = ""
    if SHA_RE.fullmatch(checkpoint):
        try:
            remote = subprocess.run(["git", "ls-remote", "origin", f"refs/heads/{target}"],
                capture_output=True, text=True, timeout=20, check=True)
            fields = remote.stdout.split()
            remote_sha = fields[0] if fields else ""
        except (OSError, subprocess.SubprocessError) as exc:
            blockers.append(f"remote branch SHA query failed: {type(exc).__name__}")
    else:
        blockers.append("checkpoint SHA is not a full 40-character SHA")
    local_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    checkpoint_ok = bool(target_ok and SHA_RE.fullmatch(checkpoint) and remote_sha == checkpoint and local_head == checkpoint
        and persisted_count >= 1 and controller_ok and terminal_ok)
    if not checkpoint_ok:
        blockers.append("local HEAD, remote SHA, persistence count or controller outcome did not agree")

    committed_report = ""
    report_committed = False
    if SHA_RE.fullmatch(checkpoint):
        try:
            report_committed = subprocess.run(["git", "cat-file", "-e", f"{checkpoint}:{report_path}"],
                capture_output=True, text=True, timeout=15).returncode == 0
            if report_committed:
                committed_report = subprocess.run(["git", "show", f"{checkpoint}:{report_path}"],
                    capture_output=True, text=True, timeout=15, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            report_committed = False

    recovered_dir = temp / f"kilo-e2e-recovered-{run_id}-{attempt}"
    recovered: dict[str, Path] = {}
    artifact_meta_ok = False
    if raw_upload_ok and artifact_id.isdigit() and repo and os.environ.get("GH_TOKEN"):
        try:
            meta_result = subprocess.run(["gh", "api", f"repos/{repo}/actions/artifacts/{artifact_id}"],
                capture_output=True, text=True, timeout=20, check=True)
            meta = json.loads(meta_result.stdout)
            workflow_run = meta.get("workflow_run") or {}
            artifact_meta_ok = (meta.get("id") == int(artifact_id) and meta.get("name") == artifact_name
                and meta.get("expired") is False and int(meta.get("size_in_bytes", 0)) > 0
                and workflow_run.get("id") == int(run_id))
            if artifact_meta_ok:
                import shutil
                if recovered_dir.exists():
                    shutil.rmtree(recovered_dir)
                recovered_dir.mkdir(parents=True)
                download = subprocess.run(["gh", "run", "download", run_id, "--repo", repo,
                    "--name", artifact_name, "--dir", str(recovered_dir)],
                    capture_output=True, text=True, timeout=60)
                if download.returncode == 0:
                    for name in REQUIRED_RAW:
                        item = find_one(recovered_dir, name)
                        if item:
                            recovered[name] = item
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError) as exc:
            blockers.append(f"artifact metadata/download verification failed: {type(exc).__name__}")
    else:
        blockers.append("raw evidence upload did not expose a usable artifact ID")
    artifact_ok = artifact_meta_ok and REQUIRED_RAW.issubset(recovered)
    artifact_evidence = f"artifact={artifact_name}; id={artifact_id}; metadata_verified={artifact_meta_ok}; recovered={sorted(recovered)}"
    if not artifact_ok:
        blockers.append("downloaded artifact lacks required role-dialogue, communication, disposition or completion-status records")
    criteria.append({"id": "recoverable_hosted_evidence", "status": "passed" if artifact_ok else "blocked",
        "verified_by": "controller", "evidence_ref": artifact_evidence})

    exchange_ok = False
    exchange_note = "raw artifact incomplete"
    session = ""
    if artifact_ok:
        raw_dialogue = recovered["agent-dialogue.jsonl"]
        raw_comm = recovered["agent-communication.jsonl"]
        try:
            disposition = json.loads(recovered["worker-disposition.json"].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            disposition = None
        dialogue_events, dialogue_errors = protocol.read_events(raw_dialogue)
        communication_events, communication_errors = protocol.read_events(raw_comm)
        disposition_ok, disposition_note, session = disposition_matches(disposition, communication_events, task_id)
        raw_gate = protocol.evaluate_completion(dialogue_path=raw_dialogue, communication_path=raw_comm,
            verification_path=None, task_id=task_id, checkpoint_sha=checkpoint, checkpoint_persisted=checkpoint_ok)
        exchange_ok = (not dialogue_errors and not communication_errors and disposition_ok
            and raw_gate.get("status") == "awaiting_independent_verification"
            and any(e.get("task_id") == task_id and e.get("direction") == "supervisor_to_worker"
                and e.get("stage") == "message_delivered" for e in dialogue_events))
        exchange_note = f"raw_gate={raw_gate.get('status')}; disposition={disposition_note}; dialogue_errors={dialogue_errors}; communication_errors={communication_errors}"
        if not exchange_ok:
            blockers.append("live role-boundary dialogue, separate acknowledgement, correlated processing and worker disposition did not all verify")
    criteria.append({"id": "correlated_live_worker_exchange", "status": "passed" if exchange_ok else "blocked",
        "verified_by": "controller", "evidence_ref": f"artifact={artifact_id}; {exchange_note}"})

    report_ok = bool(report_committed and "KILO_E2E_TASK_REPORT_V1" in committed_report
        and task_id in committed_report and session and session in committed_report)
    if not report_ok:
        blockers.append("run-scoped report is missing from the exact checkpoint or does not include the task/session IDs")
    criteria.append({"id": "run_scoped_task_report", "status": "passed" if report_ok else "blocked",
        "verified_by": "controller", "evidence_ref": f"{checkpoint}:{report_path}"})

    failed_tests = [t for t in tests if t["status"] != "passed"]
    if failed_tests:
        blockers.append("one or more independent post-run regression tests failed")
    artifacts = []
    if artifact_ok:
        artifacts.append({"ref": f"actions-artifact:{artifact_id}", "verified": True, "verified_by": "controller",
            "evidence_ref": f"Artifact metadata and downloaded archive verified; files={sorted(recovered)}"})
    if report_ok and checkpoint_ok:
        artifacts.append({"ref": f"git:{checkpoint}:{report_path}", "verified": True, "verified_by": "controller",
            "evidence_ref": f"git cat-file/show verified report at {checkpoint}"})

    manifest = {"schema_version": 1, "verifier": "controller", "task_id": task_id, "target_branch": target,
        "session_id": session or None, "acceptance_criteria": criteria, "tests": tests, "artifacts": artifacts,
        "remote_checkpoint": {"verified": checkpoint_ok, "sha": checkpoint if SHA_RE.fullmatch(checkpoint) else "",
            "remote_observed_sha": remote_sha or None},
        "blockers": blockers, "outstanding_work": list(blockers), "raw_artifact_id": artifact_id or None,
        "raw_artifact_url": os.environ.get("RAW_ARTIFACT_URL", ""), "report_path": report_path,
        "test_log_directory": str(test_dir)}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    transcripts.mkdir(parents=True, exist_ok=True)
    gate_cmd = [sys.executable, ".github/scripts/kilo_dialogue_protocol.py", "completion-status",
        "--dialogue", str(dialogue), "--communication", str(communication), "--verification", str(manifest_path),
        "--task-id", task_id, "--checkpoint-sha", checkpoint, "--checkpoint-persisted", "1" if checkpoint_ok else "0",
        "--output", str(status_path)]
    gate = subprocess.run(gate_cmd, capture_output=True, text=True, timeout=30)
    if gate.stdout:
        print(gate.stdout.strip())
    if gate.stderr:
        print(gate.stderr.strip(), file=sys.stderr)
    try:
        final_status = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        final_status = {"status": "incomplete_evidence", "reasons": ["final completion status is missing/unreadable"]}
    summary = {"task_id": task_id, "target_branch": target, "remote_checkpoint_sha": remote_sha or None,
        "worker_session_id": session or None, "raw_artifact_id": artifact_id or None, "raw_artifact_recovered": artifact_ok,
        "acceptance_criteria_passed": sum(1 for item in criteria if item["status"] == "passed"),
        "acceptance_criteria_total": len(criteria), "failed_tests": failed_tests, "completion_gate": final_status}
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if gate.returncode == 0 and final_status.get("status") == "verified_completion" else 1

if __name__ == "__main__":
    raise SystemExit(main())
