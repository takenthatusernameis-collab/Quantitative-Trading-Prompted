import subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_run():
    r = subprocess.run([sys.executable, "research/sectorrotation_walkforward_embargo_audit.py"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0
    assert "OVERALL: PASS" in r.stdout


def test_artifacts_exist():
    assert (REPO / "research/reports/sectorrotation_walkforward_embargo_001.md").exists()
    assert (REPO / "research/experiments/sectorrotation_walkforward_embargo_001.md").exists()


def test_determinism():
    r1 = subprocess.run([sys.executable, "research/sectorrotation_walkforward_embargo_audit.py"], cwd=REPO, capture_output=True, text=True)
    h1 = (REPO / "research/reports/sectorrotation_walkforward_embargo_001.md").read_text()
    r2 = subprocess.run([sys.executable, "research/sectorrotation_walkforward_embargo_audit.py"], cwd=REPO, capture_output=True, text=True)
    h2 = (REPO / "research/reports/sectorrotation_walkforward_embargo_001.md").read_text()
    assert h1 == h2
