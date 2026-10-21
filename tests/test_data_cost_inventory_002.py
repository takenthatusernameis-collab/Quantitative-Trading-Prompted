"""Tests for the data-and-cost inventory 002 (Cycle 929).

The inventory is read-only: it re-measures the committed cache, re-verifies the
digests published by the Cycle-912 inventory, re-derives the committed cost
model and measures the point-in-time universe membership of the incumbent's
published walk-forward.  These tests pin the artefacts' existence, the
inventory's coverage, the agreement with ``src/backtest/engine.py``, the
reproduction anchor of the published walk-forward, the membership split, the
read-only guarantee on ``data/`` and ``config/``, the immutability of every
committed artefact, determinism, and the pre-registration completeness of the
new candidate hypothesis.
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

import pytest  # noqa: E402

from research.data_cost_inventory_002 import (  # noqa: E402
    GATE_WF_MEAN_MIN,
    PUBLISHED_POOLED_TRADES,
    PUBLISHED_WF_MEAN,
    fingerprint,
    tracked_artifact_hashes,
)
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402

TOOL = "research/data_cost_inventory_002.py"
REPORT = REPO / "research" / "reports" / "data_cost_inventory_002.md"
EXPERIMENT = REPO / "research" / "experiments" / "data_cost_inventory_002.md"
HYPOTHESIS = REPO / "research" / "hypotheses" / "riskparity_001.md"
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
def report_text() -> str:
    return REPORT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def experiment_text() -> str:
    return EXPERIMENT.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Artefacts
# ---------------------------------------------------------------------------
def test_tool_runs_and_passes():
    result = _run_tool()
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
# Inventory coverage and drift
# ---------------------------------------------------------------------------
def test_report_inventory_covers_every_raw_file(report_text: str):
    raw_files = sorted(p for p in RAW_DIR.rglob("*") if p.is_file())
    assert raw_files, "the raw cache is empty"
    for path in raw_files:
        rel = path.relative_to(RAW_DIR).as_posix()
        assert f"data/raw/{rel}" in report_text, f"{rel} is missing from the report"


def test_report_lists_the_measured_digests(report_text: str):
    for digest in re.findall(r"\| `([0-9a-f]{16})` \|", report_text):
        assert len(digest) == 16
    assert "35 of 35 match" in report_text


def test_drift_audit_is_truthful(report_text: str):
    """Every published digest is either matched or explicitly reported."""
    assert "0 changed" in report_text
    assert "0 removed" in report_text
    assert "0 added" in report_text


# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------
def test_cost_figures_match_the_engine(report_text: str):
    commission, slippage = get_cost_params()
    risk_free = get_risk_free_rate()
    assert f"{commission * 10000:.1f} bps per trade" in report_text
    assert f"{slippage * 10000:.1f} bps per trade" in report_text
    assert f"{(commission + slippage) * 10000:.1f} bps" in report_text
    assert f"{risk_free * 100:.2f}% annual" in report_text


def test_unconfigured_cost_components_are_reported(report_text: str):
    for component in (
        "bid_ask_spread",
        "borrow",
        "roll",
        "market_impact",
        "latency",
        "margin",
    ):
        assert component in report_text


# ---------------------------------------------------------------------------
# Point-in-time universe membership
# ---------------------------------------------------------------------------
def test_published_walk_forward_is_reproduced(report_text: str):
    assert "48" in report_text
    assert f"{PUBLISHED_WF_MEAN}" in report_text
    assert str(PUBLISHED_POOLED_TRADES) in report_text


def test_membership_split_is_reported(report_text: str):
    assert "7" in report_text and "41" in report_text
    assert "Point-in-time-complete" in report_text
    assert "Point-in-time-incomplete" in report_text


def test_gate_thresholds_are_the_committed_ones():
    assert GATE_WF_MEAN_MIN == 0.9


# ---------------------------------------------------------------------------
# The pre-registered candidate hypothesis
# ---------------------------------------------------------------------------
def test_hypothesis_exists():
    assert HYPOTHESIS.exists()
    assert HYPOTHESIS.stat().st_size > 0


def test_hypothesis_has_every_required_field():
    text = HYPOTHESIS.read_text(encoding="utf-8")
    required = {
        "mechanism": "## Mechanism description",
        "direction": "Expected direction and magnitude",
        "horizon": "## Holding horizon",
        "universe": "## Asset universe",
        "features": "## Features and data sources",
        "entry_exit": "## Entry and exit rules",
        "benchmark": "## Benchmarks",
        "confounders": "## Known confounders",
        "falsification": "Falsification",
        "cost_model": "## Cost model assumptions",
    }
    for field, marker in required.items():
        assert marker in text, f"the hypothesis is missing the {field} section"


def test_hypothesis_declares_universe_grid_and_gates():
    text = HYPOTHESIS.read_text(encoding="utf-8")
    for symbol in ("SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"):
        assert symbol in text
    assert "9 configurations" in text
    assert "0.9" in text
    assert "positive-fold rate" in text
    assert "pooled out-of-sample trades" in text
    # The hypothesis is pre-registered before any execution of the candidate.
    assert "before" in text.lower()


def test_hypothesis_is_point_in_time_complete():
    """The candidate must not inherit the membership defect the audit measured."""
    text = HYPOTHESIS.read_text(encoding="utf-8")
    assert "point-in-time-complete" in text
    assert "Cycle 929" in text or "data_cost_inventory_002" in text


# ---------------------------------------------------------------------------
# Experiment record
# ---------------------------------------------------------------------------
def test_experiment_record_references_the_report(experiment_text: str):
    assert "data_cost_inventory_002" in experiment_text
    assert "research/data_cost_inventory_002.py" in experiment_text
    assert (
        "python -m pytest -q tests/test_data_cost_inventory_002.py" in experiment_text
    )


# ---------------------------------------------------------------------------
# Read-only guarantee and determinism
# ---------------------------------------------------------------------------
def test_data_and_config_are_byte_identical_before_and_after():
    before_data = fingerprint(REPO / "data")
    before_config = fingerprint(REPO / "config")
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert fingerprint(REPO / "data") == before_data
    assert fingerprint(REPO / "config") == before_config


def test_committed_artifacts_are_byte_identical_before_and_after():
    before = tracked_artifact_hashes()
    assert before, "no committed artifacts were found"
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    after = tracked_artifact_hashes()
    assert after == before
    if "research/reports/data_cost_inventory_002.md" in before:
        assert _sha256(REPORT) == before["research/reports/data_cost_inventory_002.md"]


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
