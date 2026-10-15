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
            checkpoint_sha = "a" * 40
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "--project-progress", "1",
                    "--checkpoint-persisted", "1", "--git-status-file", str(status),
                    "--cutoff", "1", "--checkpoint-sha", checkpoint_sha, "--output", str(output),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                output.read_text(encoding="utf-8").splitlines(),
                ["terminal_status=verified_progress", "cutoff_reached=true", f"terminal_checkpoint_sha={checkpoint_sha}"],
            )

    def test_cli_records_checkpoint_sha_for_intentional_noop(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "github-output.txt"
            checkpoint_sha = "b" * 40
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "--intentional-noop",
                    "--checkpoint-sha", checkpoint_sha, "--output", str(output),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                output.read_text(encoding="utf-8").splitlines(),
                ["terminal_status=intentional_noop", "cutoff_reached=false", f"terminal_checkpoint_sha={checkpoint_sha}"],
            )

    def test_cli_returns_nonzero_for_no_progress(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--project-progress", "0", "--checkpoint-persisted", "1"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("no_progress_failure", result.stdout)


    def test_rejected_checkpoint_push_drives_failure_terminal_outcome(self):
        """A genuinely rejected push must not be classified as verified progress."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            remote = root / "remote.git"
            work = root / "work"

            def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["git", *args],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    check=check,
                )

            git(root, "init", "--bare", str(remote))
            git(root, "init", str(work))
            git(work, "config", "user.name", "Kilo terminal-outcome regression")
            git(work, "config", "user.email", "kilo-terminal-test@example.invalid")
            git(work, "checkout", "-b", "main")
            (work / "baseline.txt").write_text("baseline\n", encoding="utf-8")
            git(work, "add", "baseline.txt")
            git(work, "commit", "-m", "test: establish baseline checkpoint")
            git(work, "remote", "add", "origin", str(remote))
            git(work, "push", "-u", "origin", "main")
            baseline_sha = git(work, "rev-parse", "HEAD").stdout.strip()

            # Reject only the subsequent test checkpoint, in this disposable bare repo.
            hook = remote / "hooks" / "pre-receive"
            hook.write_text(
                "#!/bin/sh\n"
                "cat >/dev/null\n"
                "echo 'injected checkpoint persistence failure' >&2\n"
                "exit 1\n",
                encoding="utf-8",
            )
            hook.chmod(0o755)
            # Runner-level core.hooksPath may be relative to the sender's workspace.
            # Pin the receiving bare repository to its own absolute hook directory.
            git(root, "--git-dir", str(remote), "config", "core.hooksPath", str(remote / "hooks"))

            (work / "research-change.txt").write_text("meaningful but unpersisted work\n", encoding="utf-8")
            git(work, "add", "research-change.txt")
            git(work, "commit", "-m", "test: create unpersisted project progress")
            local_checkpoint_sha = git(work, "rev-parse", "HEAD").stdout.strip()
            rejected = git(work, "push", "origin", "HEAD:refs/heads/main", check=False)
            self.assertNotEqual(rejected.returncode, 0, "the simulated remote must reject the checkpoint push")
            self.assertIn("injected checkpoint persistence failure", rejected.stdout + rejected.stderr)

            remote_sha = git(root, "--git-dir", str(remote), "rev-parse", "refs/heads/main").stdout.strip()
            self.assertEqual(remote_sha, baseline_sha, "remote default-branch head must stay at the prior checkpoint")
            self.assertNotEqual(local_checkpoint_sha, remote_sha)
            status = git(work, "status", "--porcelain", "--untracked-files=all").stdout
            self.assertEqual(status, "", "committed-but-unpushed work can leave a clean local worktree")

            status_file = root / "final-git-status.txt"
            status_file.write_text(status, encoding="utf-8")
            github_output = root / "github-output.txt"
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--project-progress", "1",
                    "--checkpoint-persisted", "0",
                    "--git-status-file", str(status_file),
                    "--cutoff", "0",
                    "--checkpoint-sha", local_checkpoint_sha,
                    "--output", str(github_output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("persistence_failure", result.stdout)
            outputs = github_output.read_text(encoding="utf-8").splitlines()
            self.assertIn("terminal_status=persistence_failure", outputs)
            self.assertIn("cutoff_reached=false", outputs)
            self.assertIn(f"terminal_checkpoint_sha={local_checkpoint_sha}", outputs)

            # Guard the real caller wiring and job summary against accidental disconnection.
            repo_root = SCRIPT.resolve().parents[2]
            controller = (repo_root / ".github/scripts/kilo-controller.sh").read_text(encoding="utf-8")
            workflow = (repo_root / ".github/workflows/main.yml").read_text(encoding="utf-8")
            self.assertIn('--checkpoint-persisted "${persisted:-1}"', controller)
            self.assertIn('exit "$terminal_rc"', controller)
            self.assertIn("persistence_failure)", workflow)
            self.assertIn("Checkpoint persistence or clean-worktree verification failed", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
