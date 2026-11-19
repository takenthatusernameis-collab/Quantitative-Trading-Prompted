"""Hermetic tests for research/drift_invariant_check.py.

The check encodes the three falsification conditions of
``research/reports/drift_decision_20261118.md`` §7. These tests build small
synthetic states so each condition is exercised in both directions without
touching the committed paper-trading record.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from research.drift_invariant_check import (
    DEFAULT_WINDOW,
    check_artifact_agreement,
    check_flag_reproduction,
    check_turnover_regime_coupling,
)
from src.evaluation.drift import sharpe_persistence
from src.evaluation.sharpe import sharpe_ratio

THRESHOLD = 0.5


def _history(exposures: list[float], turnovers: list[float]) -> list[dict]:
    n = len(exposures)
    dates = [f"2026-01-{i + 1:02d}" for i in range(n)]
    returns = [(-0.002 if i % 2 else -0.001) for i in range(n)]
    return [
        {
            "date": dates[i],
            "nav": 100000.0,
            "daily_return": returns[i],
            "turnover": turnovers[i],
            "regime_exposure": exposures[i],
        }
        for i in range(n)
    ]


def _state(exposures: list[float], turnovers: list[float]) -> dict:
    history = _history(exposures, turnovers)
    dates = [row["date"] for row in history]
    returns = [row["daily_return"] for row in history]
    last, prev = history[-1], history[-2]
    recent = np.asarray(returns[-DEFAULT_WINDOW:])
    flags: dict = {
        "high_turnover": {
            "value": last["turnover"],
            "threshold": THRESHOLD,
            "date": last["date"],
        },
        "low_rolling_sharpe": {
            "value": sharpe_ratio(recent),
            "threshold": 0.5,
            "date": last["date"],
            "persistence_days": int(
                sharpe_persistence(dates, returns)["streak_days"]
            ),
        },
    }
    if prev["regime_exposure"] != last["regime_exposure"]:
        flags["regime_flip"] = {
            "from": prev["regime_exposure"],
            "to": last["regime_exposure"],
            "date": last["date"],
        }
        flags["regime_persistence_low"] = {
            "value": 1,
            "threshold": 5,
            "date": last["date"],
        }
    return {
        "run_history": history,
        "drift_flags": flags,
        "cumulative_dates": dates,
        "cumulative_returns": returns,
        "previous_regime_exposure": last["regime_exposure"],
        "regime_persistence_days": 1 if "regime_flip" in flags else 2,
    }


def test_coupling_passes_on_regime_transition_day() -> None:
    history = _history([1.0, 1.0, 0.0], [0.01, 0.01, 0.51])
    assert check_turnover_regime_coupling(history, THRESHOLD) == []


def test_coupling_flags_high_turnover_without_transition() -> None:
    history = _history([1.0, 1.0, 1.0], [0.01, 0.01, 0.51])
    violations = check_turnover_regime_coupling(history, THRESHOLD)
    assert len(violations) == 1
    assert "without a regime transition" in violations[0]


def test_flag_reproduction_passes_on_consistent_state() -> None:
    state = _state([1.0, 1.0, 0.0], [0.01, 0.01, 0.51])
    assert check_flag_reproduction(state, THRESHOLD) == []


def test_flag_reproduction_detects_wrong_turnover() -> None:
    state = _state([1.0, 1.0, 0.0], [0.01, 0.01, 0.51])
    state["drift_flags"]["high_turnover"]["value"] = 0.123
    violations = check_flag_reproduction(state, THRESHOLD)
    assert any("high_turnover" in item for item in violations)


def test_flag_reproduction_detects_missing_regime_flip() -> None:
    state = _state([1.0, 1.0, 0.0], [0.01, 0.01, 0.51])
    del state["drift_flags"]["regime_flip"]
    violations = check_flag_reproduction(state, THRESHOLD)
    assert any("regime_flip" in item for item in violations)


def test_flag_reproduction_detects_wrong_sharpe() -> None:
    state = _state([1.0, 1.0, 0.0], [0.01, 0.01, 0.51])
    state["drift_flags"]["low_rolling_sharpe"]["value"] = 9.99
    violations = check_flag_reproduction(state, THRESHOLD)
    assert any("low_rolling_sharpe" in item for item in violations)


def test_artifact_agreement_detects_exposure_mismatch(tmp_path: Path) -> None:
    state = _state([1.0, 1.0, 0.0], [0.01, 0.01, 0.51])
    stamp = state["run_history"][-1]["date"].replace("-", "")
    pd.DataFrame(
        [{"date": state["run_history"][-1]["date"], "spy_price": np.nan,
          "regime_exposure": 1.0}]
    ).to_parquet(tmp_path / f"regime_{stamp}.parquet", index=False)
    violations = check_artifact_agreement(state, tmp_path)
    assert any("artifact exposure" in item for item in violations)


def test_artifact_agreement_detects_nonzero_weights_at_zero_exposure(
    tmp_path: Path,
) -> None:
    state = _state([1.0, 1.0, 0.0], [0.01, 0.01, 0.51])
    stamp = state["run_history"][-1]["date"].replace("-", "")
    pd.DataFrame(
        [{"date": state["run_history"][-1]["date"], "spy_price": np.nan,
          "regime_exposure": 0.0}]
    ).to_parquet(tmp_path / f"regime_{stamp}.parquet", index=False)
    pd.DataFrame([{"weight_A": 0.25, "weight_B": 0.25}]).to_parquet(
        tmp_path / f"positions_{stamp}.parquet", index=False
    )
    violations = check_artifact_agreement(state, tmp_path)
    assert any("zero exposure" in item for item in violations)
