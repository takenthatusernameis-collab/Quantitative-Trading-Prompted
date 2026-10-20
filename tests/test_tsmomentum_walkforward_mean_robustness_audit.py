"""Tests for the ``tsmomentum_spytrend_001`` walk-forward mean stability audit (Cycle 911).

The audit is a read-only sensitivity: it decomposes the published walk-forward
mean into the two fold phases implied by the 6-month step and publishes a fold
leave-one-out influence table, while reproducing the published anchor and
leaving ``data/``, ``config/`` and every committed artifact byte-identical.
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

from research.tsmomentum_walkforward_mean_robustness_audit import (  # noqa: E402
    GATE_WF_MEAN_MIN,
    PUBLISHED_WF_MEAN,
    fingerprint,
    resolve_published_record,
    run_audit,
)

TOOL = "research/tsmomentum_walkforward_mean_robustness_audit.py"
REPORT = REPO / "research" / "reports" / "tsmomentum_walkforward_mean_robustness_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "tsmomentum_walkforward_mean_robustness_001.md"
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
    anchor = payload["anchor"] if "anchor" in payload else None
    if anchor is not None:
        assert anchor["matches"], anchor["rows"]
        assert anchor["per_fold_match"]
        assert anchor["per_fold_count"] == 48
    summary = payload["published_design"]["summary"]
    assert summary["n_folds"] == 48
    assert abs(summary["mean_test_sharpe"] - PUBLISHED_WF_MEAN) <= 1e-4
    assert summary["total_test_trades"] == 6013
    assert abs(summary["median_test_sharpe"] - 1.2933) <= 1e-4


def test_published_record_is_resolved_by_content():
    path, published = resolve_published_record(REPO / "research" / "experiments")
    assert path == PUBLISHED_RECORD
    assert published["aggregate"]["mean_test_sharpe"]["value"] == PUBLISHED_WF_MEAN
    assert published["gates"]["wf_mean_oos_sharpe_min"] == GATE_WF_MEAN_MIN


def test_phase_decomposition_is_exact(payload):
    phases = payload["phase_decomposition"]
    # The two sub-designs are pairwise disjoint and their union is the published fold set.
    assert phases["phases_are_pairwise_disjoint"] is True
    assert phases["union_covers_published_folds"] is True
    assert len(phases["phase_a_fold_numbers"]) == 24
    assert len(phases["phase_b_fold_numbers"]) == 24
    assert set(phases["phase_a_fold_numbers"]) | set(phases["phase_b_fold_numbers"]) == set(
        range(1, 49)
    )
    assert set(phases["phase_a_fold_numbers"]) & set(phases["phase_b_fold_numbers"]) == set()
    # Their means average to the published mean.
    mean_a = phases["phase_a"]["mean_test_sharpe"]
    mean_b = phases["phase_b"]["mean_test_sharpe"]
    assert abs((mean_a + mean_b) / 2.0 - payload["published_mean_recomputed"]) <= 1e-9
    assert phases["phase_means_average_to_published_mean"] is True
    # Gate 1 passes under phase A and fails under phase B.
    assert phases["gate1_phase_a"] == "PASS"
    assert phases["gate1_phase_b"] == "FAIL"


def test_leave_one_out_table_is_consistent(payload):
    """Recomputing the leave-one-out mean of the most influential fold from the
    published fold Sharpes reproduces the audit's value."""
    influence = payload["fold_influence"]["influence"]
    most_influential = payload["fold_influence"]["most_influential_fold"]
    assert most_influential["fold"] == 12
    assert most_influential["test_trades"] == 2

    # Fold Sharpes from the published record (4-decimal published cells).
    _, published = resolve_published_record(REPO / "research" / "experiments")
    pub_sharpes = [float(f["test_sharpe"]) for f in published["folds"]]
    fold_12_index = [f["fold"] for f in published["folds"]].index(12)
    loo_from_published = sum(
        s for i, s in enumerate(pub_sharpes) if i != fold_12_index
    ) / (len(pub_sharpes) - 1)
    assert abs(loo_from_published - most_influential["loo_mean"]) <= 1e-3
    # The shift sign: removing fold 12 raises the mean.
    assert most_influential["shift"] > 0.4


def test_thin_trade_folds_and_influence(payload):
    infl = payload["fold_influence"]
    assert infl["thin_trade_folds"] == [12, 13]
    assert abs(infl["loo_mean_thin_trade_folds"]["12"] - 1.431928) <= 1e-4
    assert abs(infl["loo_mean_thin_trade_folds"]["13"] - 0.973134) <= 1e-4
    assert infl["gate1_when_thin_trade_folds_excluded"] == "PASS"
    assert infl["gate1_outcome_changes_when_thin_trade_folds_excluded"] is False
    assert abs(infl["trimmed_mean_drop_min_max"] - 1.378012) <= 1e-4
    assert abs(infl["published_median"] - 1.2933) <= 1e-4


def test_stability_verdict(payload):
    stab = payload["stability"]
    assert stab["gate1_outcome_changes_between_phases"] is True
    assert stab["published_pass_stable"] is False


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
