import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.extend_paper_trading_state as ext
from research.extend_paper_trading_state import (
    complete_session_view,
    run_extension,
    session_is_complete,
)
from src.simulation.paper_trading import PaperTradingState

TZ = ZoneInfo("America/New_York")
SYMBOLS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]


# ---------------------------------------------------------------------------
# Session-completeness guard
# ---------------------------------------------------------------------------


def test_session_guard():
    # completed: now next day
    now = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
    assert session_is_complete("2026-10-17", now) is True
    # open session: same day before close+1
    now2 = datetime(2026, 10, 17, 15, 0, tzinfo=timezone.utc)  # 11am ET
    assert session_is_complete("2026-10-17", now2) is False
    # after close+1 same day
    now3 = datetime(2026, 10, 17, 22, 0, tzinfo=timezone.utc)  # 6pm ET
    assert session_is_complete("2026-10-17", now3) is True


def test_session_guard_uses_configured_close_hour():
    # 15:30 ET (19:30 UTC): complete under a 14:00 close, not under 16:00.
    now = datetime(2026, 10, 17, 19, 30, tzinfo=timezone.utc)
    assert session_is_complete("2026-10-17", now, close_hour=14) is True
    assert session_is_complete("2026-10-17", now, close_hour=16) is False


# ---------------------------------------------------------------------------
# Incomplete-bar exclusion
# ---------------------------------------------------------------------------


def _market_frame(dates, symbols=SYMBOLS):
    """Synthetic universe frame with (Open, High, Low, Close, Volume) columns."""
    index = pd.DatetimeIndex([pd.Timestamp(d, tz="UTC") for d in dates], name="Date")
    cols = pd.MultiIndex.from_product(
        [["Open", "High", "Low", "Close", "Volume"], list(symbols)]
    )
    data = _constant_rows(index, cols)
    return pd.DataFrame(data, index=index, columns=cols)


def _constant_rows(index, cols):
    n = len(index)
    base = {
        "Open": 100.0,
        "High": 101.0,
        "Low": 99.0,
        "Close": 100.5,
        "Volume": 1_000_000.0,
    }
    out = {}
    for field, _sym in cols:
        out[field] = [base[field]] * n
    return out


def test_complete_session_view_drops_in_progress_bar():
    frame = _market_frame(["2026-10-16", "2026-10-19", "2026-10-20"])
    # 2026-10-19 10:30 ET -> the 10-19 session is still open.
    now = datetime(2026, 10, 19, 14, 30, tzinfo=timezone.utc)
    view = complete_session_view(frame, now, close_hour=16, tz=TZ)
    kept = [pd.Timestamp(t).strftime("%Y-%m-%d") for t in view.index.unique()]
    assert kept == ["2026-10-16"]
    # after the close, the 10-19 session becomes usable
    now2 = datetime(2026, 10, 19, 22, 30, tzinfo=timezone.utc)
    view2 = complete_session_view(frame, now2, close_hour=16, tz=TZ)
    kept2 = [pd.Timestamp(t).strftime("%Y-%m-%d") for t in view2.index.unique()]
    assert kept2 == ["2026-10-16", "2026-10-19"]


# ---------------------------------------------------------------------------
# Extension control flow (offline, no network, canonical state untouched)
# ---------------------------------------------------------------------------


def _write_state(path: Path, last_run_date: str = "2026-10-16") -> Path:
    state = {
        "last_run_date": last_run_date,
        "current_positions": {"SPY": 0.5},
        "cumulative_returns": [0.001, -0.002],
        "cumulative_pnl": [100.0, -200.0],
        "cumulative_dates": ["2026-10-15", "2026-10-16"],
        "peak_nav": 100000.0,
        "current_nav": 99900.0,
        "max_drawdown": -0.001,
        "drift_flags": {},
        "run_history": [
            {"date": "2026-10-15", "nav": 100100.0, "daily_return": 0.001,
             "daily_pnl": 100.0, "turnover": 0.1, "vol_scale": 1.0,
             "dd_scale": 1.0, "regime_exposure": 1.0, "n_positions": 3},
            {"date": "2026-10-16", "nav": 99900.0, "daily_return": -0.002,
             "daily_pnl": -200.0, "turnover": 0.1, "vol_scale": 1.0,
             "dd_scale": 1.0, "regime_exposure": 1.0, "n_positions": 3},
        ],
        "previous_regime_exposure": 1.0,
    }
    path.write_text(yaml.safe_dump(state, sort_keys=False))
    return path


def _stub_fetch(frame: pd.DataFrame):
    """Mimic yfinance's exclusive end date semantics."""
    def fetch(end_date: str) -> pd.DataFrame:
        end = pd.Timestamp(end_date, tz="UTC")
        return frame.loc[frame.index < end]
    return fetch


def _stub_update(monkeypatch, target_date: str):
    """Replace the simulation update with a deterministic state transition."""
    calls = []

    def fake_update(config, state, market_data=None):
        calls.append(market_data)
        latest = pd.Timestamp(market_data.index.max()).strftime("%Y-%m-%d")
        state.last_run_date = latest
        state.cumulative_returns.append(0.001)
        state.cumulative_pnl.append(state.current_nav * 0.001)
        state.cumulative_dates.append(latest)
        state.current_nav = state.current_nav * 1.001
        state.run_history.append(
            {
                "date": latest, "nav": state.current_nav, "daily_return": 0.001,
                "daily_pnl": state.current_nav * 0.001, "turnover": 0.1,
                "vol_scale": 1.0, "dd_scale": 1.0, "regime_exposure": 1.0,
                "n_positions": 3,
            }
        )
        return state, {}

    monkeypatch.setattr(ext, "run_daily_paper_update", fake_update)
    monkeypatch.setattr(ext, "generate_paper_report", lambda state, config: "")
    return calls


def _config(tmp_path):
    cfg = ext.PaperTradingConfig.from_paper_config_yaml(
        ROOT / "config" / "paper_trading_config.yaml"
    )
    cfg.report_path = str(tmp_path / "report.md")
    return cfg


def test_extension_is_noop_without_completed_session(tmp_path, monkeypatch):
    state_path = _write_state(tmp_path / "state.yaml")
    before = hashlib.sha256(state_path.read_bytes()).hexdigest()
    frame = _market_frame(["2026-10-15", "2026-10-16", "2026-10-19"])
    # 2026-10-19 10:30 ET -> the next session has not closed yet.
    now = datetime(2026, 10, 19, 14, 30, tzinfo=timezone.utc)
    calls = _stub_update(monkeypatch, "2026-10-19")

    result = run_extension(
        _config(tmp_path), state_path, now, _stub_fetch(frame),
        close_hour=16, tz=TZ,
    )
    assert result["target"] is None
    assert result["sessions_extended"] == 0
    assert result["state_writes"] == 0
    assert calls == []
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == before


def test_dry_run_reports_target_without_writing(tmp_path, monkeypatch):
    state_path = _write_state(tmp_path / "state.yaml")
    before = hashlib.sha256(state_path.read_bytes()).hexdigest()
    frame = _market_frame(["2026-10-15", "2026-10-16", "2026-10-19"])
    # 2026-10-19 18:30 ET -> the 10-19 session has closed.
    now = datetime(2026, 10, 19, 22, 30, tzinfo=timezone.utc)
    calls = _stub_update(monkeypatch, "2026-10-19")

    result = run_extension(
        _config(tmp_path), state_path, now, _stub_fetch(frame),
        dry_run=True, close_hour=16, tz=TZ,
    )
    assert result["target"] == "2026-10-19"
    assert result["state_writes"] == 0
    assert calls == []
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == before


def test_extension_writes_once_and_is_idempotent(tmp_path, monkeypatch):
    state_path = _write_state(tmp_path / "state.yaml")
    frame = _market_frame(["2026-10-15", "2026-10-16", "2026-10-19"])
    now = datetime(2026, 10, 19, 22, 30, tzinfo=timezone.utc)
    calls = _stub_update(monkeypatch, "2026-10-19")
    config = _config(tmp_path)

    result = run_extension(
        config, state_path, now, _stub_fetch(frame), close_hour=16, tz=TZ
    )
    assert result["target"] == "2026-10-19"
    assert result["sessions_extended"] == 1
    assert result["state_writes"] == 1
    assert result["nav_after"] > result["nav_before"]
    assert len(calls) == 1
    # the market slice handed to the update ends exactly at the target session
    assert pd.Timestamp(calls[0].index.max()).strftime("%Y-%m-%d") == "2026-10-19"
    written = yaml.safe_load(state_path.read_text())
    assert written["last_run_date"] == "2026-10-19"

    # second invocation is a no-op: the session was already processed
    result2 = run_extension(
        config, state_path, now, _stub_fetch(frame), close_hour=16, tz=TZ
    )
    assert result2["target"] is None
    assert result2["state_writes"] == 0
    assert len(calls) == 1


def test_extension_aborts_when_update_does_not_reach_target(tmp_path, monkeypatch):
    """A state update that lands on another date must not be written."""
    state_path = _write_state(tmp_path / "state.yaml")
    before = hashlib.sha256(state_path.read_bytes()).hexdigest()
    frame = _market_frame(["2026-10-15", "2026-10-16", "2026-10-19"])
    now = datetime(2026, 10, 19, 22, 30, tzinfo=timezone.utc)

    def wrong_update(config, state, market_data=None):
        state.last_run_date = "2026-10-20"
        return state, {}

    monkeypatch.setattr(ext, "run_daily_paper_update", wrong_update)
    monkeypatch.setattr(ext, "generate_paper_report", lambda state, config: "")

    with pytest.raises(RuntimeError):
        run_extension(
            _config(tmp_path), state_path, now, _stub_fetch(frame),
            close_hour=16, tz=TZ,
        )
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == before


# ---------------------------------------------------------------------------
# Canonical raw cache must never be written by the monitoring tool
# ---------------------------------------------------------------------------


def test_main_uses_scratch_raw_dir_and_leaves_cache_untouched(tmp_path, monkeypatch):
    raw_dir = ROOT / "data" / "raw"
    before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(raw_dir.glob("*.parquet"))
    }
    assert before, "expected canonical raw cache files"

    recorded = {}

    def fake_fetch_universe(symbols, start, end, raw_dir=None, force=False):
        recorded["raw_dir"] = Path(raw_dir) if raw_dir else None
        recorded["force"] = force
        return _market_frame(["2026-10-15", "2026-10-16"])

    monkeypatch.setattr(ext, "fetch_universe", fake_fetch_universe)
    # The committed state's last_run_date is now 2026-10-23, so the clock gate
    # only releases once the 2026-10-24 session is complete. Pin the clock to
    # 2026-10-25 00:00 UTC (20:00 ET the prior evening) so the gate releases
    # and the scratch/raw_dir contract is actually exercised.
    fixed_now = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)

    class _StubClock:
        timezone = timezone

        @staticmethod
        def now(tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    monkeypatch.setattr(ext, "datetime", _StubClock)
    monkeypatch.setattr(sys, "argv", ["extend_paper_trading_state.py"])
    ext.main()

    assert recorded["raw_dir"] is not None
    assert recorded["raw_dir"].resolve() != raw_dir.resolve()
    assert recorded["force"] is True

    after = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(raw_dir.glob("*.parquet"))
    }
    assert after == before


def test_clock_gate_skips_fetch_when_session_not_complete(tmp_path, monkeypatch):
    """A no-op monitoring run must not touch the network at all."""
    state_path = _write_state(tmp_path / "state.yaml")
    before = hashlib.sha256(state_path.read_bytes()).hexdigest()

    called = {"fetch": False}

    def fake_fetch(end_date):
        called["fetch"] = True
        return _market_frame(["2026-10-15", "2026-10-16"])

    # 2026-10-17 10:30 ET -> the 10-17 session is still open, so the gate
    # releases only once the following day has started.
    now = datetime(2026, 10, 17, 14, 30, tzinfo=timezone.utc)
    result = run_extension(
        _config(tmp_path), state_path, now, fake_fetch, close_hour=16, tz=TZ,
    )
    assert result["target"] is None
    assert result["sessions_extended"] == 0
    assert result["state_writes"] == 0
    assert called["fetch"] is False
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == before


# ---------------------------------------------------------------------------
# Readiness diagnostic (acceptance criterion 2)
# ---------------------------------------------------------------------------


def test_next_trading_session_skips_weekends():
    # Friday 2026-10-23 -> Monday 2026-10-26
    assert ext.next_trading_session(pd.Timestamp("2026-10-23")).strftime(
        "%Y-%m-%d"
    ) == "2026-10-26"
    # Saturday 2026-10-24 -> Monday 2026-10-26
    assert ext.next_trading_session(pd.Timestamp("2026-10-24")).strftime(
        "%Y-%m-%d"
    ) == "2026-10-26"
    # Sunday 2026-10-25 -> Monday 2026-10-26
    assert ext.next_trading_session(pd.Timestamp("2026-10-25")).strftime(
        "%Y-%m-%d"
    ) == "2026-10-26"
    # Thursday 2026-10-22 -> Friday 2026-10-23
    assert ext.next_trading_session(pd.Timestamp("2026-10-22")).strftime(
        "%Y-%m-%d"
    ) == "2026-10-23"


def test_readiness_reports_clock_gate_and_next_session():
    state = PaperTradingState(last_run_date="2026-10-23")
    # Friday 20:00 ET -> gate not released; next session Monday
    now = datetime(2026, 10, 23, 20, 0, tzinfo=timezone.utc)
    r = ext.build_readiness(state, now, close_hour=16, tz=TZ)
    assert r["last_run_date"] == "2026-10-23"
    assert r["clock_gate_released"] is False
    assert r["next_calendar_day"] == "2026-10-24"
    assert r["next_expected_session"] == "2026-10-26"
    assert r["next_session_weekday"] == "Monday"
    assert r["next_session_already_complete"] is False
    assert "17:00 ET on 2026-10-26" in r["next_session_complete_time"]


def test_readiness_gate_releases_after_close_on_session_date():
    state = PaperTradingState(last_run_date="2026-10-22")
    # Thursday 17:30 ET -> the calendar day after last_run (Friday) has
    # started, so the gate releases; the next session is Friday itself and it
    # is already complete.
    now = datetime(2026, 10, 23, 21, 30, tzinfo=timezone.utc)
    r = ext.build_readiness(state, now, close_hour=16, tz=TZ)
    assert r["clock_gate_released"] is True
    assert r["next_expected_session"] == "2026-10-23"
    assert r["next_session_already_complete"] is True


def test_readiness_fresh_state_has_no_last_run():
    state = PaperTradingState()  # last_run_date is None
    now = datetime(2026, 10, 23, 20, 0, tzinfo=timezone.utc)
    r = ext.build_readiness(state, now, close_hour=16, tz=TZ)
    assert r["last_run_date"] is None
    assert r["next_calendar_day"] is None
    assert r["clock_gate_released"] is True
    assert r["next_expected_session"] == "2026-10-23"


def test_readiness_is_pure_and_untouched_by_extension(tmp_path, monkeypatch):
    """build_readiness must not write state or touch the raw cache."""
    state_path = _write_state(tmp_path / "state.yaml")
    before = hashlib.sha256(state_path.read_bytes()).hexdigest()
    state = PaperTradingState.from_yaml(state_path)
    now = datetime(2026, 10, 23, 20, 0, tzinfo=timezone.utc)
    ext.build_readiness(state, now, close_hour=16, tz=TZ)
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == before
