import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "research" / "csmomentum_sample_gate_audit.py"
POLICY = REPO / "config" / "sample_policy.yaml"
CONFIG_CAND = REPO / "config" / "csmomentum_candidate_001.yaml"
REPORT = REPO / "research" / "reports" / "csmomentum_common_inception_gate_001.md"
RAW_DIR = REPO / "data" / "raw"

COMMITTED_ARTIFACTS = (
    "research/experiments/csmomentum_001_experiment_001.md",
    "research/experiments/csmomentum_baseline_wf_001.md",
    "research/reports/month_end_candidate_reaudit_001.md",
    "research/reports/promotion_feasibility_backtest_001.md",
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
    assert all(c["pass"] for c in payload["checks"])
    assert payload["gate_scale"] == "backtest_sharpe_ratio"


@pytest.mark.parametrize(
    "body",
    [
        "schema_version: 1\n",
        "schema_version: 2\ncandidates:\n  csmomentum_001: {}\n",
        "schema_version: 1\ncandidates: {}\n",
        "schema_version: 1\ncandidates:\n  other: {}\n",
        "schema_version: 1\ncandidates:\n  csmomentum_001:\n    rule_id: wrong_rule\n",
        (
            "schema_version: 1\ncandidates:\n  csmomentum_001:\n"
            "    rule_id: common_inception_fully_populated\n"
            "    long_sample_diagnostic:\n      evaluation_sample: union_sample\n"
        ),
        (
            "schema_version: 1\ncandidates:\n  csmomentum_001:\n"
            "    rule_id: common_inception_fully_populated\n"
            "    common_inception: '2006-02-06'\n"
        ),
        (
            "schema_version: 1\ncandidates:\n  csmomentum_001:\n"
            "    rule_id: common_inception_fully_populated\n"
            "    long_sample_diagnostic:\n      evaluation_sample: common_inception_slice\n"
            "      publish_alongside: [union_sample]\n"
        ),
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


def test_fails_closed_when_the_policy_universe_differs_from_the_candidate(tmp_path):
    """A well-formed policy that names a different universe must not be accepted."""
    import yaml

    pol = yaml.safe_load(POLICY.read_text())
    pol["candidates"]["csmomentum_001"]["universe"] = ["SPY", "QQQ"]
    mismatched = tmp_path / "mismatched.yaml"
    mismatched.write_text(yaml.safe_dump(pol))
    r = run_tool("--policy", str(mismatched))
    assert r.returncode != 0
    assert "ERROR" in r.stderr + r.stdout


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


def test_common_inception_is_rederived_from_the_raw_cache():
    import pandas as pd
    import yaml

    cand = yaml.safe_load(CONFIG_CAND.read_text())
    first_dates = []
    for sym in cand["universe"]:
        df = pd.read_parquet(RAW_DIR / f"{sym}.parquet")
        first_dates.append(pd.Timestamp(pd.to_datetime(df.index).min()))
    expected = max(first_dates).date().isoformat()

    r = run_tool()
    assert r.returncode == 0, r.stderr
    payload = report_json()
    assert payload["common_inception"] == expected
    # every symbol's first date is published with its cache fingerprint
    for sym in cand["universe"]:
        info = payload["raw_cache_fingerprint"]["per_symbol"][sym]
        assert info["sha256"] == sha_file(RAW_DIR / f"{sym}.parquet")
        assert info["first_date"] == payload["raw_cache_fingerprint"]["per_symbol"][sym][
            "first_date"
        ]


def test_reproduces_the_committed_config_faithful_record(tool_run):
    """The reproduction anchor: research/reports/month_end_candidate_reaudit_001.md."""
    payload = report_json()
    anchor = payload["reproduction_anchor"]
    assert anchor["matches"] is True
    observed = {row["metric"]: row["observed"] for row in anchor["rows"]}
    assert observed["n_folds"] == 48
    assert observed["mean_test_sharpe"] == pytest.approx(0.6975, abs=1e-4)
    assert observed["mean_test_sharpe_canonical"] == pytest.approx(0.8404, abs=1e-4)
    assert observed["median_test_sharpe"] == pytest.approx(0.6179, abs=1e-4)
    assert observed["pct_positive_sharpe"] == pytest.approx(0.7917, abs=1e-4)
    assert observed["total_test_trades"] == 400
    assert all(row["match"] for row in anchor["rows"])


def test_does_not_produce_the_legacy_or_daily_values(tool_run):
    payload = report_json()
    assert payload["forbidden_values"], "the forbidden values must be published"
    for row in payload["forbidden_values"]:
        assert row["produced"] is False
    mean = payload["samples"]["union_sample"]["walk_forward"]["mean_test_sharpe"]
    assert mean != pytest.approx(0.6868, abs=1e-4)
    assert mean != pytest.approx(0.6928, abs=1e-4)


def test_three_samples_publish_their_gate_table(tool_run):
    payload = report_json()
    for name in SAMPLES:
        sample = payload["samples"][name]
        wf = sample["walk_forward"]
        assert wf["n_folds"] > 0
        assert len(wf["folds"]) == wf["n_folds"]
        assert wf["mean_test_sharpe"] == pytest.approx(
            sum(f["test_sharpe"] for f in wf["folds"]) / wf["n_folds"], abs=1e-9
        )
        gates = {g["gate"]: g for g in sample["gates"]}
        assert set(gates) == {
            "wf_mean_oos_sharpe",
            "positive_fold_rate",
            "pooled_oos_trades",
            "plateau",
        }
        assert gates["plateau"]["status"] == "NOT EVALUATED"
        assert gates["plateau"]["observed"] is None
        assert gates["plateau"]["reason"].strip()
        assert sample["decision"]["label"]
        assert len(sample["fold_diagnostics"]) == wf["n_folds"]


def test_the_decision_does_not_move_on_any_sample(tool_run):
    payload = report_json()
    for name in SAMPLES:
        sample = payload["samples"][name]
        gates = {g["gate"]: g for g in sample["gates"]}
        assert gates["wf_mean_oos_sharpe"]["status"] == "FAIL"
        assert gates["positive_fold_rate"]["status"] == "PASS"
        assert gates["pooled_oos_trades"]["status"] == "PASS"
        assert sample["decision"]["label"] == "Rejected/Failed"
        assert sample["decision"]["falsified"] is True


def test_the_evaluation_window_ends_at_the_frozen_test_end(tool_run):
    import yaml

    cand = yaml.safe_load(CONFIG_CAND.read_text())
    test_end = str(cand["evaluation"]["splits"]["test_end"])
    payload = report_json()
    for name in SAMPLES:
        assert payload["samples"][name]["end_date"] == test_end


def test_two_runs_agree_bit_for_bit(tool_run):
    first_bytes = REPORT.read_bytes()
    first_stdout = tool_run.stdout
    second = run_tool()
    assert second.returncode == 0, second.stderr
    assert REPORT.read_bytes() == first_bytes
    assert second.stdout == first_stdout
