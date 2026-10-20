import subprocess, sys, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
TOOL = "research/csmomentum_common_inception_audit.py"

def test_runs():
    proc = subprocess.run([sys.executable, TOOL], cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0
    assert "OVERALL: PASS" in proc.stdout
    assert (ROOT / "research/reports/csmomentum_common_inception_audit_001.md").exists()

def test_bad_policy_fails():
    import tempfile, os
    bad = Path(tempfile.mktemp())
    bad.write_text("schema_version: 1\n")
    proc = subprocess.run([sys.executable, TOOL, "--policy", str(bad)], cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert proc.returncode != 0
    bad.unlink()
