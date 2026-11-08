"""Regression test: verify_monday_extension_path.py exercises the ACTIVE path.

Cycle 1034 pinned the target session to 2026-10-22 and the clock to
2026-10-22 22:30 UTC. Once the committed cache receded past that date the
script could no longer exercise the active extension branch: it asserted a
no-op (target != 2026-10-22) and reported RESULT: FAIL on a path it could not
reach. That is a stale hard-code, not a code defect, and it left the active
write path unverified.

The script now derives its target from the canonical SPY frame at run time, so
this test pins the *behaviour* (active path -> sessions_extended: 1, single
state write, canonical state and data/raw untouched) rather than a date. It
runs the script as a subprocess against the cache-backed offline mode.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCRIPT = ROOT / "research" / "verify_monday_extension_path.py"
STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"
RAW_DIR = ROOT / "data" / "raw"


def _hashes():
    state = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()
    raw = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(RAW_DIR.glob("*.parquet"))
    }
    return state, raw


def test_verify_monday_extension_path_passes_and_is_side_effect_free():
    state_before, raw_before = _hashes()
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RESULT: PASS" in result.stdout
    assert "sessions_extended: 1" in result.stdout
    assert "state_writes: 1" in result.stdout

    state_after, raw_after = _hashes()
    assert state_after == state_before, "canonical paper_trading_state.yaml changed"
    assert raw_after == raw_before, "canonical data/raw cache changed"


def test_verify_monday_extension_path_target_matches_canonical_cache():
    """The script's target session is the max date of the committed SPY frame."""
    import pandas as pd

    spy = pd.read_parquet(RAW_DIR / "SPY.parquet")
    expected = pd.Timestamp(spy.index.max()).strftime("%Y-%m-%d")

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"target session: {expected}" in result.stdout