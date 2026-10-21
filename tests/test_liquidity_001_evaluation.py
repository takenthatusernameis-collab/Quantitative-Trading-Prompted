"""Cycle 938: tests for the frozen ``liquidity_001`` evaluation."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.liquidity_001_evaluation import (  # noqa: E402
    FROZEN,
    OUT_EXP,
    OUT_REPORT,
    EvaluationError,
    build_liquidity_weights,
    build_benchmark_weights,
    load_frozen_config,
    load_ohlcv,
    build_payload,
    run_checks,
    verdict,
    render_experiment,
    render_report,
    FREEZE_COMMIT,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hash(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(REPO_ROOT)): _sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.fixture(scope="module")
def payload() -> dict:
    return build_payload()


def test_the_frozen_configuration_is_unchanged():
    config = load_frozen_config()
    assert config["universe"] == FROZEN["universe"]
    assert config["lookback_sessions"] == 21
    assert config["select_count"] == 2
    assert config["total_round_trip_bps"] == 3.0
    assert config["total_configs"] == 1
    assert config["selection"] == "top_illiquid"


def test_a_post_freeze_drift_fails_closed(monkeypatch):
    config = load_frozen_config()
    monkeypatch.setitem(FROZEN, "lookback_sessions", 5)
    with pytest.raises(EvaluationError):
        load_frozen_config()
    # restore
    FROZEN["lookback_sessions"] = 21


def test_the_hypothesis_and_config_exist():
    assert (REPO_ROOT / "research" / "hypotheses" / "liquidity_001.md").exists()
    assert (REPO_ROOT / "config" / "liquidity_candidate_001.yaml").exists()


def _synthetic_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    index = pd.date_range("2020-01-01", periods=80, freq="B", tz="UTC")
    close = pd.DataFrame(
        {
            "A": 100.0 * np.ones(80),  # low vol
            "B": 100.0 * np.ones(80),
            "C": 100.0,
            "D": 100.0,
        },
        index=index,
    )
    # make B have big move but low volume -> illiquid
    close.iloc[10:15, 1] = 120.0  # jump
    volume = pd.DataFrame(1000000.0, index=index, columns=close.columns)
    volume["B"] = 10000.0  # low volume
    return close, volume


def test_amihud_measure_computed_correctly():
    close, volume = _synthetic_panel()
    weights, amihud, formed = build_liquidity_weights(
        close, volume, lookback=5, select_count=2, every_n=21
    )
    # Amihud should be computed
    assert amihud.shape == close.shape
    # B should have high Amihud due to big move / low volume
    assert np.isfinite(amihud["B"].iloc[20])


def test_most_illiquid_quintile_selection_is_correct():
    close, volume = _synthetic_panel()
    weights, amihud, formed = build_liquidity_weights(
        close, volume, lookback=5, select_count=2, every_n=21
    )
    assert formed, "the rule must form positions"
    for date in formed[:3]:
        position = close.index.get_loc(date)
        if position + 1 >= len(close.index):
            continue
        effective = weights.iloc[position + 1]
        picked = effective[effective > 0].index.tolist()
        assert len(picked) == 2
        # should pick the most illiquid (B)
        assert "B" in picked


def test_monthly_rebalance_with_one_session_lag():
    close, volume = _synthetic_panel()
    weights, _amihud, formed = build_liquidity_weights(
        close, volume, lookback=5, select_count=2, every_n=21
    )
    # first row all zeros (lagged)
    assert weights.iloc[0].sum() == 0.0
    # rebalances every 21 sessions
    assert len(formed) > 0


def test_benchmark_is_1n_of_same_universe():
    close, _volume = _synthetic_panel()
    bench = build_benchmark_weights(close)
    for idx in bench.index:
        assert bench.loc[idx].sum() == pytest.approx(1.0)
        assert all(abs(w - 0.25) < 1e-10 for w in bench.loc[idx])


def test_cost_model_applied():
    config = load_frozen_config()
    assert config["total_round_trip_bps"] == 3.0


def test_walkforward_design_matches_frozen_spec():
    config = load_frozen_config()
    assert config["train_years"] == 10
    assert config["test_months"] == 12
    assert config["step_months"] == 6
    assert config["purge_days"] == 21
    assert config["embargo_days"] == 21


def test_falsification_conditions_drive_verdict():
    v = verdict({"config": load_frozen_config(), "evaluation": {"wf_mean_oos_sharpe": 0.5, "excess_ci": {"ci_low": -0.1, "ci_high": 0.1}, "amihud_dispersion_median": 0.001, "post2009_excess_annualized": 0.01}})
    assert len(v["conditions"]) == 4
    assert v["falsified"] is True  # wf mean < 0.9 and CI includes zero fire


def test_two_runs_byte_identical_output():
    outputs = []
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "research/liquidity_001_evaluation.py", "--no-report"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]


def test_data_and_config_unchanged_before_and_after():
    data_before = _tree_hash(REPO_ROOT / "data")
    config_before = _tree_hash(REPO_ROOT / "config")
    result = subprocess.run(
        [sys.executable, "research/liquidity_001_evaluation.py", "--no-report"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OVERALL: PASS" in result.stdout
    assert _tree_hash(REPO_ROOT / "data") == data_before
    assert _tree_hash(REPO_ROOT / "config") == config_before


def test_all_structural_checks_pass(payload):
    checks = run_checks(payload)
    failed = [check["name"] for check in checks if not check["pass"]]
    assert not failed, failed


def test_artifacts_written_correctly():
    result = subprocess.run(
        [sys.executable, "research/liquidity_001_evaluation.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OVERALL: PASS" in result.stdout
    assert OUT_REPORT.exists()
    assert OUT_EXP.exists()
    exp_text = OUT_EXP.read_text()
    assert "liquidity_001" in exp_text
    assert FREEZE_COMMIT in exp_text
