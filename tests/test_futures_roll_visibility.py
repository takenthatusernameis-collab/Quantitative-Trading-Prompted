"""Offline tests for the Cycle 884 roll-visibility diagnostic.

No network access and no writes to ``data/`` or ``config/``: the tests
exercise the pure helpers of ``research/futures_roll_visibility.py`` and one
integration path that reads the committed futures caches and checks that the
externally verified 2026-09 roll is detected and that each product's modal
roll spacing reproduces its contract cycle.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import research.futures_roll_visibility as frv  # noqa: E402


def _ratio(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.bdate_range("2024-01-01", periods=len(values)))


# ======================================================================
# Pure helpers
# ======================================================================
def test_volume_ratio_is_point_in_time() -> None:
    """A session's own volume must not enter its own ratio."""
    volume = pd.Series([100.0] * 30 + [10_000.0])
    ratio = frv.volume_ratio(volume)
    # the last session's ratio uses the preceding 30 sessions only
    assert ratio.iloc[-1] == pytest.approx(10_000.0 / 100.0, rel=1e-9)
    # and the spike does not change the ratio of the previous session
    assert ratio.iloc[-2] == pytest.approx(1.0, rel=1e-9)


def test_volume_ratio_ignores_non_finite_medians() -> None:
    volume = pd.Series([float("nan")] * 5 + [100.0] * 40)
    ratio = frv.volume_ratio(volume)
    assert np.isnan(ratio.iloc[0])
    assert ratio.iloc[-1] == pytest.approx(1.0, rel=1e-9)


def test_detect_roll_events_finds_run_off_then_recovery() -> None:
    """A run-off followed by a recovery yields one event; the roll is next."""
    ratio = _ratio([1.0] * 10 + [0.4, 0.3, 1.5] + [1.1] * 6)
    events = frv.detect_roll_events(ratio)
    assert len(events) == 1
    row = events.iloc[0]
    assert row["trough_ratio"] == pytest.approx(0.3)
    assert row["recovery_ratio"] == pytest.approx(1.5)
    # the expiry session is the recovery session, the roll the session after
    assert row["expiry_date"] == ratio.index[12]
    assert row["roll_date"] == ratio.index[13]


def test_detect_roll_events_ignores_a_quiet_series() -> None:
    ratio = _ratio([1.0] * 30)
    assert frv.detect_roll_events(ratio).empty


def test_detect_roll_events_requires_the_volume_to_stay_recovered() -> None:
    """A transient spike that immediately collapses is not an expiry session.

    The run-off's local minimum is the 0.2 session, and the detector waits
    for the *sustained* recovery (1.1) instead of taking the transient 1.5
    spike, whose very next session collapses.
    """
    ratio = _ratio([1.0] * 10 + [0.4, 0.3, 1.5, 0.2] + [1.1] * 6)
    events = frv.detect_roll_events(ratio)
    assert len(events) == 1
    row = events.iloc[0]
    assert row["trough_ratio"] == pytest.approx(0.2)
    assert row["recovery_ratio"] == pytest.approx(1.1)
    assert row["expiry_date"] == ratio.index[14]
    assert row["roll_date"] == ratio.index[15]


def test_event_spacings_and_cycle_consistency() -> None:
    events = pd.DataFrame(
        {
            "roll_date": pd.to_datetime(["2024-01-10", "2024-02-09", "2024-04-08"]),
            "expiry_date": pd.to_datetime(["2024-01-09", "2024-02-08", "2024-04-07"]),
        }
    )
    spacings = frv.event_spacings(events)
    assert list(spacings) == [30.0, 59.0]
    assert frv.cycle_consistency(spacings, (25, 35)) == pytest.approx(0.5)
    assert frv.cycle_consistency(spacings, (80, 100)) == pytest.approx(0.0)
    assert frv.modal_spacing(spacings) == (30, 1)


def test_annualized_roll_count() -> None:
    """Twelve monthly events are annualized over the first-to-last span."""
    events = pd.DataFrame(
        {
            "roll_date": pd.to_datetime(
                [f"2024-{month:02d}-10" for month in range(1, 13)]
            )
        }
    )
    days = (events["roll_date"].iloc[-1] - events["roll_date"].iloc[0]).days
    assert days == 335
    assert frv.annualized_roll_count(events) == pytest.approx(
        12 * 365.25 / 335, rel=1e-9
    )


def test_block_bootstrap_is_deterministic() -> None:
    values = np.random.default_rng(7).normal(0.0, 0.004, 1200)
    a = frv.block_bootstrap_annualized_gap(values)
    b = frv.block_bootstrap_annualized_gap(values)
    assert a == b
    assert a["draws"] == frv.BOOTSTRAP_DRAWS
    assert a["ci_low"] <= a["mean"] <= a["ci_high"]


def test_block_bootstrap_refuses_a_short_series() -> None:
    out = frv.block_bootstrap_annualized_gap(np.zeros(10))
    assert out["draws"] == 0
    assert np.isnan(out["ci_low"])


def test_aggregate_roll_effect_uses_the_cached_spot_proxy() -> None:
    """The gold leg's aggregate roll effect is measurable but not significant."""
    result = frv.measure_aggregate_roll_effect("GC-F", "GLD")
    assert result["proxy_symbol"] == "GLD"
    assert result["sessions"] > 2500
    assert np.isfinite(result["annualized_gap"])
    boot = result["bootstrap"]
    assert boot["ci_low"] <= result["annualized_gap"] <= boot["ci_high"]
    # the interval contains zero: the effect is not distinguishable from zero
    assert result["distinguishable_from_zero"] is False


# ======================================================================
# Integration against the committed cache
# ======================================================================
def test_committed_cache_reproduces_the_verified_roll() -> None:
    """The externally verified 2026-09 roll must be found in the cache."""
    summary = frv.summarize_series(frv.GROUND_TRUTH_SYMBOL)
    check = frv.ground_truth_check(summary)
    assert check["applicable"] is True
    assert check["expiry_detected"] is True
    assert check["roll_detected"] is True
    assert check["pass"] is True


@pytest.mark.parametrize("symbol", frv.FUTURES_SYMBOLS)
def test_modal_spacing_reproduces_the_contract_cycle(symbol: str) -> None:
    summary = frv.summarize_series(symbol)
    low, high = frv.CYCLE_WINDOW_DAYS[symbol]
    assert len(summary.events) >= frv.MIN_EVENTS_PER_SERIES
    assert low <= summary.modal_days <= high
    assert summary.modal_count >= 3


def test_diagnostic_does_not_touch_data_or_config() -> None:
    before = frv.directory_fingerprint([REPO_ROOT / "data", REPO_ROOT / "config"])
    for symbol in frv.FUTURES_SYMBOLS:
        frv.summarize_series(symbol)
    after = frv.directory_fingerprint([REPO_ROOT / "data", REPO_ROOT / "config"])
    assert before == after
