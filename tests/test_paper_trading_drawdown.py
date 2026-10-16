"""Regression test for running-maximum drawdown tracking in paper trading.

The paper-trading engine must report the *running-maximum* drawdown: the
deepest trough observed relative to the highest NAV *seen up to that point*.
A prior implementation reset the running max to the current NAV each day,
which silently understated drawdown whenever the portfolio recovered and then
fell again (the running max is the all-time peak, not the recent peak).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.utils import compute_running_drawdown


def test_running_max_drawdown_is_anchored_to_all_time_peak() -> None:
    # NAV path: 100 -> 110 (new peak) -> 100 (dd -9.1%) -> 105 -> 95
    # The all-time peak is 110, so the 95 trough is a -13.6% drawdown from
    # the running max, NOT a -9.5% drawdown from the recent 105 peak.
    peak = 100.0
    prev_max_dd = 0.0

    peak, prev_max_dd = compute_running_drawdown(peak, 110.0, prev_max_dd)
    assert peak == 110.0 and prev_max_dd == 0.0

    peak, prev_max_dd = compute_running_drawdown(peak, 100.0, prev_max_dd)
    assert peak == 110.0
    assert abs(prev_max_dd - (100.0 / 110.0 - 1.0)) < 1e-12  # -0.090909...

    peak, prev_max_dd = compute_running_drawdown(peak, 105.0, prev_max_dd)
    assert peak == 110.0 and abs(prev_max_dd - (100.0 / 110.0 - 1.0)) < 1e-12

    # Recovery to 95 must measure against the 110 all-time peak.
    peak, prev_max_dd = compute_running_drawdown(peak, 95.0, prev_max_dd)
    assert peak == 110.0
    assert abs(prev_max_dd - (95.0 / 110.0 - 1.0)) < 1e-12  # -0.136363...


def test_running_max_drawdown_is_monotonic_in_depth() -> None:
    # A deeper later trough must widen (not reset) the tracked drawdown.
    peak, prev_max_dd = 100.0, 0.0
    peak, prev_max_dd = compute_running_drawdown(peak, 90.0, prev_max_dd)
    peak, prev_max_dd = compute_running_drawdown(peak, 95.0, prev_max_dd)
    peak, prev_max_dd = compute_running_drawdown(peak, 80.0, prev_max_dd)
    assert abs(prev_max_dd - (80.0 / 100.0 - 1.0)) < 1e-12  # -0.20


def test_running_max_drawdown_is_monotonic_and_never_resets() -> None:
    # The running max drawdown is the *minimum* drawdown over all history,
    # so it is monotonic and never resets at a new all-time high. The
    # *current* drawdown at a new high is 0, but the running max keeps the
    # deepest trough ever seen.
    peak, prev_max_dd = 100.0, -0.10
    peak, running_max_dd = compute_running_drawdown(peak, 120.0, prev_max_dd)
    assert peak == 120.0
    assert running_max_dd == -0.10  # running max unchanged (monotonic)