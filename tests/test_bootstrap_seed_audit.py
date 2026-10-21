"""Cycle 940: tests for the repository-wide bootstrap seed audit."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.bootstrap_seed_audit import (  # noqa: E402
    CANDIDATE_EVALUATOR_GLOB,
    TARGETS,
    _seed_state,
    run_checks,
    scan,
)


def _classify(source: str) -> list[bool]:
    """Classify every audited call in a python snippet."""
    tree = ast.parse(source)
    states: list[bool] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name not in TARGETS:
            continue
        states.append(_seed_state(node, TARGETS[name])[0])
    return states


def test_a_seeded_call_is_recognised():
    assert _classify("compute_dsr(x, n_configs=1, seed=42)") == [True]
    assert _classify("compute_psr(x, sr_target=0.0, n_bootstrap=10, block_size=22, seed=7)") == [True]
    assert _classify("block_bootstrap_sharpe(x, n_samples=10, block_size=22, seed=7)") == [True]


def test_an_unseeded_call_is_recognised():
    assert _classify("compute_dsr(x, n_configs=1)") == [False]
    assert _classify("compute_psr(x, sr_target=0.0, n_bootstrap=10, block_size=22)") == [False]
    assert _classify("block_bootstrap_sharpe(x, n_samples=10, block_size=22)") == [False]


def test_an_explicit_none_seed_counts_as_unseeded():
    assert _classify("compute_dsr(x, n_configs=1, seed=None)") == [False]


def test_the_scan_finds_the_bootstrap_call_sites():
    result = scan()
    assert result["call_sites"], "no bootstrap call site was found"
    assert not result["parse_errors"], result["parse_errors"]
    files = {site["file"] for site in result["call_sites"]}
    assert "research/liquidity_001_evaluation.py" in files
    assert "research/leadlag_001_evaluation.py" in files


def test_every_candidate_evaluator_seeds_its_bootstrap():
    """The gate: a candidate evaluator must never publish an unseeded statistic."""
    result = scan()
    assert result["offending_evaluators"] == []
    checks = {check["name"]: check for check in run_checks(result)}
    assert checks["candidate_evaluators_seed_every_bootstrap"]["pass"] is True


def test_the_candidate_evaluator_glob_covers_the_published_evaluators():
    evaluators = sorted(
        path.name for path in REPO_ROOT.glob(CANDIDATE_EVALUATOR_GLOB)
    )
    for name in (
        "leadlag_001_evaluation.py",
        "liquidity_001_evaluation.py",
        "pairs_001_evaluation.py",
        "reversal_001_evaluation.py",
    ):
        assert name in evaluators


def test_the_scan_is_deterministic():
    first = scan()
    second = scan()
    assert first == second
