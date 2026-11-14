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
# The next real gate (2026-11-13T22:00:00Z), used to test gate-derived handoff names.
GATE_20261113 = "1794607200"


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


def _run_script_copy(
    tmp_path: Path,
    extra_args: list[str],
    gate_epoch: str,
    handoff: str | None = None,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a copy of the script rooted in ``tmp_path`` so its default HANDOFF
    (which is written next to the script's repo root) cannot touch the real repo."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "post_gate_orchestrator.sh"
    script.write_text(SCRIPT.read_text())
    env = dict(os.environ)
    env.update({"PYTHON": "true", "RUFF": "true", "GATE_EPOCH": gate_epoch})
    env.pop("HANDOFF", None)
    if handoff is not None:
        env["HANDOFF"] = handoff
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(script), *extra_args],
        cwd=tmp_path,
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


def _stub_python(tmp_path: Path) -> tuple[Path, Path]:
    """A fake interpreter that records every invocation and exits 0.

    The real ``/tmp/kilo-venv/bin/python`` is absent in a fresh runner, and a
    ``true`` stub makes every step an indistinguishable no-op -- so the existing
    tests could only assert the handoff's *text*, never which steps actually ran
    or in what order. This stub logs ``$*`` so the mutating extend (cmd2) and the
    idempotency re-run (cmd4) can be proven to execute, exactly once each, in the
    right position -- without touching live state.
    """
    log = tmp_path / "python_calls.log"
    stub = tmp_path / "fake_python.sh"
    stub.write_text(f'#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "{log}"\nexit 0\n')
    stub.chmod(0o755)
    return stub, log


def _calls(log: Path) -> list[str]:
    if not log.exists():
        return []
    return [line for line in log.read_text().splitlines() if line.strip()]


def test_full_cycle_runs_extend_in_order_and_reports_full_mode(tmp_path: Path) -> None:
    # The gate-release acceptance criteria are stated for the FULL cycle
    # ("Mode: full cycle (extend included)", "Cmds run" includes "2 extend"), but
    # every prior test forced --read-only, so a regression that silently skipped
    # the mutating extend would still exit 0 and write an "OK" handoff. Prove the
    # real ordering: extend -> drift -> idempotent re-extend -> pytest -> cmd7.
    handoff = tmp_path / "handoff.md"
    py, log = _stub_python(tmp_path)
    proc = _run([], PAST_GATE, handoff, env_extra={"PYTHON": str(py), "RUFF": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _calls(log)
    # Only the direct interpreter calls; cmd8's ruff target list also names the
    # script but is a lint invocation, not an execution of it.
    extend_calls = [c for c in calls if c.startswith("research/extend_paper_trading_state.py")]
    assert len(extend_calls) == 2, calls
    assert "extend_paper_trading_state.py" in calls[0], calls
    assert "drift_persistence_report.py" in calls[1], calls
    assert "extend_paper_trading_state.py" in calls[2], calls
    assert "data_cost_inventory_001.py" in " ".join(calls), calls
    assert "data_cost_inventory_002.py" in " ".join(calls), calls

    text = handoff.read_text()
    assert "- **Mode:** full cycle (extend included)" in text, text
    assert "- **Gate state:** released (gate epoch reached)" in text, text
    assert "**Status:** OK" in text, text
    run_line = text.split("- **Cmds run:**")[1].split("\n")[0]
    assert "2 extend" in run_line, text
    assert "4 idempotent re-extend" in run_line, text
    assert "- **Cmds skipped:** none" in text, text


def test_read_only_cycle_never_invokes_the_extend(tmp_path: Path) -> None:
    # Behavioral complement to test_read_only_handoff_reports_skipped_extend: the
    # handoff text says cmds 2/4 were skipped, but nothing proved the script did
    # not invoke the mutating extend anyway. The stub log is the evidence.
    handoff = tmp_path / "handoff.md"
    py, log = _stub_python(tmp_path)
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(py), "RUFF": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _calls(log)
    assert calls, "the stub was never invoked; the test proves nothing"
    assert not [c for c in calls if c.startswith("research/extend_paper_trading_state.py")], calls
    # Read-only still runs the verification portion (drift, pytest, inventory).
    assert [c for c in calls if c.startswith("research/drift_persistence_report.py")], calls
    assert "- **Cmds skipped:**" in handoff.read_text()


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


def test_mixed_pass_fail_marks_handoff_failed_and_exit_nonzero(tmp_path: Path) -> None:
    # Mixed regime (the documented gap): every python step passes (PYTHON=true makes
    # cmd2/3/4/5/7a/7b/7c no-ops that exit 0) but ruff fails (RUFF=false). The
    # orchestrator must exit non-zero, mark the handoff FAILED, and report ONLY the
    # failing step -- it must not collapse to "cycle complete" nor fabricate a pass
    # for cmd8.
    handoff = tmp_path / "handoff.md"
    proc = _run(
        ["--read-only"],
        PAST_GATE,
        handoff,
        env_extra={"PYTHON": "true", "RUFF": "false"},
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert handoff.exists()
    text = handoff.read_text()
    assert "**Status:** FAILED" in text, text
    assert "STEP FAILED (rc=1): cmd8 ruff" in proc.stdout, proc.stdout
    # Only cmd8 must be flagged; the passing steps must not be reported as failures.
    assert "cmd5 6-module pytest" not in proc.stdout
    assert "cmd7c inventory pytest" not in proc.stdout


def test_read_only_handoff_reports_skipped_extend(tmp_path: Path) -> None:
    # Fidelity of the durable record: in read-only mode cmds 2/4 do NOT run, so a
    # handoff claiming "2 extend" would misrepresent the cycle to whoever reads it
    # after the gate. The handoff must list what ran and what was skipped.
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], PAST_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    assert "- **Cmds run:**" in text, text
    run_line = text.split("- **Cmds run:**")[1].split("\n")[0]
    assert "2 extend" not in run_line, text
    assert "2 extend (read-only)" in text, text
    assert "4 idempotent re-extend (read-only)" in text, text


def test_handoff_write_failure_exits_nonzero(tmp_path: Path) -> None:
    # The orchestrator exists to leave durable evidence in the repo. If the write
    # fails (bad path, full disk, teardown), reporting success would let the only
    # record of the gate check be lost silently.
    bad = tmp_path / "missing-dir" / "handoff.md"
    proc = _run(["--read-only"], PAST_GATE, bad)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "could not write durable handoff" in proc.stdout, proc.stdout
    assert not bad.exists()


def test_max_wait_seconds_rejects_non_integer(tmp_path: Path) -> None:
    # A non-numeric --max-wait-seconds used to die with "unbound variable" (rc=1)
    # instead of a usage error; the gate-active run passes this flag.
    handoff = tmp_path / "handoff.md"
    proc = _run(
        ["--read-only", "--wait-until-gate", "--max-wait-seconds", "abc"],
        FUTURE_GATE,
        handoff,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "requires a positive integer" in proc.stdout, proc.stdout
    assert not handoff.exists()


def test_unknown_flag_is_a_usage_error(tmp_path: Path) -> None:
    # An unknown flag used to be silently ignored (`*) shift ;;`), so a typo'd
    # `--wait-until-gate` would still exit 3 "gate NOT released" before the gate
    # and the durable record would never reveal the mis-invocation. Fail closed.
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only", "--bogus-flag"], PAST_GATE, handoff)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "unknown argument" in proc.stdout, proc.stdout
    assert not handoff.exists()


def test_max_wait_seconds_rejects_zero(tmp_path: Path) -> None:
    # 0 is not a usable wait budget: it degrades to "do not wait" and exits 3
    # exactly like the no-wait path, indistinguishable from a mis-invocation.
    # The help text and prior fix claim "positive integer"; enforce strictly > 0.
    handoff = tmp_path / "handoff.md"
    proc = _run(
        ["--read-only", "--wait-until-gate", "--max-wait-seconds", "0"],
        FUTURE_GATE,
        handoff,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "requires a positive integer" in proc.stdout, proc.stdout
    assert not handoff.exists()


def test_help_exits_zero(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    proc = _run(["--help"], FUTURE_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "usage:" in proc.stdout, proc.stdout
    assert not handoff.exists()

def test_default_handoff_follows_gate_epoch(tmp_path: Path) -> None:
    # A partial invocation that overrides only GATE_EPOCH (the natural way to
    # target the next gate) used to write the hard-coded 2026-11-12 handoff with
    # the new gate's content, destroying the prior gate's durable record. The
    # default HANDOFF must be derived from GATE_EPOCH.
    proc = _run_script_copy(tmp_path, ["--force", "--read-only"], GATE_20261113)
    derived = tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261113.md"
    stale = tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261112.md"
    assert derived.exists(), proc.stdout + proc.stderr
    assert not stale.exists(), proc.stdout + proc.stderr
    assert "gate 2026-11-13T22:00:00Z" in derived.read_text()


def test_default_handoff_for_default_gate_epoch_is_unchanged(tmp_path: Path) -> None:
    # Backwards compatibility: with no overrides the script must still write the
    # 2026-11-12 handoff (GATE_EPOCH default 1794520800).
    proc = _run_script_copy(tmp_path, ["--force", "--read-only"], PAST_GATE)
    derived = tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261112.md"
    assert derived.exists(), proc.stdout + proc.stderr
    assert "gate 2026-11-12T22:00:00Z" in derived.read_text()


def test_handoff_gate_date_mismatch_is_usage_error(tmp_path: Path) -> None:
    # An explicit HANDOFF naming a different gate date must fail closed (rc=2)
    # before any cycle runs, not silently write into the other gate's record.
    handoff = tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261113.md"
    proc = _run(["--read-only"], PAST_GATE, handoff)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "names gate date" in proc.stdout, proc.stdout
    assert not handoff.exists()


def test_pre_gate_forced_run_is_marked_pre_gate(tmp_path: Path) -> None:
    # Evidence-integrity hazard: a `--force --read-only` run BEFORE the gate
    # writes the same durable handoff file as the real post-gate cycle, so
    # "Status: OK" alone reads like post-gate evidence to the next session (the
    # handoff has already been mistaken for exactly that once). The handoff must
    # state that the gate was not released and that the mutating extend was
    # withheld.
    handoff = tmp_path / "handoff.md"
    proc = _run(["--force", "--read-only"], FUTURE_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    assert "- **Gate state:** NOT released" in text, text
    assert "pre-gate verification run only" in text, text
    assert "mutating extend withheld" in text, text
    assert "released (gate epoch reached)" not in text, text


def test_released_gate_is_marked_released(tmp_path: Path) -> None:
    # The complementary case: a real post-gate cycle must NOT be labelled
    # pre-gate, otherwise the marker carries no information.
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], PAST_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    assert "- **Gate state:** released (gate epoch reached)" in text, text
    assert "NOT released" not in text, text


def test_matching_gate_date_handoff_proceeds(tmp_path: Path) -> None:
    # An explicit HANDOFF whose date matches GATE_EPOCH must still work.
    handoff = tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261113.md"
    proc = _run(["--read-only", "--force"], GATE_20261113, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert handoff.exists()
    assert "gate 2026-11-13T22:00:00Z" in handoff.read_text()


def test_state_fingerprint_failure_marks_handoff_failed(tmp_path: Path) -> None:
    # Evidence-integrity defect (Cycle 1258): the State line is the only anchor
    # proving which paper-trading state the cycle ran against (hash + last_run +
    # nav + run count). It was produced by an unguarded `$(...)` subshell, so a
    # failing interpreter (python error, missing yaml, missing dependency) left
    # "- **State:** " empty while the cycle still reported "Status: OK" and
    # exited 0 -- an OK-looking handoff with no verifiable state evidence.
    # Reproduce with a stub that prints nothing and exits non-zero: every other
    # step is a no-op pass, so ONLY the fingerprint can fail.
    handoff = tmp_path / "handoff.md"
    py = tmp_path / "py_state_fail.sh"
    py.write_text("#!/usr/bin/env bash\nexit 1\n")
    py.chmod(0o755)
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(py)})
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "STEP FAILED" in proc.stdout, proc.stdout
    assert "state fingerprint" in proc.stdout, proc.stdout
    text = handoff.read_text()
    assert "**Status:** FAILED" in text, text
    assert "9 state fingerprint" in text, text


def test_populated_state_fingerprint_is_recorded(tmp_path: Path) -> None:
    # Positive complement: a working interpreter that prints a fingerprint must
    # still yield Status OK and a non-empty State line, so the new check cannot
    # be satisfied by a handoff that merely omits the evidence.
    handoff = tmp_path / "handoff.md"
    py = tmp_path / "py_state_ok.sh"
    py.write_text('#!/usr/bin/env bash\nprintf "%s last_run=2026-11-13 nav=1.0 runs=3\\n" "$(printf \'a%.0s\' {1..64})"\nexit 0\n')
    py.chmod(0o755)
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    assert "**Status:** OK" in text, text
    state_line = text.split("- **State:**")[1].split("\n")[0]
    assert "last_run=2026-11-13" in state_line, text
    assert "runs=3" in state_line, text


def test_malformed_state_fingerprint_marks_handoff_failed(tmp_path: Path) -> None:
    # Evidence-integrity gap (Cycle 1259): the Cycle-1258 guard only caught the
    # *empty* fingerprint (python error -> empty output -> rc!=0). A python that
    # exits 0 but loads a state whose current_nav/last_run_date key is absent
    # prints `nav=None` / `last_run=None` -- a syntactically present but
    # semantically empty fingerprint that passed record_rc and yielded
    # "Status: OK" with no verifiable NAV. Reproduce with a stub that prints a
    # well-formed-looking line whose nav is None and exits 0: every other step is
    # a no-op pass, so ONLY the fingerprint can fail.
    handoff = tmp_path / "handoff.md"
    py = tmp_path / "py_state_malformed.sh"
    py.write_text(
        '#!/usr/bin/env bash\n'
        'printf "%s last_run=2026-11-13 nav=None runs=0\\n" "$(printf \'a%.0s\' {1..64})"\n'
        'exit 0\n'
    )
    py.chmod(0o755)
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(py)})
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "STEP FAILED" in proc.stdout, proc.stdout
    assert "malformed" in proc.stdout, proc.stdout
    text = handoff.read_text()
    assert "**Status:** FAILED" in text, text
    assert "9 state fingerprint" in text, text


def test_silent_success_fingerprint_still_passes(tmp_path: Path) -> None:
    # The malformed-fingerprint guard must not over-reach into the empty-output
    # case. Eleven legitimate tests use silent-success stubs (PYTHON=true: no
    # output, exit 0) to keep the cycle fast and side-effect free; a guard that
    # hard-failed on *any* non-matching State line (including empty) broke them
    # (Cycle 1258 reverted exactly that). An empty fingerprint is left to
    # record_rc's exit-code check, so a silent-success stub must still yield
    # Status OK -- only a *malformed non-empty* fingerprint fails.
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": "true"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    assert "**Status:** OK" in text, text
    assert "STEP FAILED" not in proc.stdout, proc.stdout
    assert "9 state fingerprint" in text, text
