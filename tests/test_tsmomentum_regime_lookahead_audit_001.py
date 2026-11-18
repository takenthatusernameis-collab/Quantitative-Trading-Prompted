"""Regression tests for the regime-filter same-session look-ahead audit.

``research/tsmomentum_regime_lookahead_audit_001.py`` quantifies one specific
measurement defect: the SPY 200-session SMA regime factor for session *t* is
built from session *t*'s own close and then gates the position that earns
session *t*'s close-to-close return.  These tests pin the invariants that make
the audit's evidence trustworthy:

* the "committed" exposure rule is reproduced bit-for-bit from a synthetic
  price panel (cash when the close is below its own trailing mean, including
  the current session),
* the point-in-time variant is exactly a one-session shift of that rule, so the
  only difference between the two audit arms is the regime factor,
* the audit's read-only guard digests a tree deterministically and detects any
  content change,
* the published walk-forward anchor the audit fails closed on is unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.tsmomentum_regime_lookahead_audit_001 as audit


def _panel(close_values: list[float]) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(close_values), freq="B", tz="UTC")
    return pd.DataFrame({"SPY": close_values}, index=index)


def test_committed_exposure_uses_the_current_session_close():
    # Session 3 closes below the trailing 3-session mean of sessions 1..3,
    # so the committed rule must hold cash on session 3 itself.
    panel = _panel([100.0, 101.0, 102.0, 90.0, 105.0])
    exposure = audit.exposure_committed(panel, window=3)
    assert exposure.iloc[3] == 0.0
    # Sessions with insufficient history are cash by construction.
    assert list(exposure.iloc[:2]) == [0.0, 0.0]
    # Session 4 closes above its trailing mean -> full exposure.
    assert exposure.iloc[4] == 1.0


def test_point_in_time_exposure_is_exactly_a_one_session_shift():
    values = [100.0 + 5.0 * np.sin(i / 3.0) for i in range(60)]
    values[40] = 10.0  # a crash session the same-session rule can dodge
    panel = _panel(values)

    committed = audit.exposure_committed(panel, window=5)
    pit = audit.exposure_point_in_time(panel, window=5)

    pd.testing.assert_series_equal(pit, committed.shift(1).fillna(0.0))
    # The crash session is cash under the same-session rule but only becomes
    # cash one session later under the point-in-time rule.
    assert committed.iloc[40] == 0.0
    assert pit.iloc[40] == committed.iloc[39]
    assert pit.iloc[41] == 0.0


def test_point_in_time_exposure_never_uses_the_current_session_close():
    values = [100.0 + 4.0 * np.cos(i / 2.0) for i in range(40)]
    panel = _panel(values)
    baseline = audit.exposure_point_in_time(panel, window=5)

    # Replacing the last close with an extreme value must not change the
    # exposure applied on that session.
    mutated = panel.copy()
    mutated.iloc[-1, 0] = 1.0
    changed = audit.exposure_point_in_time(mutated, window=5)

    assert baseline.iloc[-1] == changed.iloc[-1]


def test_tree_digest_is_deterministic_and_content_sensitive(tmp_path):
    (tmp_path / "a.txt").write_text("alpha")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "b.bin").write_bytes(b"\x00\x01")

    first = audit.tree_digest(tmp_path)
    assert first == audit.tree_digest(tmp_path)

    (tmp_path / "nested" / "b.bin").write_bytes(b"\x00\x02")
    assert audit.tree_digest(tmp_path) != first


def test_published_anchor_constant_is_unchanged():
    assert audit.ANCHOR_WF_SHARPE == pytest.approx(0.947307)
