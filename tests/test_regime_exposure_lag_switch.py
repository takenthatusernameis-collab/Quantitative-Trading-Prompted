"""Regression tests for the opt-in SPY-SMA regime exposure lag switch.

``SimulationConfig.lag_regime_exposure`` exists to separate the committed
(same-session) regime rule from the point-in-time rule.  The default path must
stay bit-for-bit identical to the committed behaviour, and the lagged path must
be exactly the committed rule shifted one session.  These tests pin that
invariant on synthetic panels and assert that no shipped configuration enables
the switch.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.tsmomentum_regime_lookahead_audit_001 as audit
from src.simulation.engine import SimulationConfig, _regime_exposure


def _panel(n: int = 80) -> pd.DataFrame:
    values = [100.0 + 5.0 * np.sin(i / 3.0) for i in range(n)]
    values[n // 2] = 10.0
    index = pd.date_range("2024-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({"SPY": values}, index=index)


def test_default_switch_is_off():
    assert SimulationConfig().lag_regime_exposure is False


def test_default_exposure_is_same_session_rule():
    close = _panel()
    cfg = SimulationConfig(regime_window=5)
    exposure = _regime_exposure(close, cfg)
    expected = audit.exposure_committed(close, window=5)
    pd.testing.assert_series_equal(exposure, expected)


def test_lagged_exposure_is_one_session_shift():
    close = _panel()
    cfg = SimulationConfig(regime_window=5, lag_regime_exposure=True)
    exposure = _regime_exposure(close, cfg)
    committed = audit.exposure_committed(close, window=5)
    pd.testing.assert_series_equal(
        exposure, committed.shift(1).fillna(cfg.exposure_below)
    )


def test_switch_changes_the_crash_session_exposure():
    close = _panel()
    default = _regime_exposure(close, SimulationConfig(regime_window=5))
    lagged = _regime_exposure(
        close, SimulationConfig(regime_window=5, lag_regime_exposure=True)
    )
    crash_idx = close.index[close["SPY"].argmin()]
    assert default.loc[crash_idx] == 0.0
    assert lagged.loc[crash_idx] == 1.0
    assert not default.equals(lagged)


def test_no_shipped_config_enables_the_lag_switch():
    offenders = []
    for path in sorted((ROOT / "config").glob("*.y*ml")):
        content = yaml.safe_load(path.read_text()) or {}
        regime = content.get("regime_filter") or {}
        if regime.get("lag_regime_exposure", False):
            offenders.append(path.name)
    assert offenders == []
