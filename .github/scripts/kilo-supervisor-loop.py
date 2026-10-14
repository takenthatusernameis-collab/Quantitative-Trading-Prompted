#!/usr/bin/env python3
"""Fail-open, 150-second-cadence Kilo supervisor for the active worker invocation."""
from __future__ import annotations

import argparse
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

STOP_REQUESTED = False
ACTIVE_REVIEW: Optional[subprocess.Popen[str]] = None

MAX_LOG_CHARS = 5_500
MAX_OBJECTIVE_CHARS = 2_500
MAX_REPORT_CHARS = 3_200
MAX_PREVIOUS_FEEDBACK_CHARS = 12_000
MAX_REVIEW_OUTPUT_CHARS = 1_200
MAX_CLI_TRANSCRIPT_CHARS = 24_000


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
) -> str:
    if not log_delta.strip():
        log_delta = "(No new worker output since the previous review; assess repository/task state without inventing progress.)"
    if not previous_feedback.strip():
        previous_feedback = "(No previous supervisor recommendation.)"
    return f"""CONTINUOUS KILO WORKER REVIEW — CYCLE {cycle}

You are reviewing an active worker, not replacing or restarting it. Analyze the actual evidence below. Every scheduled review must be concise, specific, and useful. If there is no new evidence or recommendation change, explicitly say that the current recommendation remains unchanged; do not invent findings just to create novelty.

CURRENT WORKER OBJECTIVE / INSTRUCTIONS (redacted, truncated):
{objective[-MAX_OBJECTIVE_CHARS:]}

NEW OR MOST RELEVANT WORKER OUTPUT (redacted, truncated):
{log_delta[-MAX_LOG_CHARS:]}

CURRENT REPOSITORY STATE:
{git_snapshot}

PREVIOUS SUPERVISOR FEEDBACK (cumulative journal tail; newer entries do not erase older ones):
{previous_feedback[-MAX_PREVIOUS_FEEDBACK_CHARS:]}

REQUIRED ACTION — REPORT-FIRST, BOUNDED REVIEW:
1. Treat the supplied worker log delta, objective, repository snapshot, and prior advice as your primary evidence. Do not rebuild inventories, run backtests, install dependencies, or inspect unrelated files.
2. If one relevant detail is needed, make no more than two targeted read/search calls. Mark anything else unverified instead of continuing exploration.
3. Write the report to this exact path on your first available write operation, no later than your fourth tool call:
REPORT_PATH: {report_relative_path}
4. Use these exact headings, in order: STATUS: CONTINUE/ATTENTION/CRITICAL; Observed evidence; Previous approaches; Likely cause; Different next step; Verification; Limitations. Keep it concise (about 150–250 words). An Alternative section is optional only when the main step is blocked or materially uncertain.
5. If no intervention is warranted, say “no change; continue” and identify the evidence supporting that decision.
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


def transcript_file(transcript_dir: Path, cycle: int, suffix: str, content: str) -> Optional[Path]:
    """Persist sanitized request/response content under a run-scoped runner-temp directory."""
    path = transcript_dir / f"review-{cycle:04d}-{suffix}"
    if not within_directory(path, transcript_dir):
        log("refusing transcript path outside the configured transcript directory")
        return None
    try:
        atomic_write(path, redact_sensitive_text(content), ensure_newline=False)
    except OSError as exc:
        log(f"could not save {suffix} transcript ({type(exc).__name__}); live review continues")
        return None
    return path


def log_content_block(label: str, content: str) -> None:
    """Print sanitized message bodies as safe, individually prefixed Actions log lines."""
    log(f"BEGIN {label}")
    for line in content.splitlines() or ["(empty)"]:
        print(f"[supervisor-message] {line}", flush=True)
    log(f"END {label}")


def bounded_cli_transcript(text: str) -> str:
    safe = redact_sensitive_text(text)
    if len(safe) <= MAX_CLI_TRANSCRIPT_CHARS:
        return safe
    half = MAX_CLI_TRANSCRIPT_CHARS // 2
    omitted = len(safe) - (half * 2)
    return safe[:half] + f"\n... [{omitted} characters omitted from CLI diagnostic output; request and advice are stored separately] ...\n" + safe[-half:]


def log_live_dialogue_box(cycle: int, content: str) -> None:
    """Render the exact redacted dialogue as a collapsible, live Actions log group."""
    print(f"::group::LIVE AGENT DIALOGUE BOX — review {cycle:04d}", flush=True)
    for line in content.splitlines() or ["(empty dialogue transcript)"]:
        # Prefix every line so transcript text cannot be interpreted as an Actions command.
        print("[agent-dialogue] " + line, flush=True)
    print("::endgroup::", flush=True)


def write_agent_dialogue(
    transcript_dir: Path,
    cycle: int,
    prompt: str,
    cli_output: str,
    advice: str,
    outcome: str,
) -> Optional[Path]:
    """Write a combined, readable record of both sides of one reviewer exchange."""
    def quote_block(value: str) -> str:
        safe = redact_sensitive_text(value).strip()
        if not safe:
            return "> (none)"
        return "\n".join("> " + line for line in safe.splitlines())

    body = (
        f"# Agent dialogue — loop-supervisor review {cycle:04d}\n\n"
        "This is the redacted exchange for one isolated reviewer session.\n\n"
        "## Worker/controller → supervisor: actual request and evidence\n\n"
        f"{quote_block(prompt)}\n\n"
        "## Supervisor CLI trace (sanitized)\n\n"
        f"{quote_block(bounded_cli_transcript(cli_output or '') or '(no CLI output captured)')}\n\n"
        "## Supervisor → worker: advice returned by the reviewer\n\n"
        f"{quote_block(advice or '(No usable advice returned; previous advice was retained.)')}\n\n"
        "## Review outcome\n\n"
        f"{quote_block(outcome)}\n\n"
        "## When the worker receives the advice\n\n"
        "A usable report is added to the cumulative feedback journal by the controller. "
        "The worker receives pending advice at its next tool-result boundary; this does not interrupt an operation already in progress. "
        "The exact text appended to the worker tool result is also saved in a worker-delivery-*.md transcript.\n"
    )
    return transcript_file(transcript_dir, cycle, "agent-dialogue.md", body)


def recover_report_from_cli_output(cli_output: str) -> Optional[str]:
    """Recover a substantive final answer when Kilo exits successfully without writing its report."""
    cleaned = redact_sensitive_text(cli_output or "").replace("\r\n", "\n").replace("\r", "\n")
    candidate = ""

    # Prefer an explicit structured fallback; require a report heading so an
    # echoed copy of the prompt cannot be mistaken for advice.
    explicit = list(re.finditer(r"(?im)^\s*REPORT_FALLBACK:\s*", cleaned))
    if explicit:
        possible = cleaned[explicit[-1].end():].strip()
        has_report_heading = re.search(
            r"(?im)^\s*(?:STATUS:\s*(?:CONTINUE|ATTENTION|CRITICAL)|"
            r"(?:#{1,3}\s*)?(?:Observed evidence|Previous approaches|Likely cause|"
            r"Different next step|Verification|Limitations)\s*(?:[:—-]|$))",
            possible,
        )
        if has_report_heading:
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
    transcript_dir: Path,
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
    ))
    request_path = transcript_file(transcript_dir, cycle, "request-to-supervisor.md", prompt)
    if request_path:
        log(f"review {cycle} exact request saved to {request_path}")
    log_content_block(f"ACTUAL REQUEST SENT TO SUPERVISOR — review {cycle}", prompt)

    def save_cli_output(value: str) -> Optional[Path]:
        return transcript_file(
            transcript_dir, cycle, "supervisor-cli-output.txt",
            bounded_cli_transcript(value or ""),
        )

    def write_outcome(value: str) -> None:
        transcript_file(transcript_dir, cycle, "outcome.txt", value)

    def save_dialogue(cli_output: str, advice: str, outcome: str) -> None:
        path = write_agent_dialogue(transcript_dir, cycle, prompt, cli_output, advice, outcome)
        if path:
            try:
                # Emit the box into the live Actions log immediately after each review,
                # including timeouts/failures. The workflow Summary step runs only at job end.
                dialogue = path.read_text(encoding="utf-8", errors="replace")
                log_live_dialogue_box(cycle, dialogue)
                log(f"review {cycle} combined agent dialogue saved to {path}")
            except OSError as exc:
                log(f"review {cycle} transcript saved but live dialogue rendering failed ({type(exc).__name__})")

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
            cli_path = save_cli_output(output or "")
            if cli_path:
                log(f"review {cycle} CLI diagnostic output saved to {cli_path}")
            if output:
                log_content_block(f"SUPERVISOR CLI OUTPUT BEFORE TIMEOUT — review {cycle}", bounded_cli_transcript(output))
            outcome = "TIMED OUT: no usable report was produced before the reviewer timeout; worker was not interrupted and previous advice remains available."
            write_outcome(outcome)
            save_dialogue(output or "", "", outcome)
            log(f"review {cycle} timed out; worker remains unaffected")
            return None
        rc = ACTIVE_REVIEW.returncode
        cli_path = save_cli_output(output or "")
        if cli_path:
            log(f"review {cycle} CLI diagnostic output saved to {cli_path}")
        if rc != 0:
            safe_tail = bounded_cli_transcript(output or "")[-MAX_REVIEW_OUTPUT_CHARS:]
            detail = safe_tail.replace("\n", " | ").strip()
            outcome = f"CLI EXIT {rc}: advice was not published for this cycle; previous advice was retained."
            write_outcome(f"{outcome}\n\n{safe_tail}")
            save_dialogue(output or "", "", outcome)
            log_content_block(f"SUPERVISOR CLI ERROR OUTPUT — review {cycle}", safe_tail)
            log(f"review {cycle} returned exit {rc}; worker continues. {detail[:500]}")
            return None
    except (OSError, subprocess.SubprocessError) as exc:
        outcome = f"LAUNCH/PROCESS FAILURE: {type(exc).__name__}; worker continues and previous advice remains available."
        write_outcome(outcome)
        save_dialogue(output or "", "", outcome)
        log(f"review {cycle} failed to launch or complete ({type(exc).__name__}); worker continues")
        return None
    finally:
        ACTIVE_REVIEW = None

    recovered_from_cli = False
    try:
        report = report_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        report = ""

    if not report:
        recovered = recover_report_from_cli_output(output or "")
        if recovered:
            report = recovered
            recovered_from_cli = True
            try:
                atomic_write(report_path, report)
                log(f"review {cycle} recovered a substantive final response into the report file")
            except OSError as exc:
                # The in-memory advice can still be published to the worker journal
                # when the diagnostic report file cannot be persisted.
                log(f"review {cycle} recovered advice but report-file persistence failed ({type(exc).__name__}); attempting journal delivery")
        else:
            outcome = "MISSING/EMPTY REPORT: the reviewer CLI returned successfully but produced neither a report file nor a recoverable actionable final response; previous advice was retained."
            write_outcome(outcome)
            save_dialogue(output or "", "", outcome)
            log(f"review {cycle} produced no report file or recoverable final response; previous advice retained")
            return None

    report = redact_sensitive_text(report).strip()
    if len(report) > MAX_REPORT_CHARS:
        head = (MAX_REPORT_CHARS - 140) // 2
        tail = MAX_REPORT_CHARS - head - 100
        report = report[:head] + "\n\n...[middle of report truncated for bounded delivery]...\n\n" + report[-tail:]
    if not report:
        outcome = "EMPTY REPORT: no advice was published; previous advice was retained."
        write_outcome(outcome)
        save_dialogue(output or "", "", outcome)
        log(f"review {cycle} report was empty after sanitization; previous advice retained")
        return None

    try:
        atomic_write(report_path, report)
    except OSError as exc:
        # Report files are diagnostic; the sanitized in-memory response is enough
        # to continue through the append-only journal and delivery plugin.
        log(f"review {cycle} could not persist sanitized report file ({type(exc).__name__}); continuing with in-memory advice")

    response_path = transcript_file(transcript_dir, cycle, "response-from-supervisor.md", report)
    if response_path:
        log(f"review {cycle} actual advice saved to {response_path}")
    log_content_block(f"ACTUAL ADVICE RETURNED BY SUPERVISOR — review {cycle}", report)
    outcome = (
        "USABLE REPORT RECOVERED: the successful reviewer CLI omitted its report file; "
        "the final response was recovered, sanitized, and is ready for journal publication; "
        "worker delivery occurs at the next tool-result boundary."
        if recovered_from_cli else
        "USABLE REPORT GENERATED: redacted advice was accepted; the report is ready for journal publication; "
        "delivery can occur only after publication, at the worker's next tool-result boundary."
    )
    write_outcome(outcome)
    save_dialogue(output or "", report, outcome)
    return report


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
    previous_feedback = read_bounded(feedback_file, MAX_PREVIOUS_FEEDBACK_CHARS).strip()
    previous_report = ""
    previous_log = ""
    consecutive_unusable_reviews = 0
    circuit_breaker_threshold = 3
    cycle = 0
    next_due = time.monotonic()
    log(f"started; reviewing immediately and then every {args.interval_seconds:g}s; supervisor failures never stop worker")

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
        log(f"review {cycle} started; gathering and recording actual worker evidence and reviewer messages")
        started = time.monotonic()
        report = run_review(
            args, cycle, objective, log_delta, git_snapshot,
            previous_feedback, repo_root, report_dir, transcript_dir,
        )
        if report is None:
            consecutive_unusable_reviews += 1
            log(
                f"review {cycle} produced no usable report "
                f"(consecutive unusable reviews: {consecutive_unusable_reviews}/"
                f"{circuit_breaker_threshold}); worker continues independently"
            )
        elif report == previous_report:
            consecutive_unusable_reviews = 0
            log(f"review {cycle} completed with usable report; recommendation unchanged, no duplicate journal entry added")
        else:
            entry = (
                f"--- SUPERVISOR ADVICE ENTRY cycle={cycle:04d} ---\n"
                "INDEPENDENT LOOP-SUPERVISOR FEEDBACK\n"
                "This is an append-only cumulative journal. Preserve earlier advice unless newer evidence explicitly supersedes it. "
                "Verify recommendations independently before changing code.\n\n"
                + report.strip()
                + f"\n--- END SUPERVISOR ADVICE ENTRY cycle={cycle:04d} ---\n"
            )
            try:
                try:
                    existing = feedback_file.read_text(encoding="utf-8", errors="replace")
                except FileNotFoundError:
                    existing = ""
                separator = "" if not existing or existing.endswith("\n") else "\n"
                atomic_write(feedback_file, existing + separator + entry)
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
                status_match = re.search(r"(?im)^STATUS:\s*(CONTINUE|ATTENTION|CRITICAL)\s*$", report)
                status = status_match.group(1) if status_match else "REVIEW"
                first_recommendation = next(
                    (line.strip() for line in report.splitlines()
                     if line.strip() and not line.lstrip().startswith("#")),
                    "Review ready",
                )
                log(f"review {cycle} appended cumulative advice status={status}: {first_recommendation[:180]}")
                log(f"review {cycle} advice queued for worker delivery at the next tool-result boundary")
                log(f"review {cycle} completed with usable report")        if consecutive_unusable_reviews >= circuit_breaker_threshold:
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
