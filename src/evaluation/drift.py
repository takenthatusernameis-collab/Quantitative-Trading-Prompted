"""Deterministic drift-flag persistence accounting.

The paper-trading loop raises the ``low_rolling_sharpe`` drift flag whenever the
rolling 63-day Sharpe falls below its alert threshold. How long that condition
has *persisted* is a monitoring question that must have exactly one
reproducible answer, otherwise the number quoted in reports drifts away from
the stored data (see ``research/reports/drift_flag_escalation_001.md`` §3).

This module provides that answer as a pure function of the stored return
series:

* :func:`annualized_sharpe` uses exactly the formula of the live paper-trading
  update (``mean(r) * 252 / (std(r, ddof=1) * sqrt(252))``), so the values
  recomputed offline match the values recorded in the state file.
* :func:`rolling_sharpe_series` rebuilds the rolling Sharpe for every session,
  using the same 63-session window and the same minimum history (20 returns)
  that gate the live flag.
* :func:`subthreshold_streak` counts the trailing sessions that stayed below
  the threshold -- the "consecutive trading days below threshold" definition.
* :func:`sharpe_persistence` bundles those pieces into a report-ready summary.

All functions are pure: they never touch the state file, the raw cache or the
network. A monitoring run can therefore recompute the persistence count at any
time and must obtain the same number the live update recorded.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

import numpy as np

from src.evaluation.sharpe import sharpe_ratio

TRADING_DAYS_PER_YEAR = 252
DEFAULT_WINDOW = 63
DEFAULT_MIN_PERIODS = 20
DEFAULT_SHARPE_THRESHOLD = 0.5
DEFAULT_CALENDAR_DAYS = 46


def annualized_sharpe(
    returns: Sequence[float],
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Annualized Sharpe ratio of ``returns`` (zero risk-free rate).

    Delegates to the repository's canonical Sharpe convention
    (:func:`src.evaluation.sharpe.sharpe_ratio`,
    ``mean(r) * 252 / (std(r, ddof=1) * sqrt(252))``), which is exactly the
    formula of the live paper-trading update, so that offline recomputation,
    the stored drift flag and the promotion gate all report the same number.
    """
    return sharpe_ratio(returns, rf_annual=0.0, periods_per_year=periods_per_year)


def rolling_sharpe_series(
    dates: Sequence[str],
    returns: Sequence[float],
    window: int = DEFAULT_WINDOW,
    min_periods: int = DEFAULT_MIN_PERIODS,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> list[tuple[str, float | None]]:
    """Rolling-window Sharpe for every session in the series.

    Parameters
    ----------
    dates:
        Session dates aligned with ``returns`` (ISO ``YYYY-MM-DD`` strings).
    returns:
        Daily net returns aligned with ``dates``.
    window:
        Rolling window length in sessions (63 for the paper-trading flag).
    min_periods:
        Minimum number of returns required before a Sharpe value is produced.
        The live flag is only evaluated once 20 returns exist, so earlier
        sessions are reported as ``None`` rather than as sub-threshold.
    periods_per_year:
        Annualization factor (252 for daily equity returns).

    Returns
    -------
    list of (date, sharpe or None)
        One entry per session, in input order.
    """
    if len(dates) != len(returns):
        raise ValueError(
            f"dates and returns must have equal length ({len(dates)} != {len(returns)})"
        )
    arr = np.asarray(list(returns), dtype=float)
    series: list[tuple[str, float | None]] = []
    for i in range(arr.size):
        if i + 1 < min_periods:
            series.append((dates[i], None))
            continue
        window_slice = arr[max(0, i - window + 1) : i + 1]
        series.append((dates[i], annualized_sharpe(window_slice, periods_per_year)))
    return series


def subthreshold_streak(
    series: Sequence[tuple[str, float | None]],
    threshold: float = DEFAULT_SHARPE_THRESHOLD,
) -> int:
    """Number of trailing sessions whose value stayed below ``threshold``.

    The backward scan stops at the first session that is not below the
    threshold, which includes sessions with no computed value (``None``, i.e.
    insufficient history).
    """
    streak = 0
    for _date, value in reversed(list(series)):
        if value is None or value >= threshold:
            break
        streak += 1
    return streak


def sharpe_persistence(
    dates: Sequence[str],
    returns: Sequence[float],
    window: int = DEFAULT_WINDOW,
    min_periods: int = DEFAULT_MIN_PERIODS,
    threshold: float = DEFAULT_SHARPE_THRESHOLD,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> dict:
    """Summary of how long the low-Sharpe condition has persisted.

    Returns a dictionary with the trailing streak of sub-threshold sessions
    (the "consecutive trading days below threshold" count), the session counts
    over the whole history, and the most recent rolling Sharpe value.
    """
    series = rolling_sharpe_series(
        dates,
        returns,
        window=window,
        min_periods=min_periods,
        periods_per_year=periods_per_year,
    )
    streak = subthreshold_streak(series, threshold=threshold)
    evaluated = [(d, v) for d, v in series if v is not None]
    subthreshold = [(d, v) for d, v in evaluated if v < threshold]
    streak_entries = evaluated[-streak:] if streak else []
    return {
        "threshold": threshold,
        "window": window,
        "min_periods": min_periods,
        "sessions": len(series),
        "evaluated_sessions": len(evaluated),
        "subthreshold_sessions": len(subthreshold),
        "streak_days": streak,
        "streak_start_date": streak_entries[0][0] if streak_entries else None,
        "streak_end_date": streak_entries[-1][0] if streak_entries else None,
        "last_date": evaluated[-1][0] if evaluated else None,
        "last_sharpe": evaluated[-1][1] if evaluated else None,
        "first_flag_date": subthreshold[0][0] if subthreshold else None,
        "series": series,
    }


def subthreshold_calendar_window(
    dates: Sequence[str],
    series: Sequence[tuple[str, float | None]],
    calendar_days: int = DEFAULT_CALENDAR_DAYS,
    threshold: float = DEFAULT_SHARPE_THRESHOLD,
) -> dict:
    """Sub-threshold session counts over a trailing calendar window.

    The streak answers "how long has the condition persisted"; this answers
    "how often has it been below threshold over the last N calendar days",
    which distinguishes a persistent regime from an oscillating one.
    """
    if len(dates) != len(series):
        raise ValueError(
            f"dates and series must have equal length ({len(dates)} != {len(series)})"
        )
    if not dates:
        return {
            "calendar_days": calendar_days,
            "window_start_date": None,
            "window_end_date": None,
            "sessions_in_window": 0,
            "subthreshold_sessions": 0,
        }
    end = date.fromisoformat(dates[-1])
    start = end - timedelta(days=calendar_days)
    in_window = [
        (d, v)
        for d, v in series
        if v is not None and start < date.fromisoformat(d) <= end
    ]
    return {
        "calendar_days": calendar_days,
        "window_start_date": start.strftime("%Y-%m-%d"),
        "window_end_date": end.strftime("%Y-%m-%d"),
        "sessions_in_window": len(in_window),
        "subthreshold_sessions": sum(1 for _d, v in in_window if v < threshold),
    }
