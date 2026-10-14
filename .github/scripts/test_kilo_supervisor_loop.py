#!/usr/bin/env python3
"""Deterministic tests for the continuous Kilo supervisor monitor; no model calls."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("kilo-supervisor-loop.py")
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("kilo_supervisor_loop", SCRIPT)
assert SPEC and SPEC.loader
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)


class SupervisorLoopTests(unittest.TestCase):

    def test_agent_and_runner_share_recoverable_report_contract(self):
        repo_root = SCRIPT.resolve().parents[2]
        agent_text = (repo_root / ".kilo" / "agents" / "loop-supervisor.md").read_text(encoding="utf-8")
        self.assertIn("steps: 4", agent_text)
        self.assertIn("The first non-empty report line must be exactly one of", agent_text)
        self.assertIn("Do not add a title, number the sections, or bold the headings.", agent_text)
        prompt = monitor.build_review_prompt(
            "Complete the active task.",
            "The test failed with a reproducible assertion.",
            " M tests/test_example.py",
            "",
            ".kilo/supervisor-reports/report.md",
            1,
            150.0,
        )
        self.assertIn("The report's first line must be exactly one of", prompt)
        self.assertIn("Do not number or bold headings.", prompt)

        bootstrap = monitor.build_review_prompt(
            "Run the bounded E2E protocol test.",
            "(No new worker output since the previous review; assess repository/task state without inventing progress.)",
            "repository status: clean",
            "",
            ".kilo/supervisor-reports/bootstrap.md",
            1,
            60.0,
            require_initial_recommendation=True,
        )
        self.assertIn("BOOTSTRAP REQUIREMENT", bootstrap)
        self.assertIn("do not return NO_NEW_DIALOGUE", bootstrap)
        self.assertIn("initial recommendation is mandatory", bootstrap.lower())

    def test_bootstrap_requires_written_event_and_repairs_half_published_recommendation(self):
        with tempfile.TemporaryDirectory(prefix="kilo-bootstrap-repair-test-") as temp:
            root = Path(temp)
            protocol_dir = root / ".kilo-runtime"
            transcript_dir = root / "transcripts"
            report = (
                "STATUS: ATTENTION\n"
                "Observed evidence: the initial recommendation file exists without its lifecycle event.\n"
                "Previous approaches: the file-backed state was published before the event append completed.\n"
                "Likely cause: the readiness check must validate both independently persisted records.\n"
                "Different next step: retry publication until the exact written event is durable.\n"
                "Verification: require the event task, session, message, correlation, and report to match.\n"
                "Limitations: worker delivery remains a separate later lifecycle stage.\n"
            )
            first_id = monitor.publish_current_recommendation(
                protocol_dir, "bootstrap-run", "2", 1, report, "observed worker and repository state",
            )
            self.assertIsNotNone(first_id)
            partial = monitor.read_current_recommendation(protocol_dir)
            self.assertFalse(monitor.initial_recommendation_is_ready(
                protocol_dir, transcript_dir, partial, "bootstrap-run", "2",
            ))
            self.assertTrue(monitor.should_run_review(
                has_new_worker_output=False, repository_changed=False,
                require_initial_recommendation=True, recommendation_ready=False,
            ))

            repaired_id = monitor.publish_current_recommendation(
                protocol_dir, "bootstrap-run", "2", 2, report, "observed worker and repository state",
                transcript_dir=transcript_dir,
            )
            self.assertIsNotNone(repaired_id)
            self.assertNotEqual(first_id, repaired_id)
            repaired = monitor.read_current_recommendation(protocol_dir)
            self.assertTrue(monitor.initial_recommendation_is_ready(
                protocol_dir, transcript_dir, repaired, "bootstrap-run", "2",
            ))
            events, errors = monitor.read_protocol_events(transcript_dir / "agent-communication.jsonl")
            self.assertEqual(errors, [])
            self.assertTrue(any(
                event.get("stage") == "message_written"
                and event.get("message_id") == repaired_id
                and event.get("correlation_id") == repaired_id
                and event.get("message") == report.strip()
                for event in events
            ))

    def test_required_initial_recommendation_retries_without_new_evidence(self):
        self.assertTrue(monitor.should_run_review(
            has_new_worker_output=False, repository_changed=False,
            require_initial_recommendation=True, recommendation_ready=False,
        ))
        self.assertFalse(monitor.should_run_review(
            has_new_worker_output=False, repository_changed=False,
            require_initial_recommendation=True, recommendation_ready=True,
        ))
        self.assertFalse(monitor.should_run_review(
            has_new_worker_output=False, repository_changed=False,
            require_initial_recommendation=False, recommendation_ready=False,
        ))
        self.assertTrue(monitor.should_run_review(
            has_new_worker_output=True, repository_changed=False,
            require_initial_recommendation=False, recommendation_ready=False,
        ))

    def test_report_fallback_requires_status_on_first_line(self):
        valid = (
            "Additional CLI narration.\n"
            "REPORT_FALLBACK:\n"
            "STATUS: ATTENTION\n"
            "Observed evidence: the same focused assertion failed again.\n"
            "Previous approaches: the previous correction left the assertion failing.\n"
            "Likely cause: the parser still mishandles the empty-field case.\n"
            "Different next step: isolate the empty-field input and fix the parser.\n"
            "Verification: rerun the focused regression test and require it to pass.\n"
            "Limitations: the full suite has not yet been rerun.\n"
        )
        recovered = monitor.recover_report_from_cli_output(valid)
        self.assertIsNotNone(recovered)
        self.assertIn("Different next step: isolate the empty-field input", recovered)

        missing_status = (
            "REPORT_FALLBACK:\n"
            "1. **Observed evidence** — the same focused assertion failed again.\n"
            "2. **Previous approaches** — the previous correction left it failing.\n"
            "3. **Likely cause** — the parser mishandles an empty field.\n"
            "4. **Different next step** — isolate the empty-field input.\n"
            "5. **Verification** — rerun the focused regression test.\n"
            "7. **Limitations** — full suite not rerun.\n"
        )
        self.assertIsNone(
            monitor.recover_report_from_cli_output(missing_status),
            "The old numbered/bold report format must not be recovered as if it matched the new status-first contract.",
        )

        status_not_first = valid.replace("REPORT_FALLBACK:\nSTATUS: ATTENTION", "REPORT_FALLBACK:\nPreamble text\nSTATUS: ATTENTION")
        self.assertIsNone(monitor.recover_report_from_cli_output(status_not_first))


    def test_secret_redaction_before_model_input(self):
        source = (
            "Authorization: Bearer abcdefghijklmnop\n"
            "ghp_123456789012345678901234567890\n"
            "GITHUB_TOKEN=super-secret-value\n"
            "hello world\n"
        )
        result = monitor.redact_sensitive_text(source)
        self.assertNotIn("abcdefghijklmnop", result)
        self.assertNotIn("ghp_123456789012345678901234567890", result)
        self.assertNotIn("super-secret-value", result)
        self.assertIn("hello world", result)

    def test_two_cycles_preserve_feedback_without_recording_internal_prompts(self):
        with tempfile.TemporaryDirectory(prefix="kilo-supervisor-test-") as temp:
            root = Path(temp)
            repo = root / "repo"
            report_dir = repo / ".kilo" / "supervisor-reports"
            report_dir.mkdir(parents=True)
            runtime = root / "runtime"
            runtime.mkdir()
            transcripts = runtime / "supervisor-transcripts"
            worker_log = runtime / "worker.log"
            worker_log.write_text(
                "worker started\nGITHUB_TOKEN=secret-value\n"
                "ghp_123456789012345678901234567890\n",
                encoding="utf-8",
            )
            pointer = runtime / "active-pointer"
            pointer.write_text(str(worker_log) + "\n", encoding="utf-8")
            objective = runtime / "objective.txt"
            objective.write_text("Complete current task and verify results.\n", encoding="utf-8")
            feedback = runtime / "feedback.md"
            capture = runtime / "captured-prompts.txt"
            fake_kilo = runtime / "fake-kilo"
            fake_kilo.write_text(
                "\n".join([
                    "#!/usr/bin/env python3",
                    "import os, re, sys",
                    "prompt = sys.argv[-1]",
                    "with open(os.environ['SUPERVISOR_TEST_CAPTURE'], 'a', encoding='utf-8') as f:",
                    "    f.write(prompt + '\\n---PROMPT-END---\\n')",
                    "match = re.search(r'(?m)^REPORT_PATH:\\s*(.+)$', prompt)",
                    "if not match:",
                    "    raise SystemExit(3)",
                    "report = match.group(1).strip()",
                    "cycle = int(re.search(r'review-(\\d+)\\.md$', report).group(1))",
                    "print('mock reviewer CLI output for cycle ' + str(cycle))",
                    "os.makedirs(os.path.dirname(report), exist_ok=True)",
                    "with open(report, 'w', encoding='utf-8') as f:",
                    "    f.write('STATUS: ATTENTION\\nEvidence: worker review ' + str(cycle) + '\\n'",
                    "            'Recommended next action: verify changed evidence ' + str(cycle))",
                ]) + "\n",
                encoding="utf-8",
            )
            fake_kilo.chmod(0o755)
            old_env = os.environ.copy()
            live_output = io.StringIO()
            try:
                os.environ["SUPERVISOR_TEST_CAPTURE"] = str(capture)
                with contextlib.redirect_stdout(live_output):
                    code = monitor.main_with_args([
                    "--repo-root", str(repo),
                    "--runtime-root", str(runtime),
                    "--active-log-pointer", str(pointer),
                    "--objective-file", str(objective),
                    "--feedback-file", str(feedback),
                    "--transcript-dir", str(transcripts),
                    "--report-dir", str(report_dir),
                    "--kilo", str(fake_kilo),
                    "--model", "test/fake",
                    "--interval-seconds", "0.02",
                    "--review-timeout-seconds", "2",
                    "--max-reviews", "2",
                    "--run-id", "test-run",
                    "--run-attempt", "1",
                ])
            finally:
                os.environ.clear()
                os.environ.update(old_env)

            self.assertEqual(code, 0)
            live_text = live_output.getvalue()
            # Internal review inputs/reports are not echoed into Actions logs.
            self.assertNotIn("::group::LIVE AGENT DIALOGUE BOX — review 0001", live_text)
            self.assertNotIn("Worker/controller → supervisor: actual request and evidence", live_text)
            self.assertNotIn("Recommended next action: verify changed evidence 1", live_text)
            self.assertIn("review skipped: no new worker output", live_text)
            published = feedback.read_text(encoding="utf-8")
            self.assertIn("worker review 1", published)
            self.assertNotIn("worker review 2", published)
            prompts = capture.read_text(encoding="utf-8")
            self.assertNotIn("worker review 2", prompts)
            self.assertEqual(prompts.count("---PROMPT-END---"), 1, "unchanged worker state should not launch repeated reviews")
            self.assertIn("[REDACTED]", prompts)
            self.assertNotIn("secret-value", prompts)
            self.assertNotIn("ghp_123456789012345678901234567890", prompts)
            self.assertEqual(len(list(report_dir.glob("run-test-run-attempt-1-review-*.md"))), 1, "supervisor-generated reports must not trigger a second review")

            self.assertEqual(
                sorted(path.name for path in transcripts.iterdir()),
                ["agent-communication.jsonl"],
                "an undelivered recommendation may be in the lifecycle ledger but not the role-boundary dialogue",
            )
            communication = [
                json.loads(line)
                for line in (transcripts / "agent-communication.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["stage"] for event in communication], ["message_written"])
            self.assertFalse(any(event["stage"] == "message_delivered" for event in communication))

    def test_failed_review_keeps_feedback_without_transcript_dumps(self):
        with tempfile.TemporaryDirectory(prefix="kilo-supervisor-failure-test-") as temp:
            root = Path(temp)
            repo = root / "repo"
            report_dir = repo / ".kilo" / "supervisor-reports"
            report_dir.mkdir(parents=True)
            runtime = root / "runtime"
            runtime.mkdir()
            transcripts = runtime / "supervisor-transcripts"
            pointer = runtime / "active-pointer"
            pointer.write_text("", encoding="utf-8")
            objective = runtime / "objective.txt"
            objective.write_text("Continue a task safely.\n", encoding="utf-8")
            feedback = runtime / "feedback.md"
            feedback.write_text("Prior actionable advice.\n", encoding="utf-8")
            fake_kilo = runtime / "failing-kilo"
            fake_kilo.write_text(
                "#!/usr/bin/env python3\nprint('mock CLI failure body')\nraise SystemExit(7)\n",
                encoding="utf-8",
            )
            fake_kilo.chmod(0o755)
            code = monitor.main_with_args([
                "--repo-root", str(repo),
                "--runtime-root", str(runtime),
                "--active-log-pointer", str(pointer),
                "--objective-file", str(objective),
                "--feedback-file", str(feedback),
                "--transcript-dir", str(transcripts),
                "--report-dir", str(report_dir),
                "--kilo", str(fake_kilo),
                "--interval-seconds", "0.02",
                "--review-timeout-seconds", "2",
                "--max-reviews", "1",
                "--run-id", "test-failure",
                "--run-attempt", "1",
            ])
            self.assertEqual(code, 0)
            self.assertEqual(feedback.read_text(encoding="utf-8"), "Prior actionable advice.\n")
            self.assertEqual(
                list(transcripts.iterdir()), [],
                "CLI failures are operational diagnostics, not messages between the two agent roles",
            )


    def test_report_missing_recovers_final_response_and_publishes_advice(self):
        with tempfile.TemporaryDirectory(prefix="kilo-supervisor-recovery-test-") as temp:
            root = Path(temp)
            repo = root / "repo"
            report_dir = repo / ".kilo" / "supervisor-reports"
            report_dir.mkdir(parents=True)
            runtime = root / "runtime"
            runtime.mkdir()
            transcripts = runtime / "supervisor-transcripts"
            pointer = runtime / "active-pointer"
            pointer.write_text("", encoding="utf-8")
            objective = runtime / "objective.txt"
            objective.write_text("Review the active worker and recommend one safe next step.\n", encoding="utf-8")
            feedback = runtime / "feedback.md"
            feedback.write_text("", encoding="utf-8")
            fake_kilo = runtime / "reportless-kilo"
            fake_kilo.write_text(
                "#!/usr/bin/env python3\n"
                "print('Maximum steps for this agent have been reached.')\n"
                "print('REPORT_FALLBACK:')\n"
                "print('STATUS: CONTINUE')\n"
                "print('Observed evidence: the reviewer inspected worker logs but did not write its report file.')\n"
                "print('Previous approaches: additional file reads exhausted the limited review steps.')\n"
                "print('Likely cause: report creation was deferred until after exploration.')\n"
                "print('Different next step: write the concise diagnostic report before optional file inspection.')\n"
                "print('Verification: confirm the next review creates a report and the delivery plugin appends this advice to a worker tool result.')\n"
                "print('Limitations: the worker must independently verify evidence before changing code.')\n",
                encoding="utf-8",
            )
            fake_kilo.chmod(0o755)
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                code = monitor.main_with_args([
                    "--repo-root", str(repo),
                    "--runtime-root", str(runtime),
                    "--active-log-pointer", str(pointer),
                    "--objective-file", str(objective),
                    "--feedback-file", str(feedback),
                    "--transcript-dir", str(transcripts),
                    "--report-dir", str(report_dir),
                    "--kilo", str(fake_kilo),
                    "--interval-seconds", "0.02",
                    "--review-timeout-seconds", "2",
                    "--max-reviews", "1",
                    "--run-id", "test-recovery",
                    "--run-attempt", "1",
                ])

            self.assertEqual(code, 0)
            output = captured.getvalue()
            self.assertIn("recovered a substantive final response into the report file", output)
            self.assertIn("review 1 issued a new supervisor recommendation", output)
            self.assertNotIn("SUPERVISOR_CIRCUIT_BREAKER_OPEN", output)
            self.assertTrue((report_dir / "run-test-recovery-attempt-1-review-0001.md").is_file())
            published = feedback.read_text(encoding="utf-8")
            self.assertIn("STATUS: ATTENTION", published)
            self.assertIn("Different next step: write the concise diagnostic report", published)
            self.assertIn("Verification: confirm the next review creates a report", published)
            self.assertEqual(
                sorted(path.name for path in transcripts.iterdir()),
                ["agent-communication.jsonl"],
                "an undelivered report has a written lifecycle event but no role-boundary dialogue event",
            )
            communication = [
                json.loads(line)
                for line in (transcripts / "agent-communication.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["stage"] for event in communication], ["message_written"])
            dialogue_path = transcripts / "agent-dialogue.jsonl"
            self.assertFalse(dialogue_path.exists(), "undelivered advice must not appear in the delivered dialogue transcript")

    def test_missing_report_without_actionable_final_response_is_not_published(self):
        with tempfile.TemporaryDirectory(prefix="kilo-supervisor-empty-recovery-test-") as temp:
            root = Path(temp)
            repo = root / "repo"
            report_dir = repo / ".kilo" / "supervisor-reports"
            report_dir.mkdir(parents=True)
            runtime = root / "runtime"
            runtime.mkdir()
            transcripts = runtime / "supervisor-transcripts"
            pointer = runtime / "active-pointer"
            pointer.write_text("", encoding="utf-8")
            objective = runtime / "objective.txt"
            objective.write_text("Review the active worker safely.\n", encoding="utf-8")
            feedback = runtime / "feedback.md"
            feedback.write_text("Previously published advice.\n", encoding="utf-8")
            fake_kilo = runtime / "nonreporting-kilo"
            fake_kilo.write_text(
                "#!/usr/bin/env python3\n"
                "print('Inspection started but no report or final recommendation was returned.')\n",
                encoding="utf-8",
            )
            fake_kilo.chmod(0o755)
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                code = monitor.main_with_args([
                    "--repo-root", str(repo),
                    "--runtime-root", str(runtime),
                    "--active-log-pointer", str(pointer),
                    "--objective-file", str(objective),
                    "--feedback-file", str(feedback),
                    "--transcript-dir", str(transcripts),
                    "--report-dir", str(report_dir),
                    "--kilo", str(fake_kilo),
                    "--interval-seconds", "0.02",
                    "--review-timeout-seconds", "2",
                    "--max-reviews", "1",
                    "--run-id", "test-empty-recovery",
                    "--run-attempt", "1",
                ])

            self.assertEqual(code, 0)
            self.assertNotIn("MISSING/EMPTY REPORT", captured.getvalue(), "internal supervisor diagnostics must not be echoed into live logs")
            self.assertIn("produced no report file or recoverable final response; previous advice retained", captured.getvalue())
            self.assertEqual(feedback.read_text(encoding="utf-8"), "Previously published advice.\n")
            self.assertFalse((report_dir / "run-test-empty-recovery-attempt-1-review-0001.md").exists())
            self.assertEqual(
                list(transcripts.iterdir()), [],
                "outcome files are not part of role-dialogue records",
            )

    def test_single_timeout_does_not_repeat_without_new_evidence(self):
        import contextlib
        import io

        with tempfile.TemporaryDirectory(prefix="kilo-supervisor-breaker-test-") as temp:
            root = Path(temp)
            repo = root / "repo"
            report_dir = repo / ".kilo" / "supervisor-reports"
            report_dir.mkdir(parents=True)
            runtime = root / "runtime"
            runtime.mkdir()
            transcripts = runtime / "supervisor-transcripts"
            pointer = runtime / "active-pointer"
            pointer.write_text("", encoding="utf-8")
            objective = runtime / "objective.txt"
            objective.write_text("Review the active worker safely.\n", encoding="utf-8")
            feedback = runtime / "feedback.md"
            feedback.write_text("", encoding="utf-8")
            fake_kilo = runtime / "slow-kilo"
            fake_kilo.write_text(
                "#!/usr/bin/env python3\n"
                "import time\n"
                "print('mock slow reviewer started', flush=True)\n"
                "time.sleep(2)\n",
                encoding="utf-8",
            )
            fake_kilo.chmod(0o755)
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                code = monitor.main_with_args([
                    "--repo-root", str(repo),
                    "--runtime-root", str(runtime),
                    "--active-log-pointer", str(pointer),
                    "--objective-file", str(objective),
                    "--feedback-file", str(feedback),
                    "--transcript-dir", str(transcripts),
                    "--report-dir", str(report_dir),
                    "--kilo", str(fake_kilo),
                    "--interval-seconds", "0.12",
                    "--review-timeout-seconds", "0.05",
                    "--max-reviews", "3",
                    "--run-id", "test-breaker",
                    "--run-attempt", "1",
                ])
            self.assertEqual(code, 0)
            output = captured.getvalue()
            self.assertNotIn("SUPERVISOR_CIRCUIT_BREAKER_OPEN", output)
            self.assertNotIn("::group::LIVE AGENT DIALOGUE BOX — review 0001", output)
            self.assertIn("timed out; no role message was produced; worker remains unaffected", output)
            self.assertNotIn("mock slow reviewer started", output)
            self.assertEqual(output.count("(consecutive unusable reviews:"), 1)
            self.assertIn("review skipped: no new worker output", output)
            self.assertEqual(
                list(transcripts.iterdir()), [],
                "timeouts are operational status, not role-to-role dialogue",
            )
            self.assertEqual(feedback.read_text(encoding="utf-8"), "")


    def test_role_dialogue_log_records_only_distinct_messages_in_both_directions(self):
        with tempfile.TemporaryDirectory(prefix="kilo-role-dialogue-test-") as temp:
            transcript_dir = Path(temp)
            recommendation_id = "run-42-review-0003-deadbeef1234"
            supervisor_message = (
                "STATUS: ATTENTION\\n"
                "Observed evidence: the focused assertion is still failing.\\n"
                "Different next step: fix the parser and rerun that assertion."
            )
            worker_reply = (
                "Disposition: in_progress\\n"
                "Reason: I am applying the focused parser fix before other work.\\n"
                "Evidence: the regression test identifies the failing input.\\n"
                "Verification: pending the next test run."
            )

            self.assertTrue(monitor.append_dialogue_event(
                transcript_dir, "supervisor_to_worker", "supervisor",
                recommendation_id, supervisor_message,
            ))
            self.assertFalse(monitor.append_dialogue_event(
                transcript_dir, "supervisor_to_worker", "supervisor",
                recommendation_id, supervisor_message,
            ), "identical supervisor messages must not be recorded twice")
            self.assertTrue(monitor.append_dialogue_event(
                transcript_dir, "worker_to_supervisor", "worker",
                recommendation_id, worker_reply,
            ))
            self.assertFalse(monitor.append_dialogue_event(
                transcript_dir, "worker_to_supervisor", "worker",
                recommendation_id, worker_reply,
            ), "identical worker replies must not be recorded twice")

            dialogue_path = transcript_dir / "agent-dialogue.jsonl"
            events = [json.loads(line) for line in dialogue_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(events), 2)
            self.assertEqual(
                [event["direction"] for event in events],
                ["supervisor_to_worker", "worker_to_supervisor"],
            )
            self.assertEqual([event["message"] for event in events], [supervisor_message, worker_reply])
            self.assertTrue(all(event["message_id"] == recommendation_id for event in events))
            self.assertTrue(all("prompt" not in event and "cli_output" not in event for event in events))


    def test_matching_worker_disposition_evidence_reaches_followup_review(self):
        with tempfile.TemporaryDirectory(prefix="kilo-dialogue-follow-through-test-") as temp:
            protocol = Path(temp) / ".kilo-runtime"
            transcripts = Path(temp) / "transcripts"
            report = (
                "STATUS: ATTENTION\n"
                "Observed evidence: the focused regression test failed on an all-NA momentum row.\n"
                "Previous approaches: the failing row was not handled before selecting weights.\n"
                "Likely cause: idxmax received a row with no valid momentum values.\n"
                "Different next step: add an all-NA guard before selecting weights.\n"
                "Verification: rerun the focused regression test and adjacent edge cases.\n"
                "Limitations: the full suite is not yet verified.\n"
            )
            recommendation_id = monitor.publish_current_recommendation(
                protocol, "test-follow-through", "1", 1, report,
                "worker log contains the reproducible all-NA failure",
            )
            self.assertIsNotNone(recommendation_id)

            reason = "The recommended missing-data guard was implemented before unrelated changes."
            evidence = "The focused regression output now reports the previously failing case as passed."
            verification = "The focused regression test reran successfully; adjacent edge cases remain."
            disposition = {
                "schema_version": 1,
                "recommendation_id": recommendation_id,
                "acknowledgement_state": "acknowledged",
                "disposition": "verified",
                "reason": reason,
                "evidence": evidence,
                "verification": verification,
                "updated_at": "2026-10-14T20:00:00Z",
            }
            (protocol / "worker-disposition.json").write_text(json.dumps(disposition), encoding="utf-8")

            current = monitor.read_current_recommendation(protocol)
            accepted = monitor.read_worker_disposition(protocol)
            self.assertIsNotNone(current)
            self.assertIsNotNone(accepted)
            worker_reply = monitor.format_worker_disposition(current, accepted)
            self.assertEqual(
                worker_reply,
                "\n".join([
                    "Disposition: verified",
                    f"Reason: {reason}",
                    f"Evidence: {evidence}",
                    f"Verification: {verification}",
                    "Work performed: (not supplied)",
                    "Acknowledgement: acknowledged",
                    "Changed files: []",
                    "Tests: []",
                    "Artifacts: []",
                    "Blockers: []",
                    "Outstanding work: []",
                ]),
            )

            log_delta = "Focused regression test passed.\n\nNEW WORKER-TO-SUPERVISOR MESSAGE\n" + worker_reply
            prompt = monitor.build_review_prompt(
                "Apply recommendations and independently verify changes.",
                log_delta,
                "repository status: test change present",
                "previous advice: add the all-NA guard",
                ".kilo/supervisor-reports/follow-through.md",
                2,
                150.0,
            )
            for expected in (
                "NEW WORKER-TO-SUPERVISOR MESSAGE",
                "Disposition: verified",
                f"Reason: {reason}",
                f"Evidence: {evidence}",
                f"Verification: {verification}",
            ):
                self.assertIn(expected, prompt)

            transcripts.mkdir(parents=True, exist_ok=True)
            self.assertTrue(monitor.append_dialogue_event(
                transcripts, "worker_to_supervisor", "worker",
                recommendation_id, worker_reply,
            ))
            self.assertFalse(monitor.append_dialogue_event(
                transcripts, "worker_to_supervisor", "worker",
                recommendation_id, worker_reply,
            ), "duplicate follow-through must not be recorded twice")
            events = [
                json.loads(line)
                for line in (transcripts / "agent-dialogue.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["direction"], "worker_to_supervisor")
            self.assertEqual(events[0]["message_id"], recommendation_id)
            self.assertEqual(events[0]["message"], worker_reply)

            disposition["recommendation_id"] = "stale-recommendation-id"
            (protocol / "worker-disposition.json").write_text(json.dumps(disposition), encoding="utf-8")
            stale = monitor.read_worker_disposition(protocol)
            self.assertIsNotNone(stale)
            self.assertEqual(monitor.format_worker_disposition(current, stale), "")

    def test_file_backed_dialogue_protocol_rejects_stale_or_malformed_dispositions(self):
        with tempfile.TemporaryDirectory(prefix="kilo-dialogue-protocol-test-") as temp:
            protocol = Path(temp)
            report = (
                "STATUS: ATTENTION\nObserved evidence: repeated failure persisted.\n"
                "Different next step: run the focused regression test.\n"
                "Verification: require the assertion to pass.\nLimitations: full suite not run.\n"
            )
            recommendation_id = monitor.publish_current_recommendation(
                protocol, "test-run", "1", 2, report,
                "worker changed file and test output showed assertion failure",
            )
            self.assertIsNotNone(recommendation_id)
            published = json.loads((protocol / "current-supervisor-recommendation.json").read_text(encoding="utf-8"))
            self.assertEqual(published["recommendation_id"], recommendation_id)
            self.assertEqual(len(published["source_worker_state_sha256"]), 64)
            self.assertIn(recommendation_id, monitor.dialogue_protocol_observation(protocol))
            self.assertIn("UNACKNOWLEDGED_OR_STALE", monitor.dialogue_protocol_observation(protocol))

            disposition = {
                "schema_version": 1,
                "recommendation_id": recommendation_id,
                "acknowledgement_state": "acknowledged",
                "disposition": "in_progress",
                "reason": "I am applying the focused recommendation before other work.",
                "evidence": "The relevant assertion failed in the previous test run.",
                "verification": "",
                "updated_at": "2026-10-14T00:00:00Z",
            }
            (protocol / "worker-disposition.json").write_text(json.dumps(disposition), encoding="utf-8")
            accepted = monitor.read_worker_disposition(protocol)
            self.assertEqual(accepted["disposition"], "in_progress")
            self.assertEqual(accepted["acknowledgement_state"], "acknowledged")
            self.assertIn("in_progress", monitor.dialogue_protocol_observation(protocol))

            # A disposition without an explicit acknowledgement must not synthesize one.
            disposition.pop("acknowledgement_state")
            (protocol / "worker-disposition.json").write_text(json.dumps(disposition), encoding="utf-8")
            self.assertIsNone(monitor.read_worker_disposition(protocol))
            disposition["acknowledgement_state"] = "acknowledged"

            disposition["recommendation_id"] = "old-run-old-recommendation"
            (protocol / "worker-disposition.json").write_text(json.dumps(disposition), encoding="utf-8")
            self.assertIn("UNACKNOWLEDGED_OR_STALE", monitor.dialogue_protocol_observation(protocol))

            disposition["recommendation_id"] = recommendation_id
            disposition["disposition"] = "verified"
            disposition["verification"] = ""
            (protocol / "worker-disposition.json").write_text(json.dumps(disposition), encoding="utf-8")
            self.assertIsNone(monitor.read_worker_disposition(protocol))

            (protocol / "worker-disposition.json").write_text("not json", encoding="utf-8")
            self.assertIsNone(monitor.read_worker_disposition(protocol))

    def test_schema_v2_worker_reply_must_match_active_task_and_message(self):
        with tempfile.TemporaryDirectory(prefix="kilo-dialogue-correlation-test-") as temp:
            protocol = Path(temp)
            report = (
                "STATUS: ATTENTION\n"
                "Observed evidence: the focused regression test failed.\n"
                "Different next step: rerun the failing input in isolation.\n"
                "Verification: require the isolated regression to pass.\n"
                "Limitations: broad suite not yet run.\n"
            )
            recommendation_id = monitor.publish_current_recommendation(
                protocol, "correlation-run", "2", 1, report,
                "the worker log contains the failing input",
            )
            recommendation = monitor.read_current_recommendation(protocol)
            self.assertIsNotNone(recommendation)
            disposition = {
                "schema_version": 2,
                "recommendation_id": recommendation_id,
                "task_id": recommendation["task_id"],
                "session_id": "correlation-run-attempt-2-session-1",
                "acknowledgement_state": "acknowledged",
                "disposition": "in_progress",
                "reason": "I am reproducing the failure before changing code.",
                "evidence": "The reported failing input is available.",
                "verification": "",
                "work_performed": "Started an isolated reproduction.",
                "blockers": [],
                "changed_files": [],
                "commit_sha": "",
                "checkpoint_sha": "",
                "commands_executed": [],
                "test_outcomes": [],
                "artifact_refs": [],
                "acceptance_criteria": [],
                "outstanding_work": ["Confirm the regression locally."],
                "updated_at": "2026-10-14T00:00:00Z",
            }
            path = protocol / "worker-disposition.json"
            path.write_text(json.dumps(disposition), encoding="utf-8")
            self.assertIsNotNone(monitor.read_worker_disposition(protocol, recommendation))

            disposition["task_id"] = "different-run-attempt"
            path.write_text(json.dumps(disposition), encoding="utf-8")
            self.assertIsNone(monitor.read_worker_disposition(protocol, recommendation),
                              "a response for a different task must not be attributed to the active recommendation")

            disposition["task_id"] = recommendation["task_id"]
            disposition["recommendation_id"] = "stale-message-id"
            path.write_text(json.dumps(disposition), encoding="utf-8")
            self.assertIsNone(monitor.read_worker_disposition(protocol, recommendation),
                              "a response for a different message must not be attributed to the active recommendation")

            disposition["recommendation_id"] = recommendation_id
            disposition["session_id"] = ""
            path.write_text(json.dumps(disposition), encoding="utf-8")
            self.assertIsNone(monitor.read_worker_disposition(protocol, recommendation),
                              "schema v2 requires the worker session identifier")

if __name__ == "__main__":
    unittest.main(verbosity=2)
