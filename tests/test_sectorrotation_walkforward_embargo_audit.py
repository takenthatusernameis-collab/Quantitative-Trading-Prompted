import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_run():
    r = subprocess.run([sys.executable, "research/sectorrotation_walkforward_embargo_audit.py"], cwd=REPO, capture_output=True, text=True, check=True)
    assert "OVERALL: PASS" in r.stdout


def test_artifacts_exist():
    assert (REPO / "research/reports/sectorrotation_walkforward_embargo_001.md").exists()
    assert (REPO / "research/experiments/sectorrotation_walkforward_embargo_001.md").exists()


def test_determinism():
    subprocess.run([sys.executable, "research/sectorrotation_walkforward_embargo_audit.py"], cwd=REPO, capture_output=True, text=True, check=True)
    h1 = (REPO / "research/reports/sectorrotation_walkforward_embargo_001.md").read_text()
    subprocess.run([sys.executable, "research/sectorrotation_walkforward_embargo_audit.py"], cwd=REPO, capture_output=True, text=True, check=True)
    h2 = (REPO / "research/reports/sectorrotation_walkforward_embargo_001.md").read_text()
    assert h1 == h2
