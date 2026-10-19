"""Offline unit tests for research/refresh_raw_cache.py.

No network access is required: the fetcher is stubbed with synthetic frames.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.refresh_raw_cache as rc
from research.extend_paper_trading_state import session_is_complete

TZ = ZoneInfo("America/New_York")
SYMBOLS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM", "^VIX"]
FIELDS = ("Open", "High", "Low", "Close", "Volume")


def _symbol_df(dates):
    index = pd.DatetimeIndex([pd.Timestamp(d, tz="UTC") for d in dates], name="Date")
    data = {f: [100.0 if f != "Volume" else 1_000_000.0] * len(dates) for f in FIELDS}
    return pd.DataFrame(data, index=index)


def _aligned_frame(symbol_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    all_index = sorted(set().union(*(df.index for df in symbol_frames.values())))
    all_index = pd.DatetimeIndex(all_index, tz="UTC")
    cols = pd.MultiIndex.from_product([FIELDS, list(symbol_frames)])
    out = pd.DataFrame(index=all_index, columns=cols, dtype=float)
    for symbol, df in symbol_frames.items():
        for f in FIELDS:
            out[(f, symbol)] = df[f].reindex(all_index)
    return out


def _stub_fetch(symbol_frames: dict[str, pd.DataFrame]):
    aligned = _aligned_frame(symbol_frames)

    def fetch(symbols, start, end, raw_dir=None, force=False):
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC")
        mask = (aligned.index >= start_ts) & (aligned.index < end_ts)
        return aligned.loc[mask]

    return fetch


def _write_cache(raw_dir: Path, symbol: str, dates):
    df = _symbol_df(dates)
    df.to_parquet(rc.cache_path(raw_dir, symbol))


def _cache_hash(raw_dir: Path, symbol: str) -> str:
    return hashlib.sha256(rc.cache_path(raw_dir, symbol).read_bytes()).hexdigest()


def _cache_state(raw_dir: Path, symbol: str):
    df = rc.load_cache(raw_dir, symbol)
    if df is None:
        return 0, None
    return len(df), pd.Timestamp(df.index.max()).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Row selection: completeness filter and no-overlap with cache
# ---------------------------------------------------------------------------


def test_rows_to_append_drops_incomplete_bar():
    # cached max 2026-10-16; provider returns 10-16 and a partial 10-19 bar;
    # now is 10:30 ET on 10-19 -> 10-19 is still in session.
    fetched = _aligned_frame(
        {"SPY": _symbol_df(["2026-10-16", "2026-10-19"])}
    )
    now = datetime(2026, 10, 19, 14, 30, tzinfo=timezone.utc)  # 10:30 ET
    new = rc.rows_to_append(
        fetched, pd.Timestamp("2026-10-16", tz="UTC"), now, close_hour=16, tz=TZ
    )
    assert new is None or len(new) == 0


def test_rows_to_append_returns_complete_newer_row():
    fetched = _aligned_frame(
        {"SPY": _symbol_df(["2026-10-16", "2026-10-19"])}
    )
    now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)  # 10-19 session closed
    new = rc.rows_to_append(
        fetched, pd.Timestamp("2026-10-16", tz="UTC"), now, close_hour=16, tz=TZ
    )
    kept = [pd.Timestamp(t).strftime("%Y-%m-%d") for t in new.index]
    assert kept == ["2026-10-19"]


def test_rows_to_append_skips_cached_dates():
    fetched = _aligned_frame({"SPY": _symbol_df(["2026-10-16", "2026-10-19"])})
    now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    new = rc.rows_to_append(
        fetched, pd.Timestamp("2026-10-19", tz="UTC"), now, close_hour=16, tz=TZ
    )
    assert new is None or len(new) == 0


def test_assert_complete_rows_refuses_incomplete():
    frame = _symbol_df(["2026-10-19"])
    now = datetime(2026, 10, 19, 14, 30, tzinfo=timezone.utc)  # 10:30 ET, open
    with pytest.raises(RuntimeError, match="refusing to write incomplete bar"):
        rc.assert_complete_rows(frame, now, close_hour=16, tz=TZ)


def test_assert_complete_rows_passes_complete():
    frame = _symbol_df(["2026-10-16"])
    now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    rc.assert_complete_rows(frame, now, close_hour=16, tz=TZ)  # should not raise


# ---------------------------------------------------------------------------
# End-to-end refresh flow (offline, tmp raw dir)
# ---------------------------------------------------------------------------


def test_refresh_dry_run_is_noop_and_writes_nothing(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_cache(raw_dir, "SPY", ["2026-10-16"])
    before_hash = _cache_hash(raw_dir, "SPY")

    frames = {s: _symbol_df(["2026-10-16", "2026-10-19"]) for s in SYMBOLS}
    monkeypatch.setattr(rc, "fetch_universe", _stub_fetch(frames))

    now = datetime(2026, 10, 19, 14, 30, tzinfo=timezone.utc)
    result = rc.refresh(
        raw_dir=raw_dir,
        symbols=["SPY"],
        now_et=now,
        dry_run=True,
        reports_dir=tmp_path / "reports",
    )

    assert result["total_appended"] == 0
    assert result["symbols"][0]["status"] == "no-op"
    assert _cache_hash(raw_dir, "SPY") == before_hash
    assert not (tmp_path / "reports").exists()


def test_refresh_appends_complete_session(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_cache(raw_dir, "SPY", ["2026-10-16"])
    before_hash = _cache_hash(raw_dir, "SPY")

    frames = {s: _symbol_df(["2026-10-16", "2026-10-19"]) for s in SYMBOLS}
    monkeypatch.setattr(rc, "fetch_universe", _stub_fetch(frames))

    now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)  # 10-19 complete
    result = rc.refresh(
        raw_dir=raw_dir,
        symbols=["SPY"],
        now_et=now,
        dry_run=False,
        reports_dir=tmp_path / "reports",
    )

    assert result["total_appended"] == 1
    rows, max_date = _cache_state(raw_dir, "SPY")
    assert rows == 2
    assert max_date == "2026-10-19"
    assert _cache_hash(raw_dir, "SPY") != before_hash


def test_refresh_is_idempotent_on_re_run(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_cache(raw_dir, "SPY", ["2026-10-16"])
    frames = {s: _symbol_df(["2026-10-16", "2026-10-19"]) for s in SYMBOLS}
    monkeypatch.setattr(rc, "fetch_universe", _stub_fetch(frames))
    now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)

    rc.refresh(raw_dir=raw_dir, symbols=["SPY"], now_et=now, dry_run=False,
               reports_dir=tmp_path / "reports")
    hash_after_first = _cache_hash(raw_dir, "SPY")

    result = rc.refresh(raw_dir=raw_dir, symbols=["SPY"], now_et=now, dry_run=False,
                        reports_dir=tmp_path / "reports")
    assert result["total_appended"] == 0
    assert result["symbols"][0]["status"] == "no-op"
    assert _cache_hash(raw_dir, "SPY") == hash_after_first


def test_refresh_never_writes_incomplete_bar(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_cache(raw_dir, "SPY", ["2026-10-16"])
    before_hash = _cache_hash(raw_dir, "SPY")

    # Provider returns a partial 10-19 bar while the session is open; nothing
    # newer and complete exists, so this must remain a no-op (not a refusal,
    # since the partial bar is dropped before the write assertion).
    frames = {s: _symbol_df(["2026-10-16", "2026-10-19"]) for s in SYMBOLS}
    monkeypatch.setattr(rc, "fetch_universe", _stub_fetch(frames))
    now = datetime(2026, 10, 19, 14, 30, tzinfo=timezone.utc)

    result = rc.refresh(raw_dir=raw_dir, symbols=["SPY"], now_et=now, dry_run=False,
                        reports_dir=tmp_path / "reports")
    assert result["total_appended"] == 0
    assert _cache_hash(raw_dir, "SPY") == before_hash


def test_manifest_content(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_cache(raw_dir, "SPY", ["2026-10-16"])
    frames = {s: _symbol_df(["2026-10-16", "2026-10-19"]) for s in SYMBOLS}
    monkeypatch.setattr(rc, "fetch_universe", _stub_fetch(frames))
    now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    reports_dir = tmp_path / "reports"

    result = rc.refresh(raw_dir=raw_dir, symbols=["SPY"], now_et=now, dry_run=False,
                        reports_dir=reports_dir)

    manifest_path = reports_dir / "raw_cache_integrity_manifest.json"
    assert manifest_path.exists()
    import json

    manifest = json.loads(manifest_path.read_text())
    assert "generated_at" in manifest and manifest["generated_at"]
    entry = manifest["symbols"]["SPY"]
    for key in ("cached_rows", "cached_max", "appended_rows", "after_rows",
                "after_max", "status"):
        assert key in entry
    assert entry["appended_rows"] == 1
    assert entry["after_max"] == "2026-10-19"
    assert entry["sha256"] == hashlib.sha256(
        rc.cache_path(raw_dir, "SPY").read_bytes()
    ).hexdigest()


def test_universe_symbols_includes_vix():
    symbols = rc.universe_symbols()
    assert "^VIX" in symbols
    assert "SPY" in symbols
    assert len(symbols) == 8


def test_session_is_complete_reuse():
    # Sanity check the reused guard matches the documented rule.
    assert session_is_complete("2026-10-16",
                               datetime(2026, 10, 19, 14, 30, tzinfo=timezone.utc))
    assert not session_is_complete("2026-10-19",
                                   datetime(2026, 10, 19, 14, 30, tzinfo=timezone.utc))
