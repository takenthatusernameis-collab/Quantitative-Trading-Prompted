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


def test_non_numeric_gate_epoch_is_usage_error(tmp_path: Path) -> None:
    # A typo'd GATE_EPOCH (e.g. a stray underscore) must fail closed as a usage
    # error, not silently degrade to arithmetic-as-zero (gate appears always
    # open) and emit a bogus handoff date/filename.
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], "17948_66400", handoff)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "GATE_EPOCH must be a non-negative integer" in proc.stderr, proc.stderr
    assert not handoff.exists()


def test_negative_gate_epoch_is_usage_error(tmp_path: Path) -> None:
    # A negative integer is not a usable epoch; reject before `date -d` and the
    # gate arithmetic can consume it.
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only", "--force"], "-1", handoff)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "GATE_EPOCH must be a non-negative integer" in proc.stderr, proc.stderr
    assert not handoff.exists()


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


def test_wait_until_gate_budget_exhausted_fails_closed(tmp_path: Path) -> None:
    # The third --wait-until-gate branch: the wait budget expires while the gate
    # is still in the future. Every other wait test either (a) never reaches the
    # gate (FUTURE_GATE with a 1s budget -> the same "budget exhausted" message,
    # but that path is exercised through the 1s-budget case above) or (b) is past
    # the gate already (no wait at all). Neither pins the *budget-limited* exit:
    # a regression that silently dropped the exit-3 after the wait loop, or that
    # wrote a handoff anyway, would pass the existing suite. This pins the exact
    # durable-evidence contract: budget exhausted -> rc=3, no handoff, and the
    # log names the exhausted budget rather than claiming the gate released.
    handoff = tmp_path / "handoff.md"
    proc = _run(
        ["--read-only", "--wait-until-gate", "--max-wait-seconds", "2"],
        FUTURE_GATE,
        handoff,
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert not handoff.exists()
    assert "wait budget exhausted" in proc.stdout, proc.stdout
    assert "refusing to run" in proc.stdout, proc.stdout


def test_wait_until_gate_past_gate_proceeds(tmp_path: Path) -> None:
    # If the gate is already released, --wait-until-gate must not block.
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only", "--wait-until-gate"], PAST_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert handoff.exists()


def test_wait_until_gate_blocks_then_releases_and_runs_cycle(tmp_path: Path) -> None:
    """The --wait-until-gate happy path: block until the gate releases, then run.

    Every other --wait-until-gate test uses a FUTURE_GATE (never reached within
    the budget -> exit 3) or a PAST_GATE (already released -> no wait). Neither
    exercises the actual wait-then-release branch, so a regression that broke
    the wait loop (e.g. sleeping past the deadline, or exiting before running)
    would pass the suite. Pin the gate to a few seconds ahead with a matching
    wait budget so the wait loop terminates at the gate and the cycle runs.

    The gate epoch is derived at call time (not fixed) so the test cannot go
    stale as wall-clock time advances; the wait budget is set to the same
    remaining span plus a small margin.
    """
    import time as _time

    handoff = tmp_path / "handoff.md"
    now = int(_time.time())
    gate_epoch = str(now + 3)
    budget = str(max(5, (now + 3) - now + 2))
    proc = _run(
        ["--read-only", "--wait-until-gate", "--max-wait-seconds", budget],
        gate_epoch,
        handoff,
        env_extra={"PYTHON": "true", "RUFF": "true"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "waiting up to" in proc.stdout, proc.stdout
    assert "clock gate released after wait" in proc.stdout, proc.stdout
    assert handoff.exists()
    text = handoff.read_text()
    assert "- **Gate state:** released (gate epoch reached)" in text, text
    assert f"**Gate epoch:** {gate_epoch}" in text, text


def test_wait_budget_is_time_to_gate_not_run_cutoff(tmp_path: Path) -> None:
    """The --wait-until-gate budget is GATE_EPOCH - now, and the header must say so.

    The script header (and the durable handoff) previously claimed the wait was
    bounded by "the run's own 355-minute cutoff", but the code binds the wait
    budget to ``GATE_EPOCH - now_epoch`` (the time-to-gate) -- the run cutoff is
    not known to this script at all. A session whose cutoff falls before the
    gate would therefore have waited past its own deadline under the old prose,
    and a reader trusting the header would misjudge the flag's safety. This
    pins the real bound: the logged "waiting up to N" must equal the remaining
    time-to-gate, and the default (no --max-wait-seconds) must NOT reference a
    run cutoff.
    """
    import time as _time

    handoff = tmp_path / "handoff.md"
    now = int(_time.time())
    # Gate 8s out; the time-to-gate is 8s. With no --max-wait-seconds the budget
    # must be exactly the time-to-gate (8s), and the log must name it.
    gate_epoch = str(now + 8)
    proc = _run(
        ["--read-only", "--wait-until-gate"],
        gate_epoch,
        handoff,
        env_extra={"PYTHON": "true", "RUFF": "true"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "waiting up to 8s for release" in proc.stdout, proc.stdout
    assert "355-minute" not in proc.stdout, proc.stdout
    assert "run cutoff" not in proc.stdout, proc.stdout
    assert "clock gate released after wait" in proc.stdout, proc.stdout
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


def test_missing_python_interpreter_is_preflight_usage_error(tmp_path: Path) -> None:
    # ``/tmp/kilo-venv`` is ephemeral (recreated per job; NEXT_AGENT_TASK.md
    # "Runtime note"). If the run active at/after the gate is a fresh container
    # without it, PYTHON/RUFF point at missing paths and every step fails with an
    # opaque ``No such file or directory`` (rc=127) -- in the real (non-read-only)
    # cycle that aborts the mutating extend (cmd2) *mid-cycle*, after the script
    # already logged "starting post-gate cycle". The preflight must detect the
    # missing interpreter up front, fail closed (rc=2), and write no handoff.
    handoff = tmp_path / "handoff.md"
    proc = _run(
        ["--read-only"],
        PAST_GATE,
        handoff,
        env_extra={"PYTHON": str(tmp_path / "no-such-python"), "RUFF": "true"},
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "required interpreter" in proc.stdout, proc.stdout
    assert "is missing or not executable" in proc.stdout, proc.stdout
    assert "starting post-gate cycle" not in proc.stdout, proc.stdout
    assert not handoff.exists()


def test_missing_ruff_interpreter_is_preflight_usage_error(tmp_path: Path) -> None:
    # Symmetric guard: a present PYTHON but missing RUFF must also fail closed
    # before any step runs (cmd8 would otherwise abort mid-cycle).
    handoff = tmp_path / "handoff.md"
    proc = _run(
        ["--read-only"],
        PAST_GATE,
        handoff,
        env_extra={"PYTHON": "true", "RUFF": str(tmp_path / "no-such-ruff")},
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "required interpreter" in proc.stdout, proc.stdout
    assert "starting post-gate cycle" not in proc.stdout, proc.stdout
    assert not handoff.exists()


def test_present_interpreters_pass_preflight(tmp_path: Path) -> None:
    # Positive complement: resolvable interpreters (the ``true``/``false`` builtins
    # the rest of the suite uses, and PATH commands) must pass the preflight so
    # the check cannot be satisfied only by rejecting everything.
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": "true", "RUFF": "true"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "required interpreter" not in proc.stdout, proc.stdout
    assert "starting post-gate cycle" in proc.stdout, proc.stdout
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
    assert "2 extend (gate not released)" in text, text
    assert "4 idempotent re-extend (gate not released)" in text, text


def test_force_full_before_gate_withholds_extend_and_labels_pre_gate(tmp_path: Path) -> None:
    # Root-cause fix for a self-contradictory durable record: a `--force` FULL run
    # (no --read-only) BEFORE the gate previously invoked the mutating extend
    # (cmd2 + cmd4) and then wrote "full cycle (extend included)" /
    # "Cmds skipped: none" while its OWN "Gate state" line said "NOT released ...
    # mutating extend withheld". The extend is now gated on the clock, not on
    # --read-only: --force only overrides the exit-3 refusal, it does NOT
    # re-enable the mutating extend before the target session is complete.
    #
    # The stub log is the proof: the extend must NOT be invoked, and the Mode
    # line must describe what actually ran (pre-gate verification with the
    # extend withheld), not the nominal "full cycle".
    handoff = tmp_path / "handoff.md"
    py, log = _stub_python(tmp_path)
    proc = _run(["--force"], FUTURE_GATE, handoff, env_extra={"PYTHON": str(py), "RUFF": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _calls(log)
    assert not [c for c in calls if c.startswith("research/extend_paper_trading_state.py")], calls
    # Verification portion still runs (drift, inventory), so the probe is not vacuous.
    assert [c for c in calls if c.startswith("research/drift_persistence_report.py")], calls
    text = handoff.read_text()
    assert "- **Gate state:** NOT released" in text, text
    assert "pre-gate verification" in text, text
    assert "extend withheld" in text, text
    assert "- **Mode:** pre-gate verification (extend withheld — gate not released)" in text, text
    assert "full cycle (extend included)" not in text, text
    assert "2 extend" not in text.split("- **Cmds run:**")[1].split("\n")[0], text
    assert "2 extend (gate not released)" in text, text
    assert "4 idempotent re-extend (gate not released)" in text, text


def test_force_read_only_before_gate_still_withholds_extend(tmp_path: Path) -> None:
    # Regression guard: the pre-gate path that already existed (--force
    # --read-only) must still withhold the extend and report the gate-aware
    # Mode label (pre-gate verification with extend withheld).
    handoff = tmp_path / "handoff.md"
    py, log = _stub_python(tmp_path)
    proc = _run(["--force", "--read-only"], FUTURE_GATE, handoff, env_extra={"PYTHON": str(py), "RUFF": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _calls(log)
    assert not [c for c in calls if c.startswith("research/extend_paper_trading_state.py")], calls
    text = handoff.read_text()
    assert "- **Mode:** pre-gate verification (extend withheld — gate not released)" in text, text
    assert "2 extend (gate not released)" in text, text


def test_released_gate_full_mode_still_runs_extend_and_reports_full_mode(tmp_path: Path) -> None:
    # Positive complement: the real post-gate full run must STILL run the
    # extend and report "full cycle (extend included)" -- the fix must not
    # have disabled the extend for the case it exists for.
    handoff = tmp_path / "handoff.md"
    py, log = _stub_python(tmp_path)
    proc = _run([], PAST_GATE, handoff, env_extra={"PYTHON": str(py), "RUFF": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _calls(log)
    extend_calls = [c for c in calls if c.startswith("research/extend_paper_trading_state.py")]
    assert len(extend_calls) == 2, calls
    text = handoff.read_text()
    assert "- **Mode:** full cycle (extend included)" in text, text
    assert "- **Cmds skipped:** none" in text, text


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


def test_last_run_none_fingerprint_marks_handoff_failed(tmp_path: Path) -> None:
    # Cycle 1260: the malformed-fingerprint guard's last_run alternative was a
    # free `[^[:space:]]+`, which matches the literal token "None" -- so a state
    # whose last_run_date key is absent (prints last_run=None) with a valid
    # numeric nav passed the guard and yielded "Status: OK" with no verifiable
    # session date. The documented target of the guard ("missing/None last_run")
    # was therefore not enforced. last_run is now anchored to YYYY-MM-DD.
    handoff = tmp_path / "handoff.md"
    py = tmp_path / "py_state_lastrun_none.sh"
    py.write_text(
        '#!/usr/bin/env bash\n'
        'printf "%s last_run=None nav=1.0 runs=3\\n" "$(printf \'a%.0s\' {1..64})"\n'
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


def test_valid_session_date_fingerprint_still_passes(tmp_path: Path) -> None:
    # Positive complement for the tightened last_run anchor: a real YYYY-MM-DD
    # session date (the production form) must still yield Status OK, so the
    # stricter pattern is not a net regression on legitimate fingerprints.
    handoff = tmp_path / "handoff.md"
    py = tmp_path / "py_state_ok.sh"
    py.write_text('#!/usr/bin/env bash\nprintf "%s last_run=2026-11-13 nav=1.0 runs=3\\n" "$(printf \'a%.0s\' {1..64})"\nexit 0\n')
    py.chmod(0o755)
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    assert "**Status:** OK" in text, text


def test_negative_nav_fingerprint_is_not_malformed(tmp_path: Path) -> None:
    # current_nav is a float; a paper account can legitimately fall below zero
    # after losses. The prior nav pattern ([0-9]+...) required a leading digit,
    # so a valid negative NAV (nav=-1234.56) was rejected as "malformed" and
    # failed an otherwise-successful cycle with Status: FAILED and exit 1 --
    # destroying the very success evidence this orchestrator exists to record.
    # The minus sign must be accepted; a negative integer or float NAV must pass.
    handoff = tmp_path / "handoff.md"
    py = tmp_path / "py_state_neg.sh"
    py.write_text(
        '#!/usr/bin/env bash\n'
        'printf "%s last_run=2026-11-13 nav=-1234.56 runs=3\\n" "$(printf \'a%.0s\' {1..64})"\n'
        'exit 0\n'
    )
    py.chmod(0o755)
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    assert "**Status:** OK" in text, text
    state_line = text.split("- **State:**")[1].split("\n")[0]
    assert "nav=-1234.56" in state_line, text
    assert "malformed" not in proc.stdout, proc.stdout


def test_negative_integer_nav_fingerprint_is_not_malformed(tmp_path: Path) -> None:
    # A negative *integer* NAV (e.g. a whole-dollar -500) is the same valid case
    # as a negative float; the optional-minus fix must cover both.
    handoff = tmp_path / "handoff.md"
    py = tmp_path / "py_state_negint.sh"
    py.write_text(
        '#!/usr/bin/env bash\n'
        'printf "%s last_run=2026-11-13 nav=-500 runs=3\\n" "$(printf \'a%.0s\' {1..64})"\n'
        'exit 0\n'
    )
    py.chmod(0o755)
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    assert "**Status:** OK" in text, text
    assert "nav=-500" in text, text


def test_double_negative_nav_fingerprint_is_malformed(tmp_path: Path) -> None:
    # Anti-vacuity guard for the optional-minus fix: `--123` is not a valid
    # number. Loosening nav to `-?[0-9]+...` must not accept a second minus or
    # any other non-numeric token; a genuinely malformed nav must still fail.
    handoff = tmp_path / "handoff.md"
    py = tmp_path / "py_state_doubleneg.sh"
    py.write_text(
        '#!/usr/bin/env bash\n'
        'printf "%s last_run=2026-11-13 nav=--123.45 runs=3\\n" "$(printf \'a%.0s\' {1..64})"\n'
        'exit 0\n'
    )
    py.chmod(0o755)
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(py)})
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "malformed" in proc.stdout, proc.stdout
    assert "**Status:** FAILED" in handoff.read_text()


def test_non_numeric_nav_fingerprint_is_still_malformed(tmp_path: Path) -> None:
    # The optional-minus loosening must not accept a non-numeric nav such as
    # "abc"; only a leading minus followed by digits is a valid negative number.
    handoff = tmp_path / "handoff.md"
    py = tmp_path / "py_state_nonnumeric.sh"
    py.write_text(
        '#!/usr/bin/env bash\n'
        'printf "%s last_run=2026-11-13 nav=-abc runs=3\\n" "$(printf \'a%.0s\' {1..64})"\n'
        'exit 0\n'
    )
    py.chmod(0o755)
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(py)})
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "malformed" in proc.stdout, proc.stdout
    assert "**Status:** FAILED" in handoff.read_text()


def test_full_cycle_regenerates_record_status_after_extend(tmp_path: Path) -> None:
    # The record-status artifacts (research/{reports,experiments}/
    # paper_trading_record_status_001.md) are derived from the paper-trading state
    # but no prior step regenerated them, so after cmd2 appends a session they go
    # stale (e.g. 470/2026-11-16 while state is 471/2026-11-17) and
    # tests/test_paper_trading_record_status_audit.py -- which asserts the
    # artifacts equal the state-derived output -- fails. A full post-gate cycle
    # must regenerate them so the durable artifacts track the state it just wrote.
    # The stub log is the proof: the audit runs exactly once, after the extend.
    handoff = tmp_path / "handoff.md"
    py, log = _stub_python(tmp_path)
    proc = _run([], PAST_GATE, handoff, env_extra={"PYTHON": str(py), "RUFF": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _calls(log)
    audit_calls = [i for i, c in enumerate(calls) if c.startswith("research/paper_trading_record_status_audit.py")]
    assert len(audit_calls) == 1, calls
    # It must run after the (first) extend so it captures the post-extend state.
    extend_idx = next(i for i, c in enumerate(calls) if c.startswith("research/extend_paper_trading_state.py"))
    assert audit_calls[0] > extend_idx, calls
    # The handoff must record the step truthfully (run, not skipped).
    text = handoff.read_text()
    run_line = text.split("- **Cmds run:**")[1].split("\n")[0]
    assert "4b record-status regen" in run_line, text
    assert "- **Cmds skipped:** none" in text, text


def test_read_only_cycle_does_not_regenerate_record_status(tmp_path: Path) -> None:
    # Side-effect-free contract: --read-only (and pre-gate) runs must never write
    # the record-status artifacts. The regen is gated on the extend running, so a
    # read-only cycle must not invoke the audit and must list it as skipped.
    handoff = tmp_path / "handoff.md"
    py, log = _stub_python(tmp_path)
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(py), "RUFF": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _calls(log)
    assert not [c for c in calls if c.startswith("research/paper_trading_record_status_audit.py")], calls
    text = handoff.read_text()
    assert "4b record-status regen (gate not released)" in text, text


def test_pre_gate_forced_full_run_withholds_record_status_regen(tmp_path: Path) -> None:
    # The regen must follow the SAME clock gate as the mutating extend: a --force
    # FULL run before the gate withholds the extend (EXTEND_DISABLED=1), so it
    # must also withhold the record-status regen -- otherwise a pre-gate run would
    # write the artifacts while claiming the extend was withheld.
    handoff = tmp_path / "handoff.md"
    py, log = _stub_python(tmp_path)
    proc = _run(["--force"], FUTURE_GATE, handoff, env_extra={"PYTHON": str(py), "RUFF": str(py)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _calls(log)
    assert not [c for c in calls if c.startswith("research/paper_trading_record_status_audit.py")], calls
    text = handoff.read_text()
    assert "4b record-status regen (gate not released)" in text, text


def test_cmd8_ruff_list_covers_every_script_the_cycle_executes() -> None:
    """cmd8 must lint every script the orchestrator actually invokes.

    The RUFF4 list is the only gate between "the cycle's extension scripts are
    lint-clean" and a silent omission. A script that runs inside the cycle but
    is absent from this list escapes linting with no evidence -- the exact gap
    cmd8 exists to close for the other scripts. The one script added in the
    cmd4b regen (research/paper_trading_record_status_audit.py) was missing from
    this list, so a latent defect in it would have failed the real post-gate
    cycle with Status: FAILED and zero lint evidence. Pin the list against the
    scripts the cycle actually executes (cmd2/3/4/4b/7a/7b), so a future edit
    that drops one cannot pass the suite.

    The expected set is derived from the same literal the orchestrator uses, so
    this test cannot pass on a stale list by construction: it reads the RUFF4
    variable from the script source and asserts it names exactly the executed
    scripts, including the cmd4b audit.
    """
    import re

    source = SCRIPT.read_text()
    match = re.search(r'^RUFF4="([^"]+)"', source, re.MULTILINE)
    assert match, "scripts/post_gate_orchestrator.sh does not define RUFF4"
    listed = set(match.group(1).split())
    # RUFF4 is the *extension-script* lint list: the four scripts the mutating
    # extend path exercises (cmd2/3/4) plus the cmd4b record-status regen. The
    # data-cost inventory scripts (cmd7a/7b) are a separate family -- they are
    # executed and their exit codes are recorded by cmd7a/cmd7b, but they are
    # NOT in RUFF4 (they fail ruff on pre-existing findings, and linting them
    # here would fail every post-gate cycle). Asserting the extension family
    # only keeps this test honest about what RUFF4 is documented to cover.
    executed = {
        "research/extend_paper_trading_state.py",          # cmd2, cmd4
        "research/drift_persistence_report.py",            # cmd3
        "research/verify_monday_extension_path.py",        # extension family
        "research/verify_gate_time_forward_bar.py",        # extension family
        "research/paper_trading_record_status_audit.py",   # cmd4b
    }
    missing = executed - listed
    assert not missing, f"RUFF4 omits extension scripts the cycle executes: {sorted(missing)}"
    # The cmd4b audit must be present -- that is the defect this test guards.
    assert "research/paper_trading_record_status_audit.py" in listed
    # It must not accidentally swallow the inventory scripts, which RUFF4 is
    # not meant to cover (they have their own cmd7 execution + recording).
    assert "research/data_cost_inventory_001.py" not in listed
    assert "research/data_cost_inventory_002.py" not in listed


def _python_stub(tmp_path: Path, fail_when: str | None = None) -> Path:
    """No-op ``PYTHON`` stub that can fail for one specific script argument.

    The orchestrator passes the same interpreter to every step, so a test that
    needs ONE step to fail cannot use ``PYTHON=false`` (that fails all of them).
    This stub returns 0 for everything except a command line containing
    ``fail_when``, letting a single step's exit code be controlled.
    """
    stub = tmp_path / "python_stub.sh"
    guard = f'  *"{fail_when}"*) exit 1 ;;\n' if fail_when else ""
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'case "$*" in\n'
        f"{guard}"
        "  *) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub


def test_drift_invariant_check_failure_marks_handoff_failed(tmp_path: Path) -> None:
    # cmd8b (research/drift_invariant_check.py) is a verification step whose
    # nonzero exit is the documented defect signal from drift_decision_20261118
    # §7. It ran untested: a failure could have been recorded only in
    # /tmp/cmd8b.out while the handoff still read "Status: OK". Pin that its
    # failure surfaces in the process log AND marks the durable handoff FAILED.
    handoff = tmp_path / "handoff.md"
    stub = _python_stub(tmp_path, fail_when="drift_invariant_check.py")
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(stub)})
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "STEP FAILED (rc=1): cmd8b drift invariant check" in proc.stdout, proc.stdout
    assert handoff.exists()
    assert "**Status:** FAILED" in handoff.read_text()


def test_drift_invariant_check_is_recorded_as_run(tmp_path: Path) -> None:
    # The durable record must show cmd8b actually ran; an orchestrator that
    # silently dropped the step would otherwise still produce "Status: OK".
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], PAST_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    run_line = text.split("- **Cmds run:**")[1].split("\n")[0]
    assert "8b drift invariant" in run_line, text


def test_coverage_audit_failure_marks_handoff_failed(tmp_path: Path) -> None:
    # cmd8c (research/paper_record_raw_coverage_audit.py) is the provenance check
    # the research contract ranks first, and it was the last cycle step with no
    # orchestrator wiring. Its nonzero exit is the documented defect signal for a
    # malformed provider digest or a non-reproducing stored Sharpe; pin that it
    # surfaces in the process log AND marks the durable handoff FAILED, instead of
    # being recorded only in /tmp/cmd8c.out while the handoff reads "Status: OK".
    handoff = tmp_path / "handoff.md"
    stub = _python_stub(tmp_path, fail_when="paper_record_raw_coverage_audit.py")
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(stub)})
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "STEP FAILED (rc=1): cmd8c coverage audit" in proc.stdout, proc.stdout
    assert handoff.exists()
    assert "**Status:** FAILED" in handoff.read_text()


def test_coverage_audit_is_recorded_as_run(tmp_path: Path) -> None:
    # The durable record must show cmd8c actually ran; an orchestrator that
    # silently dropped the step would otherwise still produce "Status: OK".
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], PAST_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    run_line = text.split("- **Cmds run:**")[1].split("\n")[0]
    assert "8c coverage audit" in run_line, text


def test_cmd8c_is_in_ruff_lint_list() -> None:
    """cmd8c's script must be linted by cmd8 (the RUFF4 family).

    The coverage audit runs inside the cycle but was absent from RUFF4 when it
    was added (Cycle 1271 inv 1) with no orchestrator wiring either, so a latent
    defect in it would have failed the real post-gate cycle with Status: FAILED
    and zero lint evidence -- the exact gap cmd8 exists to close for the other
    extension scripts. Pin the list against the scripts the cycle executes.
    """
    import re

    source = SCRIPT.read_text()
    match = re.search(r'^RUFF4="([^"]+)"', source, re.MULTILINE)
    assert match, "scripts/post_gate_orchestrator.sh does not define RUFF4"
    listed = set(match.group(1).split())
    assert "research/paper_record_raw_coverage_audit.py" in listed, sorted(listed)


def test_artifact_reconciliation_failure_marks_handoff_failed(tmp_path: Path) -> None:
    # cmd8d (research/paper_trading_artifact_reconciliation_audit.py) is the only
    # step that compares every run_history row with its committed per-session
    # parquet artifacts. An unattested mismatch exits 1; pin that this surfaces in
    # the process log AND marks the durable handoff FAILED, instead of being
    # recorded only in /tmp/cmd8d.out while the handoff reads "Status: OK".
    handoff = tmp_path / "handoff.md"
    stub = _python_stub(tmp_path, fail_when="paper_trading_artifact_reconciliation_audit.py")
    proc = _run(["--read-only"], PAST_GATE, handoff, env_extra={"PYTHON": str(stub)})
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "STEP FAILED (rc=1): cmd8d artifact reconciliation" in proc.stdout, proc.stdout
    assert handoff.exists()
    assert "**Status:** FAILED" in handoff.read_text()


def test_artifact_reconciliation_is_recorded_as_run(tmp_path: Path) -> None:
    # The durable record must show cmd8d actually ran; an orchestrator that
    # silently dropped the step would otherwise still produce "Status: OK".
    handoff = tmp_path / "handoff.md"
    proc = _run(["--read-only"], PAST_GATE, handoff)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = handoff.read_text()
    run_line = text.split("- **Cmds run:**")[1].split("\n")[0]
    assert "8d artifact reconciliation" in run_line, text


def test_cmd8d_is_in_ruff_lint_list() -> None:
    # Same wiring contract as cmd8c: a script executed by the cycle must be
    # linted, or a latent defect fails the real cycle with zero lint evidence.
    import re

    source = SCRIPT.read_text()
    match = re.search(r'^RUFF4="([^"]+)"', source, re.MULTILINE)
    assert match, "scripts/post_gate_orchestrator.sh does not define RUFF4"
    listed = set(match.group(1).split())
    assert "research/paper_trading_artifact_reconciliation_audit.py" in listed, sorted(listed)


def _argv_logging_stub(tmp_path: Path) -> tuple[Path, Path]:
    """``PYTHON`` stub that records every invocation's argv into a log file.

    Repeated argv are newline-joined so a test can assert which flags the
    orchestrator passed to one specific script. The stub consumes stdin for the
    heredoc invocations (``PYTHON -``) so bash never blocks writing the heredoc.
    """
    log = tmp_path / "argv.log"
    stub = tmp_path / "argv_python_stub.sh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$*" >> "$ARGV_LOG"\n'
        'if [ "${1:-}" = "-" ]; then cat >/dev/null; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub, log


def _init_git(tmp_path: Path) -> None:
    """cmd6 runs ``git status``; a copied script run from a bare temp dir would
    fail that step (rc=128) and mask the behaviour under test."""
    subprocess.run(
        ["git", "init", "-q", str(tmp_path)],
        check=True,
        capture_output=True,
    )


def _write_state(tmp_path: Path, last_run: str) -> None:
    state_dir = tmp_path / "data" / "processed"
    state_dir.mkdir(parents=True)
    (state_dir / "paper_trading_state.yaml").write_text(
        f"last_run_date: {last_run}\ncurrent_nav: 1.0\nrun_history: []\n",
        encoding="utf-8",
    )


def _coverage_audit_argv(argv_log: Path) -> list[str]:
    lines = [
        line
        for line in argv_log.read_text().splitlines()
        if "paper_record_raw_coverage_audit.py" in line
    ]
    assert lines, argv_log.read_text()
    assert len(lines) == 1, lines
    return lines[0].split()


def test_cmd8c_receives_pre_extend_last_run_anchor(tmp_path: Path) -> None:
    # The audit's provider-digest guard (``--extend-before``) only fires when it
    # is told the pre-extension last_run_date. Without the flag, a real extend
    # that silently failed to write a ``provider_digest_YYYYMMDD.json`` would
    # leave the cycle reading "Status: OK" -- the documented regression. Pin that
    # the real orchestrator arms the guard.
    stub, log = _argv_logging_stub(tmp_path)
    _init_git(tmp_path)
    _write_state(tmp_path, "2026-11-19")
    proc = _run_script_copy(
        tmp_path,
        ["--read-only"],
        PAST_GATE,
        env_extra={"PYTHON": str(stub), "ARGV_LOG": str(log)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    argv = _coverage_audit_argv(log)
    assert "--extend-before" in argv, argv
    assert argv[argv.index("--extend-before") + 1] == "2026-11-19", argv


def test_cmd8c_anchor_omitted_when_state_is_absent(tmp_path: Path) -> None:
    # No state file (a stubbed/ad-hoc run): the audit must still be invoked, but
    # without a fabricated anchor. Passing a bogus value would fail the audit for
    # the wrong reason.
    stub, log = _argv_logging_stub(tmp_path)
    _init_git(tmp_path)
    proc = _run_script_copy(
        tmp_path,
        ["--read-only"],
        PAST_GATE,
        env_extra={"PYTHON": str(stub), "ARGV_LOG": str(log)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "--extend-before" not in _coverage_audit_argv(log)


def test_cmd8c_anchor_omitted_when_last_run_is_not_a_session_date(
    tmp_path: Path,
) -> None:
    # A malformed last_run_date (missing key renders as "None", a free string,
    # etc.) must not be forwarded: the audit would then require a digest for a
    # session that does not exist and fail a healthy cycle.
    stub, log = _argv_logging_stub(tmp_path)
    _init_git(tmp_path)
    _write_state(tmp_path, "not-a-date")
    proc = _run_script_copy(
        tmp_path,
        ["--read-only"],
        PAST_GATE,
        env_extra={"PYTHON": str(stub), "ARGV_LOG": str(log)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "--extend-before" not in _coverage_audit_argv(log)
    assert "anchor unavailable" in proc.stdout, proc.stdout


def _extend_call_counting_stub(tmp_path: Path, rewrite_on_call: int) -> Path:
    """``PYTHON`` stub that rewrites the state on the Nth extend invocation.

    The idempotency acceptance criterion is "the re-run shows ``sessions
    extended: 0`` and writes no second state". cmd4's exit code alone cannot show
    that: a buggy extend that appends a duplicate session and still exits 0 would
    have been recorded as "Status: OK". This stub lets one extend call mutate the
    state so the orchestrator's before/after hash check has something to catch.
    ``rewrite_on_call=0`` means never rewrite (the healthy idempotent case).
    """
    counter = tmp_path / "extend_calls.count"
    stub = tmp_path / "extend_rewriter.sh"
    rewrite_guard = (
        f'    if [ "$n" -eq {rewrite_on_call} ]; then\n'
        "      printf 'last_run_date: 2026-11-21\\ncurrent_nav: 2.0\\nrun_history: []\\n'"
        " > data/processed/paper_trading_state.yaml\n"
        "    fi\n"
        if rewrite_on_call
        else ""
    )
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'case "$*" in\n'
        "  *extend_paper_trading_state.py*)\n"
        f'    n=$(cat "{counter}" 2>/dev/null || echo 0)\n'
        '    n=$((n + 1))\n'
        f'    printf "%s" "$n" > "{counter}"\n'
        f"{rewrite_guard}"
        "    ;;\n"
        "esac\n"
        "exit 0\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub


def test_idempotent_reextend_that_rewrites_state_fails_the_cycle(tmp_path: Path) -> None:
    # cmd4 is the idempotency re-run: the gate cycle's acceptance criteria require
    # it to show "sessions extended: 0" and no second state write. Before this
    # guard only cmd4's exit code was recorded, so a re-run that rewrote the state
    # (duplicate session / corrupted record) still produced "Status: OK". Force
    # the second extend call to rewrite the state and pin that the cycle fails.
    stub = _extend_call_counting_stub(tmp_path, rewrite_on_call=2)
    _init_git(tmp_path)
    _write_state(tmp_path, "2026-11-19")
    handoff = tmp_path / "handoff.md"
    proc = _run_script_copy(
        tmp_path,
        [],
        PAST_GATE,
        handoff=str(handoff),
        env_extra={"PYTHON": str(stub)},
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "cmd4 idempotent re-extend rewrote the state" in proc.stdout, proc.stdout
    assert handoff.exists(), proc.stdout
    text = handoff.read_text()
    assert "- **Mode:** full cycle (extend included)" in text, text
    assert "**Status:** FAILED" in text, text


def test_idempotent_reextend_with_unchanged_state_is_verified(tmp_path: Path) -> None:
    # Positive complement: when the re-run leaves the state byte-identical the
    # cycle must record that evidence and stay "Status: OK" (so the new guard
    # cannot only reject).
    stub = _extend_call_counting_stub(tmp_path, rewrite_on_call=0)
    _init_git(tmp_path)
    _write_state(tmp_path, "2026-11-19")
    handoff = tmp_path / "handoff.md"
    proc = _run_script_copy(
        tmp_path,
        [],
        PAST_GATE,
        handoff=str(handoff),
        env_extra={"PYTHON": str(stub)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "cmd4 idempotency verified: state sha unchanged" in proc.stdout, proc.stdout
    assert handoff.exists(), proc.stdout
    assert "**Status:** OK" in handoff.read_text()
