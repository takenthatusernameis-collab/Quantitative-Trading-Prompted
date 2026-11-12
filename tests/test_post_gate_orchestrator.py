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


def _run(extra_args: list[str], gate_epoch: str, handoff: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update(
        {
            "PYTHON": "true",  # no-op python so the cycle is fast and side-effect free
            "RUFF": "true",
            "GATE_EPOCH": gate_epoch,
            "HANDOFF": str(handoff),
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT), *extra_args],
        cwd=REPO_ROOT,
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