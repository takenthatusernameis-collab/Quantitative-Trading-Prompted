"""Shared rebalance-schedule implementations for the portfolio construction.

This module is the single source of truth for the **month-end** rebalance
schedule that the frozen candidate configurations specify
(``config/sectorrotation_candidate_001.yaml``,
``config/csmomentum_candidate_001.yaml``,
``config/macroregime_candidate_001.yaml``: ``rebalance_schedule: monthly``
with ``signal_lag_days: 1``).

Definition used from Cycle 870 on (identical everywhere in the repository):

* the **month-end session** of a calendar month is the *last session of the
  session calendar* that falls in that month. The session calendar is the
  aligned price index built by ``src.data.yfinance_fetcher``; it contains
  trading sessions only. A month whose last calendar day is a weekend (or a
  market holiday) therefore rebalances on the last session that actually
  happened -- the Friday session for a weekend month end -- and never on a
  calendar day that is not in the calendar.
* the **signal** is formed on that month-end session, so the positions are
  **effective from the next session** (``signal_lag_days: 1``) and are held
  unchanged until the next month-end signal.
* a month whose signal is not defined (no valid cross-section, e.g. during
  the momentum warm-up) opens **no** position: positions are never
  back-filled and no position exists before the first valid signal.

The daily schedule (``None`` or ``"daily"``) is the repository's historical
behaviour: the universe is re-ranked every session. It is kept as the
default so that every committed artifact stays reproducible.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import numpy as np
import pandas as pd

DAILY_SCHEDULE = "daily"
MONTH_END_SCHEDULE = "month_end"

#: Accepted spellings of a rebalance schedule and their canonical name.
SCHEDULE_ALIASES: dict[str, str] = {
    "daily": DAILY_SCHEDULE,
    "d": DAILY_SCHEDULE,
    "month_end": MONTH_END_SCHEDULE,
    "monthend": MONTH_END_SCHEDULE,
    "monthly": MONTH_END_SCHEDULE,
    "m": MONTH_END_SCHEDULE,
}


def normalize_schedule(schedule: Optional[str]) -> str:
    """Return the canonical name of *schedule*.

    ``None`` is not accepted here: the caller decides what the default is.
    An unknown schedule is a hard error (fail closed) rather than a silent
    fallback to the daily re-ranking.
    """
    if schedule is None:
        raise ValueError("rebalance schedule must be given explicitly")
    key = str(schedule).strip().lower()
    if key not in SCHEDULE_ALIASES:
        raise ValueError(
            f"Unsupported rebalance schedule: {schedule!r} "
            f"(supported: {sorted(set(SCHEDULE_ALIASES.values()))})"
        )
    return SCHEDULE_ALIASES[key]


def month_end_sessions(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Last session of every calendar month present in *index* (ascending).

    Parameters
    ----------
    index:
        Session calendar (a :class:`pandas.DatetimeIndex`).

    Returns
    -------
    list of pandas.Timestamp
        One timestamp per calendar month: the last session of that month.
    """
    index = pd.DatetimeIndex(index)
    last: dict[str, pd.Timestamp] = {}
    for d, key in zip(index, index.strftime("%Y-%m")):
        last[key] = d
    return [last[k] for k in sorted(last)]


def build_month_end_weights(
    mask: pd.DataFrame,
    month_ends: Optional[Sequence[pd.Timestamp]] = None,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Month-end rebalanced, 1-session-lagged, equal-weight target weights.

    Parameters
    ----------
    mask:
        Per-session selection mask (one column per asset, ``True`` = held).
        Its index is the session calendar.
    month_ends:
        Optional precomputed list of month-end sessions; computed from the
        mask's index when omitted.

    Returns
    -------
    (weights, segments)
        ``weights`` holds the target weights per session (zero before the
        first valid signal), ``segments`` describes every rebalance:
        ``signal_date``, ``effective_date``, ``n_selected`` and ``weights``.
    """
    idx = mask.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.DatetimeIndex(idx)
    if not idx.is_unique:
        raise ValueError("session calendar must not contain duplicate timestamps")
    if len(idx) == 0:
        return pd.DataFrame(0.0, index=idx, columns=mask.columns), []

    weights = pd.DataFrame(0.0, index=idx, columns=mask.columns)
    segments: list[dict[str, Any]] = []

    if month_ends is None:
        month_ends = month_end_sessions(idx)

    for d in month_ends:
        sel = mask.loc[d]
        n_selected = int(np.asarray(sel).sum())
        if n_selected == 0:
            # No valid signal in this month: no position is opened and the
            # previous month-end positions are not extended by a new signal.
            continue
        eff_pos = int(idx.searchsorted(d, side="right"))
        if eff_pos >= len(idx):
            # The last month-end has no following session: no position can
            # become effective from it.
            break
        eff = idx[eff_pos]
        segments.append(
            {
                "signal_date": d,
                "effective_date": eff,
                "n_selected": n_selected,
                "weights": np.asarray(sel, dtype=float) / n_selected,
            }
        )

    for j, seg in enumerate(segments):
        start = int(idx.searchsorted(seg["effective_date"], side="left"))
        if j + 1 < len(segments):
            end = int(idx.searchsorted(segments[j + 1]["effective_date"], side="left"))
        else:
            end = len(idx)
        weights.iloc[start:end, :] = seg["weights"]

    return weights, segments
