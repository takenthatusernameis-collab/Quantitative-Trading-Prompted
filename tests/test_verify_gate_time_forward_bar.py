"""Regression test: verify_gate_time_forward_bar.py exercises the FORWARD path.

verify_monday_extension_path.py (inv339) exercises the extension against the
COMMITTED cache's own max date (2026-11-05), which is a backward replay: the
target session is already in the past relative to the pinned clock. That proves
the active write path, but it does NOT prove the exact scenario the real gate
release will face.

verify_gate_time_forward_bar.py instead simulates the 22:00 UTC 2026-11-09 gate
release: clock pinned at 2026-11-09 22:00:00 UTC (17:00 ET), canonical state
left at last_run_date 2026-11-06, and a synthetic 2026-11-09 bar appended to
scratch copies of the committed raw cache. The active write path is therefore
exercised against a FORWARD bar that the live fetch will return once the Monday
session closes, with the canonical state, data/raw, and tracked report all
verified untouched.

This test pins the behaviour (forward gate-release scenario -> sessions_extended:
1, single state write, canonical state/data/raw/report unchanged) rather than a
hard-coded date, and runs the script as a subprocess.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCRIPT = ROOT / "research" / "verify_gate_time_forward_bar.py"
STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"
REPORT_PATH = ROOT / "research" / "reports" / "paper_trading_rolling.md"
RAW_DIR = ROOT / "data" / "raw"


def _hashes():
    state = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()
    report = hashlib.sha256(REPORT_PATH.read_bytes()).hexdigest()
    raw = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(RAW_DIR.glob("*.parquet"))
    }
    return state, report, raw


def test_gate_time_forward_bar_passes_and_is_side_effect_free():
    state_before, report_before, raw_before = _hashes()
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RESULT: PASS" in result.stdout
    # The script prints the raw result dict and the post-write state; the
    # extension metrics are asserted there rather than on labeled lines.
    assert "'target': '2026-11-09'" in result.stdout
    assert "'sessions_extended': 1" in result.stdout
    assert "'state_writes': 1" in result.stdout
    assert "canonical state hash unchanged: True" in result.stdout
    assert "tracked report hash unchanged: True" in result.stdout

    state_after, report_after, raw_after = _hashes()
    assert state_after == state_before, "canonical paper_trading_state.yaml changed"
    assert report_after == report_before, "tracked paper_trading_rolling.md changed"
    assert raw_after == raw_before, "canonical data/raw cache changed"


def test_gate_time_forward_bar_targets_2026_11_09():
    """The synthetic scenario advances the canonical state to the gate-release
    target session 2026-11-09, the next trading session after last_run_date."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "'target': '2026-11-09'" in result.stdout
    assert "new last_run_date: 2026-11-09" in result.stdout