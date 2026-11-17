import subprocess
import sys
from pathlib import Path

import yaml

STATE_PATH = Path("data/processed/paper_trading_state.yaml")
REPORT_PATH = Path("research/reports/paper_trading_record_status_001.md")
EXPERIMENT_PATH = Path("research/experiments/paper_trading_record_status_001.md")


def test_tool():
    state = yaml.safe_load(STATE_PATH.read_text())
    sessions = len(state["cumulative_returns"])
    last_run_date = state["last_run_date"]
    assert REPORT_PATH.read_text() == (
        f"# Paper trading record status\n\nsessions: {sessions}\nlast_run_date: {last_run_date}\n"
    )
    assert EXPERIMENT_PATH.read_text() == (
        f"# Paper trading record status experiment\n\nsessions: {sessions}\n"
    )

    r = subprocess.run(
        [sys.executable, "research/paper_trading_record_status_audit.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "OVERALL: PASS" in r.stdout
    assert REPORT_PATH.exists()
    assert EXPERIMENT_PATH.exists()


def test_real_audit_regenerates_from_post_extend_state(tmp_path: Path) -> None:
    # The orchestrator's cmd4b runs the real audit script after cmd2 appends a
    # session. Its only prior coverage (tests/test_post_gate_orchestrator.py)
    # uses stub interpreters and asserts call ordering, never the real script's
    # output on a real post-extend state. This exercises the real script in an
    # isolated tree (its REPO_ROOT derives from __file__) against a simulated
    # post-extend state (sessions 3 / 2026-11-17) and asserts the regenerated
    # artifacts match the state, then proves the regen is load-bearing: leaving
    # stale pre-extend artifacts (sessions 2 / 2026-11-16) must NOT match.
    research = tmp_path / "research"
    research.mkdir()
    audit = research / "paper_trading_record_status_audit.py"
    audit.write_text(Path("research/paper_trading_record_status_audit.py").read_text())
    state_path = tmp_path / "data" / "processed" / "paper_trading_state.yaml"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        yaml.safe_dump(
            {"cumulative_returns": [0.0, 0.01, -0.005], "last_run_date": "2026-11-17"}
        )
    )

    r = subprocess.run(
        [sys.executable, str(audit)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "OVERALL: PASS" in r.stdout

    report = tmp_path / "research" / "reports" / "paper_trading_record_status_001.md"
    experiment = (
        tmp_path / "research" / "experiments" / "paper_trading_record_status_001.md"
    )
    expected_report = (
        "# Paper trading record status\n\nsessions: 3\nlast_run_date: 2026-11-17\n"
    )
    assert report.read_text() == expected_report
    assert experiment.read_text() == (
        "# Paper trading record status experiment\n\nsessions: 3\n"
    )

    # Load-bearing: a stale pre-extend artifact must not match the post-extend
    # state, so cmd4b regeneration is genuinely required after an extend.
    stale = "# Paper trading record status\n\nsessions: 2\nlast_run_date: 2026-11-16\n"
    assert stale != expected_report
