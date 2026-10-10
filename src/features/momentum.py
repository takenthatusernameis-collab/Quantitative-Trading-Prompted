"""Time-series momentum feature engineering.

Computes 12-month price momentum (12-month return excluding the most recent
month) for each asset in a universe, ranks assets, and produces long-only
position weights. All signals use strictly lagged data to avoid
look-ahead bias.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


def compute_momentum(
    prices: pd.DataFrame,
    lookback: int = 252,
    skip: int = 21,
) -> pd.DataFrame:
    """Return per-asset 12-month momentum (return over ``lookback`` days
    skipping the most recent ``skip`` days).

    Parameters
    ----------
    prices:
        DataFrame indexed by date with one column per asset (Close prices).
    lookback:
        Trading-day lookback for the momentum window (default 252 ~ 1 year).
    skip:
        Number of most-recent trading days to exclude (default 21 ~ 1 month)
        to avoid short-term reversal microstructure noise.

    Returns
    -------
    pd.DataFrame
        Same shape as ``prices``; NaN where insufficient history exists.
    """
    if prices.empty:
        return prices

    shifted = prices.shift(skip)
    past = shifted.shift(lookback)
    momentum = (shifted / past) - 1.0
    return momentum


def rank_assets(momentum: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectionally rank assets each period (higher momentum = higher rank)."""
    return momentum.rank(axis=1, ascending=True, method="average", na_option="keep")


def select_top_decile(
    momentum: pd.DataFrame,
    top_fraction: float = 0.5,
) -> pd.DataFrame:
    """Boolean mask selecting assets in the top ``top_fraction`` of momentum.

    For universes with fewer than 5 assets the top decile is replaced by the
    single best asset to avoid degenerate equal-weight splits.
    """
    if momentum.empty:
        return momentum.astype(bool)

    n_assets = momentum.shape[1]
    if n_assets < 5:
        # Small universe: pick the single best asset each period
        best = momentum.idxmax(axis=1)
        mask = pd.DataFrame(False, index=momentum.index, columns=momentum.columns)
        for date, col in best.items():
            if pd.notna(col) and col in mask.columns:
                mask.loc[date, col] = True
        return mask

    ranks = rank_assets(momentum)
    threshold = ranks.max(axis=1) * (1.0 - top_fraction)
    return ranks.ge(threshold, axis=0)


def build_weights(
    prices: pd.DataFrame,
    lookback: int = 252,
    skip: int = 21,
    top_fraction: float = 0.5,
) -> pd.DataFrame:
    """Compute long-only equal-weight position weights for the top momentum assets.

    Weights are shifted by one day so that signals are point-in-time: a
    signal computed on day ``t`` produces positions effective on day ``t+1``.
    """
    momentum = compute_momentum(prices, lookback=lookback, skip=skip)
    mask = select_top_decile(momentum, top_fraction=top_fraction)

    n_selected = mask.sum(axis=1).replace(0, np.nan)
    weights = mask.astype(float).div(n_selected, axis=0).fillna(0.0)
    # Point-in-time: positions effective next day
    weights = weights.shift(1).fillna(0.0)
    return weights


def signal_summary(weights: pd.DataFrame) -> pd.DataFrame:
    """Return a tidy summary of active positions per date."""
    active = (weights > 0).sum(axis=1)
    return pd.DataFrame(
        {
            "n_long": active,
            "allocation": weights.sum(axis=1),
        },
        index=weights.index,
    )