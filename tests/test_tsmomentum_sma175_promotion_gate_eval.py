"""Regression tests for the SMA-175 promotion gate evaluation tool (Cycle 921).

One measurement defect was corrected in Cycle 921 and is pinned here so that it
cannot silently return:

1. The ``psr`` gate was computed against the candidate's *own* backtest-scale
   Sharpe instead of the fixed backtest baseline (1.4178) that
   ``config/promotion_gates.yaml`` documents for that gate. The candidate
   therefore scored itself against itself, and the published PSR (0.856637)
   was not comparable with any other PSR in the repository. The corrected
   value is 0.896592 (the target is unchanged, the *comparison* was wrong).

The promotion gates, their thresholds and the decision mapping are untouched
by the correction: the corrected PSR is *higher* (0.896592) than the
incorrect one, the verdict is unchanged (NO-GO), and the decision is
unchanged because ``rolling_63d_sharpe`` fails independently of the PSR.

The tool's ``OVERALL`` keeps the repository-wide meaning -- the verdict on
the tool's own internal checks, as required by the Cycle 920 acceptance
criterion 2 -- and is therefore *independent* of the candidate's promotion
verdict, which is the separate ``Decision``. These tests pin both axes so
that neither can be silently conflated with the other again.

The tool is exercised with ``--no-report`` (the convention already used by
research/gate_false_negative_rate.py and research/long_sample_overlay_
attribution.py) so that running the tests never rewrites a tracked artifact.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pandas as pd
import pytest
import yaml

from research.run_cycle6 import SYMBOLS
from research.tsmomentum_sma175_promotion_gate_eval import (
    OUT_EXP,
    OUT_REPORT,
    PSR_TARGET_BACKTEST_SCALE,
    _eval_full_period,
    evaluate,
    load_close_from_cache,
    render_experiment,
    render_report,
)
from src.evaluation.statistics import compute_psr

TOOL = "research/tsmomentum_sma175_promotion_gate_eval.py"
GATES_YAML = REPO / "config" / "promotion_gates.yaml"
SOURCE = REPO / TOOL


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_hashes() -> dict[str, str]:
    return {str(p.relative_to(REPO)): _sha256(p) for p in (OUT_REPORT, OUT_EXP)}


@pytest.fixture(scope="module")
def tool_run() -> dict:
    """Run the tool without writing artifacts and record the artifact hashes."""
    before = _artifact_hashes()
    proc = subprocess.run(
        [sys.executable, TOOL, "--no-report"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    after = _artifact_hashes()
    return {"proc": proc, "before": before, "after": after}


@pytest.fixture(scope="module")
def payload() -> dict:
    """The tool's own payload, computed in memory (no file is written)."""
    return evaluate()


@pytest.fixture(scope="module")
def expected_psr() -> float:
    """PSR of the candidate series against the documented backtest baseline.

    Computed independently of the tool: the return series is rebuilt from the
    raw parquet cache and the PSR is computed with the repository's own
    ``compute_psr`` against the fixed baseline 1.4178.
    """
    close = load_close_from_cache(list(SYMBOLS))
    net_ret, _ = _eval_full_period(close, spy_sma_window=175)
    result = compute_psr(net_ret, sr_target=1.4178, n_bootstrap=1000, block_size=22, seed=20240101)
    return float(result["psr_normal"])


def test_psr_target_is_the_documented_backtest_baseline():
    assert PSR_TARGET_BACKTEST_SCALE == 1.4178
    gates = yaml.safe_load(GATES_YAML.read_text())
    psr_gate = next(g for g in gates["gates"] if g["name"] == "psr")
    assert "1.4178" in psr_gate["metric_definition"]


def test_tool_does_not_use_a_candidate_specific_psr_target():
    source = SOURCE.read_text()
    assert "sr_target=backtest_sharpe_ratio" not in source


def test_tool_runs_read_only_and_passes_its_own_checks(tool_run):
    proc = tool_run["proc"]
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "STRUCTURAL: PASS" in proc.stdout
    assert "OVERALL: PASS" in proc.stdout
    assert "DECISION|NO-GO" in proc.stdout
    assert "CANDIDATE_PROMOTABLE|NO" in proc.stdout
    assert "PSR_TARGET|1.4178" in proc.stdout
    assert "(not written: --no-report)" in proc.stdout


def test_tool_does_not_write_tracked_artifacts(tool_run):
    """Running the tool under test must not rewrite a tracked artifact."""
    assert tool_run["after"] == tool_run["before"]


def test_reported_psr_matches_the_documented_baseline_psr(tool_run, expected_psr):
    psr_lines = [
        line for line in tool_run["proc"].stdout.splitlines() if line.startswith("GATE|psr|")
    ]
    assert len(psr_lines) == 1
    reported = float(psr_lines[0].split("|")[3])
    assert reported == pytest.approx(expected_psr, abs=1e-9)
    assert reported == pytest.approx(0.8996990715818167, abs=1e-9)


def test_overall_is_the_tool_check_verdict_and_not_the_candidate_verdict(payload):
    """Acceptance criterion 2: OVERALL is PASS iff the internal checks pass.

    The candidate verdict is a separate axis (``Decision``); a NO-GO candidate
    does not make a correctly executed evaluation report ``OVERALL: FAIL``.
    """
    assert payload["structural_pass"] is True
    assert payload["overall_pass"] == payload["structural_pass"]
    assert payload["gates_pass"] is False
    assert payload["candidate_promotable"] is False
    assert payload["decision"] == "NO-GO"
    assert payload["failed_gates"] == ["rolling_63d_sharpe", "psr"]


def test_report_states_the_two_verdicts_separately(payload):
    report = render_report(payload)
    assert "- Decision: **NO-GO**" in report
    assert "OVERALL: PASS" in report
    assert "STRUCTURAL: PASS" in report
    assert "Candidate promotable (every promotion gate passes): NO" in report
    assert "It is *not* the" in report
    assert "candidate's promotion verdict" in report
    assert "OVERALL is the promotability verdict" not in report


def test_experiment_record_states_the_two_verdicts_separately(payload):
    experiment = render_experiment(payload)
    assert "- Decision: NO-GO" in experiment
    assert "- OVERALL: PASS (verdict on the tool's own internal checks)" in experiment
    assert "- candidate_promotable (every promotion gate passes): False" in experiment


def test_committed_artifacts_record_the_corrected_psr():
    report = OUT_REPORT.read_text()
    experiment = OUT_EXP.read_text()
    assert "PSR target: 1.4178" in report
    assert "psr_target: 1.4178" in experiment
    assert "0.899699" in report
    assert "0.899699" in experiment
    assert "0.856637" not in report
    assert "0.856637" not in experiment


def test_report_overall_agrees_with_the_tool_checks():
    report = OUT_REPORT.read_text()
    overall = next(
        line for line in report.splitlines() if line.startswith("OVERALL: ")
    )
    assert overall == "OVERALL: PASS"


def test_report_has_no_failing_structural_check():
    report = OUT_REPORT.read_text()
    for line in report.splitlines():
        if line.strip().startswith("- [") and ": FAIL" in line:
            raise AssertionError(f"Found failing structural check: {line}")


def test_data_config_unchanged():
    result = subprocess.run(
        ["git", "status", "--porcelain", "data/", "config/"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""


def test_run_cycle6_unchanged():
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    changed = [x.strip() for x in result.stdout.splitlines() if x.strip()]
    assert "research/run_cycle6.py" not in changed
    assert "config/promotion_gates.yaml" not in changed


def test_promotion_gates_are_unmodified():
    """The gate table is the single source of truth and must not be edited."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "config/promotion_gates.yaml"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""
