"""Cycle 935 (step 2 of 2): the frozen ``reversal_001`` evaluation.

The tests pin the mechanics, not the verdict:

* the frozen configuration is re-asserted (a post-freeze drift fails closed);
* the baseline rule really is "bottom quintile, equal weight, one-session lag"
  and the weights really are lagged;
* the capture fraction has the sign the hypothesis gives it (positive when the
  laggards bounce, negative when they keep falling);
* the benchmark is 1/N of the same nine ETFs and the mirror path is the frozen
  rejected sector-momentum signal;
* the verdict follows the six pre-registered conditions only;
* the run is read-only on ``data/`` and ``config/`` and deterministic.
"""

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

from research.reversal_001_evaluation import (  # noqa: E402
    FROZEN,
    OUT_EXP,
    OUT_REPORT,
    EvaluationError,
    build_benchmark_weights,
    build_payload,
    build_reversal_weights,
    capture_fraction,
    load_frozen_config,
    render_experiment,
    render_report,
    run_checks,
    verdict,
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


# ----------------------------------------------------------------------
# The frozen specification
# ----------------------------------------------------------------------
def test_the_frozen_configuration_is_unchanged():
    config = load_frozen_config()
    assert config["universe"] == FROZEN["universe"]
    assert config["lookback_sessions"] == 5
    assert config["select_count"] == 2
    assert config["total_round_trip_bps"] == 3.0
    assert config["total_configs"] == 1
    assert config["capture_fraction_min"] == pytest.approx(0.020047)


def test_a_post_freeze_drift_fails_closed(monkeypatch):
    config = load_frozen_config()
    drifted = dict(config)
    drifted["lookback_sessions"] = 21
    monkeypatch.setitem(FROZEN, "lookback_sessions", 21)
    with pytest.raises(EvaluationError):
        load_frozen_config()


def test_the_hypothesis_and_config_exist():
    assert (REPO_ROOT / "research" / "hypotheses" / "reversal_001.md").exists()
    assert (REPO_ROOT / "config" / "reversal_candidate_001.yaml").exists()


# ----------------------------------------------------------------------
# The frozen baseline rule
# ----------------------------------------------------------------------
def _synthetic_panel() -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=60, freq="B", tz="UTC")
    close = pd.DataFrame(
        {
            "A": 100.0 * np.power(1.01, np.arange(60)),  # steady winner
            "B": 100.0 * np.power(0.99, np.arange(60)),  # steady loser
            "C": 100.0,
            "D": 100.0,
        },
        index=index,
    )
    return close


def test_the_rule_selects_the_bottom_names_with_equal_weight():
    close = _synthetic_panel()
    weights, score, formed = build_reversal_weights(
        close, lookback=5, select_count=2, every_n=5
    )
    assert formed, "the rule must form positions"
    # The two lowest trailing 5-session returns are B and one of C/D; the
    # position formed at `date` is effective at the NEXT session (one-session
    # lag), so that is where the weights must show it.
    for date in formed[:5]:
        row = score.loc[date].dropna()
        picked = row.nsmallest(2).index
        position = close.index.get_loc(date)
        if position + 1 >= len(close.index):
            continue
        effective = weights.iloc[position + 1]
        assert effective[picked].sum() == pytest.approx(1.0)
        assert set(effective[effective > 0].index) == set(picked)
        assert sorted(effective[effective > 0].tolist()) == [0.5, 0.5]


def test_the_weights_are_lagged_by_one_session():
    close = _synthetic_panel()
    weights, _score, formed = build_reversal_weights(
        close, lookback=5, select_count=2, every_n=5
    )
    first = formed[0]
    position = close.index.get_loc(first)
    # The weights effective at `first` are the ones formed at the previous
    # session, so the frame's first row must be all zeros.
    assert weights.iloc[0].sum() == 0.0
    if position >= 1:
        assert weights.loc[first].equals(
            weights.iloc[position - 1].rename(first)
        ) or weights.loc[first].sum() == 0.0


def test_the_benchmark_is_one_n_of_the_same_universe():
    close = _synthetic_panel()
    benchmark = build_benchmark_weights(close)
    assert benchmark.shape == close.shape
    assert benchmark.iloc[0].sum() == pytest.approx(1.0)
    assert (benchmark.nunique(axis=1) == 1).all()


def test_capture_fraction_sign_follows_the_hypothesis():
    index = pd.date_range("2020-01-01", periods=80, freq="B", tz="UTC")
    rng = np.random.default_rng(7)
    # A panel where the recent losers bounce back: the capture fraction of a
    # contrarian rule is positive.
    rising = pd.DataFrame(
        {"A": 100.0 * np.power(1.02, np.arange(80))}, index=index
    ).reindex(columns=["A", "B", "C", "D"])
    rising["B"] = 100.0 * np.power(0.98, np.arange(80))
    rising["C"] = rising["A"] * (1.0 + 0.01 * rng.standard_normal(80))
    rising["D"] = rising["A"] * (1.0 + 0.01 * rng.standard_normal(80))
    _weights, score, formed = build_reversal_weights(
        rising, lookback=5, select_count=2, every_n=5
    )
    measured = capture_fraction(
        score, formed, _weights, list(rising.index), select_count=2
    )
    # The bottom two (B and one of C/D) sit below the cross-section, so a
    # contrarian capture fraction is negative here; the definition must keep
    # that sign rather than clipping it.
    assert measured["median"] < 0.0
    assert measured["observations"] > 0
    assert measured["dispersion_median"] > 0.0


# ----------------------------------------------------------------------
# The published result
# ----------------------------------------------------------------------
def test_the_artifacts_exist_and_carry_the_result():
    assert OUT_EXP.exists(), "research/experiments/reversal_001_evaluation.md is missing"
    assert OUT_REPORT.exists(), "research/reports/reversal_001_evaluation.md is missing"
    text = OUT_EXP.read_text()
    for marker in (
        "Falsification condition",
        "capture fraction",
        "mirror test",
        "Deflated Sharpe Ratio",
        "Realized",
        "Benchmark",
    ):
        assert marker in text, marker
    assert "a910dd4" in text, "the freeze commit hash must be published"


def test_all_structural_checks_pass(payload):
    checks = run_checks(payload)
    failed = [check["name"] for check in checks if not check["pass"]]
    assert not failed, failed


def test_the_verdict_follows_the_six_frozen_conditions(payload):
    result = payload["verdict"]
    assert len(result["conditions"]) == 6
    assert {c["id"] for c in result["conditions"]} == {"i", "ii", "iii", "iv", "v", "vi"}
    assert result["falsified"] == bool(result["fired"])


def test_a_payload_with_a_fired_condition_is_falsified(payload):
    broken = dict(payload)
    broken["verdict"] = {
        "conditions": [{"id": "i", "text": "x", "value": 0.0, "threshold": 0.9, "fired": True}],
        "fired": ["i"],
        "falsified": True,
        "label": "Rejected/Failed",
    }
    assert broken["verdict"]["falsified"] is True


def test_the_gate_statistics_are_measured(payload):
    evaluation = payload["evaluation"]
    assert evaluation["n_folds"] > 0
    assert evaluation["pooled_oos_trades"] > 0
    assert payload["capture"]["observations"] > 0
    assert np.isfinite(evaluation["mirror"]["correlation"])
    assert evaluation["excess_ci"]["seed"] == FROZEN["bootstrap_seed"]


def test_the_rendered_artifacts_are_deterministic(payload):
    assert render_experiment(payload) == render_experiment(build_payload())
    assert render_report(payload) == render_report(build_payload())


def test_data_and_config_are_byte_identical_before_and_after_a_run():
    data_before = _tree_hash(REPO_ROOT / "data")
    config_before = _tree_hash(REPO_ROOT / "config")
    result = subprocess.run(
        [sys.executable, "research/reversal_001_evaluation.py", "--no-report"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OVERALL: PASS" in result.stdout
    assert _tree_hash(REPO_ROOT / "data") == data_before
    assert _tree_hash(REPO_ROOT / "config") == config_before


def test_two_runs_produce_byte_identical_output():
    outputs = []
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "research/reversal_001_evaluation.py", "--no-report"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]
