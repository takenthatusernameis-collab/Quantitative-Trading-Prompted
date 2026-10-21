"""Tests for promoted candidate docs (Cycle 917)."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_promoted_candidate_files_exist():
    assert (REPO / "research" / "experiments" / "tsmomentum_sma175_promoted_candidate_001.md").exists()
    assert (REPO / "research" / "reports" / "tsmomentum_sma175_promoted_candidate_001.md").exists()
