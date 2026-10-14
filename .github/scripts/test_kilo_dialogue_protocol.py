#!/usr/bin/env python3
"""Regression tests for the dual-track dialogue protocol and completion evidence gate."""
from __future__ import annotations

import concurrent.futures
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("kilo_dialogue_protocol.py")
SPEC = importlib.util.spec_from_file_location("kilo_dialogue_protocol", SCRIPT)
assert SPEC and SPEC.loader
protocol = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(protocol)


class DialogueProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.dialogue = self.root / "agent-dialogue.jsonl"
        self.communication = self.root / "agent-communication.jsonl"
        self.task = "run-42-attempt-1"
        self.message_id = self.task + "-review-0001"

    def tearDown(self):
        self.temp.cleanup()

    def event(self, stage, direction="supervisor_to_worker", disposition="", task=None, message_id=None, **extra):
        return protocol.make_event(
            stage=stage,
            direction=direction,
            role="supervisor" if direction == "supervisor_to_worker" else ("worker" if direction == "worker_to_supervisor" else "controller"),
            message_id=message_id or self.message_id,
            correlation_id=self.message_id,
            task_id=task or self.task,
            message=extra.pop("message", "message for the task"),
            disposition=disposition,
            **extra,
        )

    def write_exchange(self, disposition="verified", task=None, work_performed="Updated implementation and regression tests.", verification="Focused tests passed and remote checkpoint inspected.", blockers=None, outstanding_work=None):
        task = task or self.task
        protocol.append_event(self.dialogue, self.event("message_delivered", task=task, message_id=self.message_id))
        protocol.append_event(self.communication, self.event("message_written", task=task, message_id=self.message_id, delivery_state="written"))
        protocol.append_event(self.communication, self.event("message_delivered", task=task, message_id=self.message_id, delivery_state="delivered"))
        protocol.append_event(self.communication, self.event(
            "worker_acknowledged", direction="worker_to_supervisor", task=task, message_id=self.message_id,
            acknowledgement_state="acknowledged", message="Worker acknowledged the recommendation.",
        ))
        protocol.append_event(self.communication, self.event(
            "worker_processed", direction="worker_to_supervisor", task=task, message_id=self.message_id,
            acknowledgement_state="acknowledged", disposition=disposition,
            work_performed=work_performed, verification=verification, reason="I assessed the advice against actual evidence.",
            blockers=blockers or [], outstanding_work=outstanding_work or [],
            message="Worker response correlated to the supervisor recommendation.",
        ))
        protocol.append_event(self.dialogue, self.event(
            "message_delivered", direction="worker_to_supervisor", task=task, message_id=self.message_id,
            acknowledgement_state="acknowledged", disposition=disposition,
            work_performed=work_performed, verification=verification,
            message="Worker response correlated to the supervisor recommendation.",
        ))

    def manifest(self, task=None, remote_sha="a" * 40):
        return {
            "schema_version": 1,
            "verifier": "controller",
            "task_id": task or self.task,
            "acceptance_criteria": [
                {"id": "implementation", "status": "passed", "verified_by": "controller", "evidence_ref": "test-report#implementation"}
            ],
            "tests": [
                {"name": "dialogue-regression-tests", "status": "passed", "exit_code": 0, "verified_by": "controller", "evidence_ref": "workflow-run#test-job"}
            ],
            "remote_checkpoint": {"verified": True, "sha": remote_sha},
            "artifacts": [
                {"ref": "workflow-artifact#dialogue", "verified": True, "verified_by": "controller", "evidence_ref": "workflow-run#artifact"}
            ],
            "blockers": [],
            "outstanding_work": [],
        }

    def evaluate(self, verification=None, checkpoint_sha="a" * 40, checkpoint_persisted=True, task=None):
        verification_path = None
        if verification is not None:
            verification_path = self.root / "verification.json"
            verification_path.write_text(json.dumps(verification), encoding="utf-8")
        return protocol.evaluate_completion(
            dialogue_path=self.dialogue,
            communication_path=self.communication,
            verification_path=verification_path,
            task_id=task or self.task,
            checkpoint_sha=checkpoint_sha,
            checkpoint_persisted=checkpoint_persisted,
        )

    def test_recommendation_without_worker_reply_never_completes(self):
        protocol.append_event(self.communication, self.event("message_written", delivery_state="written"))
        protocol.append_event(self.dialogue, self.event("message_delivered"))
        protocol.append_event(self.communication, self.event("message_delivered", delivery_state="delivered"))
        result = self.evaluate(self.manifest())
        self.assertNotEqual(result["status"], "verified_completion")
        self.assertEqual(result["status"], "awaiting_worker_response")

    def test_acknowledgement_without_execution_does_not_complete(self):
        protocol.append_event(self.communication, self.event("message_written", delivery_state="written"))
        protocol.append_event(self.communication, self.event("message_delivered", delivery_state="delivered"))
        protocol.append_event(self.dialogue, self.event("message_delivered"))
        protocol.append_event(self.communication, self.event(
            "worker_acknowledged", direction="worker_to_supervisor",
            acknowledgement_state="acknowledged", message="Acknowledged only; I have not executed the task."
        ))
        result = self.evaluate(self.manifest())
        self.assertNotEqual(result["status"], "verified_completion")
        self.assertEqual(result["status"], "awaiting_worker_response")

    def test_failed_test_blocks_completion_even_when_worker_claims_verified(self):
        self.write_exchange()
        manifest = self.manifest()
        manifest["tests"][0]["exit_code"] = 1
        self.assertNotEqual(self.evaluate(manifest)["status"], "verified_completion")

    def test_unverified_remote_checkpoint_blocks_completion(self):
        self.write_exchange()
        manifest = self.manifest()
        manifest["remote_checkpoint"]["sha"] = "b" * 40
        self.assertNotEqual(self.evaluate(manifest)["status"], "verified_completion")
        self.assertNotEqual(self.evaluate(self.manifest(), checkpoint_persisted=False)["status"], "verified_completion")

    def test_only_correlated_worker_response_and_full_manifest_can_complete(self):
        self.write_exchange()
        result = self.evaluate(self.manifest())
        self.assertEqual(result["status"], "verified_completion")
        self.assertTrue(result["remote_checkpoint_verified"])
        self.assertTrue(result["acceptance_criteria_verified"])
        self.assertTrue(result["tests_verified"])
        self.assertTrue(result["artifacts_verified"])

    def test_rejected_recommendation_is_recorded_but_not_completion(self):
        self.write_exchange(disposition="rejected_with_reason", work_performed="I examined the advice and rejected it due to evidence.")
        result = self.evaluate(self.manifest())
        self.assertEqual(result["status"], "blocked")
        self.assertNotEqual(result["status"], "verified_completion")

    def test_duplicate_events_are_idempotent_and_survive_reload(self):
        event = self.event("message_delivered")
        self.assertTrue(protocol.append_event(self.dialogue, event))
        self.assertFalse(protocol.append_event(self.dialogue, event))
        events, errors = protocol.read_events(self.dialogue)
        self.assertEqual(errors, [])
        self.assertEqual(len(events), 1)

    def test_partial_append_is_preserved_and_reported(self):
        self.dialogue.write_text('{"schema_version":2,"partial":', encoding="utf-8")
        with self.assertRaises(protocol.ProtocolError):
            protocol.append_event(self.dialogue, self.event("message_delivered"))
        events, errors = protocol.read_events(self.dialogue)
        self.assertEqual(events, [])
        self.assertTrue(any("incomplete trailing record" in error for error in errors))

    def test_malformed_record_is_not_silently_accepted(self):
        self.dialogue.write_text('{"schema_version":1,"direction":"supervisor_to_worker"}\n', encoding="utf-8")
        events, errors = protocol.read_events(self.dialogue)
        self.assertEqual(events, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(self.evaluate()["status"], "incomplete_evidence")

    def test_parallel_writers_do_not_duplicate_or_corrupt_distinct_session_events(self):
        def add(index):
            event = self.event("message_delivered", task=f"task-{index}", message_id=f"message-{index}", message=f"message {index}")
            return protocol.append_event(self.communication, event)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(add, range(40)))
        self.assertEqual(sum(outcomes), 40)
        events, errors = protocol.read_events(self.communication)
        self.assertEqual(errors, [])
        self.assertEqual(len(events), 40)
        self.assertEqual(len({(e["task_id"], e["message_id"]) for e in events}), 40)

    def test_messages_from_other_tasks_cannot_satisfy_this_task(self):
        other_task = "run-99-attempt-1"
        self.write_exchange(task=other_task)
        self.assertEqual(self.evaluate(self.manifest(), task=self.task)["status"], "awaiting_worker_response")

    def test_missing_artifacts_and_acceptance_criteria_never_pass(self):
        self.write_exchange()
        manifest = self.manifest()
        manifest["artifacts"] = []
        manifest["acceptance_criteria"] = []
        self.assertNotEqual(self.evaluate(manifest)["status"], "verified_completion")
        self.assertEqual(self.evaluate(None)["status"], "awaiting_independent_verification")


if __name__ == "__main__":
    unittest.main(verbosity=2)
