"""Regression tests for scripts/pre_gate_check.sh.

The cheap pre-gate path was prose-only and unenforced, so pre-gate sessions kept
re-running the full cycle and committing handoff-timestamp churn. This script
encodes the cheap path as a deterministic, side-effect-free check. These tests
pin the exit-code contract and, critically, that the script NEVER writes a file
or touches ``data/raw``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "pre_gate_check.sh"

# 2026-11-16T22:00:00Z — the gate the current cycle targets.
GATE_20261116 = "1794866400"
# Far-future gate so the "before gate" branch triggers deterministically.
FUTURE_GATE = "4102444800"  # 2100-01-01T00:00:00Z
# Past gate so the "gate reached" branch triggers deterministically.
PAST_GATE = "1794520800"  # 2026-11-12T22:00:00Z
# Any 64-char hex string works for the "gate reached" short-circuit test.
DUMMY_SHA = "0" * 64


def _make_state(tmp_path: Path) -> Path:
    """Create the throwaway state file at the default relative path and return it."""
    state_path = tmp_path / "data" / "processed" / "paper_trading_state.yaml"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("last_run_date: '2026-11-13'\ncurrent_nav: 1.0\n")
    return state_path


def _run(
    tmp_path: Path,
    gate_epoch: str,
    state_sha: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the script against a throwaway copy of the repo tree rooted in tmp_path.

    The script ``cd``s to its own repo root (parent of ``scripts/``), so we copy
    just the script into ``tmp_path/scripts`` and create a minimal state file and
    git context there. This keeps the real repo untouched.
    """
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script = scripts_dir / "pre_gate_check.sh"
    script.write_text(SCRIPT.read_text())

    # Minimal fake state file at the default relative path.
    _make_state(tmp_path)

    # A git repo so `git status --porcelain -- data/raw` succeeds with empty out.
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)

    env = dict(os.environ)
    env.update({"GATE_EPOCH": gate_epoch, "STATE_SHA256": state_sha})
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(script)],
        cwd=tmp_path,
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_missing_env_args_exits_2(tmp_path: Path) -> None:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "pre_gate_check.sh").write_text(SCRIPT.read_text())
    env = dict(os.environ)
    env.pop("GATE_EPOCH", None)
    env.pop("STATE_SHA256", None)
    proc = subprocess.run(
        ["bash", str(scripts_dir / "pre_gate_check.sh")],
        cwd=tmp_path,
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_bad_gate_epoch_exits_2(tmp_path: Path) -> None:
    proc = _run(tmp_path, "not-an-int", DUMMY_SHA)
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_bad_sha_format_exits_2(tmp_path: Path) -> None:
    proc = _run(tmp_path, FUTURE_GATE, "xyz")
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_missing_state_file_exits_2(tmp_path: Path) -> None:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "pre_gate_check.sh").write_text(SCRIPT.read_text())
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    proc = subprocess.run(
        ["bash", str(scripts_dir / "pre_gate_check.sh")],
        cwd=tmp_path,
        check=False,
        env={**os.environ, "GATE_EPOCH": FUTURE_GATE, "STATE_SHA256": DUMMY_SHA},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_before_gate_matching_hash_clean_raw_exits_0(tmp_path: Path) -> None:
    sha = _sha256(_make_state(tmp_path))
    # Materialize the script copy first so the snapshot captures the exact tree
    # the script will execute against; then assert the run is side-effect free.
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "pre_gate_check.sh").write_text(SCRIPT.read_text())
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    before = _snapshot(tmp_path)
    proc = _run(tmp_path, FUTURE_GATE, sha)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PRE-GATE OK" in proc.stderr, proc.stderr
    # Side-effect free: the tree must be byte-identical after the check.
    assert _snapshot(tmp_path) == before


def test_gate_reached_exits_3(tmp_path: Path) -> None:
    sha = _sha256(_make_state(tmp_path))
    proc = _run(tmp_path, PAST_GATE, sha)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "gate is released" in proc.stderr, proc.stderr


def test_hash_drift_exits_3(tmp_path: Path) -> None:
    _make_state(tmp_path)
    proc = _run(tmp_path, FUTURE_GATE, "1" * 64)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "state hash" in proc.stderr, proc.stderr


def test_dirty_raw_exits_3(tmp_path: Path) -> None:
    sha = _sha256(_make_state(tmp_path))
    # _run already git-init'd; create and commit a tracked raw file, then dirty it.
    raw = tmp_path / "data" / "raw" / "x.csv"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("a,b\n1,2\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    raw.write_text("a,b\n1,3\n")  # dirty
    proc = _run(tmp_path, FUTURE_GATE, sha)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "data/raw" in proc.stderr, proc.stderr


def test_git_status_failure_is_not_reported_clean(tmp_path: Path) -> None:
    """A failing `git status` must fail closed, not report data/raw as clean.

    Reproduces the defect: outside a git repository `git status --porcelain`
    exits 128 with empty stdout. Treating that empty stdout as "clean" is a
    false assurance that defeats the check; the script must exit 3.
    """
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "pre_gate_check.sh").write_text(SCRIPT.read_text())
    # No `git init`: `git status` will fail with rc 128.
    sha = _sha256(_make_state(tmp_path))
    proc = _run_no_git(tmp_path, FUTURE_GATE, sha)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "git status" in proc.stderr, proc.stderr
    assert "do NOT take the cheap path" in proc.stderr, proc.stderr


def _run_no_git(
    tmp_path: Path,
    gate_epoch: str,
    state_sha: str,
) -> subprocess.CompletedProcess[str]:
    """Run the script in tmp_path WITHOUT initialising a git repo."""
    scripts_dir = tmp_path / "scripts"
    script = scripts_dir / "pre_gate_check.sh"
    env = dict(os.environ)
    env.update({"GATE_EPOCH": gate_epoch, "STATE_SHA256": state_sha})
    return subprocess.run(
        ["bash", str(script)],
        cwd=tmp_path,
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _snapshot(root: Path) -> dict[str, str]:
    """Map every file under root (excluding .git) to its sha256."""
    snap: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            snap[str(path.relative_to(root))] = _sha256(path)
    return snap