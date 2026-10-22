"""Cycle 941: tests for the shortlist gross-edge re-verification harness."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_published_vs_recomputed_crosscheck_present():
    exp = REPO_ROOT / "research" / "experiments" / "shortlist_gross_edge_001.md"
    rep = REPO_ROOT / "research" / "reports" / "shortlist_gross_edge_001.md"
    assert exp.exists()
    assert rep.exists()
    text = exp.read_text()
    for cand in ["reversal_001", "pairs_001", "liquidity_001", "leadlag_001"]:
        assert cand in text


def test_gross_net_decomposition_identity():
    import research.shortlist_gross_edge_001 as harness
    results = []
    results.append(harness.recompute_reversal())
    results.append(harness.recompute_pairs_correct2())
    results.append(harness.recompute_liquidity())
    results.append(harness.recompute_leadlag_fixed())
    for r in results:
        if r["candidate_id"] == "pairs_001":
            assert abs(r["gross_excess_ann"] - r["measured_turnover_cost_ann"] - r["borrow_drag_ann"] - r["net_excess_ann"]) < 1e-10
        else:
            assert abs(r["gross_excess_ann"] - r["measured_cost_drag_ann"] - r["net_excess_ann"]) < 1e-10


def test_determinism_two_runs_byte_identical():
    exp = REPO_ROOT / "research" / "experiments" / "shortlist_gross_edge_001.md"
    rep = REPO_ROOT / "research" / "reports" / "shortlist_gross_edge_001.md"
    h1 = _sha256_file(exp)
    r1 = _sha256_file(rep)
    result = subprocess.run([sys.executable, "research/shortlist_gross_edge_001.py"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=1800)
    assert result.returncode == 0
    assert "OVERALL: PASS" in result.stdout
    h2 = _sha256_file(exp)
    r2 = _sha256_file(rep)
    assert h1 == h2
    assert r1 == r2


def test_git_status_clean_data_config():
    result = subprocess.run(["git", "status", "--porcelain", "data/"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.stdout.strip() == ""
    result = subprocess.run(["git", "status", "--porcelain", "config/"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.stdout.strip() == ""


def test_writes_nothing_outside_research():
    # After running harness, ensure no writes outside research/ or tests/ (tests may be created)
    result = subprocess.run(["git", "diff", "--name-only"], cwd=REPO_ROOT, capture_output=True, text=True)
    changed = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    for c in changed:
        assert c.startswith(("research/", "tests/")), f"Wrote outside research/tests/: {c}"
