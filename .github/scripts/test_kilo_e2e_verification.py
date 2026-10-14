#!/usr/bin/env python3
"""Regression tests for the bounded hosted Kilo E2E verifier."""
from __future__ import annotations
import importlib.util
import unittest
from pathlib import Path
SCRIPT = Path(__file__).with_name("kilo-e2e-verification.py")
SPEC = importlib.util.spec_from_file_location("kilo_e2e_verification", SCRIPT)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)

class E2EVerificationTests(unittest.TestCase):
    def fixture(self):
        task = "123-attempt-1"
        session = "123-attempt-1-session-1-try-1"
        recommendation = "123-attempt-1-review-0001"
        disposition = {"schema_version": 2, "task_id": task, "session_id": session,
            "recommendation_id": recommendation, "acknowledgement_state": "acknowledged",
            "disposition": "verified", "reason": "Completed the bounded task.",
            "evidence": "Created report and ran focused tests.", "verification": "Focused tests returned zero.",
            "work_performed": "Created a run-scoped report and ran regressions.", "blockers": [], "outstanding_work": []}
        events = [
            {"task_id": task, "session_id": session, "direction": "worker_to_supervisor",
             "stage": "worker_acknowledged", "correlation_id": recommendation, "acknowledgement_state": "acknowledged"},
            {"task_id": task, "session_id": session, "direction": "worker_to_supervisor",
             "stage": "worker_processed", "correlation_id": recommendation, "disposition": "verified",
             "work_performed": disposition["work_performed"], "verification": disposition["verification"]}]
        return task, session, disposition, events
    def test_startup_gate_uses_real_shell_variables(self):
        # Guard against escaped ${...} expressions making the shell if-condition
        # compare a literal string and silently bypass the E2E startup barrier.
        controller = SCRIPT.with_name("kilo-controller.sh").read_text(encoding="utf-8")
        start = controller.index('if [ "${KILO_E2E_MODE:-0}" = "1" ]; then')
        end = controller.index("# Project changes exclude workflow definitions and control-only markers.", start)
        gate = controller[start:end]
        self.assertNotIn("\\${", gate)
        self.assertIn("current-supervisor-recommendation.json", gate)
        self.assertIn('"message_written"', gate)
        self.assertIn("no worker was started", gate)

    def test_only_non_default_infra_branch_allowed(self):
        self.assertTrue(verifier.isolated_target_branch("infra/e2e-test", "main"))
        self.assertFalse(verifier.isolated_target_branch("main", "main"))
        self.assertFalse(verifier.isolated_target_branch("feature/e2e-test", "main"))
        self.assertFalse(verifier.isolated_target_branch("infra/e2e-test", "infra/e2e-test"))
    def test_correlated_disposition_passes(self):
        task, session, disposition, events = self.fixture()
        ok, note, found = verifier.disposition_matches(disposition, events, task)
        self.assertTrue(ok, note)
        self.assertEqual(found, session)
    def test_wrong_task_or_session_fails(self):
        task, session, disposition, events = self.fixture()
        self.assertFalse(verifier.disposition_matches(disposition, events, "other-task")[0])
        disposition["session_id"] = "wrong-session"
        self.assertFalse(verifier.disposition_matches(disposition, events, task)[0])
    def test_processed_response_without_ack_fails(self):
        task, session, disposition, events = self.fixture()
        self.assertFalse(verifier.disposition_matches(disposition, [events[-1]], task)[0])
    def test_open_work_or_nonverified_disposition_fails(self):
        task, session, disposition, events = self.fixture()
        disposition["outstanding_work"] = ["more work"]
        self.assertFalse(verifier.disposition_matches(disposition, events, task)[0])
        disposition["outstanding_work"] = []
        disposition["disposition"] = "in_progress"
        self.assertFalse(verifier.disposition_matches(disposition, events, task)[0])

if __name__ == "__main__":
    unittest.main(verbosity=2)
