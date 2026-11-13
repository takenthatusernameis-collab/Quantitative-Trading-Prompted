"""Regression tests for scripts/post_gate_orchestrator.sh argument handling.

Focus: the ``--force`` clock-gate override must be honored in ANY argument
position (inv5 flagged that only a leading ``--force`` bypassed the gate), while
the default (no ``--force``) clock-gate guard must be preserved.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "post_gate_orchestrator.sh"

# Far-future gate (2100-01-01T00:00:00Z) so the guard would trigger without --force.
FUTURE_GATE = "4102444800"
# Past gate (2026-11-12T22:00:00Z) that is already released.
PAST_GATE = "1794520800"


def _run(
    extra_args: list[str],
    gate_epoch: str,
    handoff: Path,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update(
        {
            "PYTHON": "true",  # no-op python so the cycle is fast and side-effect free
            "RUFF": "true",
            "GATE_EPOCH": gate_epoch,
            "HANDOFF": str(handoff),
        }
    )
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), *extra_args],
        cwd=REPO_ROOT,
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_default_guard_blocks_before_gate(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], FUTURE_GATE, handoff)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert not handoff.exists()


def test_force_second_position_bypasses_gate(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only", "--force"], FUTURE_GATE, handoff)
    assert proc.returncode != 3, proc.stdout + proc.stderr
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert handoff.exists()


def test_force_first_position_still_bypasses_gate(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    proc = _run(["--force", "--read-only"], FUTURE_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert handoff.exists()


def test_released_gate_default_proceeds_read_only(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], PAST_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert handoff.exists()


def test_wait_until_gate_times_out_before_release(tmp_path: Path) -> None:
    # A far-future gate with a 1s wait budget must block, then exit 3 without
    # writing the handoff (the run cutoff is the real bound in production).
    handoff = tmp_path / "handoff.md"
    proc = _run(
        ["--read-only", "--wait-until-gate", "--max-wait-seconds", "1"],
        FUTURE_GATE,
        handoff,
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert not handoff.exists()
    assert "wait budget exhausted" in proc.stdout


def test_wait_until_gate_past_gate_proceeds(tmp_path: Path) -> None:
    # If the gate is already released, --wait-until-gate must not block.
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only", "--wait-until-gate"], PAST_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert handoff.exists()


def test_max_wait_seconds_requires_value(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only", "--max-wait-seconds"], FUTURE_GATE, handoff)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert not handoff.exists()


def test_failed_subcheck_exits_nonzero_and_marks_handoff(tmp_path: Path) -> None:
    # A failing sub-check must make the orchestrator exit non-zero AND mark the
    # handoff FAILED -- it must not silently claim "cycle complete" on failure.
    handoff = tmp_path / "handoff.md"
    proc = _run(
        ["--read-only"],
        PAST_GATE,
        handoff,
        env_extra={"PYTHON": "false", "RUFF": "false"},
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "STEP FAILED" in proc.stdout
    assert handoff.exists()
    assert "FAILED" in handoff.read_text()


def test_successful_cycle_marks_handoff_ok(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], PAST_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert handoff.exists()
    assert "OK" in handoff.read_text()