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

    def test_two_cycles_preserve_feedback_and_record_exact_request_response(self):
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
                list(transcripts.iterdir()), [],
                "reviewer prompts, CLI traces, status files, and undelivered advice must not be recorded as role dialogue",
            )

    def test_failed_review_records_request_and_cli_output_without_erasing_feedback(self):
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
                list(transcripts.iterdir()), [],
                "an undelivered report is not a supervisor-to-worker dialogue message",
            )

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
                "disposition": "in_progress",
                "reason": "I am applying the focused recommendation before other work.",
                "evidence": "The relevant assertion failed in the previous test run.",
                "verification": "",
                "updated_at": "2026-10-14T00:00:00Z",
            }
            (protocol / "worker-disposition.json").write_text(json.dumps(disposition), encoding="utf-8")
            accepted = monitor.read_worker_disposition(protocol)
            self.assertEqual(accepted["disposition"], "in_progress")
            self.assertIn("in_progress", monitor.dialogue_protocol_observation(protocol))

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

if __name__ == "__main__":
    unittest.main(verbosity=2)
