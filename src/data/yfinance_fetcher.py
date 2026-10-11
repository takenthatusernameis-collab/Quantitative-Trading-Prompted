"""Data ingestion for Yahoo Finance via yfinance.

Fetches daily OHLCV for a configurable symbol list, normalizes timezone-aware
dates, backfills missing dates via the union of all symbols' calendars, and
caches results to data/raw/ as parquet files.

Point-in-time safety: the fetcher only ever looks at data up to the requested
end date. No forward-looking calls are made.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd
import yaml
import yfinance as yf


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_settings() -> dict:
    """Load config/settings.yaml relative to the repository root."""
    path = _project_root() / "config" / "settings.yaml"
    with open(path, "r") as fh:
        return yaml.safe_load(fh) or {}


def _ensure_utc(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Normalize an index to tz-aware UTC, handling naive and aware input."""
    index = pd.to_datetime(index)
    if isinstance(index, pd.DatetimeIndex):
        if index.tz is None:
            return index.tz_localize("UTC", ambiguous="infer", nonexistent="shift_forward")
        return index.tz_convert("UTC")
    return pd.DatetimeIndex(index).tz_localize(
        "UTC", ambiguous="infer", nonexistent="shift_forward"
    )


class YFinanceFetcher:
    """Fetch and cache daily OHLCV from Yahoo Finance.

    Parameters
    ----------
    symbols:
        Iterable of ticker symbols (e.g. SPY, QQQ, IWM).
    start_date:
        Inclusive start date as YYYY-MM-DD.
    end_date:
        Inclusive end date as YYYY-MM-DD. Defaults to today.
    raw_dir:
        Directory for cached parquet files. Defaults to data/raw.
    """

    def __init__(
        self,
        symbols: Sequence[str],
        start_date: str,
        end_date: Optional[str] = None,
        raw_dir: Optional[str] = None,
    ) -> None:
        self.symbols: List[str] = list(symbols)
        self.start_date = start_date
        self.end_date = end_date or datetime.utcnow().strftime("%Y-%m-%d")

        settings = load_settings()
        data_cfg = settings.get("data", {})
        self.raw_dir = Path(raw_dir) if raw_dir else (
            _project_root() / data_cfg.get("raw_dir", "data/raw")
        )
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch(self, force: bool = False) -> pd.DataFrame:
        """Return a timezone-normalized DataFrame of daily OHLCV.

        The returned DataFrame has a DatetimeIndex (UTC) covering the union
        of all trading calendars across symbols. Missing values are filled
        forward within each symbol so every symbol is observed on every
        date; columns are MultiIndex (field, symbol).

        Existing parquet caches are reused unless ``force`` is True.
        """
        frames: dict[str, pd.DataFrame] = {}
        for symbol in self.symbols:
            cached = self._load_cached(symbol)
            if cached is not None and not force:
                frames[symbol] = cached
                continue
            downloaded = self._download(symbol)
            if downloaded is None or downloaded.empty:
                raise RuntimeError(f"No data returned for {symbol}")
            self._save_cached(symbol, downloaded)
            frames[symbol] = downloaded

        return self._align(frames)

    def fetch_symbol(self, symbol: str, force: bool = False) -> pd.DataFrame:
        """Fetch a single symbol and return its cleaned frame."""
        cached = self._load_cached(symbol)
        if cached is not None and not force:
            return cached
        downloaded = self._download(symbol)
        if downloaded is None or downloaded.empty:
            raise RuntimeError(f"No data returned for {symbol}")
        self._save_cached(symbol, downloaded)
        return downloaded

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _download(self, symbol: str) -> Optional[pd.DataFrame]:
        raw = yf.download(
            symbol,
            start=self.start_date,
            end=self.end_date,
            progress=False,
            auto_adjust=False,
            group_by="ticker",
        )
        if raw is None or raw.empty:
            return None

        # yfinance returns a MultiIndex (ticker, field) when group_by='ticker'
        if isinstance(raw.columns, pd.MultiIndex):
            raw = raw.xs(symbol, level=0, axis=1)

        raw = raw.rename(columns=str.title)
        for col in ("Open", "High", "Low", "Close", "Volume"):
            if col not in raw.columns:
                raw[col] = np.nan
        raw = raw[["Open", "High", "Low", "Close", "Volume"]]

        raw.index = _ensure_utc(raw.index)
        raw = raw[~raw.index.duplicated(keep="last")].sort_index()
        return raw

    def _cache_path(self, symbol: str) -> Path:
        safe = symbol.replace("/", "-").replace("=", "-")
        return self.raw_dir / f"{safe}.parquet"

    def _load_cached(self, symbol: str) -> Optional[pd.DataFrame]:
        path = self._cache_path(symbol)
        if not path.exists():
            return None
        try:
            df = pd.read_parquet(path)
        except Exception:
            return None
        if df.empty:
            return None
        df.index = _ensure_utc(df.index)
        return df.sort_index()

    def _save_cached(self, symbol: str, df: pd.DataFrame) -> None:
        df.to_parquet(self._cache_path(symbol))

    @staticmethod
    def _align(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Align all symbols onto a common calendar and forward-fill gaps."""
        if not frames:
            return pd.DataFrame()

        all_index = sorted(set().union(*[f.index for f in frames.values()]))
        all_index = pd.DatetimeIndex(all_index)
        all_index = all_index[(all_index.weekday < 5)]

        out = pd.DataFrame(index=all_index, columns=pd.MultiIndex.from_product(
            [["Open", "High", "Low", "Close", "Volume"], list(frames.keys())]
        ))
        for symbol, df in frames.items():
            reindexed = df.reindex(all_index)
            for col in ("Open", "High", "Low", "Close", "Volume"):
                s = reindexed[col].ffill()
                out[(col, symbol)] = s
        return out


def fetch_universe(
    symbols: Sequence[str],
    start_date: str,
    end_date: Optional[str] = None,
    raw_dir: Optional[str] = None,
    force: bool = False,
) -> pd.DataFrame:
    """Convenience wrapper used by the backtest engine."""
    fetcher = YFinanceFetcher(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        raw_dir=raw_dir,
    )
    return fetcher.fetch(force=force)