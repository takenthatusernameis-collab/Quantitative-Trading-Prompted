"""Cycle 937: tests for pairs_001 failure analysis (read-only)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.pairs_001_failure_analysis import (
    COINT_SUMMARY,
    COST_BREAKDOWN,
    FIRED_CONDITIONS,
    PAIR_ATTRIBUTION,
    build_payload,
)


@pytest.fixture(scope="module")
def payload() -> dict:
    return build_payload()


def test_reads_only_committed_artifacts_no_data_config_modified(payload):
    assert payload["data_unchanged"] is True
    assert payload["config_unchanged"] is True


def test_reports_all_six_pairs_with_attribution(payload):
    assert len(payload["pair_attribution"]) == 6
    pairs = [r["pair"] for r in payload["pair_attribution"]]
    assert pairs == ["XLP/XLU", "XLF/XLK", "XLE/XLB", "XLI/XLB", "XLV/XLY", "XLK/XLU"]
    # each has required fields
    for r in payload["pair_attribution"]:
        assert "net_excess_annualized" in r
        assert "sharpe" in r
        assert "trades" in r


def test_states_fired_conditions_with_values(payload):
    fired = payload["fired_conditions"]
    assert fired["i"]["outcome"] == "FIRED"
    assert fired["iii"]["outcome"] == "FIRED"
    assert fired["iv"]["outcome"] == "FIRED"
    assert fired["ii"]["outcome"] == "not fired"
    # values present
    assert fired["i"]["observed"] == -0.829067
    assert fired["iv"]["observed"] == -0.136774


def test_cointegration_summary_present(payload):
    assert len(payload["cointegration"]) == 6
    for pair, info in payload["cointegration"].items():
        assert info["train_windows"] == 36
        assert "cointegrated" in info
        assert "min_p" in info
        assert "max_p" in info


def test_cost_breakdown_present(payload):
    cb = payload["cost_breakdown"]
    assert cb["realized_borrow_drag_per_year"] > 0
    assert cb["net_excess_after_borrow_annualized"] < 0


def test_determinism_two_runs():
    p1 = build_payload()
    p2 = build_payload()
    assert p1["pair_attribution"] == p2["pair_attribution"]
    assert p1["cointegration"] == p2["cointegration"]
    assert p1["fired_conditions"] == p2["fired_conditions"]
    assert p1["cost_breakdown"] == p2["cost_breakdown"]


def test_files_created_by_tool():
    # ensure expected files exist after running tool
    res = subprocess.run([sys.executable, "research/pairs_001_failure_analysis.py"], cwd=REPO_ROOT, stdout=subprocess.PIPE)
    assert res.returncode == 0
    assert (REPO_ROOT / "research/experiments/pairs_001_failure_analysis.md").exists()
    assert (REPO_ROOT / "research/reports/pairs_001_failure_analysis.md").exists()
    assert b"OVERALL: PASS" in res.stdout
