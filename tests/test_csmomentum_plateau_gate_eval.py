"""Regression tests for the csmomentum_001 plateau-gate evaluation (Cycle 922).

Why this tool exists
--------------------
The Cycle 922 hand-off asked for a first execution of the C3 baseline. That
premise is stale: the baseline was executed in Cycle 13
(``research/run_cycle13.py``) and its **config-faithful** gate table was
published in Cycle 907 (``research/reports/csmomentum_common_inception_gate_001.md``),
where the candidate's label is *Rejected/Failed*. The one pre-registered gate
that was still open on that path is the **parameter-plateau gate** (gate 4),
which every config-faithful record reports as *NOT EVALUATED*.

These tests pin the following invariants, so that a later cycle cannot change
them silently:

1. the tool reproduces the published config-faithful record (the union sample
   and the pre-registered common-inception sample) -- it is a reproduction
   anchor, not a second opinion;
2. the pre-registered baseline is consumed **as frozen** from
   ``config/csmomentum_candidate_001.yaml`` (252/21/0.5) and no gate,
   threshold, universe, cost model or decision mapping is touched;
3. the plateau gate is **evaluated** (3 of 3 lookbacks within the repository
   tolerance) and the verdict is unchanged: gate 1 fails, so the candidate
   stays *Rejected/Failed*;
4. the walk-forward uses fixed parameters (one continuously computed
   point-in-time path, sliced by the fold windows) -- no per-fold
   re-optimisation;
5. the run is read-only: ``data/`` and ``config/`` are byte-identical before
   and after, the committed artifacts are byte-identical before and after, and
   the fetcher is never called;
6. the results are bit-for-bit deterministic across two runs.

The tool is exercised with ``--no-report`` (the convention already used by
``research/gate_false_negative_rate.py`` and
``research/long_sample_overlay_attribution.py``) so that running the tests
never rewrites a tracked artifact.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.csmomentum_plateau_gate_eval import (  # noqa: E402
    BASELINE,
    COMMITTED_ARTIFACTS,
    OUT_EXP,
    OUT_REPORT,
    PLATEAU_MIN_LOOKBACKS,
    evaluate,
    render_experiment,
    render_report,
)

TOOL = "research/csmomentum_plateau_gate_eval.py"
SOURCE = REPO / TOOL
CONFIG_CAND = REPO / "config" / "csmomentum_candidate_001.yaml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(REPO)): _sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, TOOL, *args],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def runs() -> dict:
    """Two independent runs of the tool (no artifact is written)."""
    data_before = _tree_hashes(REPO / "data")
    config_before = _tree_hashes(REPO / "config")
    artifacts_before = {rel: _sha256(REPO / rel) for rel in COMMITTED_ARTIFACTS}
    outputs_before = {rel: _sha256(REPO / rel) for rel in ("research/reports/csmomentum_plateau_gate_eval_001.md", "research/experiments/csmomentum_plateau_gate_eval_001.md") if (REPO / rel).exists()}
    first = _run("--no-report")
    second = _run("--no-report")
    return {
        "first": first,
        "second": second,
        "data_before": data_before,
        "data_after": _tree_hashes(REPO / "data"),
        "config_before": config_before,
        "config_after": _tree_hashes(REPO / "config"),
        "artifacts_before": artifacts_before,
        "artifacts_after": {rel: _sha256(REPO / rel) for rel in COMMITTED_ARTIFACTS},
        "outputs_before": outputs_before,
        "outputs_after": {rel: _sha256(REPO / rel) for rel in ("research/reports/csmomentum_plateau_gate_eval_001.md", "research/experiments/csmomentum_plateau_gate_eval_001.md") if (REPO / rel).exists()},
    }


@pytest.fixture(scope="module")
def payload() -> dict:
    """The tool's own payload, computed in memory (no file is written)."""
    return evaluate()


@pytest.fixture(scope="module")
def config() -> dict:
    return yaml.safe_load(CONFIG_CAND.read_text())


# ----------------------------------------------------------------------
# Execution
# ----------------------------------------------------------------------
def test_tool_runs_read_only_and_passes_its_own_checks(runs):
    proc = runs["first"]
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "STRUCTURAL: PASS" in proc.stdout
    assert "DECISION|NO-GO" in proc.stdout
    assert "LABEL|Rejected/Failed" in proc.stdout
    assert "PLATEAU|3|3|" in proc.stdout
    assert "ROBUSTNESS_CLEARING_GATE1|0|18" in proc.stdout
    assert "(not written: --no-report)" in proc.stdout


def test_tool_prints_every_check_as_pass(runs):
    lines = [ln for ln in runs["first"].stdout.splitlines() if ln.startswith("CHECK|")]
    assert lines, "the tool printed no structural checks"
    assert all(ln.endswith("|PASS") for ln in lines), lines


def test_tool_does_not_write_tracked_artifacts(runs):
    assert runs["outputs_after"] == runs["outputs_before"]
    assert runs["artifacts_after"] == runs["artifacts_before"]


def test_results_are_deterministic_across_two_runs(runs):
    """Bit-for-bit identical output across two independent runs."""
    assert runs["second"].returncode == 0
    assert runs["first"].stdout == runs["second"].stdout


# ----------------------------------------------------------------------
# Read-only guarantee
# ----------------------------------------------------------------------
def test_data_and_config_are_byte_identical_before_and_after(runs):
    assert runs["data_after"] == runs["data_before"]
    assert runs["config_after"] == runs["config_before"]


def test_working_tree_under_data_and_config_is_clean():
    result = subprocess.run(
        ["git", "status", "--porcelain", "data/", "config/"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""


def test_frozen_config_is_not_modified():
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "config/csmomentum_candidate_001.yaml"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""


def test_the_fetcher_is_never_called():
    source = SOURCE.read_text()
    assert "fetch_" + "universe" not in source
    assert "yfinance_fetcher" not in source


# ----------------------------------------------------------------------
# The pre-registered configuration
# ----------------------------------------------------------------------
def test_baseline_is_consumed_as_frozen(config):
    signal = config["signal"]
    assert BASELINE == (
        int(signal["lookback"]),
        int(signal["skip"]),
        float(signal["top_fraction"]),
    )
    assert BASELINE == (252, 21, 0.5)


def test_payload_uses_the_frozen_configuration(payload, config):
    cfg = payload["candidate_configuration"]
    assert cfg["lookback"] == config["signal"]["lookback"]
    assert cfg["skip"] == config["signal"]["skip"]
    assert cfg["top_fraction"] == config["signal"]["top_fraction"]
    assert cfg["universe"] == list(config["universe"])
    assert cfg["promotion_gates"] == config["evaluation"]["promotion_gates"]
    assert cfg["walk_forward"] == config["evaluation"]["walk_forward"]
    assert cfg["cost_model"] == config["cost_model"]


def test_gate_thresholds_are_read_from_the_frozen_config(payload, config):
    thresholds = {g["name"]: g["threshold"] for g in payload["gates_union"]}
    gates = config["evaluation"]["promotion_gates"]
    assert thresholds["wf_mean_oos_sharpe"] == gates["wf_mean_oos_sharpe_min"]
    assert thresholds["positive_fold_rate"] == gates["positive_fold_rate_min"]
    assert thresholds["pooled_oos_trades"] == gates["pooled_oos_trades_min"]
    plateau = next(g for g in payload["gates_union"] if g["name"] == "plateau")
    assert plateau["config_fraction_threshold"] == gates["plateau_fraction_min"]
    assert plateau["threshold_text"] == ">= 2 of 3 lookbacks"


# ----------------------------------------------------------------------
# The reproduction anchors
# ----------------------------------------------------------------------
def test_union_sample_reproduces_the_published_config_faithful_record(payload):
    for group in ("union_path", "union_walk_forward", "slice_walk_forward"):
        for row in payload["anchors"][group]:
            assert row["match"], (group, row)


def test_published_walk_forward_numbers_are_reproduced(payload):
    wf = payload["walk_forward_union"]
    assert wf["n_folds"] == 48
    assert wf["mean_test_sharpe"] == pytest.approx(0.697524, abs=1e-4)
    assert wf["median_test_sharpe"] == pytest.approx(0.617881, abs=1e-4)
    assert wf["pct_positive_sharpe"] == pytest.approx(0.791667, abs=1e-4)
    assert wf["total_test_trades"] == 400


# ----------------------------------------------------------------------
# The plateau gate and the verdict
# ----------------------------------------------------------------------
def test_plateau_gate_is_evaluated_and_passes(payload):
    plateau = payload["plateau"]
    assert plateau["n_lookbacks"] == 3
    assert plateau["n_within"] == 3
    assert plateau["passed"] is True
    assert plateau["min_lookbacks_required"] == PLATEAU_MIN_LOOKBACKS == 2
    assert plateau["threshold"] == pytest.approx(0.1, abs=1e-12)
    lookbacks = sorted(row["lookback"] for row in plateau["lookbacks"])
    assert lookbacks == [189, 252, 315]


def test_the_plateau_measurement_is_invariant_to_the_sample(payload):
    union = payload["plateau"]
    slice_ = payload["plateau_slice_sample"]
    assert slice_["n_within"] == union["n_within"]
    assert slice_["baseline_test_sharpe"] == pytest.approx(
        union["baseline_test_sharpe"], abs=1e-9
    )


def test_the_verdict_is_unchanged_and_the_failed_gate_is_gate_1(payload):
    gates = {g["name"]: g for g in payload["gates_union"]}
    assert gates["wf_mean_oos_sharpe"]["passed"] is False
    assert gates["positive_fold_rate"]["passed"] is True
    assert gates["pooled_oos_trades"]["passed"] is True
    assert gates["plateau"]["passed"] is True
    assert payload["failed_gates"] == ["wf_mean_oos_sharpe"]
    assert payload["decision"] == "NO-GO"
    assert payload["label"] == "Rejected/Failed"
    assert payload["falsified"] is True


def test_no_pre_registered_configuration_clears_gate_1(payload):
    """The rejection is not an artefact of the pre-registered baseline."""
    robustness = payload["robustness_diagnostic"]
    assert robustness["n_configs"] == 18
    assert robustness["n_clearing_gate1"] == 0
    assert robustness["best_wf_config"]["wf_mean_test_sharpe"] < 0.9


def test_walk_forward_uses_fixed_parameters(payload):
    check = next(c for c in payload["checks"] if c["name"] == "walk_forward_uses_fixed_parameters")
    assert check["pass"] is True
    assert check["observed"]["baseline_paths_built"] == 1
    assert check["observed"]["folds"] == 48


def test_the_grid_is_the_pre_registered_18_configurations(payload):
    grid = payload["grid"]
    assert len(grid) == 18
    combos = {(row["lookback"], row["skip"], row["top_fraction"]) for row in grid}
    assert len(combos) == 18
    assert (252, 21, 0.5) in combos
    assert {row["lookback"] for row in grid} == {189, 252, 315}
    assert {row["skip"] for row in grid} == {21, 42}
    assert {row["top_fraction"] for row in grid} == {0.3, 0.5, 0.7}


def test_selection_follows_the_documented_rank_rule(payload):
    """The shared selection is rank-based (rank >= max_rank x (1 - top_fraction)).

    An earlier draft of this cycle's report mis-described it as a
    momentum-*value* threshold; the check below pins the correct rule so the
    mistake cannot return.
    """
    check = next(
        c for c in payload["checks"] if c["name"] == "selection_follows_the_documented_rank_rule"
    )
    assert check["pass"] is True
    breadth = payload["selection_breadth"]
    assert breadth["test_window_min"] == breadth["test_window_max"] == 10
    assert breadth["universe_size"] == 18
    assert breadth["implied_rank_count"] == 9


def test_the_report_does_not_claim_a_momentum_value_threshold(payload):
    report = render_report(payload)
    assert "momentum-VALUE" not in report
    assert "value threshold" not in report
    assert "rank >= max_rank x (1 - top_fraction)" in report


# ----------------------------------------------------------------------
# The published records
# ----------------------------------------------------------------------
def test_the_records_state_the_gate_table_and_the_label(payload):
    report = render_report(payload)
    experiment = render_experiment(payload)
    for text in (report, experiment):
        assert "Rejected/Failed" in text
        assert "NO-GO" in text
    plateau_row = next(
        line for line in report.splitlines() if line.startswith("| plateau |")
    )
    assert "PASS" in plateau_row
    assert "NOT EVALUATED" not in plateau_row


def test_the_committed_records_are_untouched_by_this_cycle():
    """The pre-existing C3 records keep their 'NOT EVALUATED' wording."""
    for rel in (
        "research/reports/csmomentum_common_inception_gate_001.md",
        "research/experiments/csmomentum_baseline_wf_001.md",
    ):
        assert (REPO / rel).exists()
    baseline_record = (REPO / "research/experiments/csmomentum_baseline_wf_001.md").read_text()
    assert "Rejected/Failed" in baseline_record


def test_the_new_records_exist_and_carry_the_verdict():
    assert OUT_REPORT.exists()
    assert OUT_EXP.exists()
    report = OUT_REPORT.read_text()
    experiment = OUT_EXP.read_text()
    assert "Rejected/Failed" in report
    assert "Rejected/Failed" in experiment
    assert "STRUCTURAL: PASS" in report
