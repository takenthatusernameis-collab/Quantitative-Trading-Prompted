"""Tests for the ``tsmomentum_spytrend_001`` fold regime attribution (Cycle 923).

The attribution is a read-only, descriptive measurement: it must reproduce the
published 48-fold walk-forward from the committed cache, attribute the folds to
the four pre-specified observable-state buckets only, and leave ``data/``,
``config/`` and every committed artifact byte-identical. It may not select,
re-rank or re-fit anything, and the incumbent's published verdict is unchanged.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from research.tsmomentum_fold_regime_attribution import (  # noqa: E402
    BUCKET_FAMILIES,
    PUBLISHED_WF_MEAN,
    run_attribution,
)
from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    resolve_published_record,
)

TOOL = "research/tsmomentum_fold_regime_attribution.py"
REPORT = REPO / "research" / "reports" / "tsmomentum_fold_regime_attribution_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "tsmomentum_fold_regime_attribution_001.md"
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
    return run_attribution(write_report=False)


def test_tool_runs_and_passes():
    result = _run_tool("--no-report")
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout
    assert "anchor reproduced: True" in result.stdout


def test_artifacts_exist():
    assert REPORT.exists()
    assert EXPERIMENT.exists()


def test_all_structural_checks_pass(payload):
    assert payload["overall"] == "PASS", [c for c in payload["checks"] if not c["pass"]]
    assert all(c["pass"] for c in payload["checks"]), payload["checks"]


def test_anchor_reproduces_published_design(payload):
    summary = payload["recomputed_summary"]
    anchor = payload["anchor"]
    assert summary["n_folds"] == 48
    assert abs(summary["mean_test_sharpe"] - 0.947307) <= 1e-4
    assert abs(summary["median_test_sharpe"] - 1.2933) <= 1e-4
    assert abs(summary["pct_positive_sharpe"] - 0.9167) <= 5e-4
    assert summary["total_test_trades"] == 6013
    assert anchor["matches"]
    assert anchor["per_fold_match"]
    assert anchor["per_fold_count"] == 48


def test_published_record_resolved_by_content():
    path, published = resolve_published_record(REPO / "research" / "experiments")
    assert path == PUBLISHED_RECORD
    assert published["aggregate"]["mean_test_sharpe"]["value"] == PUBLISHED_WF_MEAN


def test_phase_decomposition_matches_cycle_910(payload):
    ph = payload["phase_decomposition"]
    assert ph["phase_A_n"] == 24
    assert ph["phase_B_n"] == 24
    assert abs(ph["phase_A_mean"] - 1.385035) < 1e-3
    assert abs(ph["phase_B_mean"] - 0.509580) < 1e-3


def test_exactly_four_bucket_families_no_fifth(payload):
    assert list(payload["families"].keys()) == list(BUCKET_FAMILIES)
    assert len(payload["families"]) == 4


def test_every_bucket_has_n_and_statistics(payload):
    for family in payload["families"].values():
        assert family["n"] > 0 if "n" in family else True
        for b in family["buckets"]:
            assert b["n"] > 0
            assert "mean_test_sharpe" in b
            assert "median_test_sharpe" in b
            assert "phase_A_n" in b and "phase_B_n" in b


def test_data_and_config_are_byte_identical_before_and_after():
    # Use the module's fingerprint for an apples-to-apples check.
    from research.tsmomentum_fold_regime_attribution import fingerprint  # noqa: E402

    before_data = fingerprint(REPO / "data")
    before_config = fingerprint(REPO / "config")
    result = _run_tool("--no-report")
    assert result.returncode == 0, result.stderr
    assert fingerprint(REPO / "data") == before_data
    assert fingerprint(REPO / "config") == before_config


def test_committed_artifacts_are_byte_identical_before_and_after():
    before = _committed_artifact_hashes()
    published_key = str(PUBLISHED_RECORD.relative_to(REPO))
    assert published_key in before
    result = _run_tool("--no-report")
    assert result.returncode == 0, result.stderr
    after = _committed_artifact_hashes()
    assert after == before
    assert _sha256(PUBLISHED_RECORD) == before[published_key]


def test_two_consecutive_runs_are_bit_for_bit_deterministic():
    first = _run_tool("--no-report")
    assert first.returncode == 0, first.stderr
    stdout_1 = first.stdout
    second = _run_tool("--no-report")
    assert second.returncode == 0, second.stderr
    assert second.stdout == stdout_1


def test_published_verdict_unchanged(payload):
    assert payload["incumbent_verdict"] == "Credible Candidate (unchanged)"
    assert payload["anchor_reproduced"] is True
    for g in payload["gates"]:
        assert g["status"] == "PASS", g


def test_no_report_writes_no_tracked_artifact(tmp_path):
    result = _run_tool(
        "--no-report",
        "--report-out",
        str(tmp_path / "report.md"),
        "--experiment-out",
        str(tmp_path / "experiment.md"),
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "report.md").exists()
    assert not (tmp_path / "experiment.md").exists()


def test_payload_is_json_serializable(payload):
    json.dumps(payload, default=str, sort_keys=True)
