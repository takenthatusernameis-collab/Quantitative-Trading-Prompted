"""Offline tests for the Cycle 881 cost-admissibility screen.

No network access, no writes to ``data/`` or ``config/``: the tests exercise the
pure helpers of ``research/cost_admissibility_screen.py``, the mechanical
cost-drag guard (including the Cycle 880 factor-10 erratum), and one
integration path that rebuilds the ``overnight_capture_001`` candidate from
the committed cache and checks that the screen reproduces Cycle 880's
published numbers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import research.cost_admissibility_screen as screen  # noqa: E402


# ======================================================================
# Pure helpers
# ======================================================================
def _series(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.RangeIndex(len(values)), dtype=float)


def test_annual_turnover_units_uses_the_repository_convention() -> None:
    turnover = _series([2.0, 2.0, 2.0, 2.0])
    assert screen.annual_turnover_units(turnover) == pytest.approx(2.0 * 252.0)


def test_annualized_cost_drag_is_turnover_times_cost_per_unit() -> None:
    turnover = _series([2.0] * 10)
    drag = screen.annualized_cost_drag(turnover, 3.0)
    assert drag == pytest.approx(504.0 * 3.0 / 10000.0)
    assert drag == pytest.approx(0.1512, abs=1e-12)


def test_annualized_cost_drag_scales_linearly_with_the_cost_row() -> None:
    turnover = _series([1.0] * 5)
    base = screen.annualized_cost_drag(turnover, 3.0)
    assert screen.annualized_cost_drag(turnover, 5.0) == pytest.approx(base * 5.0 / 3.0)
    assert screen.annualized_cost_drag(turnover, 10.0) == pytest.approx(base * 10.0 / 3.0)


def test_net_return_series_subtracts_turnover_times_cost() -> None:
    gross = _series([0.01, -0.02, 0.0])
    turnover = _series([2.0, 2.0, 2.0])
    net = screen.net_return_series(gross, turnover, 3.0)
    pd.testing.assert_series_equal(
        net, gross - 2.0 * 3.0 / 10000.0, check_names=False
    )


def test_annualized_return_is_geometric() -> None:
    returns = _series([0.01, 0.01, 0.01, 0.01])
    expected = (1.01 ** 4) ** (252 / 4) - 1.0
    assert screen.annualized_return(returns) == pytest.approx(expected)


def test_solve_break_even_finds_a_monotone_crossing() -> None:
    # f(c) = 5 - c, root at c = 5
    result = screen.solve_break_even_cost_bps(lambda c: 5.0 - c, lo=0.0, hi=10.0)
    assert result["bracketed"] is True
    assert result["solution"] == pytest.approx(5.0, abs=1e-6)


def test_solve_break_even_reports_a_missing_root() -> None:
    result = screen.solve_break_even_cost_bps(lambda c: 1.0 + c, lo=0.0, hi=10.0)
    assert result["solution"] is None
    assert result["bracketed"] is False
    assert "does not change sign" in result["reason"]


def test_solve_break_even_finds_a_negative_root_as_a_rebate() -> None:
    # f(c) = -1 - 0.1c is decreasing and crosses zero at c = -10 (a rebate)
    result = screen.solve_break_even_cost_bps(lambda c: -1.0 - 0.1 * c, lo=-100.0, hi=10.0)
    assert result["bracketed"] is True
    assert result["solution"] == pytest.approx(-10.0, abs=1e-6)


# ======================================================================
# The mechanical guard (Cycle 880 erratum)
# ======================================================================
def test_guard_accepts_a_consistent_cost_drag() -> None:
    result = screen.check_cost_drag_consistency(0.1512, 504.0, 3.0)
    assert result["consistent"] is True
    assert result["expected_cost_drag"] == pytest.approx(0.1512, abs=1e-12)
    assert result["abs_diff"] <= 1e-9


def test_guard_rejects_the_cycle_880_factor_10_erratum() -> None:
    """The stated '1.51%/yr' that was really 15.12%/yr must not pass."""
    result = screen.check_cost_drag_consistency(0.0151, 504.0, 3.0)
    assert result["consistent"] is False
    assert result["abs_diff"] == pytest.approx(0.1361, abs=1e-9)
    assert result["abs_diff"] > 1e-9


def test_guard_rejects_a_factor_10_turnover_error_too() -> None:
    result = screen.check_cost_drag_consistency(0.1512, 50.4, 3.0)
    assert result["consistent"] is False


def test_guard_tolerance_is_one_part_in_a_billion() -> None:
    exact = screen.check_cost_drag_consistency(0.1512, 504.0, 3.0)
    assert exact["tolerance"] == 1e-9
    just_inside = screen.check_cost_drag_consistency(0.1512 + 1e-12, 504.0, 3.0)
    assert just_inside["consistent"] is True
    just_outside = screen.check_cost_drag_consistency(0.1512 + 1e-6, 504.0, 3.0)
    assert just_outside["consistent"] is False


def test_require_guard_raises_on_an_inconsistent_figure() -> None:
    with pytest.raises(ValueError):
        screen.require_cost_drag_consistency(0.0151, 504.0, 3.0)
    # the consistent figure passes
    screen.require_cost_drag_consistency(0.1512, 504.0, 3.0)


def test_guard_rejects_the_erratum_at_every_cost_row() -> None:
    for bps in screen.COST_ROWS_BPS:
        expected = 504.0 * bps / 10000.0
        wrong = expected / 10.0
        assert screen.check_cost_drag_consistency(wrong, 504.0, bps)["consistent"] is False
        assert screen.check_cost_drag_consistency(expected, 504.0, bps)["consistent"] is True


# ======================================================================
# Integration: the screen reproduces Cycle 880 from the committed cache
# ======================================================================
@pytest.fixture(scope="module")
def overnight_screen() -> dict:
    cand = screen.build_overnight_candidate()
    return screen.screen_candidate(cand)


def test_overnight_screen_reproduces_the_published_cost_drag(overnight_screen) -> None:
    drag = overnight_screen["cost_drag"][3.0]
    assert drag == pytest.approx(0.1512, abs=1e-9)
    assert overnight_screen["annual_turnover_units"] == pytest.approx(504.0)
    assert overnight_screen["gross_annualized_signal"] == pytest.approx(0.0916, abs=1e-3)


def test_overnight_screen_reproduces_the_published_walk_forward_sharpe(
    overnight_screen,
) -> None:
    assert overnight_screen["wf_mean_oos_sharpe"] == pytest.approx(-0.599718, abs=1e-6)
    assert overnight_screen["benchmark_wf_mean_oos_sharpe"] == pytest.approx(
        0.844696, abs=1e-6
    )
    assert overnight_screen["wf_positive_fold_rate"] == pytest.approx(0.151515, abs=1e-6)
    assert overnight_screen["wf_pooled_trades"] == 8016


def test_overnight_candidate_is_inadmissible_at_the_repository_cost_model(
    overnight_screen,
) -> None:
    assert overnight_screen["admissibility_verdict"] == "INADMISSIBLE"
    assert overnight_screen["net_annualized_return"][3.0] < 0.0
    # its break-even cost is below the 3 bp/unit the model charges
    assert overnight_screen["break_even_cost"]["solution"] < 3.0
    assert overnight_screen["min_gross_signal_required"] == pytest.approx(
        overnight_screen["cost_drag"][3.0]
    )


def test_screen_does_not_write_under_data_or_config() -> None:
    roots = [REPO_ROOT / "data", REPO_ROOT / "config"]
    before = screen.directory_fingerprint(roots)
    assert before, "expected files under data/ and config/"
    screen.build_overnight_candidate()
    screen.build_calendar_candidate()
    screen.build_incumbent_candidate()
    after = screen.directory_fingerprint(roots)
    assert before == after


def test_calendar_candidate_rebuilds_its_committed_artifacts_exactly() -> None:
    result = screen.verify_calendar_against_committed()
    assert result["weights_max_abs_diff"] == 0.0
    assert result["gross_max_abs_diff"] == 0.0
    assert result["turnover_max_abs_diff"] == 0.0


def test_incumbent_committed_artifact_is_internally_consistent() -> None:
    result = screen.verify_incumbent_artifact()
    assert result["cost_max_abs_diff"] == 0.0
    assert result["net_max_abs_diff"] <= 1e-12
    assert result["weight_max_abs_diff"] <= 1e-12


def test_overnight_session_leg_decomposition_is_exact() -> None:
    result = screen.verify_overnight_leg_identity()
    assert result["max_abs_error"] < 1e-12
    assert result["missing_opens"] == 0
    assert result["sessions"] == 6637


# ======================================================================
# The published report
# ======================================================================
def test_report_exists_and_publishes_the_required_quantities() -> None:
    report = screen.REPORT_MD
    assert report.exists(), "run research/cost_admissibility_screen.py first"
    text = report.read_text()
    for needle in (
        "Annualized gross signal",
        "Annualized cost drag",
        "Break-even cost per unit",
        "Minimum gross signal required for admissibility",
        "Admissibility verdict",
        "necessary, not sufficient",
        "0.1512",
        "-0.599718",
        "checks passed",
    ):
        assert needle in text, needle
    assert "OVERALL: PASS" in text
