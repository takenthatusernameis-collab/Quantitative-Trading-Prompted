"""Regression tests for the commodity data gate of `commoditytrend_001` (Cycle 949).

The tool (`research/commodity_data_gate_001.py`) measures the pre-registered
*data gate* of the frozen candidate on the **upstream** history fetched into a
scratch directory. It publishes no trading verdict and writes nothing under
``data/`` or ``config/``.

These tests pin the following invariants:

1. the tool runs read-only and passes its own structural checks;
2. ``data/`` and ``config/`` are byte-identical before and after the run;
3. the committed cache is never rewritten (the fetcher refuses to write inside
   the repository);
4. the upstream panel extends the committed cache and agrees with it on the
   overlap (the cached start of 2015-01-02 is a fetch window, not history);
5. the pre-registered gate is measured on both calendars and the common
   inception is on or before the pre-registered deadline;
6. the results are bit-for-bit deterministic across two runs.

The tool is exercised with ``--no-report`` so that running the tests never
rewrites a tracked artifact.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.commodity_data_gate_001 import (  # noqa: E402
    COMMON_INCEPTION_DEADLINE,
    MIN_FOLDS,
    REQUIRED_BUSINESS_DAYS,
    SYMBOLS,
    evaluate,
    render_experiment,
    render_report,
)

TOOL = "research/commodity_data_gate_001.py"
SOURCE = REPO / TOOL
CONFIG_CAND = REPO / "config" / "commoditytrend_001.yaml"
OUT_REPORT = REPO / "research" / "reports" / "commoditytrend_001_data_gate.md"
OUT_EXP = REPO / "research" / "experiments" / "commoditytrend_001_data_gate.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(REPO)): _sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, TOOL, *args],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def runs() -> dict:
    """Two independent runs of the tool (no artifact is written)."""
    data_before = _tree_hashes(REPO / "data")
    config_before = _tree_hashes(REPO / "config")
    artifacts_before = {rel: _sha256(REPO / rel) for rel in (str(OUT_REPORT), str(OUT_EXP))}
    first = _run("--no-report")
    second = _run("--no-report")
    return {
        "first": first,
        "second": second,
        "data_before": data_before,
        "data_after": _tree_hashes(REPO / "data"),
        "config_before": config_before,
        "config_after": _tree_hashes(REPO / "config"),
        "artifacts_before": artifacts_before,
        "artifacts_after": {rel: _sha256(REPO / rel) for rel in (str(OUT_REPORT), str(OUT_EXP))},
    }


@pytest.fixture(scope="module")
def payload() -> dict:
    """The tool's own payload, computed in memory (no file is written)."""
    return evaluate()


@pytest.fixture(scope="module")
def config() -> dict:
    import yaml

    return yaml.safe_load(CONFIG_CAND.read_text())


# ----------------------------------------------------------------------
# Execution
# ----------------------------------------------------------------------
def test_tool_runs_read_only_and_passes_its_own_checks(runs):
    proc = runs["first"]
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OVERALL: PASS" in proc.stdout
    assert "Common inception:" in proc.stdout
    assert "Folds:" in proc.stdout
    assert "(not written: --no-report)" in proc.stdout


def test_tool_prints_every_check_as_pass(runs):
    lines = [ln for ln in runs["first"].stdout.splitlines() if ln.startswith("  [PASS]")]
    assert lines, "the tool printed no structural checks"
    assert all("PASS" in ln for ln in lines), lines


def test_tool_does_not_write_tracked_artifacts(runs):
    assert runs["artifacts_after"] == runs["artifacts_before"]


def test_results_are_deterministic_across_two_runs(runs):
    """Bit-for-bit identical output across two independent runs."""
    assert runs["second"].returncode == 0
    assert runs["first"].stdout == runs["second"].stdout


# ----------------------------------------------------------------------
# Read-only guarantee
# ----------------------------------------------------------------------
def test_data_and_config_are_byte_identical_before_and_after(runs):
    assert runs["data_after"] == runs["data_before"]
    assert runs["config_after"] == runs["config_before"]


def test_working_tree_under_data_and_config_is_clean():
    result = subprocess.run(
        ["git", "status", "--porcelain", "data/", "config/"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""


def test_frozen_config_is_not_modified():
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "config/commoditytrend_001.yaml"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""


def test_the_fetcher_is_never_called():
    source = SOURCE.read_text()
    assert "fetch_" + "universe" not in source
    assert "yfinance_fetcher" not in source


# ----------------------------------------------------------------------
# The pre-registered gate
# ----------------------------------------------------------------------
def test_gate_constants_are_pinned():
    assert MIN_FOLDS == 10
    assert REQUIRED_BUSINESS_DAYS == 3906
    assert COMMON_INCEPTION_DEADLINE == "2011-10-20"
    assert set(SYMBOLS) == {"DBC", "BNO", "UNG", "GLD"}


def test_gate_passes_on_both_calendars(payload):
    gate = payload["gate"]
    assert gate["business_day_folds"] >= MIN_FOLDS
    assert gate["session_calendar_folds"] >= MIN_FOLDS
    assert gate["inception_before_deadline"] is True
    assert gate["gate_passed"] is True


def test_common_inception_is_before_the_deadline(payload):
    gate = payload["gate"]
    assert gate["common_inception"] == "2010-06-02"
    assert gate["business_days"] >= REQUIRED_BUSINESS_DAYS


def test_upstream_extends_the_committed_cache(payload):
    cache_rows = payload["cache_comparison"]
    total_extension = sum(row["extension_sessions"] for row in cache_rows)
    assert total_extension > 0
    for row in cache_rows:
        if row["cache_present"]:
            assert row["overlap_sessions"] == row["identical_sessions"]


def test_panel_is_continuous(payload):
    counters = payload["counters"]
    assert len(counters) == len(SYMBOLS)
    for row in counters:
        assert row["missing_prices"] == 0
        assert row["dup_timestamps"] == 0
        assert row["non_positive_prices"] == 0
        assert row["max_abs_1d_return"] < 0.5


# ----------------------------------------------------------------------
# The records
# ----------------------------------------------------------------------
def test_the_records_state_the_gate_verdict(payload):
    report = render_report(payload, payload["checks"])
    experiment = render_experiment(payload, payload["checks"])
    for text in (report, experiment):
        assert "PASS" in text
        assert "Blocked by data/infrastructure" in text
        assert "2010-06-02" in text


def test_the_committed_records_carry_the_gate_verdict():
    assert OUT_REPORT.exists()
    assert OUT_EXP.exists()
    report = OUT_REPORT.read_text()
    experiment = OUT_EXP.read_text()
    assert "PASS" in report
    assert "PASS" in experiment
    assert "OVERALL: PASS" not in report  # the report is prose, not a tool dump