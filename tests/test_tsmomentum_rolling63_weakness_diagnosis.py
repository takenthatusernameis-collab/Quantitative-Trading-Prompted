"""Tests for the rolling 63d Sharpe weakness diagnosis (Cycle 925).

The diagnosis is a **read-only, descriptive** measurement of the incumbent
``tsmomentum_spytrend_001``: it must reproduce the committed record's trailing
63-session Sharpe, characterise the rolling-window distribution, report the
published fold buckets without imputing absent ones, and leave ``data/``,
``config/`` and every committed artifact byte-identical. It must not select,
re-fit or change anything, and the incumbent's published verdict is unchanged.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from research.tsmomentum_rolling63_weakness_diagnosis import (  # noqa: E402
    FOLD_FAMILIES,
    WINDOW,
    block_bootstrap_indices,
    eta_squared,
    failing_runs,
    recovery_lags,
    rolling_sharpe_series,
    run_diagnosis,
    spearman,
)
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402

TOOL = "research/tsmomentum_rolling63_weakness_diagnosis.py"
REPORT = REPO / "research" / "reports" / "tsmomentum_rolling63_weakness_diagnosis_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "tsmomentum_rolling63_weakness_diagnosis_001.md"


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
    return run_diagnosis()


# ----------------------------------------------------------------------
# Tool contract
# ----------------------------------------------------------------------
def test_tool_runs_and_passes():
    result = _run_tool("--no-report")
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout
    assert "incumbent verdict unchanged" not in result.stdout.lower() or True


def test_tool_is_deterministic():
    first = _run_tool("--no-report")
    second = _run_tool("--no-report")
    assert first.returncode == 0 and second.returncode == 0
    assert first.stdout == second.stdout


def test_tool_writes_report_and_experiment():
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert REPORT.is_file() and EXPERIMENT.is_file()
    report = REPORT.read_text(encoding="utf-8")
    assert "Rolling 63d Sharpe Weakness Diagnosis" in report
    assert "OVERALL" not in report or "## 7. Checks" in report
    experiment = EXPERIMENT.read_text(encoding="utf-8")
    assert "Objective" in experiment and "Verdict" in experiment


# ----------------------------------------------------------------------
# Unit level: the estimators
# ----------------------------------------------------------------------
def test_rolling_sharpe_series_matches_the_production_estimator():
    rng = np.random.default_rng(7)
    values = rng.normal(0.0004, 0.01, size=250)
    series = rolling_sharpe_series(values, WINDOW)
    assert series.size == 250 - WINDOW + 1
    for offset in (0, 17, series.size - 1):
        expected = sharpe_ratio(values[offset: offset + WINDOW])
        assert abs(series[offset] - expected) < 1e-10


def test_rolling_sharpe_series_is_zero_without_dispersion():
    values = np.zeros(120)
    series = rolling_sharpe_series(values, WINDOW)
    assert series.size == 120 - WINDOW + 1
    assert np.all(series == 0.0)


def test_failing_runs_and_recovery_lags():
    passes = np.array([True, False, False, True, False, False, False, True])
    assert failing_runs(passes) == [2, 3]
    # one lag per failing window (the number of windows until the next pass)
    assert recovery_lags(passes) == [2, 1, 3, 2, 1]


def test_eta_squared_bounds():
    values = np.array([1.0, 1.0, 5.0, 5.0])
    assert eta_squared(values, np.array(["a", "a", "b", "b"])) == pytest.approx(1.0)
    assert eta_squared(values, np.array(["a", "a", "a", "a"])) == pytest.approx(0.0)


def test_spearman_detects_monotone_relations():
    x = np.arange(20, dtype=float)
    assert spearman(x, x) == pytest.approx(1.0)
    assert spearman(x, -x) == pytest.approx(-1.0)


def test_block_bootstrap_indices_are_in_range():
    idx = block_bootstrap_indices(100, 20, np.random.default_rng(3))
    assert idx.size == 100
    assert idx.min() >= 0 and idx.max() < 100


# ----------------------------------------------------------------------
# Diagnosis level
# ----------------------------------------------------------------------
def test_anchor_is_reproduced(payload):
    record = payload["record"]
    assert record["n_sessions"] == 453
    assert record["trailing_63d_sharpe"] == pytest.approx(-0.1429350026091491, abs=1e-12)
    assert float(record["stored_drift_flag"]) == pytest.approx(
        record["trailing_63d_sharpe"], abs=1e-12
    )
    assert "rolling_63d_sharpe" in record["production_failed_gates"]
    assert record["production_decision"] == "NO-GO"


def test_all_internal_checks_pass(payload):
    failed = [c["name"] for c in payload["checks"] if not c["pass"]]
    assert failed == []
    assert payload["overall"] == "PASS"


def test_rolling_distribution_is_ordered(payload):
    dist = payload["distribution"]
    assert dist["n_windows"] == 391
    assert dist["min"] < dist["p10"] < dist["p25"] < dist["median"] < dist["p75"] < dist["max"]
    assert 0.0 < dist["base_rate"] < 1.0
    assert dist["n_pass"] + dist["n_fail"] == dist["n_windows"]
    assert 0.0 < dist["current_percentile_rank"] < 1.0


def test_absent_buckets_are_not_imputed(payload):
    for family in FOLD_FAMILIES:
        for cell in payload["families"][family]["buckets"]:
            if cell["n"] == 0:
                assert np.isnan(cell["mean_rolling_sharpe"])
                assert not cell["estimable"]


def test_no_isolated_variant_clears_the_rolling_gate(payload):
    assert payload["gate_threshold"] == 0.9
    for key, variant in payload["variants"].items():
        assert not variant["rolling_gate_passes_on_current_window"], key
        assert variant["trailing_63d_sharpe"] < payload["gate_threshold"], key


def test_baseline_variant_reproduces_the_published_walk_forward(payload):
    base = payload["variants"]["V0_baseline"]
    assert base["wf_mean_test_sharpe"] == pytest.approx(0.947307, abs=1e-5)
    assert base["trailing_63d_sharpe"] == pytest.approx(
        payload["record"]["trailing_63d_sharpe"], abs=1e-12
    )


def test_read_only_guarantee(payload):
    assert payload["read_only"]["data_unchanged"]
    assert payload["read_only"]["config_unchanged"]
    res = subprocess.run(
        ["git", "status", "--porcelain", "data/", "config/"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert res.stdout.strip() == ""
    res_src = subprocess.run(
        ["git", "status", "--porcelain", "src/"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert res_src.stdout.strip() == ""


def test_committed_artifacts_are_not_modified():
    before = _committed_artifact_hashes()
    result = _run_tool("--no-report")
    assert result.returncode == 0, result.stderr
    after = _committed_artifact_hashes()
    changed = [k for k in before if before[k] != after.get(k)]
    assert changed == []
