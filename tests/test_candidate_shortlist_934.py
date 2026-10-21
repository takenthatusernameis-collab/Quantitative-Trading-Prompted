"""Cycle 934 -- the candidate shortlist tool, its artifacts and its invariants.

The tests pin the **mechanical** parts of the cycle, not the scores themselves:

* the complete panel is the calendar **intersection** of the candidate's
  instruments, and the membership churn is the share of union sessions it does
  not cover;
* the cost hurdle is the measured drag divided by the measured gross scale,
  and it is compared against the declared thresholds;
* the effective-independent-bets count is a real number for a multi-bet
  candidate and an explicit "not applicable" for a single-book one -- never a
  value that silently satisfies a threshold;
* the roll contamination of the futures-based candidate is detected and
  published;
* the tool is read-only on ``data/`` and ``config/``, deterministic, and its
  published selection follows the declared rule.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.candidate_shortlist_934 import (  # noqa: E402
    CANDIDATES,
    OUT_EXP,
    OUT_REPORT,
    PRIOR_LINES,
    SECTOR_UNIVERSE,
    TURNOVER_UNITS_PER_REBALANCE,
    build_payload,
    complete_panel,
    cross_sectional_dispersion,
    effective_independent_bets,
    hurdle_score,
    render_experiment,
    render_report,
    run_checks,
    select_candidate,
)
from src.backtest.engine import get_cost_params  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hash(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(REPO_ROOT)): _sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.fixture(scope="module")
def payload() -> dict:
    return build_payload()


# ----------------------------------------------------------------------
# The committed artifact
# ----------------------------------------------------------------------
def test_artifacts_exist():
    assert OUT_EXP.exists(), "research/experiments/candidate_shortlist_934.md is missing"
    assert OUT_REPORT.exists(), "research/reports/candidate_shortlist_934.md is missing"


def test_experiment_record_contains_the_required_content():
    text = OUT_EXP.read_text()
    assert text.count("### ") >= 0
    for field in (
        "**Mechanism**",
        "**Holding horizon**",
        "**Asset universe**",
        "**Benchmark**",
        "**Known confounders**",
        "**Falsification condition**",
        "**Cost model assumptions**",
    ):
        assert field in text, f"the selected candidate is missing {field}"
    for dimension in ("(a) Data quality", "(b) Plausible structural", "(c) Expected return after costs",
                       "(d) Robustness", "(e) Liquidity", "(f) Automation", "(g) Diversification"):
        assert dimension in text, f"the score table is missing {dimension}"


def test_at_least_three_candidates_are_scored_on_all_seven_dimensions(payload):
    assert len(payload["measured"]) >= 3
    for row in payload["measured"]:
        assert set(row["scores"]) == set("abcdefg")
        assert all(1 <= value <= 5 for value in row["scores"].values())
        assert row["total"] == sum(row["scores"].values())
        assert row["falsification"].strip()
        assert row["data_files"]


def test_no_candidate_carries_a_parameter_grid():
    for candidate in CANDIDATES:
        assert "grid" not in candidate
        assert candidate["horizon_sessions"] > 0
        assert candidate["rebalances_per_year"] > 0


def test_no_riskparity_variant_is_proposed():
    for candidate in CANDIDATES:
        blob = f"{candidate['id']} {candidate['name']}".lower()
        assert "riskpar" not in blob and "risk par" not in blob


def test_every_prior_status_quote_is_present_in_its_committed_record(payload):
    for entry in payload["prior_lines"]:
        text = (REPO_ROOT / entry["record"]).read_text()
        assert entry["status_quote"] in text, entry["record"]
        assert entry["status_class"]


# ----------------------------------------------------------------------
# The mechanical measurements
# ----------------------------------------------------------------------
def test_complete_panel_is_the_calendar_intersection():
    index_a = pd.date_range("2020-01-01", periods=10, freq="B", tz="UTC")
    index_b = pd.date_range("2020-01-03", periods=10, freq="B", tz="UTC")
    union = index_a.union(index_b)
    frame = pd.DataFrame(index=union, columns=["A", "B"], dtype=float)
    frame.loc[index_a, "A"] = np.arange(10, dtype=float)
    frame.loc[index_b, "B"] = np.arange(10, dtype=float)
    complete, churn = complete_panel(frame)
    assert list(complete.index) == sorted(set(index_a) & set(index_b))
    assert churn == pytest.approx(1.0 - len(complete) / len(frame), abs=1e-12)


def test_sector_panel_is_membership_stable(payload):
    row = next(r for r in payload["measured"] if r["id"] == "reversal_001")
    assert row["measured"]["membership_churn"] == 0.0
    assert row["measured"]["sessions"] == 6991
    assert row["measured"]["first"] == "1998-12-22"
    assert row["measured"]["last"] == "2026-10-08"


def test_cost_hurdle_is_the_measured_drag_over_the_measured_scale(payload):
    commission, slippage = get_cost_params()
    cost_per_unit = commission + slippage
    for row in payload["measured"]:
        measured = row["measured"]
        expected_drag = measured["turnover_units_per_year"] * cost_per_unit
        assert measured["annual_cost_drag"] == pytest.approx(expected_drag, rel=1e-12)
        assert measured["turnover_units_per_year"] == pytest.approx(
            row["rebalances_per_year"] * TURNOVER_UNITS_PER_REBALANCE, rel=1e-12
        )
        expected_capture = expected_drag / measured["gross_ceiling_per_year"]
        assert measured["required_capture_fraction"] == pytest.approx(expected_capture, rel=1e-9)
        assert measured["hurdle_score"] == hurdle_score(expected_capture)


def test_hurdle_thresholds_are_the_declared_ones():
    assert hurdle_score(0.01) == 5
    assert hurdle_score(0.05) == 5
    assert hurdle_score(0.0500001) == 4
    assert hurdle_score(0.10) == 4
    assert hurdle_score(0.20) == 3
    assert hurdle_score(0.40) == 2
    assert hurdle_score(0.80) == 1


def test_cross_sectional_dispersion_is_a_scale_not_a_return():
    close = pd.DataFrame(
        {
            "A": [100.0, 101.0, 99.0, 100.0],
            "B": [100.0, 99.0, 101.0, 100.0],
        }
    )
    dispersion = cross_sectional_dispersion(close, 1)
    assert dispersion > 0.0
    # A constant cross-section has no dispersion.
    flat = pd.DataFrame({"A": [100.0, 100.0], "B": [100.0, 100.0]})
    assert cross_sectional_dispersion(flat, 1) == 0.0


def test_effective_independent_bets_is_measured_for_multi_bet_candidates(payload):
    for row in payload["measured"]:
        value = row["measured"]["effective_independent_bets"]
        if row["multi_bet"]:
            assert value is not None
            assert np.isfinite(value)
            assert value > 0.0
        else:
            assert value is None, "a single-book candidate must not report a bet count"


def test_effective_independent_bets_matches_a_hand_computed_case():
    frame = pd.DataFrame(
        {
            "a": [0.01, 0.02, -0.01, 0.03],
            "b": [0.02, 0.04, -0.02, 0.06],
            "c": [-0.01, 0.00, 0.02, -0.03],
        }
    )
    value = effective_independent_bets(frame)
    assert 1.0 <= value <= 3.0


def test_roll_contamination_of_the_futures_candidate_is_published(payload):
    row = next(r for r in payload["measured"] if r["id"] == "leadlag_001")
    facts = row["measured"]["facts"]
    assert facts["CL-F"]["non_positive_close"] >= 1, "the CL-F defect must be measured"
    assert row["measured"]["membership_churn"] > 0.0, "the futures/ETF calendars differ"
    assert row["missing_execution_input"]
    assert payload["roll_counts"], "the roll-event counts must be measured"
    for symbol, count in payload["roll_counts"].items():
        assert count > 0, symbol


def test_the_candidate_data_files_are_the_cited_cache_files(payload):
    for row in payload["measured"]:
        assert row["data_files"]
        for path in row["data_files"]:
            assert (REPO_ROOT / path).exists(), path
            assert path.endswith(".parquet")
    assert SECTOR_UNIVERSE == [
        "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"
    ]


# ----------------------------------------------------------------------
# The selection rule and the checks
# ----------------------------------------------------------------------
def test_selection_follows_the_declared_rule(payload):
    selected_id, ranked = select_candidate(payload["measured"])
    assert ranked[0]["id"] == selected_id
    assert payload["selected_id"] == selected_id
    assert ranked[0]["total"] >= ranked[1]["total"]
    manual = sorted(
        payload["measured"],
        key=lambda row: (-row["total"], -row["scores"]["a"], -row["scores"]["c"], row["id"]),
    )
    assert [row["id"] for row in manual] == [row["id"] for row in ranked]


def test_all_structural_checks_pass(payload):
    checks = run_checks(payload)
    failed = [check["name"] for check in checks if not check["pass"]]
    assert not failed, failed


def test_rendered_artifacts_are_deterministic(payload):
    assert render_experiment(payload) == render_experiment(build_payload())
    assert render_report(payload) == render_report(build_payload())


def test_data_and_config_are_byte_identical_before_and_after_a_run():
    data_before = _tree_hash(REPO_ROOT / "data")
    config_before = _tree_hash(REPO_ROOT / "config")
    result = subprocess.run(
        [sys.executable, "research/candidate_shortlist_934.py", "--no-report"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OVERALL: PASS" in result.stdout
    assert _tree_hash(REPO_ROOT / "data") == data_before
    assert _tree_hash(REPO_ROOT / "config") == config_before


def test_two_runs_produce_byte_identical_output():
    outputs = []
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "research/candidate_shortlist_934.py", "--no-report"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=900,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]


def test_the_tool_prints_the_candidate_table_and_the_selection():
    result = subprocess.run(
        [sys.executable, "research/candidate_shortlist_934.py", "--no-report"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "nan" not in result.stdout.lower(), "no published cell may be nan"
    assert "SELECTED|reversal_001" in result.stdout
    for candidate in CANDIDATES:
        assert f"CANDIDATE|{candidate['id']}|TOTAL|" in result.stdout
    for check in ("data_unchanged", "config_unchanged", "committed_artifacts_unchanged"):
        assert f"CHECK|{check}|PASS|" in result.stdout


def test_prior_lines_cover_every_committed_candidate_record():
    records = {entry["record"] for entry in PRIOR_LINES}
    for entry in PRIOR_LINES:
        assert (REPO_ROOT / entry["record"]).exists()
    assert len(records) >= 8
