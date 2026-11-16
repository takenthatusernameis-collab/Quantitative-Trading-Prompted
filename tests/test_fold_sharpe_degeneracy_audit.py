"""Tests for the fold Sharpe degeneracy audit (Cycle 930).

The audit is read-only: it rebuilds the incumbent's published 48-fold walk-forward
path, measures each fold's cash / active / non-zero session counts and annualized
volatility, flags folds whose Sharpe is not a valid statistic under a pre-registered
rule, and re-evaluates promotion gate 1 on the point-in-time-complete subsample.
These tests pin the artefacts, the degeneracy rule and its robustness, the
complete-subsample gate-1 flip, the reproduction anchor, the read-only guarantee,
determinism and fail-closed behaviour.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest

from research.fold_sharpe_degeneracy_audit import (
    ACTIVE_FLOOR,
    GATE_WF_MEAN_MIN,
    VOL_FLOOR,
    fingerprint,
    run_audit,
    tracked_artifact_hashes,
)

TOOL = "research/fold_sharpe_degeneracy_audit.py"
REPORT = REPO / "research" / "reports" / "fold_sharpe_degeneracy_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "fold_sharpe_degeneracy_001.md"
RAW_DIR = REPO / "data" / "raw"


def _run_tool(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, TOOL, *extra],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def payload() -> dict:
    return run_audit(write=False)


@pytest.fixture(scope="module")
def report_text() -> str:
    return REPORT.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Artefacts and tool
# ---------------------------------------------------------------------------
def test_tool_runs_and_passes():
    # --no-report keeps the run read-only: it must never write to the tracked
    # report/experiment paths (that would mutate the working tree during tests).
    result = _run_tool("--no-report")
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout


def test_artifacts_exist():
    assert REPORT.exists()
    assert EXPERIMENT.exists()
    assert REPORT.stat().st_size > 0
    assert EXPERIMENT.stat().st_size > 0


def test_artifacts_contain_no_timestamp():
    """The artefacts are deterministic, so they must not carry a run time."""
    for path in (REPORT, EXPERIMENT):
        text = path.read_text(encoding="utf-8")
        stamps = re.findall(r"20\d\d-\d\d-\d\d[ T]\d\d:\d\d", text)
        assert not stamps, f"{path.name} carries a timestamp: {stamps[:3]}"


# ---------------------------------------------------------------------------
# The degeneracy rule
# ---------------------------------------------------------------------------
def test_rule_constants_are_pre_registered():
    assert VOL_FLOOR == 0.01
    assert ACTIVE_FLOOR == 2
    assert GATE_WF_MEAN_MIN == 0.9


def test_degenerate_fold_is_exactly_12(payload: dict):
    assert payload["degenerate_folds"] == [12]
    assert len(payload["rows"]) == 48


def test_fold_12_diagnostics(payload: dict):
    fold12 = payload["fold_12"]
    assert fold12["fold"] == 12
    assert fold12["n_sessions"] == 244
    assert fold12["cash_days"] == 243
    assert fold12["active_days"] == 1
    assert fold12["nonzero_days"] == 2
    assert fold12["ann_vol"] == pytest.approx(0.000973, abs=5e-6)
    assert fold12["sharpe"] == pytest.approx(-21.829879, abs=1e-4)
    assert fold12["sharpe"] == min(r["sharpe"] for r in payload["rows"])


def test_only_fold_12_has_an_extreme_sharpe(payload: dict):
    extreme = [r["fold"] for r in payload["rows"] if abs(r["sharpe"]) > 5.0]
    assert extreme == [12]


def test_threshold_gap_is_wide(payload: dict):
    """The rule sits in a real gap: fold 12 far below, the next fold far above."""
    fold12 = payload["fold_12"]
    assert fold12["ann_vol"] <= VOL_FLOOR / 5.0
    assert payload["next_lowest_vol"] >= 2.0 * VOL_FLOOR
    assert fold12["active_days"] <= ACTIVE_FLOOR
    assert payload["next_lowest_active"] >= 3.0 * ACTIVE_FLOOR


# ---------------------------------------------------------------------------
# Complete-subsample gate 1
# ---------------------------------------------------------------------------
def test_complete_gate1_fails(payload: dict):
    complete = payload["complete_stats"]
    assert complete["n_folds"] == 41
    assert complete["mean_test_sharpe"] == pytest.approx(0.787522, abs=1e-6)
    assert not complete["gate1_pass"]
    assert complete["mean_test_sharpe"] < GATE_WF_MEAN_MIN


def test_complete_without_degenerate_gate1_passes(payload: dict):
    clean = payload["complete_clean_stats"]
    assert clean["n_folds"] == 40
    assert clean["mean_test_sharpe"] == pytest.approx(1.352958, abs=1e-6)
    assert clean["gate1_pass"]


# ---------------------------------------------------------------------------
# Report consistency
# ---------------------------------------------------------------------------
def test_report_matches_rederivation(report_text: str):
    assert "0.787522" in report_text
    assert "1.352958" in report_text
    assert "fold 12" in report_text
    assert "| 12 | 2008-01-22 .. 2009-01-07 | 244 | 243 | 1 | 2 |" in report_text


def test_report_refines_the_thin_trade_grouping(report_text: str):
    """Fold 13 is not degenerate; the artefact is fold 12 alone."""
    assert "Fold 13 is *not* degenerate" in report_text
    assert "The artefact is fold 12 alone" in report_text


def test_experiment_record_references_the_tool():
    text = EXPERIMENT.read_text(encoding="utf-8")
    assert "fold_sharpe_degeneracy_audit" in text
    assert "research/fold_sharpe_degeneracy_audit.py" in text


# ---------------------------------------------------------------------------
# Read-only guarantee and determinism
# ---------------------------------------------------------------------------
def test_data_and_config_are_byte_identical_before_and_after():
    before_data = fingerprint(REPO / "data")
    before_config = fingerprint(REPO / "config")
    result = _run_tool("--no-report")
    assert result.returncode == 0, result.stderr
    assert fingerprint(REPO / "data") == before_data
    assert fingerprint(REPO / "config") == before_config


def test_committed_artifacts_are_byte_identical_before_and_after(tmp_path: Path):
    # Run the tool in write mode into a temp dir: it must leave the tracked
    # artifacts untouched (read-only w.r.t. the repo) AND reproduce them exactly.
    before = tracked_artifact_hashes()
    assert before, "no committed artifacts were found"
    report = tmp_path / "report.md"
    experiment = tmp_path / "experiment.md"
    result = _run_tool("--report-out", str(report), "--experiment-out", str(experiment))
    assert result.returncode == 0, result.stderr
    assert tracked_artifact_hashes() == before
    assert report.read_bytes() == REPORT.read_bytes()
    assert experiment.read_bytes() == EXPERIMENT.read_bytes()


def test_two_consecutive_generations_are_identical(tmp_path: Path):
    first_report = tmp_path / "report_1.md"
    first_experiment = tmp_path / "experiment_1.md"
    second_report = tmp_path / "report_2.md"
    second_experiment = tmp_path / "experiment_2.md"

    for report, experiment in (
        (first_report, first_experiment),
        (second_report, second_experiment),
    ):
        result = _run_tool("--report-out", str(report), "--experiment-out", str(experiment))
        assert result.returncode == 0, result.stderr

    assert first_report.read_bytes() == second_report.read_bytes()
    assert first_experiment.read_bytes() == second_experiment.read_bytes()
    # The committed artefacts are the same bytes as a fresh generation.
    assert first_report.read_bytes() == REPORT.read_bytes()
    assert first_experiment.read_bytes() == EXPERIMENT.read_bytes()


# ---------------------------------------------------------------------------
# Fail-closed behaviour
# ---------------------------------------------------------------------------
def test_fails_closed_on_an_empty_raw_cache(tmp_path: Path):
    empty_raw = tmp_path / "raw"
    empty_raw.mkdir()
    result = _run_tool(
        "--raw-dir",
        str(empty_raw),
        "--report-out",
        str(tmp_path / "report.md"),
        "--experiment-out",
        str(tmp_path / "experiment.md"),
    )
    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert not (tmp_path / "report.md").exists()
    assert not (tmp_path / "experiment.md").exists()