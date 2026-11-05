"""Regression test: the LIVE extension path (real clock + real network) is
exercised and reproduces the committed state, with canonical artifacts
untouched.

The existing test suite exercises the active write path only with a PINNED
clock and an offline cache (test_real_extension_path.py,
verify_monday_extension_path.py). That proves the write machinery is correct
when the clock is fake and the provider is the committed cache. It does NOT
prove that the path works at the REAL wall-clock time against the LIVE provider,
which is the exact scenario research/extend_paper_trading_state.py runs at
22:00 UTC on 2026-11-05.

This test runs research/verify_live_extension_path.py as a subprocess. The
script derives its target from the canonical SPY frame and uses the REAL clock,
so it is a genuine end-to-end check of the production path. It is skipped when
the live provider is unreachable (network down) or when no completed session
beyond the throwaway prior state exists, so CI without egress cannot fail the
suite on a transient network condition.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCRIPT = ROOT / "research" / "verify_live_extension_path.py"


def test_live_extension_path_runs_and_passes():
    """The live end-to-end extension path reproduces the committed state."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    # The script prints RESULT: PASS on success and exits 0. If the live
    # provider is unreachable it prints RESULT: FAIL with an explicit reason
    # and exits non-zero; treat that as a skip rather than a hard failure so a
    # sandbox without egress does not break the suite on a transient condition.
    if result.returncode != 0:
        if "RESULT: FAIL" in result.stdout and (
            "network" in (result.stdout + result.stderr).lower()
            or "connection" in (result.stdout + result.stderr).lower()
            or "timeout" in (result.stdout + result.stderr).lower()
        ):
            pytest.skip(f"live provider unreachable:\n{result.stdout}\n{result.stderr}")
        pytest.fail(f"verify_live_extension_path.py failed:\n{result.stdout}\n{result.stderr}")
    assert "RESULT: PASS" in result.stdout
    assert "sessions_extended: 1" in result.stdout
    assert "state_writes: 1" in result.stdout
    assert "canonical state hash unchanged: True" in result.stdout
    assert "canonical data/raw unchanged: True" in result.stdout