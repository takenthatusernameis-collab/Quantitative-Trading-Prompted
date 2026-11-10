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
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCRIPT = ROOT / "research" / "verify_gate_time_forward_bar.py"
STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"
REPORT_PATH = ROOT / "research" / "reports" / "paper_trading_rolling.md"
RAW_DIR = ROOT / "data" / "raw"
TZ = ZoneInfo("America/New_York")


def _expected_target() -> str:
    """Next trading session after the committed state's last_run_date.

    The target is derived from the state rather than hard-coded: the state
    advanced 2026-11-06 -> 2026-11-09 in the post-gate run, so a fixed
    2026-11-09 target would no longer describe the forward scenario the live
    run would face next (Cycle 1186).
    """
    with open(ROOT / "config" / "paper_trading_config.yaml") as fh:
        cfg = yaml.safe_load(fh) or {}
    state_path = Path(cfg.get("state_path", "data/processed/paper_trading_state.yaml"))
    state_path = state_path if state_path.is_absolute() else ROOT / state_path
    with open(state_path) as fh:
        state = yaml.safe_load(fh) or {}
    last = pd.Timestamp(state["last_run_date"])
    nxt = last.normalize() + pd.Timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += pd.Timedelta(days=1)
    return nxt.strftime("%Y-%m-%d")


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
    assert f"'target': '{_expected_target()}'" in result.stdout
    assert "'sessions_extended': 1" in result.stdout
    assert "'state_writes': 1" in result.stdout
    assert "canonical state hash unchanged: True" in result.stdout
    assert "tracked report hash unchanged: True" in result.stdout

    state_after, report_after, raw_after = _hashes()
    assert state_after == state_before, "canonical paper_trading_state.yaml changed"
    assert report_after == report_before, "tracked paper_trading_rolling.md changed"
    assert raw_after == raw_before, "canonical data/raw cache changed"


def test_gate_time_forward_bar_targets_next_session():
    """The synthetic scenario advances the canonical state to the next trading
    session after last_run_date, i.e. the gate-release target session the live
    run would extend into next."""
    target = _expected_target()
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"'target': '{target}'" in result.stdout
    assert f"new last_run_date: {target}" in result.stdout