import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "research" / "csmomentum_walkforward_embargo_audit.py"
POLICY = REPO / "config" / "sample_policy.yaml"
REPORT = REPO / "research" / "reports" / "csmomentum_walkforward_embargo_001.md"
EXP = REPO / "research" / "experiments" / "csmomentum_walkforward_embargo_001.md"
RAW_DIR = REPO / "data" / "raw"

COMMITTED_ARTIFACTS = (
    "research/experiments/csmomentum_001_experiment_001.md",
    "research/experiments/csmomentum_baseline_wf_001.md",
    "research/reports/month_end_candidate_reaudit_001.md",
    "research/reports/promotion_feasibility_backtest_001.md",
    "research/reports/csmomentum_common_inception_gate_001.md",
)

SAMPLES = ("union_sample", "common_inception_slice", "common_inception_window")


def sha_tree(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(REPO))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_tool(*args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args], capture_output=True, text=True
    )


def report_json():
    text = REPORT.read_text()
    block = text.split("```json", 1)[1].split("```", 1)[0]
    return json.loads(block)


@pytest.fixture(scope="module")
def tool_run():
    return run_tool()


def test_tool_overall_pass(tool_run):
    assert tool_run.returncode == 0, tool_run.stderr
    assert "OVERALL: PASS" in tool_run.stdout
    payload = report_json()
    assert payload["overall"] == "PASS"
    assert payload["candidate"] == "csmomentum_001"


@pytest.mark.parametrize(
    "body",
    [
        "schema_version: 1\n",
        "schema_version: 2\ncandidates:\n  csmomentum_001: {}\n",
        "schema_version: 1\ncandidates: {}\n",
        "schema_version: 1\ncandidates:\n  other: {}\n",
        "schema_version: 1\ncandidates:\n  csmomentum_001:\n    rule_id: wrong_rule\n",
    ],
)
def test_fails_closed_bad_policy(tmp_path, body):
    bad = tmp_path / "bad.yaml"
    bad.write_text(body)
    r = run_tool("--policy", str(bad))
    assert r.returncode != 0
    assert "ERROR" in r.stderr + r.stdout


def test_fails_closed_missing_policy(tmp_path):
    r = run_tool("--policy", str(tmp_path / "absent.yaml"))
    assert r.returncode != 0
    assert "ERROR" in r.stderr + r.stdout


def test_anchor_reproduces(tool_run):
    payload = report_json()
    assert payload["anchor"]["matches"] is True
    assert payload["published_design"]["union_sample"]["wf"]["n_folds"] == 48
    assert abs(payload["published_design"]["union_sample"]["wf"]["mean_test_sharpe"] - 0.6975) <= 1e-4


def test_design_a_disjoint_and_published_has_overlap(tool_run):
    payload = report_json()
    # published has overlap
    assert payload["published_design"]["union_sample"]["independence"]["mean_consecutive_overlap_days"] > 0
    # design a is disjoint
    a = payload["design_a_nonoverlapping"]["union_sample"]
    assert a["independence"]["mean_consecutive_overlap_days"] == 0.0
    assert a["independence"]["max_disjoint_test_windows"] == len(a["rows"])


def test_data_and_config_untouched():
    before_data = sha_tree(REPO / "data")
    before_config = sha_tree(REPO / "config")
    r = run_tool()
    assert r.returncode == 0, r.stderr
    assert sha_tree(REPO / "data") == before_data
    assert sha_tree(REPO / "config") == before_config


def test_committed_artifacts_untouched():
    before = {rel: sha_file(REPO / rel) for rel in COMMITTED_ARTIFACTS}
    r = run_tool()
    assert r.returncode == 0, r.stderr
    after = {rel: sha_file(REPO / rel) for rel in COMMITTED_ARTIFACTS}
    assert after == before


def test_two_runs_identical():
    r1 = run_tool()
    assert r1.returncode == 0
    content1 = REPORT.read_text()
    exp1 = EXP.read_text()
    r2 = run_tool()
    assert r2.returncode == 0
    assert REPORT.read_text() == content1
    assert EXP.read_text() == exp1
