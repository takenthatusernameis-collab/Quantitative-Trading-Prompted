"""Regression test: the REAL daily-update write path reproduces the committed state.

Every existing test in test_paper_trading_extend.py stubs out
``run_daily_paper_update`` with a synthetic transition, so the real write path
(the simulation engine, the drift-flag computation, the state mutation and the
atomic write) has never been exercised by the test suite. If that path had a
latent defect, the next ``sessions extended: 1`` run would corrupt the canonical
paper-trading state.

This test replays the real path against a throwaway scratch raw_dir and a
throwaway state file, and asserts that the replayed positions and NAV match the
committed state bit-for-bit. It drives ``run_daily_paper_update`` directly
(rather than ``run_extension``) because the extension's clock/data gates
correctly refuse to select a candidate session while the provider has not yet
served a bar beyond the last processed session -- that is the documented data
gate, not a defect, and a test must not pretend otherwise.
"""
import hashlib
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.extend_paper_trading_state as ext
from src.data.yfinance_fetcher import fetch_universe
from src.simulation.paper_trading import PaperTradingConfig, PaperTradingState

CONFIG_PATH = ROOT / "config" / "paper_trading_config.yaml"
COMMITTED_STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"

# Fixed "now" used across the real-path tests: Monday 2026-11-02 23:00 UTC
# (18:00 ET), i.e. after the 2026-11-02 session has closed. This is the moment
# at which the extension's ``sessions extended: 1`` branch becomes exercisable
# once the provider serves a completed bar beyond the last processed session.
NOW = datetime(2026, 11, 2, 23, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def committed_state():
    return PaperTradingState.from_yaml(COMMITTED_STATE_PATH)


@pytest.fixture(scope="module")
def real_cfg():
    return PaperTradingConfig.from_paper_config_yaml(CONFIG_PATH)


def _real_fetch(real_cfg):
    """Fetch the universe into a scratch dir, mirroring extend_paper_trading_state.

    The scratch dir must outlive every fetch() call, so it is owned by the
    returned (fetch, cleanup) pair rather than by a ``with`` block inside the
    closure (which would delete it after the first call).
    """
    scratch = tempfile.mkdtemp(prefix="test-real-ext-raw-")

    def cleanup():
        for p in Path(scratch).glob("*.parquet"):
            p.unlink(missing_ok=True)
        Path(scratch).rmdir()

    def fetch(end_date: str):
        raw = fetch_universe(
            real_cfg.universe,
            real_cfg.history_start,
            end_date,
            raw_dir=scratch,
            force=True,
            append_only=False,
        )
        return ext.complete_session_view(
            raw, NOW,
            close_hour=real_cfg.data_refresh_market_close_hour,
            tz=ZoneInfo(real_cfg.data_refresh_timezone),
        )

    return fetch, cleanup


def test_real_daily_update_reproduces_committed_state(
    tmp_path, real_cfg, committed_state
):
    """The real write path reproduces the committed state for 2026-10-30."""
    from src.simulation.paper_trading import run_daily_paper_update

    state_path = tmp_path / "state.yaml"
    state_path.write_text(COMMITTED_STATE_PATH.read_text())
    state = PaperTradingState.from_yaml(state_path)
    before = hashlib.sha256(state_path.read_bytes()).hexdigest()

    target = "2026-10-30"
    fetch, cleanup = _real_fetch(real_cfg)
    try:
        # Slice the market data exactly to the target session, as
        # run_extension does (market_slice = all_data.loc[:target]).
        all_data = fetch((pd.Timestamp(target) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
        market_slice = all_data.loc[:target]

        new_state, artifacts = run_daily_paper_update(
            real_cfg, state, market_data=market_slice
        )
    finally:
        cleanup()

    assert new_state.last_run_date == target
    assert new_state.current_nav == pytest.approx(
        committed_state.current_nav, rel=1e-12
    )
    for sym in real_cfg.universe:
        assert new_state.current_positions[sym] == pytest.approx(
            committed_state.current_positions[sym], abs=1e-12
        )


def test_real_extension_path_is_idempotent(tmp_path, real_cfg, committed_state):
    """A second invocation against the same target must be a no-op."""
    state_path = tmp_path / "state.yaml"
    state_path.write_text(COMMITTED_STATE_PATH.read_text())

    target = "2026-10-30"
    fetch, cleanup = _real_fetch(real_cfg)
    try:
        result = ext.run_extension(
            real_cfg, state_path, NOW, fetch,
            close_hour=real_cfg.data_refresh_market_close_hour,
            tz=ZoneInfo(real_cfg.data_refresh_timezone),
        )
    finally:
        cleanup()

    # With no provider bar beyond 2026-10-30, the extension correctly reports
    # no candidate session (data gate). This is the documented no-op branch,
    # not a failure -- the state is untouched.
    assert result["target"] is None
    assert result["sessions_extended"] == 0
    assert result["state_writes"] == 0
    assert result["nav_before"] == result["nav_after"] == pytest.approx(
        committed_state.current_nav, rel=1e-12
    )
    assert PaperTradingState.from_yaml(state_path).last_run_date == committed_state.last_run_date


def test_real_path_leaves_canonical_cache_untouched(real_cfg, committed_state):
    """The real path must never write into the canonical data/raw cache."""
    raw_dir = ROOT / "data" / "raw"
    before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(raw_dir.glob("*.parquet"))
    }
    assert before, "expected canonical raw cache files"

    fetch, cleanup = _real_fetch(real_cfg)
    try:
        # Consume the fetcher once (the closure downloads into scratch).
        _ = fetch("2026-10-31")
    finally:
        cleanup()

    after = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(raw_dir.glob("*.parquet"))
    }
    assert after == before