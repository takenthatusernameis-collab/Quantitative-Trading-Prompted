#!/usr/bin/env python3
"""Unit and CLI tests for trustworthy Kilo controller terminal outcomes."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("kilo-terminal-outcome.py")
SPEC = importlib.util.spec_from_file_location("kilo_terminal_outcome", SCRIPT)
assert SPEC and SPEC.loader
outcome = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(outcome)


class TerminalOutcomeTests(unittest.TestCase):
    def test_verified_progress_requires_persistence_and_clean_worktree(self):
        self.assertEqual(
            outcome.classify_outcome(project_progress=True, checkpoint_persisted=True, dirty_project_worktree=False),
            ("verified_progress", 0),
        )

    def test_failed_persistence_takes_precedence_over_prior_progress(self):
        self.assertEqual(
            outcome.classify_outcome(project_progress=True, checkpoint_persisted=False, dirty_project_worktree=False),
            ("persistence_failure", 1),
        )

    def test_dirty_substantive_worktree_takes_precedence_over_prior_progress(self):
        self.assertEqual(
            outcome.classify_outcome(project_progress=True, checkpoint_persisted=True, dirty_project_worktree=True),
            ("persistence_failure", 1),
        )

    def test_no_progress_is_not_reported_as_a_successful_worker_run(self):
        self.assertEqual(
            outcome.classify_outcome(project_progress=False, checkpoint_persisted=True, dirty_project_worktree=False),
            ("no_progress_failure", 1),
        )

    def test_intentional_noop_remains_successful_and_is_explicit(self):
        self.assertEqual(
            outcome.classify_outcome(project_progress=False, checkpoint_persisted=False, dirty_project_worktree=True, intentional_noop=True),
            ("intentional_noop", 0),
        )

    def test_control_and_generated_files_are_not_project_changes(self):
        status_lines = [
            "?? .kilo-runtime/current-supervisor-recommendation.json",
            "?? .kilo-runtime/worker-disposition.json",
            "?? .kilo/TWO_AGENT_ONCE",
            "?? .kilo/SKIP_NEXT_ROUTINE_KILO",
            "?? .kilo/supervisor-reports/run-1.md",
            "?? data/cache.tmp",
            "?? research/worker-output.pyc",
            "?? coverage.xml",
        ]
        self.assertFalse(outcome.project_worktree_is_dirty(status_lines))

    def test_real_source_changes_and_workflow_residue_are_dirty(self):
        self.assertTrue(outcome.project_worktree_is_dirty([" M src/engine.py"]))
        self.assertTrue(outcome.project_worktree_is_dirty([" M .github/workflows/main.yml"]))

    def test_missing_final_status_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing-status.txt"
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "--project-progress", "1",
                    "--checkpoint-persisted", "1", "--git-status-file", str(missing),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("persistence_failure", result.stdout)

    def test_cli_writes_explicit_terminal_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "github-output.txt"
            status = Path(temp) / "git-status.txt"
            status.write_text("", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "--project-progress", "1",
                    "--checkpoint-persisted", "1", "--git-status-file", str(status),
                    "--cutoff", "1", "--output", str(output),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                output.read_text(encoding="utf-8").splitlines(),
                ["terminal_status=verified_progress", "cutoff_reached=true"],
            )

    def test_cli_returns_nonzero_for_no_progress(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--project-progress", "0", "--checkpoint-persisted", "1"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("no_progress_failure", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
