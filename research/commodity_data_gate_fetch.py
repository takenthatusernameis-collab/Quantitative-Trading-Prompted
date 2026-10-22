#!/usr/bin/env python3
"""Cycle 949 -- scratch-only upstream fetch for the commodity data gate.

What this tool does
-------------------
Fetches the daily OHLCV history of the frozen ``commoditytrend_001`` universe
(``DBC``, ``BNO``, ``UNG``, ``GLD``) from Yahoo Finance into a **scratch
directory** and writes a provenance report beside the frames. It is the
upstream half of the data-gate measurement; the measurement itself is
``research/commodity_data_gate_001.py``.

Why a scratch directory
-----------------------
The candidate is frozen and blocked by a *data* gate. The committed cache
under ``data/raw/`` carries the four instruments from 2015-01-02, a fetch
window rather than instrument history. This tool therefore never touches the
committed cache: it refuses to write anywhere inside the repository, so the
committed cache can only be rewritten in a separate, explicit step.

Price convention
----------------
The fetch uses ``auto_adjust=False``, which is the convention of the
repository's own fetcher (``src/data/yfinance_fetcher.py``): the ``Close``
column is split-adjusted by the upstream source but **not** dividend-adjusted.
The committed cache was fetched with the same convention, so the upstream
extension is directly comparable with it (the measurement verifies this
session by session).

Reproduction
------------
```bash
python research/commodity_data_gate_fetch.py
python research/commodity_data_gate_001.py
```
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parent.parent

SYMBOLS = ("DBC", "BNO", "UNG", "GLD")
DEFAULT_OUT_DIR = Path("/tmp/scratchpad/commodity_fetch")
DEFAULT_START = "2000-01-01"

#: The upstream source and the price field, stated in the provenance report.
SOURCE = "yahoo_finance"
PRICE_FIELD = "Close"
ADJUSTED_VS_RAW = (
    "raw (auto_adjust=False; the upstream close is split-adjusted but not "
    "dividend-adjusted -- the same convention as src/data/yfinance_fetcher.py)"
)


class FetchError(RuntimeError):
    """Raised when the fetch cannot be completed as specified (fails closed)."""


def _guard_out_dir(out_dir: Path) -> Path:
    """Refuse to write inside the repository (the committed cache is sacred)."""
    resolved = out_dir.resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise FetchError(
            f"refusing to write inside the repository: {resolved} "
            "(the committed cache is not rewritten by this tool)"
        )
    return resolved


def fetch_symbol(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Fetch one symbol and return the normalised OHLCV frame."""
    raw = yf.download(
        symbol,
        start=start,
        end=end,
        progress=False,
        auto_adjust=False,
        group_by="ticker",
    )
    if raw is None or raw.empty:
        raise FetchError(f"no data returned for {symbol}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw.xs(symbol, level=0, axis=1)
    raw = raw.rename(columns=str.title)
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in raw.columns:
            raw[col] = float("nan")
    raw = raw[["Open", "High", "Low", "Close", "Volume"]]
    idx = pd.to_datetime(raw.index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    raw.index = idx
    return raw[~raw.index.duplicated(keep="last")].sort_index()


def describe(symbol: str, frame: pd.DataFrame, retrieval_date: str) -> dict[str, Any]:
    """Provenance and coverage record for one fetched symbol."""
    close = frame["Close"].dropna()
    if close.empty:
        raise FetchError(f"{symbol}: the fetched frame carries no close")
    return {
        "symbol": symbol,
        "status": "OK",
        "source": SOURCE,
        "retrieval_date_utc": retrieval_date,
        "price_field": PRICE_FIELD,
        "adjusted_vs_raw": ADJUSTED_VS_RAW,
        "frequency": "daily",
        "rows": int(len(frame)),
        "close_rows": int(len(close)),
        "first_date": str(close.index.min().date()),
        "last_date": str(close.index.max().date()),
        "first_close": float(close.iloc[0]),
        "last_close": float(close.iloc[-1]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default="")
    args = parser.parse_args(argv)

    out_dir = _guard_out_dir(Path(args.out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    end = args.end or datetime.now(timezone.utc).date().isoformat()
    retrieval_date = datetime.now(timezone.utc).date().isoformat()

    provenance: list[dict[str, Any]] = []
    for symbol in SYMBOLS:
        frame = fetch_symbol(symbol, args.start, end)
        frame.to_parquet(out_dir / f"{symbol}.parquet")
        provenance.append(describe(symbol, frame, retrieval_date))
        print(
            f"  {symbol}: rows={len(frame)} "
            f"{provenance[-1]['first_date']}..{provenance[-1]['last_date']} "
            f"-> {out_dir / f'{symbol}.parquet'}"
        )

    report = {
        "cycle": 949,
        "task": "commodity_data_gate_measurement",
        "retrieval_date_utc": retrieval_date,
        "source": SOURCE,
        "price_field": PRICE_FIELD,
        "adjusted_vs_raw": ADJUSTED_VS_RAW,
        "request_start": args.start,
        "request_end": end,
        "output_dir": str(out_dir),
        "symbols": list(SYMBOLS),
        "provenance": provenance,
    }
    report_path = out_dir / "commodity_fetch_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"provenance report: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FetchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
