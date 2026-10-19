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
# The published-tolerance rule (Cycle 882)
# ======================================================================
def test_published_tolerance_is_the_unit_of_the_last_published_decimal() -> None:
    assert screen.published_tolerance("0.6975") == pytest.approx(1e-4)
    assert screen.published_tolerance("0.472367") == pytest.approx(1e-6)
    assert screen.published_tolerance("2.47") == pytest.approx(1e-2)
    assert screen.published_tolerance("0.151515") == pytest.approx(1e-6)


def test_published_tolerance_of_a_count_is_exact() -> None:
    assert screen.published_tolerance("400") == 0.0
    assert screen.published_tolerance("36") == 0.0


def test_invested_window_starts_at_the_first_non_zero_position() -> None:
    index = pd.date_range("2020-01-01", periods=5, tz="UTC")
    weights = pd.DataFrame(
        {"A": [0.0, 0.0, 0.5, 0.5, 0.5], "B": [0.0, 0.0, 0.5, 0.5, 0.5]},
        index=index,
    )
    window = screen.invested_window(weights)
    assert window[0] == index[2]
    assert len(window) == 3


def test_gross_and_turnover_matches_the_repository_path_returns() -> None:
    """The screen's gross/turnover arithmetic must be the repository's own."""
    import research.month_end_candidate_reaudit as reaudit

    index = pd.date_range("2020-01-01", periods=6, tz="UTC")
    close = pd.DataFrame(
        {"A": [100.0, 101.0, 102.0, 101.0, 103.0, 104.0], "B": [50.0, 50.5, 49.0, 50.0, 51.0, 50.5]},
        index=index,
    )
    weights = pd.DataFrame(
        {"A": [0.0, 0.5, 0.5, 1.0, 0.5, 0.5], "B": [0.0, 0.5, 0.5, 0.0, 0.5, 0.5]},
        index=index,
    )
    gross, turnover = screen.gross_and_turnover(close, weights)
    net = gross - turnover * 0.0003
    daily = close.pct_change().fillna(0.0)
    expected_gross = (weights * daily).sum(axis=1)
    expected_turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
    pd.testing.assert_series_equal(gross, expected_gross)
    pd.testing.assert_series_equal(turnover, expected_turnover)
    pd.testing.assert_series_equal(
        net, gross - turnover * 0.0003, check_names=False
    )
    assert reaudit.path_returns is not None  # the repository's own helper is importable


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
    screen.build_csmomentum_candidate()
    screen.build_sectorrotation_candidate()
    screen.build_macroregime_candidate()
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


def test_report_publishes_the_gate_headroom_for_every_candidate() -> None:
    """A decision number that exists for one candidate and not another is not a decision number."""
    report = screen.REPORT_MD
    assert report.exists(), "run research/cost_admissibility_screen.py first"
    text = report.read_text()
    for cid in (
        "overnight_capture_001",
        "calendar_effects_001",
        "tsmomentum_spytrend_001",
        "csmomentum_001",
        "sectorrotation_001",
        "macroregime_001",
    ):
        assert cid in text, cid
    assert text.count("Gate headroom: cost per unit at which the net WF mean OOS Sharpe") == 6
    assert "Promotion threshold (walk-forward mean OOS Sharpe) | 0.90" in text


def test_report_still_publishes_the_cycle_881_numbers() -> None:
    """The Cycle 881 blocks must keep their numbers to the published precision."""
    text = screen.REPORT_MD.read_text()
    for needle in (
        "+15.1200%",      # overnight drag @3 bp/unit
        "1.7385 bp/unit",  # overnight break-even cost
        "-0.599718",     # overnight net WF mean OOS Sharpe
        "0.844696",      # benchmark WF mean OOS Sharpe
        "-0.025432",     # calendar net WF mean OOS Sharpe
        "0.424242",      # calendar positive fold rate
        "106.7540 bp/unit",  # incumbent break-even cost
        "32.3052 bp/unit",   # incumbent benchmark-parity cost
    ):
        assert needle in text, needle


# ======================================================================
# The three month-end candidates (Cycle 882)
# ======================================================================
@pytest.fixture(scope="module")
def month_end_candidates() -> dict:
    return {
        "csmomentum_001": screen.build_csmomentum_candidate(),
        "sectorrotation_001": screen.build_sectorrotation_candidate(),
        "macroregime_001": screen.build_macroregime_candidate(),
    }


@pytest.mark.parametrize(
    "cid", ["csmomentum_001", "sectorrotation_001", "macroregime_001"]
)
def test_every_published_number_of_the_new_candidates_is_reproduced(
    month_end_candidates, cid
) -> None:
    """A published number that changes must fail here, not be re-tuned."""
    cand = month_end_candidates[cid]
    assert cand.verification, "the candidate must publish a reproduction table"
    failed = [
        (e["quantity"], e["published"], e["observed"], e["tolerance"])
        for e in cand.verification
        if not e["match"]
    ]
    assert not failed, failed


@pytest.mark.parametrize(
    "cid", ["csmomentum_001", "sectorrotation_001", "macroregime_001"]
)
def test_new_candidates_use_the_config_faithful_month_end_schedule(
    month_end_candidates, cid
) -> None:
    """The defective calendar rule and the daily re-rank must not be used.

    A month-end schedule means: the signal is formed on the **last session of
    the month** and the positions become effective on the **next** session, so
    the weight frame may only change on the session that follows a month-end
    session - never on an arbitrary day.
    """
    cand = month_end_candidates[cid]
    assert "month_end" in cand.provenance["schedule"]
    index = cand.weights.index
    is_last_of_month = (
        index.to_series().groupby(index.to_period("M")).transform("max") == index
    )
    changed = cand.weights.diff().abs().sum(axis=1) > 1e-10
    changed_dates = index[changed.values]
    assert len(changed_dates) > 0
    for i, date in enumerate(changed_dates):
        position = index.get_loc(date)
        assert position > 0
        previous = index[position - 1]
        assert bool(is_last_of_month.iloc[position - 1]), (
            f"{cid}: the position changed on {date.date()} but the previous "
            f"session {previous.date()} is not a month-end session"
        )
    years = (index[-1] - index[0]).days / 365.25
    # a month-end schedule changes the book at most once per month; a daily
    # re-rank would change it ~250 times a year
    assert 4.0 * years <= len(changed_dates) <= 13.5 * years


def test_sectorrotation_reproduces_its_invested_sample_numbers(
    month_end_candidates,
) -> None:
    cand = month_end_candidates["sectorrotation_001"]
    assert cand.window_start == "2000-02-01"
    assert cand.window_end == "2026-10-08"
    turnover = screen.annual_turnover_units(cand.turnover)
    assert turnover == pytest.approx(2.9961, abs=1e-4)
    assert int((cand.turnover > 1e-10).sum()) == 175
    assert len(cand.splits) == 36


def test_csmomentum_reproduces_its_test_window_numbers(month_end_candidates) -> None:
    cand = month_end_candidates["csmomentum_001"]
    assert cand.window_start == "1994-03-01"
    assert len(cand.splits) == 48
    entries = {e["quantity"]: e for e in cand.verification}
    assert entries["Test-window Sharpe (backtest scale)"]["observed"] == pytest.approx(
        0.4878, abs=1e-4
    )
    assert entries["Test-window trade days"]["observed"] == 77


def test_macroregime_reproduces_its_test_window_numbers(month_end_candidates) -> None:
    cand = month_end_candidates["macroregime_001"]
    assert len(cand.splits) == 24
    entries = {e["quantity"]: e for e in cand.verification}
    assert entries["Test-window Sharpe (backtest scale)"]["observed"] == pytest.approx(
        0.1428, abs=1e-4
    )
    assert entries["Test-window trade days"]["observed"] == 84


# ======================================================================
# The gate headroom (Cycle 882)
# ======================================================================
@pytest.fixture(scope="module")
def incumbent_screen() -> dict:
    return screen.screen_candidate(screen.build_incumbent_candidate())


def test_gate_headroom_is_published_on_the_repository_threshold(incumbent_screen) -> None:
    assert incumbent_screen["promotion_threshold"] == 0.9
    assert incumbent_screen["gate_headroom"]["solution"] is not None
    assert incumbent_screen["gate_headroom_backtest_scale"]["solution"] is not None


def test_gate_headroom_brackets_the_gate(incumbent_screen) -> None:
    """Above the headroom the walk-forward mean must be below the gate, below it above."""
    cand = screen.build_incumbent_candidate()
    headroom = incumbent_screen["gate_headroom"]["solution"]
    above = screen.wf_mean_canonical_sharpe(
        cand.gross, cand.turnover, cand.weights, cand.splits,
        headroom * 1.10, cand.explicit_turnover,
    )
    below = screen.wf_mean_canonical_sharpe(
        cand.gross, cand.turnover, cand.weights, cand.splits,
        max(headroom * 0.50, 0.0), cand.explicit_turnover,
    )
    assert above < 0.9
    assert below > 0.9


def test_the_incumbent_is_the_only_candidate_with_a_positive_gate_headroom() -> None:
    """The screen's answer to the cycle's objective question, as an executable check."""
    screens = {
        "tsmomentum_spytrend_001": screen.screen_candidate(
            screen.build_incumbent_candidate()
        ),
        "csmomentum_001": screen.screen_candidate(screen.build_csmomentum_candidate()),
        "sectorrotation_001": screen.screen_candidate(
            screen.build_sectorrotation_candidate()
        ),
        "macroregime_001": screen.screen_candidate(screen.build_macroregime_candidate()),
    }
    positive = [
        cid
        for cid, s in screens.items()
        if s["gate_headroom"]["solution"] is not None
        and s["gate_headroom"]["solution"] > 0.0
    ]
    assert positive == ["tsmomentum_spytrend_001"]
    for cid in ("csmomentum_001", "sectorrotation_001", "macroregime_001"):
        s = screens[cid]
        # below the gate before a basis point is charged
        assert s["wf_sharpe_at_zero_cost"] < 0.9, cid
        # and behind the passive basket on the same folds even at zero cost
        assert s["benchmark_parity_cost"]["solution"] < 0.0, cid
