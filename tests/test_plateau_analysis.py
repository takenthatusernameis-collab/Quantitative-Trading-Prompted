"""Regression tests for parameter-plateau (perturbation) analysis.

The perturbation set around a baseline strategy configuration is only a
meaningful factorial design when the *unperturbed* baseline is itself present
in the results. Without it the markdown formatter has no row to anchor the
"within +/-10% of baseline" stability statistic, and it silently drops both
the baseline row and the whole stability paragraph.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.evaluation.statistics import (
    _evaluate_config,
    format_plateau_markdown,
    parameter_perturbation,
)
from src.evaluation.utils import fetch_close_prices

SYMBOLS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
BASELINE = (252, 21, 0.5)


def _close() -> pd.DataFrame:
    return fetch_close_prices(SYMBOLS, "2000-01-01", "2026-10-14")


def test_baseline_is_present_in_perturbation_results() -> None:
    df = parameter_perturbation(_close(), baseline=BASELINE)
    baseline_mask = (
        (df.index.get_level_values("lookback") == BASELINE[0])
        & (df.index.get_level_values("skip") == BASELINE[1])
        & (df.index.get_level_values("top_fraction") == BASELINE[2])
    )
    assert baseline_mask.any(), "baseline configuration must appear in perturbation results"
    assert df.loc[baseline_mask, "label"].iloc[0] == "baseline"


def test_baseline_row_is_rendered_in_markdown() -> None:
    df = parameter_perturbation(_close(), baseline=BASELINE)
    out = format_plateau_markdown(df, baseline=BASELINE)
    assert "**Baseline (train, val, test Sharpe):**" in out, (
        "markdown must render the baseline row"
    )


def test_stability_paragraph_is_rendered_when_baseline_present() -> None:
    df = parameter_perturbation(_close(), baseline=BASELINE)
    out = format_plateau_markdown(df, baseline=BASELINE)
    assert "**Stability:**" in out, (
        "markdown must render the stability paragraph anchored on the baseline"
    )


def test_evaluate_config_matches_baseline_perturbation_row() -> None:
    """_evaluate_config must reproduce the baseline row produced by
    parameter_perturbation, so the extracted helper is not a second,
    divergent implementation."""
    close = _close()
    df = parameter_perturbation(close, baseline=BASELINE)
    baseline_mask = (
        (df.index.get_level_values("lookback") == BASELINE[0])
        & (df.index.get_level_values("skip") == BASELINE[1])
        & (df.index.get_level_values("top_fraction") == BASELINE[2])
    )
    baseline_row = df.loc[baseline_mask].iloc[0]

    from src.evaluation.utils import get_cost_params

    commission_bps, slippage_bps = get_cost_params()
    cost = commission_bps + slippage_bps
    train_end_dt = pd.Timestamp("2009-12-31", tz="UTC")
    val_end_dt = pd.Timestamp("2017-12-31", tz="UTC")
    direct = _evaluate_config(
        close, BASELINE[0], BASELINE[1], BASELINE[2], cost, train_end_dt, val_end_dt
    )

    assert abs(direct["train_sharpe"] - baseline_row["train_sharpe"]) < 1e-9
    assert abs(direct["val_sharpe"] - baseline_row["val_sharpe"]) < 1e-9
    assert abs(direct["test_sharpe"] - baseline_row["test_sharpe"]) < 1e-9