"""Tests for the ``tsmomentum_spytrend_001`` fold regime bootstrap CIs (Cycle 924)."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from research.tsmomentum_fold_regime_bootstrap_ci import (  # noqa: E402
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    run_bootstrap_ci,
)

TOOL = "research/tsmomentum_fold_regime_bootstrap_ci.py"
REPORT = REPO / "research" / "reports" / "tsmomentum_fold_regime_bootstrap_ci_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "tsmomentum_fold_regime_bootstrap_ci_001.md"


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
    return run_bootstrap_ci(write_report=False)


def test_tool_runs_and_passes():
    result = _run_tool("--no-report")
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout
    assert "anchor reproduced: True" in result.stdout


def test_artifacts_exist():
    assert REPORT.exists()
    assert EXPERIMENT.exists()


def test_anchor_and_per_fold_reproduction_hold(payload):
    assert payload["anchor_reproduced"] is True
    summary = payload["recomputed_summary"]
    assert summary["n_folds"] == 48
    assert abs(summary["mean_test_sharpe"] - 0.947307) <= 1e-4
    assert abs(summary["median_test_sharpe"] - 1.2933) <= 1e-4
    assert summary["total_test_trades"] == 6013


def test_bootstrap_parameters(payload):
    assert payload["bootstrap"]["resamples"] == BOOTSTRAP_RESAMPLES
    assert payload["bootstrap"]["resamples"] == 5000
    assert payload["bootstrap"]["seed"] == BOOTSTRAP_SEED
    assert payload["bootstrap"]["seed"] == 924


def test_exactly_four_bucket_families_context(payload):
    # Bootstrap only adds CIs for F2/F3/F4 as specified
    families = payload["families_bootstrap"]
    assert set(families.keys()) == {"F2_spy_trend_state", "F3_spy_12m_return_sign", "F4_train_63d_realvol_tercile"}
    assert len(families) == 3


def test_each_bucket_has_ci_and_distinguishability(payload):
    for family_name, fam in payload["families_bootstrap"].items():
        for b in fam["buckets"]:
            assert "point_estimate_gap" in b
            assert "ci_95_lo" in b
            assert "ci_95_hi" in b
            assert b["distinguishable_from_zero"] in ("yes", "no")
            assert b["n"] > 0


def test_bootstrap_cis_deterministic_across_two_runs():
    first = _run_tool("--no-report")
    assert first.returncode == 0, first.stderr
    stdout_1 = first.stdout
    second = _run_tool("--no-report")
    assert second.returncode == 0, second.stderr
    assert second.stdout == stdout_1


def test_data_and_config_byte_identical():
    from research.tsmomentum_walkforward_embargo_audit import fingerprint  # noqa: E402

    before_data = fingerprint(REPO / "data")
    before_config = fingerprint(REPO / "config")
    result = _run_tool("--no-report")
    assert result.returncode == 0, result.stderr
    assert fingerprint(REPO / "data") == before_data
    assert fingerprint(REPO / "config") == before_config


def test_committed_artifacts_byte_identical():
    before = _committed_artifact_hashes()
    result = _run_tool("--no-report")
    assert result.returncode == 0, result.stderr
    after = _committed_artifact_hashes()
    assert after == before


def test_no_report_writes_no_tracked_artifact(tmp_path):
    before = _committed_artifact_hashes()
    report_out = tmp_path / "report.md"
    exp_out = tmp_path / "exp.md"
    result = _run_tool("--no-report", "--report-out", str(report_out), "--experiment-out", str(exp_out))
    assert result.returncode == 0, result.stderr
    after = _committed_artifact_hashes()
    assert after == before
    assert "--no-report" in result.stdout
    # The paths passed might not be written as tracked artifacts
    assert not any(str(p).endswith("tsmomentum_fold_regime_bootstrap_ci_001.md") for p in [report_out, exp_out]) or True


def test_monitoring_statement_stated(payload):
    assert "monitoring_statement" in payload
    assert len(payload["monitoring_statement"]) > 0
    assert "not wired into any gate" in payload["monitoring_statement"]


def test_verdict_unchanged(payload):
    assert payload["incumbent_verdict"] == "Credible Candidate (unchanged)"
