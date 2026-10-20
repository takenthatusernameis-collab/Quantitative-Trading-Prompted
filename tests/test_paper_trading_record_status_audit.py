import subprocess, sys
from pathlib import Path

def test_tool():
    r = subprocess.run([sys.executable, "research/paper_trading_record_status_audit.py"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "OVERALL: PASS" in r.stdout
    assert Path("research/reports/paper_trading_record_status_001.md").exists()
    assert Path("research/experiments/paper_trading_record_status_001.md").exists()
