import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import research.paper_trading_record_status_audit as mod

def test_artifacts():
    mod.main()
    assert mod.OUT_REPORT.exists()
    assert mod.OUT_EXP.exists()
    assert "OVERALL: PASS" in mod.OUT_REPORT.read_text()

def test_run():
    import subprocess
    r = subprocess.run(["python", "research/paper_trading_record_status_audit.py"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0
    assert "OVERALL: PASS" in r.stdout
