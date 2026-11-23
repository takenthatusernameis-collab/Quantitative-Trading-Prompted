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
import time
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
    # Default to an empty RUNNER_TEMP so the heartbeat auto-derivation is
    # deterministic (no real controller progress file leaks in); tests that
    # exercise auto-derivation override RUNNER_TEMP via extra_env.
    env["RUNNER_TEMP"] = str(tmp_path / "runner-temp")
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


def test_state_file_override_matching_hash_exits_0(tmp_path: Path) -> None:
    """The STATE_FILE override selects a non-default state file for hashing.

    The script honors a STATE_FILE env override (scripts/pre_gate_check.sh:39) so
    callers can check a state file at a path other than the default
    data/processed/paper_trading_state.yaml. This path was previously untested:
    a regression that ignored STATE_FILE (always hashing the default) would have
    silently produced a false "hash matches" against the wrong file. Pin it.
    """
    custom = tmp_path / "alt" / "state.yaml"
    custom.parent.mkdir(parents=True, exist_ok=True)
    custom.write_text("last_run_date: '2026-11-13'\ncurrent_nav: 2.0\n")
    # A *different* default state file must exist so a regression that ignores
    # STATE_FILE and hashes the default would produce a different hash and fail.
    default = _make_state(tmp_path)
    sha = _sha256(custom)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "pre_gate_check.sh").write_text(SCRIPT.read_text())
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    proc = _run(tmp_path, FUTURE_GATE, sha, extra_env={"STATE_FILE": "alt/state.yaml"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PRE-GATE OK" in proc.stderr, proc.stderr
    assert default.exists(), "default state file must still be present"


def test_state_file_override_missing_exits_2(tmp_path: Path) -> None:
    """A STATE_FILE override pointing at a missing path fails closed with exit 2."""
    _make_state(tmp_path)  # default exists; the override does not
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "pre_gate_check.sh").write_text(SCRIPT.read_text())
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    proc = _run(
        tmp_path,
        FUTURE_GATE,
        DUMMY_SHA,
        extra_env={"STATE_FILE": "alt/does_not_exist.yaml"},
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "state file not found" in proc.stderr, proc.stderr


def test_gate_reached_exits_3(tmp_path: Path) -> None:
    sha = _sha256(_make_state(tmp_path))
    proc = _run(tmp_path, PAST_GATE, sha)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "gate is released" in proc.stderr, proc.stderr


def test_reachability_reports_unreachable_when_budget_too_small(tmp_path: Path) -> None:
    """A budget far smaller than T-remaining yields GATE_REACHABLE=0 on exit 0.

    Pre-gate sessions repeatedly re-derived by hand that the 22:00Z gate release
    falls after the ~355-minute run cutoff. SESSION_BUDGET_SECONDS makes that a
    deterministic verdict; it must never turn the cheap path into a failure.
    """
    sha = _sha256(_make_state(tmp_path))
    proc = _run(tmp_path, FUTURE_GATE, sha, extra_env={"SESSION_BUDGET_SECONDS": "1"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE_REACHABLE=0" in proc.stderr, proc.stderr


def test_reachability_reports_waitable_when_budget_covers_gate(tmp_path: Path) -> None:
    """A budget larger than T-remaining yields GATE_REACHABLE=1 on exit 0."""
    sha = _sha256(_make_state(tmp_path))
    # FUTURE_GATE is 2100-01-01; any budget below that is unreachable, so use a
    # very large budget to exercise the reachable branch deterministically.
    proc = _run(
        tmp_path,
        FUTURE_GATE,
        sha,
        extra_env={"SESSION_BUDGET_SECONDS": "999999999999"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE_REACHABLE=1" in proc.stderr, proc.stderr


def test_bad_session_budget_exits_2(tmp_path: Path) -> None:
    """A non-numeric SESSION_BUDGET_SECONDS fails closed instead of acting as 0."""
    sha = _sha256(_make_state(tmp_path))
    proc = _run(tmp_path, FUTURE_GATE, sha, extra_env={"SESSION_BUDGET_SECONDS": "1h"})
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "SESSION_BUDGET_SECONDS" in proc.stderr, proc.stderr


def test_bad_cutoff_epoch_exits_2(tmp_path: Path) -> None:
    """A non-numeric CUTOFF_EPOCH fails closed instead of acting as 0.

    Mirrors the GATE_EPOCH/SESSION_BUDGET_SECONDS guards: an absolute cutoff that
    silently degraded to 0 would report the gate as trivially unreachable, a false
    verdict that defeats the deterministic reachability this input exists to add.
    """
    sha = _sha256(_make_state(tmp_path))
    proc = _run(tmp_path, FUTURE_GATE, sha, extra_env={"CUTOFF_EPOCH": "soon"})
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "CUTOFF_EPOCH" in proc.stderr, proc.stderr


def test_reachability_absolute_cutoff_unreachable(tmp_path: Path) -> None:
    """An absolute CUTOFF_EPOCH just after now, with a far-future gate, is unreachable.

    The absolute cutoff is the exact global run deadline (controller start + 355m);
    it must yield the same GATE_REACHABLE=0 verdict as a small relative budget, but
    without any session-start estimation.
    """
    sha = _sha256(_make_state(tmp_path))
    cutoff = str(int(time.time()) + 1)
    proc = _run(tmp_path, FUTURE_GATE, sha, extra_env={"CUTOFF_EPOCH": cutoff})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE_REACHABLE=0" in proc.stderr, proc.stderr
    assert "absolute CUTOFF_EPOCH" in proc.stderr, proc.stderr


def test_reachability_absolute_cutoff_waitable(tmp_path: Path) -> None:
    """An absolute CUTOFF_EPOCH at/after the gate yields GATE_REACHABLE=1.

    With CUTOFF_EPOCH == the far-future gate, remaining budget equals T-remaining,
    so the gate is (boundary) reachable and the script must say so on exit 0.
    """
    sha = _sha256(_make_state(tmp_path))
    proc = _run(tmp_path, FUTURE_GATE, sha, extra_env={"CUTOFF_EPOCH": FUTURE_GATE})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE_REACHABLE=1" in proc.stderr, proc.stderr


def test_absolute_cutoff_takes_precedence_over_relative_budget(tmp_path: Path) -> None:
    """When both are set, the absolute CUTOFF_EPOCH wins over SESSION_BUDGET_SECONDS.

    A relative budget of ~1e12s would say "reachable"; the absolute cutoff just
    after now must override it and report unreachable. Otherwise a caller who sets
    both could get the optimistic (wrong) relative verdict instead of the exact one.
    """
    sha = _sha256(_make_state(tmp_path))
    cutoff = str(int(time.time()) + 1)
    proc = _run(
        tmp_path,
        FUTURE_GATE,
        sha,
        extra_env={"CUTOFF_EPOCH": cutoff, "SESSION_BUDGET_SECONDS": "999999999999"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE_REACHABLE=0" in proc.stderr, proc.stderr
    assert "absolute CUTOFF_EPOCH" in proc.stderr, proc.stderr


def test_reachability_is_side_effect_free(tmp_path: Path) -> None:
    """Enabling the reachability verdict must not write anything."""
    sha = _sha256(_make_state(tmp_path))
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "pre_gate_check.sh").write_text(SCRIPT.read_text())
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    before = _snapshot(tmp_path)
    proc = _run(tmp_path, FUTURE_GATE, sha, extra_env={"SESSION_BUDGET_SECONDS": "1"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _snapshot(tmp_path) == before


def _write_heartbeat(dirpath: Path, updated_utc: str, remaining_seconds: str) -> Path:
    """Write a controller-style progress heartbeat and return its path."""
    dirpath.mkdir(parents=True, exist_ok=True)
    hb = dirpath / "kilo-progress-state-45173663210-1.txt"
    hb.write_text(
        f"updated_utc={updated_utc}\nphase=invocation-start\nsession=1\n"
        f"session_limit=1000\nattempt=1\nremaining_seconds={remaining_seconds}\n"
    )
    return hb


def _utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_reachability_auto_derives_unreachable_from_heartbeat(tmp_path: Path) -> None:
    """With no explicit budget, a stale/small heartbeat yields GATE_REACHABLE=0.

    This is the durable fix for the recurring hand-computation of the cutoff:
    the controller's own heartbeat (updated_utc + remaining_seconds) is the
    authoritative source. A tiny remaining budget against a far-future gate must
    report unreachable, on exit 0, without the caller passing CUTOFF_EPOCH.
    """
    sha = _sha256(_make_state(tmp_path))
    hb_dir = tmp_path / "runner-temp"
    _write_heartbeat(hb_dir, _utc_now_iso(), "1")
    proc = _run(tmp_path, FUTURE_GATE, sha, extra_env={"RUNNER_TEMP": str(hb_dir)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE_REACHABLE=0" in proc.stderr, proc.stderr
    assert "controller heartbeat" in proc.stderr, proc.stderr


def test_reachability_auto_derives_waitable_from_heartbeat(tmp_path: Path) -> None:
    """A heartbeat with a huge remaining budget yields GATE_REACHABLE=1.

    cutoff = epoch(updated_utc) + remaining_seconds; a near-infinite budget puts
    the cutoff past the far-future gate, so the gate is waitable.
    """
    sha = _sha256(_make_state(tmp_path))
    hb_dir = tmp_path / "runner-temp"
    _write_heartbeat(hb_dir, _utc_now_iso(), "999999999999")
    proc = _run(tmp_path, FUTURE_GATE, sha, extra_env={"RUNNER_TEMP": str(hb_dir)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE_REACHABLE=1" in proc.stderr, proc.stderr
    assert "controller heartbeat" in proc.stderr, proc.stderr


def test_reachability_auto_derive_no_heartbeat_emits_no_verdict(tmp_path: Path) -> None:
    """No heartbeat and no explicit budget means no verdict, still exit 0.

    The auto-derivation must never fail the cheap path or invent a budget: with
    an empty RUNNER_TEMP and no CONTROLLER_PROGRESS_FILE, the script prints no
    GATE_REACHABLE line but still exits 0 (reachability is informational only).
    """
    sha = _sha256(_make_state(tmp_path))
    proc = _run(tmp_path, FUTURE_GATE, sha)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE_REACHABLE" not in proc.stderr, proc.stderr


def test_reachability_explicit_cutoff_beats_auto_heartbeat(tmp_path: Path) -> None:
    """An explicit CUTOFF_EPOCH takes precedence over the auto-derived heartbeat.

    A heartbeat with a near-infinite budget would say reachable; a CUTOFF_EPOCH
    just after now must override it and report unreachable, so an explicit
    absolute cutoff is never second-guessed by heartbeat auto-derivation.
    """
    sha = _sha256(_make_state(tmp_path))
    hb_dir = tmp_path / "runner-temp"
    _write_heartbeat(hb_dir, _utc_now_iso(), "999999999999")
    cutoff = str(int(time.time()) + 1)
    proc = _run(
        tmp_path,
        FUTURE_GATE,
        sha,
        extra_env={"RUNNER_TEMP": str(hb_dir), "CUTOFF_EPOCH": cutoff},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE_REACHABLE=0" in proc.stderr, proc.stderr
    assert "absolute CUTOFF_EPOCH" in proc.stderr, proc.stderr


def test_reachability_auto_derive_uses_explicit_progress_file(tmp_path: Path) -> None:
    """CONTROLLER_PROGRESS_FILE selects the heartbeat path explicitly.

    RUNNER_TEMP points at an empty dir, so only an explicit CONTROLLER_PROGRESS_FILE
    can supply the heartbeat. This pins the override that lets a caller (or test)
    name the exact heartbeat regardless of RUNNER_TEMP/GITHUB_* layout.
    """
    sha = _sha256(_make_state(tmp_path))
    hb_dir = tmp_path / "elsewhere"
    hb = _write_heartbeat(hb_dir, _utc_now_iso(), "1")
    proc = _run(
        tmp_path,
        FUTURE_GATE,
        sha,
        extra_env={"CONTROLLER_PROGRESS_FILE": str(hb)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GATE_REACHABLE=0" in proc.stderr, proc.stderr
    assert "controller heartbeat" in proc.stderr, proc.stderr


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