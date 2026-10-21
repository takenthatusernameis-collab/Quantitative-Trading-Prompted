"""Cycle 939: tests for the frozen ``leadlag_001`` evaluation."""

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

from research.leadlag_001_evaluation import (  # noqa: E402
    FROZEN,
    FREEZE_COMMIT,
    OUT_EXP,
    OUT_REPORT,
    EvaluationError,
    book_returns,
    build_pair_weights,
    build_panel,
    detect_roll_dates,
    futures_signal,
    load_closes,
    load_frozen_config,
    build_payload,
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


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120
    )


@pytest.fixture(scope="module")
def payload() -> dict:
    return build_payload()


# ----------------------------------------------------------------------
# The frozen pre-registration
# ----------------------------------------------------------------------
def test_the_frozen_configuration_is_unchanged():
    config = load_frozen_config()
    assert config["universe"] == FROZEN["universe"]
    assert config["pairs"] == FROZEN["pairs"]
    assert config["lookback_sessions"] == 5
    assert config["rebalance_every_n_sessions"] == 5
    assert config["signal_lag_days"] == 1
    assert config["pair_weight"] == 0.2
    assert config["total_round_trip_bps"] == 3.0
    assert config["total_configs"] == 5
    assert config["history_start"] == "2015-01-02"
    assert config["history_end"] == "2026-10-15"


def test_a_post_freeze_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(FROZEN, "lookback_sessions", 7)
    with pytest.raises(EvaluationError):
        load_frozen_config()


def test_a_post_freeze_drift_of_the_pairs_fails_closed(monkeypatch):
    monkeypatch.setitem(FROZEN, "pairs", FROZEN["pairs"][:-1])
    with pytest.raises(EvaluationError):
        load_frozen_config()


def test_the_hypothesis_and_the_config_exist():
    assert (REPO_ROOT / "research" / "hypotheses" / "leadlag_001.md").exists()
    assert (REPO_ROOT / "config" / "leadlag_candidate_001.yaml").exists()


def test_the_freeze_commit_contains_exactly_the_two_pre_registration_files():
    result = _git("show", "--name-only", "--format=", FREEZE_COMMIT)
    assert result.returncode == 0, result.stderr
    paths = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    assert paths == {
        "config/leadlag_candidate_001.yaml",
        "research/hypotheses/leadlag_001.md",
    }


def test_the_pre_registration_files_are_byte_identical_to_the_freeze_commit():
    for rel in (
        "config/leadlag_candidate_001.yaml",
        "research/hypotheses/leadlag_001.md",
    ):
        frozen = _git("show", f"{FREEZE_COMMIT}:{rel}")
        assert frozen.returncode == 0, frozen.stderr
        assert frozen.stdout.encode() == (REPO_ROOT / rel).read_bytes()


# ----------------------------------------------------------------------
# The frozen rule
# ----------------------------------------------------------------------
def _synthetic_futures(n: int = 40, start: float = 100.0) -> pd.Series:
    index = pd.date_range("2020-01-01", periods=n, freq="B", tz="UTC")
    return pd.Series(start * (1.01 ** np.arange(n)), index=index)


def test_the_signal_is_the_sign_of_the_futures_trailing_five_session_return():
    futures = _synthetic_futures()
    contaminated = pd.Series(False, index=futures.index)
    signal, usable = futures_signal(futures, 5, contaminated)
    for position in range(5, len(futures)):
        expected = np.sign(
            futures.iloc[position] / futures.iloc[position - 5] - 1.0
        )
        assert signal.iloc[position] == expected
        assert bool(usable.iloc[position]) is True
    # a falling futures leg gives a negative signal
    falling = pd.Series(
        100.0 * (0.99 ** np.arange(len(futures))), index=futures.index
    )
    signal_down, _usable_down = futures_signal(falling, 5, contaminated)
    assert signal_down.iloc[-1] == -1.0


def test_a_signal_whose_window_contains_a_contaminated_session_is_unusable():
    futures = _synthetic_futures()
    contaminated = pd.Series(False, index=futures.index)
    contaminated.iloc[20] = True  # a roll date or a non-positive close
    signal, usable = futures_signal(futures, 5, contaminated)
    # the sessions whose trailing window contains position 20 are unusable
    for position in range(20, 26):
        assert bool(usable.iloc[position]) is False
    assert bool(usable.iloc[19]) is True
    assert bool(usable.iloc[26]) is True


def test_the_non_positive_close_makes_the_affected_signal_unusable():
    index = pd.date_range("2020-01-01", periods=12, freq="B", tz="UTC")
    close = pd.Series(100.0, index=index)
    close.iloc[6] = -37.63
    contaminated = close <= 0.0
    _signal, usable = futures_signal(close, 5, contaminated)
    assert bool(usable.iloc[6]) is False
    assert bool(usable.iloc[7]) is False
    assert bool(usable.iloc[5]) is True


def test_the_pair_selection_is_the_five_frozen_pairs(payload):
    config = payload["config"]
    assert [tuple(p) for p in config["pairs"]] == [
        ("CL-F", "USO"),
        ("CL-F", "BNO"),
        ("GC-F", "GLD"),
        ("NG-F", "UNG"),
        ("ZB-F", "TLT"),
    ]
    assert payload["n_pairs"] == 5


def test_the_rebalance_is_every_five_sessions_with_a_one_session_lag():
    index = pd.date_range("2020-01-01", periods=40, freq="B", tz="UTC")
    futures = _synthetic_futures()
    signal, usable = futures_signal(futures, 5, pd.Series(False, index=futures.index))
    signals = {"CL-F": signal}
    usability = {"CL-F": usable}
    weights, per_pair = build_pair_weights(
        index, [("CL-F", "USO")], signals, usability, 5, 1, 0.2
    )
    assert list(weights.columns) == ["USO"]
    assert per_pair["USO"].equals(weights["USO"])
    # the first session cannot be traded (the signal formed at t is effective
    # at t+1) and no signal exists before the fifth session
    assert weights["USO"].iloc[0] == 0.0
    assert weights["USO"].iloc[1] == 0.0
    # a rising futures leg is long from the first usable signal (position 5)
    assert weights["USO"].iloc[6] == pytest.approx(0.2)
    # the weight never changes except on the effective sessions
    changes = weights["USO"].diff().fillna(0.0).ne(0.0)
    effective_positions = {p + 1 for p in range(0, len(index), 5)}
    assert set(np.flatnonzero(changes.to_numpy())) <= effective_positions


def test_an_unusable_signal_leaves_the_pair_flat():
    index = pd.date_range("2020-01-01", periods=40, freq="B", tz="UTC")
    futures = _synthetic_futures()
    contaminated = pd.Series(False, index=futures.index)
    contaminated.iloc[10] = True  # the rebalance at position 10 cannot use it
    signal, usable = futures_signal(futures, 5, contaminated)
    weights, _per_pair = build_pair_weights(
        index, [("CL-F", "USO")], {"CL-F": signal}, {"CL-F": usable}, 5, 1, 0.2
    )
    # the rebalance at position 5 is clean -> long from position 6
    assert weights["USO"].iloc[6] == pytest.approx(0.2)
    # the rebalance at position 10 has an unusable signal -> flat from 11
    assert weights["USO"].iloc[11] == 0.0
    # the rebalance at position 20 is clean again -> long from 21
    assert weights["USO"].iloc[21] == pytest.approx(0.2)


def test_the_benchmark_is_cash():
    import yaml

    raw = yaml.safe_load(
        (REPO_ROOT / "config" / "leadlag_candidate_001.yaml").read_text()
    )
    assert raw["evaluation"]["benchmarks"] == ["cash"]
    # a book that never holds a position earns exactly the cash return (0)
    index = pd.date_range("2020-01-01", periods=5, freq="B", tz="UTC")
    panel = pd.DataFrame({"USO": 100.0}, index=index)
    weights = pd.DataFrame({"USO": 0.0}, index=index)
    series = book_returns(panel, weights, 3.0 / 10_000.0)
    assert float(series["net"].abs().max()) == 0.0


def test_the_cost_model_is_three_bp_per_unit_of_weight_change():
    config = load_frozen_config()
    assert config["total_round_trip_bps"] == 3.0
    assert config["commission_bps"] == 1.0
    assert config["slippage_bps"] == 2.0
    index = pd.date_range("2020-01-01", periods=3, freq="B", tz="UTC")
    panel = pd.DataFrame({"USO": [100.0, 101.0, 102.0]}, index=index)
    weights = pd.DataFrame({"USO": [0.0, 0.2, 0.2]}, index=index)
    series = book_returns(panel, weights, 3.0 / 10_000.0)
    # one unit of weight change costs 3 bp
    assert series["cost"].iloc[1] == pytest.approx(0.2 * 3.0 / 10_000.0)
    assert series["cost"].iloc[2] == pytest.approx(0.0)
    assert series["net"].iloc[1] == pytest.approx(
        series["gross"].iloc[1] - 0.2 * 3.0 / 10_000.0
    )


def test_the_walk_forward_design_matches_the_frozen_spec(payload):
    config = payload["config"]
    assert config["train_years"] == 10
    assert config["test_months"] == 12
    assert config["step_months"] == 6
    assert config["purge_days"] == 21
    assert config["embargo_days"] == 21
    folds = payload["evaluation"]["folds"]
    assert len(folds) == 3
    for fold in folds:
        span = pd.Timestamp(fold["test_end"]) - pd.Timestamp(fold["test_start"])
        assert 330 <= span.days <= 400


def test_the_panel_is_the_cycle_934_complete_cross_section(payload):
    assert payload["sessions"] == 2960
    assert payload["union_sessions"] == 6098
    assert payload["calendar_churn"] == pytest.approx(0.5146, abs=1e-3)
    config = payload["config"]
    assert payload["sessions"] == config["sessions"]


# ----------------------------------------------------------------------
# The data-quality rules
# ----------------------------------------------------------------------
def test_the_roll_windows_are_detected(payload):
    rolls = payload["data_quality"]["rolls_by_symbol"]
    assert rolls == {"CL-F": 127, "GC-F": 72, "NG-F": 125, "ZB-F": 62}
    # the Cycle-884 externally verified roll of 2026-09-23 is detected
    dates, count = detect_roll_dates("CL-F")
    assert count == 127
    assert "2026-09-23" in {str(pd.Timestamp(d).date()) for d in dates}


def test_the_roll_windows_are_excluded_from_the_cleaned_variant(payload):
    quality = payload["data_quality"]
    assert quality["roll_signal_sessions_excluded"] > 0
    clean = payload["evaluation"]["net_excess_annualized"]
    unclean = payload["unclean_evaluation"]["net_excess_annualized"]
    # the two variants differ, i.e. the roll exclusion really changes the result
    assert clean != unclean


def test_the_cl_f_non_positive_close_is_detected(payload):
    quality = payload["data_quality"]
    assert quality["cl_f_non_positive_close_sessions"] == 1
    assert quality["cl_f_non_positive_close_dates"] == ["2020-04-20"]
    assert quality["cl_f_non_positive_close_values"][0] == pytest.approx(-37.63)


# ----------------------------------------------------------------------
# The verdict
# ----------------------------------------------------------------------
def test_the_falsification_conditions_drive_the_verdict(payload):
    evaluation = payload["evaluation"]
    assert len(payload["verdict"]["conditions"]) == 4
    fired = payload["verdict"]["fired"]
    assert "i" in fired  # the walk-forward mean OOS Sharpe is far below 0.9
    assert "ii" in fired  # the bootstrap CI includes zero and the DSR is <= 0
    assert payload["verdict"]["label"] == "Rejected/Failed"


def test_a_passing_payload_would_not_be_labelled_rejected():
    config = load_frozen_config()
    passing = {
        "config": config,
        "evaluation": {
            "wf_mean_oos_sharpe": 1.2,
            "excess_ci": {"ci_low": 0.01, "ci_high": 0.05},
            "dsr": {"dsr": 0.9},
            "net_excess_annualized": 0.05,
            "non_cl_f_net_excess_annualized": 0.04,
            "positive_fold_rate": 0.9,
            "pooled_oos_trades": 500,
        },
        "unclean_evaluation": {"net_excess_annualized": 0.06},
    }
    result = verdict(passing)
    assert result["fired"] == []
    assert result["label"] == "Promotable/NO-GO"


def test_a_roll_artefact_fires_condition_iii():
    config = load_frozen_config()
    artefact = {
        "config": config,
        "evaluation": {
            "wf_mean_oos_sharpe": 1.2,
            "excess_ci": {"ci_low": 0.01, "ci_high": 0.05},
            "dsr": {"dsr": 0.9},
            "net_excess_annualized": -0.01,
            "non_cl_f_net_excess_annualized": 0.04,
            "positive_fold_rate": 0.9,
            "pooled_oos_trades": 500,
        },
        "unclean_evaluation": {"net_excess_annualized": 0.06},
    }
    result = verdict(artefact)
    assert "iii" in result["fired"]


def test_a_cl_f_carried_excess_fires_condition_iv():
    config = load_frozen_config()
    cl_f_carried = {
        "config": config,
        "evaluation": {
            "wf_mean_oos_sharpe": 1.2,
            "excess_ci": {"ci_low": 0.01, "ci_high": 0.05},
            "dsr": {"dsr": 0.9},
            "net_excess_annualized": 0.05,
            "non_cl_f_net_excess_annualized": -0.01,
            "positive_fold_rate": 0.9,
            "pooled_oos_trades": 500,
        },
        "unclean_evaluation": {"net_excess_annualized": 0.06},
    }
    result = verdict(cl_f_carried)
    assert "iv" in result["fired"]


# ----------------------------------------------------------------------
# Determinism and read-only guarantees
# ----------------------------------------------------------------------
def test_two_runs_byte_identical_output():
    outputs = []
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "research/leadlag_001_evaluation.py", "--no-report"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]


def test_two_runs_write_byte_identical_artifacts():
    result = subprocess.run(
        [sys.executable, "research/leadlag_001_evaluation.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    first = (_sha256(OUT_REPORT), _sha256(OUT_EXP))
    result = subprocess.run(
        [sys.executable, "research/leadlag_001_evaluation.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert first == (_sha256(OUT_REPORT), _sha256(OUT_EXP))


def test_data_and_config_unchanged_before_and_after():
    data_before = _tree_hash(REPO_ROOT / "data")
    config_before = _tree_hash(REPO_ROOT / "config")
    result = subprocess.run(
        [sys.executable, "research/leadlag_001_evaluation.py", "--no-report"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OVERALL: PASS" in result.stdout
    assert _tree_hash(REPO_ROOT / "data") == data_before
    assert _tree_hash(REPO_ROOT / "config") == config_before


def test_git_reports_no_change_under_data_or_config():
    result = _git("status", "--porcelain", "data/", "config/")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_the_shared_cost_model_is_untouched():
    result = _git("diff", "--name-only", "HEAD", "--", "config/settings.yaml")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_all_structural_checks_pass(payload):
    checks = run_checks(payload)
    failed = [check["name"] for check in checks if not check["pass"]]
    assert not failed, failed


def test_the_artifacts_are_written_and_carry_the_freeze_commit():
    result = subprocess.run(
        [sys.executable, "research/leadlag_001_evaluation.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OVERALL: PASS" in result.stdout
    assert OUT_REPORT.exists()
    assert OUT_EXP.exists()
    for path in (OUT_REPORT, OUT_EXP):
        text = path.read_text()
        assert "leadlag_001" in text
        assert FREEZE_COMMIT in text
        assert "Rejected/Failed" in text
