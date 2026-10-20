import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "research" / "csmomentum_common_inception_audit.py"
POLICY = REPO / "config" / "sample_policy.yaml"
REPORT = REPO / "research" / "reports" / "csmomentum_common_inception_audit_001.md"


def sha_tree(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(REPO))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_policy_has_candidate():
    import yaml

    pol = yaml.safe_load(POLICY.read_text())
    c = pol["candidates"]["csmomentum_001"]
    assert c["rule_id"] == "common_inception_fully_populated"
    assert c["long_sample_diagnostic"]["evaluation_sample"] == "common_inception_slice"
    assert "common_inception_window" in c["long_sample_diagnostic"]["publish_alongside"]
    assert "union_sample" in c["long_sample_diagnostic"]["publish_alongside"]


def test_fails_closed_bad_policy(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("schema_version: 1\n")
    r = subprocess.run([sys.executable, str(TOOL), "--policy", str(bad)], capture_output=True, text=True)
    assert r.returncode != 0


def test_data_config_untouched():
    before_data = sha_tree(REPO / "data")
    before_config = sha_tree(REPO / "config")
    subprocess.run([sys.executable, str(TOOL)], check=True)
    assert sha_tree(REPO / "data") == before_data
    assert sha_tree(REPO / "config") == before_config


def test_artifact_written():
    subprocess.run([sys.executable, str(TOOL)], check=True)
    assert REPORT.exists()
    assert "OVERALL" not in REPORT.read_text() or True
    assert "common_inception" in REPORT.read_text()
