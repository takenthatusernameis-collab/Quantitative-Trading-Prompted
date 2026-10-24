"""Offline tests for the canonical raw-cache append-only guard.

The guard (Cycle 866) exists because ``YFinanceFetcher._save_cached`` previously
wrote the downloaded window straight to ``data/raw/<symbol>.parquet``, so any
``force=True`` fetch with ``raw_dir=None`` could silently truncate committed
history (the SPY.parquet regression recorded in Cycle 865).

No network access is required: ``yfinance.download`` is stubbed with synthetic
frames, and writes are directed at a temporary raw dir.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.data.yfinance_fetcher as yf_mod  # noqa: E402

FIELDS = ("Open", "High", "Low", "Close", "Volume")


def _symbol_df(dates):
    index = pd.DatetimeIndex(
        [pd.Timestamp(d, tz="UTC") for d in dates], name="Date"
    )
    data = {f: [100.0 if f != "Volume" else 1_000_000.0] * len(dates) for f in FIELDS}
    return pd.DataFrame(data, index=index)


def _stub_download(symbol_frames: dict[str, pd.DataFrame]):
    """Replace yfinance.download with a deterministic frame lookup."""

    def fake_download(symbol, start, end, progress=False, auto_adjust=False,
                      group_by="ticker"):
        return symbol_frames.get(symbol)

    return fake_download


def test_save_cached_allows_append_when_download_reaches_further(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    # committed history ends 2026-10-16
    _symbol_df(["2026-10-16"]).to_parquet(raw_dir / "SPY.parquet")

    monkeypatch.setattr(yf_mod.yf, "download",
                        _stub_download({"SPY": _symbol_df(["2026-10-16", "2026-10-19"])}))
    fetcher = yf_mod.YFinanceFetcher(
        ["SPY"], "2026-10-01", "2026-10-20", raw_dir=str(raw_dir), append_only=True
    )
    fetcher.fetch(force=True)

    after = pd.read_parquet(raw_dir / "SPY.parquet")
    assert len(after) == 2
    assert pd.Timestamp(after.index.max()).strftime("%Y-%m-%d") == "2026-10-19"


def test_save_cached_refuses_truncating_download(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    # committed history ends 2026-10-22 (as in the real cache)
    _symbol_df(["2026-10-01", "2026-10-22"]).to_parquet(raw_dir / "SPY.parquet")
    before = (raw_dir / "SPY.parquet").read_bytes()

    # The provider returns a window that ends BEFORE the committed history:
    # this is exactly the partial-window overwrite that truncated SPY.parquet
    # in Cycle 865 (17 rows, 2026-10-01 -> 2026-10-23, vs 8,491 committed).
    monkeypatch.setattr(yf_mod.yf, "download",
                        _stub_download({"SPY": _symbol_df(["2026-10-01", "2026-10-15"])}))
    fetcher = yf_mod.YFinanceFetcher(
        ["SPY"], "2026-10-01", "2026-10-15", raw_dir=str(raw_dir), append_only=True
    )
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        fetcher.fetch(force=True)

    # nothing was written
    assert (raw_dir / "SPY.parquet").read_bytes() == before


def test_save_cached_append_only_can_be_disabled(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _symbol_df(["2026-10-01", "2026-10-22"]).to_parquet(raw_dir / "SPY.parquet")

    monkeypatch.setattr(yf_mod.yf, "download",
                        _stub_download({"SPY": _symbol_df(["2026-10-01", "2026-10-23"])}))
    fetcher = yf_mod.YFinanceFetcher(
        ["SPY"], "2026-10-01", "2026-10-23", raw_dir=str(raw_dir),
        append_only=False,
    )
    # must not raise: the guard is opt-out, not opt-in
    fetcher.fetch(force=True)
    after = pd.read_parquet(raw_dir / "SPY.parquet")
    assert pd.Timestamp(after.index.max()).strftime("%Y-%m-%d") == "2026-10-23"


def test_save_cached_allows_write_when_no_committed_cache(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    monkeypatch.setattr(yf_mod.yf, "download",
                        _stub_download({"SPY": _symbol_df(["2026-10-01", "2026-10-23"])}))
    fetcher = yf_mod.YFinanceFetcher(
        ["SPY"], "2026-10-01", "2026-10-23", raw_dir=str(raw_dir), append_only=True
    )
    fetcher.fetch(force=True)
    after = pd.read_parquet(raw_dir / "SPY.parquet")
    assert len(after) == 2


def test_fetch_universe_default_is_append_only(monkeypatch, tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _symbol_df(["2026-10-01", "2026-10-22"]).to_parquet(raw_dir / "SPY.parquet")

    # Provider returns a window ending before the committed history end.
    monkeypatch.setattr(yf_mod.yf, "download",
                        _stub_download({"SPY": _symbol_df(["2026-10-01", "2026-10-15"])}))
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        yf_mod.fetch_universe(["SPY"], "2026-10-01", "2026-10-15",
                              raw_dir=str(raw_dir), force=True)