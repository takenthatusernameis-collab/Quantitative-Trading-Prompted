"""Offline tests for the promotion-gate false-negative-rate helpers.

No network, no data mutation: every test uses synthetic series.
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.gate_false_negative_rate as tool


def test_rolling_sharpe_matches_direct_computation():
    rng = np.random.default_rng(20240101)
    returns = rng.normal(0.0004, 0.009, size=200)
    values = tool.rolling_sharpe_values(returns, window=63)
    assert values.size == returns.size - 63 + 1
    manual = [
        float(np.mean(returns[i : i + 63]) * 252 / (np.std(returns[i : i + 63], ddof=1) * np.sqrt(252)))
        for i in range(returns.size - 62)
    ]
    assert np.allclose(values, manual, atol=1e-9)


def test_zero_dispersion_windows_score_zero():
    returns = np.zeros(100)
    values = tool.rolling_sharpe_values(returns, window=63)
    assert np.all(values == 0.0)
    assert tool.zero_dispersion_windows(returns, window=63) == returns.size - 62


def test_failure_rate_counts_strictly_below():
    values = np.array([0.0, 0.5, 0.9, 1.5])
    payload = tool.failure_rate(values, 0.9)
    assert payload["failures"] == 2
    assert abs(payload["rate"] - 0.5) < 1e-12
    assert payload["effective_independent_windows"] == values.size / tool.WINDOW


def test_failure_rate_standard_error_shrinks_with_n():
    values = np.concatenate([np.zeros(50), np.ones(950)])
    payload = tool.failure_rate(values, 0.9)
    assert payload["failures"] == 50
    assert payload["stderr_independent_window_approx"] > 0.0
    assert payload["effective_independent_windows"] == values.size / tool.WINDOW


def test_percentile_rank_is_inclusive():
    values = np.array([-1.0, 0.0, 1.0, 2.0])
    assert tool.percentile_rank(values, 2.0) == 100.0
    assert tool.percentile_rank(values, -1.0) == 25.0


def test_distribution_reports_expected_fields():
    payload = tool.distribution(np.array([1.0, 2.0, 3.0, 4.0]))
    for key in ("count", "mean", "sd", "min", "p01", "p05", "p25", "median", "p75", "p95", "p99", "max"):
        assert key in payload
    assert payload["count"] == 4
    assert abs(payload["mean"] - 2.5) < 1e-12
    assert abs(payload["median"] - 2.5) < 1e-12
