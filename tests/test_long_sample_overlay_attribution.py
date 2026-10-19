"""Offline tests for the long-sample overlay attribution helpers.

No network, no data mutation: every test uses synthetic frames or reads the
committed configuration read-only.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.long_sample_overlay_attribution as tool
from src.evaluation.sharpe import sharpe_ratio


def _weights(rows):
    return pd.DataFrame(
        rows,
        index=pd.date_range("2020-01-01", periods=len(rows), freq="B", tz="UTC"),
        columns=["AAA", "BBB"],
    )


def test_own_cost_net_path_charges_own_turnover():
    weights = _weights([[0.5, 0.5], [0.5, 0.5], [0.25, 0.25]])
    asset_ret = _weights([[0.01, 0.0], [-0.02, 0.01], [0.03, -0.01]])
    path = tool.own_cost_net_path(weights, asset_ret, cost_per_unit=0.0003)

    gross = [0.005, 0.5 * -0.02 + 0.5 * 0.01, 0.25 * 0.03 + 0.25 * -0.01]
    turnover = [0.0, 0.0, 0.5]
    expected = [g - t * 0.0003 for g, t in zip(gross, turnover)]
    assert np.allclose(path.to_numpy(), expected)


def test_decompose_chain_telescopes_exactly():
    comp = {
        "base": 1.0,
        "gated": 2.0,
        "vol_targeted": 1.5,
        "dd_scaled": 1.5,
        "combined": 1.5,
    }
    result = tool.decompose_chain(comp)
    assert result["effects"]["filter_effect"] == 1.0
    assert result["effects"]["vol_overlay_effect"] == -0.5
    assert result["effects"]["drawdown_overlay_effect"] == 0.0
    assert result["effects"]["gross_exposure_cap_effect"] == 0.0
    assert result["residual"] == 0.0


def test_rolling_compounded_matches_brute_force():
    returns = np.array([0.01, -0.02, 0.005, 0.03, -0.01, 0.002])
    window = 3
    rolled = tool.rolling_compounded(returns, window)
    expected = [
        float(np.prod(1.0 + returns[i : i + window]) - 1.0)
        for i in range(len(returns) - window + 1)
    ]
    assert np.allclose(rolled, expected, atol=1e-15)
    assert len(rolled) == len(returns) - window + 1


def test_percentile_rank_is_inclusive():
    values = np.array([0.0, 1.0, 2.0, 3.0])
    assert tool.percentile_rank(values, 3.0) == 100.0
    assert tool.percentile_rank(values, 0.0) == 25.0
    assert tool.percentile_rank(values, 1.0) == 50.0
    assert tool.percentile_rank(np.array([]), 0.0) != tool.percentile_rank(values, 0.0)


def test_annualised_turnover_matches_manual_sum():
    weights = _weights([[0.5, 0.5], [0.5, 0.5], [0.25, 0.25]])
    turnover = tool.annualised_turnover(weights)
    expected = (0.0 + 0.0 + 0.5) / 3 * 252
    assert abs(turnover - expected) < 1e-12


def test_cost_model_matches_frozen_config():
    with open(tool.CONFIG_CAND) as fh:
        cfg = yaml.safe_load(fh)
    assert float(cfg["cost_model"]["total_round_trip_bps"]) == tool.COST_BPS
    assert tool.COST_PER_UNIT == tool.COST_BPS / 10000.0


def test_layer_chain_metrics_uses_canonical_sharpe():
    net_paths = {
        "base": pd.Series([0.001, -0.002, 0.003, 0.001]),
        "gated": pd.Series([0.001, -0.002, 0.003, 0.001]),
        "vol_targeted": pd.Series([0.0005, -0.001, 0.0015, 0.0005]),
        "dd_scaled": pd.Series([0.0005, -0.001, 0.0015, 0.0005]),
        "combined": pd.Series([0.0005, -0.001, 0.0015, 0.0005]),
    }
    metrics = tool.layer_chain_metrics(net_paths)
    assert metrics["sharpe"]["base"] == sharpe_ratio(net_paths["base"])
    assert abs(metrics["residual"]) <= 1e-12
