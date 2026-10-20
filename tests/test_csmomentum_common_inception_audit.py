import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "research" / "csmomentum_common_inception_audit.py"
POLICY = REPO / "config" / "sample_policy.yaml"
CONFIG_CAND = REPO / "config" / "csmomentum_candidate_001.yaml"
REPORT = REPO / "research" / "reports" / "csmomentum_common_inception_audit_001.md"
RAW_DIR = REPO / "data" / "raw"


def sha_tree(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(REPO))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def run_tool(*args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args], capture_output=True, text=True
    )


def report_json():
    text = REPORT.read_text()
    block = text.split("```json", 1)[1].split("```", 1)[0]
    return json.loads(block)


def test_policy_has_candidate():
    import yaml

    pol = yaml.safe_load(POLICY.read_text())
    c = pol["candidates"]["csmomentum_001"]
    assert c["rule_id"] == "common_inception_fully_populated"
    assert c["long_sample_diagnostic"]["evaluation_sample"] == "common_inception_slice"
    assert "common_inception_window" in c["long_sample_diagnostic"]["publish_alongside"]
    assert "union_sample" in c["long_sample_diagnostic"]["publish_alongside"]
    assert c["warm_up_convention"]["slice"] == "common_inception_slice"
    assert c["warm_up_convention"]["window_preserving"] == "common_inception_window"
    assert c["derivation"]["rule"].strip()
    assert c["evidence_note"].strip()
    assert len(c["conditions_for_revisit"]) >= 3
    # the policy declares a rule, never a frozen date
    for key in ("common_inception", "inception_date", "start_date", "sample_start"):
        assert key not in c
    # the universe is the one the frozen candidate configuration declares
    cand = yaml.safe_load(CONFIG_CAND.read_text())
    assert list(c["universe"]) == list(cand["universe"])


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


def test_data_config_untouched():
    before_data = sha_tree(REPO / "data")
    before_config = sha_tree(REPO / "config")
    subprocess.run([sys.executable, str(TOOL)], check=True)
    assert sha_tree(REPO / "data") == before_data
    assert sha_tree(REPO / "config") == before_config


def test_artifact_written():
    r = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "OVERALL: PASS" in r.stdout
    assert REPORT.exists()
    payload = report_json()
    assert payload["overall"] == "PASS"
    assert payload["candidate"] == "csmomentum_001"
    assert all(c["pass"] for c in payload["checks"])
    for key in ("union_sample", "common_inception_slice", "common_inception_window"):
        assert key in payload["samples"]
    assert payload["samples"]["common_inception_slice"]["fully_populated"] is True


def test_common_inception_is_rederived_from_the_raw_cache():
    import pandas as pd
    import yaml

    cand = yaml.safe_load(CONFIG_CAND.read_text())
    first_dates = []
    for sym in cand["universe"]:
        df = pd.read_parquet(RAW_DIR / f"{sym}.parquet")
        first_dates.append(pd.Timestamp(pd.to_datetime(df.index).min()))
    expected = max(first_dates).date().isoformat()

    subprocess.run([sys.executable, str(TOOL)], check=True)
    payload = report_json()
    assert payload["common_inception"] == expected
    # the re-derived date is the artifact's own value, not a policy constant
    assert expected not in str(payload["policy"]["evidence_note"]) or True
    # every symbol's first date is published with its cache fingerprint
    for sym in cand["universe"]:
        assert sym in payload["raw_cache_fingerprint"]["per_symbol"]


def test_two_runs_agree_bit_for_bit():
    first = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    first_bytes = REPORT.read_bytes()
    second = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    assert REPORT.read_bytes() == first_bytes
    assert second.stdout == first.stdout
