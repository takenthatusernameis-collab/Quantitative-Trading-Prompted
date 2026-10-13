#!/usr/bin/env python3
"""Deterministic tests for the continuous Kilo supervisor monitor; no model calls."""
from __future__ import annotations

import importlib.util
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
            try:
                os.environ["SUPERVISOR_TEST_CAPTURE"] = str(capture)
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
            published = feedback.read_text(encoding="utf-8")
            self.assertIn("worker review 1", published)
            self.assertIn("worker review 2", published)
            prompts = capture.read_text(encoding="utf-8")
            self.assertIn("worker review 1", prompts)
            self.assertIn("[REDACTED]", prompts)
            self.assertNotIn("secret-value", prompts)
            self.assertNotIn("ghp_123456789012345678901234567890", prompts)
            self.assertEqual(len(list(report_dir.glob("run-test-run-attempt-1-review-*.md"))), 2)

            first_prompt = prompts.split("\n---PROMPT-END---\n", 1)[0]
            request_file = transcripts / "review-0001-request-to-supervisor.md"
            response_file = transcripts / "review-0001-response-from-supervisor.md"
            cli_file = transcripts / "review-0001-supervisor-cli-output.txt"
            saved_request = request_file.read_text(encoding="utf-8")
            self.assertEqual(saved_request.rstrip("\n"), first_prompt.rstrip("\n"),
                             "saved request must match the exact redacted prompt sent to Kilo")
            self.assertIn("worker started", saved_request)
            self.assertNotIn("secret-value", saved_request)
            self.assertEqual(
                response_file.read_text(encoding="utf-8"),
                "STATUS: ATTENTION\nEvidence: worker review 1\nRecommended next action: verify changed evidence 1",
            )
            self.assertIn("mock reviewer CLI output for cycle 1", cli_file.read_text(encoding="utf-8"))

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
            self.assertTrue((transcripts / "review-0001-request-to-supervisor.md").is_file())
            self.assertIn(
                "mock CLI failure body",
                (transcripts / "review-0001-supervisor-cli-output.txt").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
