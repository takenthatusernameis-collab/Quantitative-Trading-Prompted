"""Tests for the ``tsmomentum_spytrend_001`` walk-forward embargo audit (Cycle 910).

The audit is a read-only sensitivity: it must reproduce the published
walk-forward of the incumbent from the committed cache, make the fold designs
independence-checkable, and leave ``data/``, ``config/`` and every committed
artifact byte-identical.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    GATE_WF_MEAN_MIN,
    PUBLISHED_WF_MEAN,
    fingerprint,
    resolve_published_record,
    run_audit,
)

TOOL = "research/tsmomentum_walkforward_embargo_audit.py"
REPORT = REPO / "research" / "reports" / "tsmomentum_walkforward_embargo_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "tsmomentum_walkforward_embargo_001.md"
PUBLISHED_RECORD = REPO / "research" / "experiments" / "tsmomentum_regime_filter_wf_001.md"


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


def _committed_artifact_hashes() -> dict[str, str]:
    """Hashes of the committed artifacts the audit must not touch."""
    res = subprocess.run(
        ["git", "ls-files", "src", "config", "research/experiments", "research/reports"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    out: dict[str, str] = {}
    for rel in res.stdout.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        path = REPO / rel
        if path.is_file():
            out[rel] = _sha256(path)
    return out


@pytest.fixture(scope="module")
def payload() -> dict:
    return run_audit()


def test_tool_runs_and_passes():
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout


def test_artifacts_exist():
    assert REPORT.exists()
    assert EXPERIMENT.exists()


def test_anchor_reproduces_published_design(payload):
    """The published design is reproduced from the committed cache."""
    anchor = payload["anchor"]
    assert anchor["matches"], anchor["rows"]
    assert anchor["per_fold_match"]
    assert anchor["per_fold_count"] == 48
    summary = payload["published_design"]["summary"]
    assert summary["n_folds"] == 48
    assert abs(summary["mean_test_sharpe"] - PUBLISHED_WF_MEAN) <= 1e-4
    assert summary["total_test_trades"] == 6013


def test_published_record_is_resolved_by_content():
    path, published = resolve_published_record(REPO / "research" / "experiments")
    assert path == PUBLISHED_RECORD
    assert published["aggregate"]["mean_test_sharpe"]["value"] == PUBLISHED_WF_MEAN
    assert published["gates"]["wf_mean_oos_sharpe_min"] == GATE_WF_MEAN_MIN


def test_design_a_windows_are_disjoint_and_published_design_overlaps(payload):
    published = payload["published_design"]["independence"]
    design_a = payload["design_a_nonoverlapping"]
    assert published["mean_consecutive_overlap_days"] > 0
    assert design_a["independence"]["mean_consecutive_overlap_days"] == 0.0
    assert (
        design_a["independence"]["max_disjoint_test_windows"]
        == design_a["summary"]["n_folds"]
    )


def test_data_and_config_are_byte_identical_before_and_after():
    before_data = fingerprint(REPO / "data")
    before_config = fingerprint(REPO / "config")
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert fingerprint(REPO / "data") == before_data
    assert fingerprint(REPO / "config") == before_config


def test_committed_artifacts_are_byte_identical_before_and_after():
    before = _committed_artifact_hashes()
    published_key = str(PUBLISHED_RECORD.relative_to(REPO))
    assert published_key in before
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    after = _committed_artifact_hashes()
    assert after == before
    assert _sha256(PUBLISHED_RECORD) == before[published_key]


def test_two_consecutive_runs_are_bit_for_bit_deterministic():
    first = _run_tool()
    assert first.returncode == 0, first.stderr
    report_1 = REPORT.read_bytes()
    experiment_1 = EXPERIMENT.read_bytes()
    second = _run_tool()
    assert second.returncode == 0, second.stderr
    assert REPORT.read_bytes() == report_1
    assert EXPERIMENT.read_bytes() == experiment_1
    assert first.stdout == second.stdout


def test_fails_closed_on_malformed_published_record(tmp_path):
    records = tmp_path / "experiments"
    records.mkdir()
    (records / "broken.md").write_text(
        "# broken\n\n## Per-Fold Results\n\n"
        "| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | "
        "Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| 1 | 1993-01-01 | 2002-08-29 | 2002-09-30 | 2003-09-16 | 1.2280 | "
        "2.5550 | 0.2376 | -0.0307 | 94 |\n\n"
        "### Aggregate Walk-Forward Statistics\n\n"
        "| Metric | Value |\n|---|---|\n| Folds | 48 |\n"
        "| Mean Test Sharpe | not-a-number |\n",
        encoding="utf-8",
    )
    result = _run_tool(
        "--experiments-dir",
        str(records),
        "--report-out",
        str(tmp_path / "report.md"),
        "--experiment-out",
        str(tmp_path / "experiment.md"),
    )
    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert not (tmp_path / "report.md").exists()
    assert not (tmp_path / "experiment.md").exists()


def test_fails_closed_on_missing_cached_prices(tmp_path):
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


def test_fails_closed_on_missing_experiments_dir(tmp_path):
    result = _run_tool(
        "--experiments-dir",
        str(tmp_path / "does-not-exist"),
        "--report-out",
        str(tmp_path / "report.md"),
        "--experiment-out",
        str(tmp_path / "experiment.md"),
    )
    assert result.returncode != 0
    assert "ERROR" in result.stderr
