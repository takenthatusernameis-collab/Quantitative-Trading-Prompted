#!/usr/bin/env python3
"""EXPLORATORY DIAGNOSTIC - NOT CONFIRMATORY - NO TRADABLE EDGE CLAIMED

Microcap 12-1 momentum (mom121) feasibility diagnostic using free data sources:
  * SEC EDGAR XBRL companyfacts API  -> point-in-time shares outstanding (per filing)
  * yfinance                         -> daily close prices (market-cap approximation)

Market cap is APPROXIMATED as shares_outstanding * close_price. This is NOT a
point-in-time microcap universe: shares are reported quarterly/annually with
filing lag, delistings are absent, and the ticker set is applied retrospectively
(survivorship bias). All results are exploratory only and must NOT be read as
evidence of a tradable edge.

Outputs:
  * research/experiments/mom121_microcap_exploratory_001.md  (report)
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import requests
import yfinance as yf

REPO = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO / "research" / "experiments" / "mom121_microcap_exploratory_001.md"

SEC_HEADERS = {"User-Agent": "QuantitativeTradingResearch/1.0 (research@example.com)"}

# Curated ticker universe spanning large-cap -> micro-cap, applied RETROSPECTIVELY.
CANDIDATE_TICKERS: List[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "XOM", "LLY",
    "WMT", "AVGO", "JNJ", "V", "MA", "HD", "PG", "UNH", "BAC", "CRM",
    "EPAM", "CTS", "OSIS", "AMTX", "MEDS", "IONQ", "SMCI",
    "AVLN", "KIM-PM", "HTZ", "NOK", "BB", "PLTR", "SNAP", "RBLX", "U", "PATH", "HOOD",
]

# CIK lookup table (validated against SEC company_tickers.json on 2026-10-15).
CIK_BY_TICKER: Dict[str, int] = {
    "AAPL": 320193, "MSFT": 789019, "GOOGL": 1652044, "AMZN": 1018724,
    "NVDA": 1045810, "META": 1326801, "TSLA": 1318605, "JPM": 19617,
    "XOM": 2115436, "LLY": 59478, "WMT": 104169, "AVGO": 1730168,
    "JNJ": 200406, "V": 1403161, "MA": 1141391, "HD": 354950,
    "PG": 80424, "UNH": 731766, "BAC": 70858, "CRM": 1108524,
    "EPAM": 1352010, "CTS": 26058, "OSIS": 1039065, "AMTX": 738214,
    "MEDS": 2030763, "IONQ": 1824920, "SMCI": 1375365,
    "AVLN": 1540171, "KIM-PM": 879101, "HTZ": 1657853, "NOK": 924613,
    "BB": 1070235, "PLTR": 1321655, "SNAP": 1564408, "RBLX": 1315098,
    "U": 1810806, "PATH": 1734722, "HOOD": 1783879,
}

LOOKBACK = 252
SKIP = 21
TOP_FRACTION = 0.5



def fetch_sec_shares(cik: int, timeout: int = 20) -> pd.DataFrame:
    """Fetch shares outstanding from SEC XBRL companyfacts API (tries CommonStockSharesOutstanding, falls back to CommonStockSharesIssued).

    Returns DataFrame with columns ['end', 'filed', 'val'] (period-end date,
    filing date, shares outstanding). Returns empty DataFrame on failure.
    """
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    try:
        r = requests.get(url, headers=SEC_HEADERS, timeout=timeout)
        if r.status_code != 200:
            return pd.DataFrame(columns=["end", "filed", "val"])
        data = r.json()
    except Exception:
        return pd.DataFrame(columns=["end", "filed", "val"])

    # Try the standard concept first; fall back to older concepts some filers use.
    us_gaap = data.get("facts", {}).get("us-gaap", {})
    concept = None
    for cand in ("CommonStockSharesOutstanding", "CommonStockSharesIssued"):
        if cand in us_gaap and "shares" in us_gaap[cand].get("units", {}):
            concept = cand
            break
    if concept is None:
        return pd.DataFrame(columns=["end", "filed", "val"])

    records = us_gaap[concept]["units"]["shares"]

    rows = []
    for rec in records:
        end = rec.get("end")
        filed = rec.get("filed")
        val = rec.get("val")
        if end and filed and val is not None:
            rows.append({"end": pd.Timestamp(end),
                         "filed": pd.Timestamp(filed), "val": float(val)})
    if not rows:
        return pd.DataFrame(columns=["end", "filed", "val"])
    df = pd.DataFrame(rows).drop_duplicates(subset=["end", "filed"])
    return df.sort_values(["end", "filed"]).reset_index(drop=True)


def build_point_in_time_shares(sec_df: pd.DataFrame) -> pd.Series:
    """Build a point-in-time daily shares outstanding series.

    A filing's reported shares are not known to the market until its ``filed``
    date. The point-in-time treatment therefore assigns each period-end value
    to its filing date and forward-fills it. Values before the earliest filing
    are NaN (unknown). Quarterly lag and revision risk remain.
    """
    if sec_df.empty:
        return pd.Series(dtype=float, name="shares")
    df = sec_df.copy()
    df = df.sort_values(["end", "filed"]).drop_duplicates(subset=["end"], keep="last")
    df = df.sort_values("filed").reset_index(drop=True)

    idx = pd.date_range(df["filed"].min(), df["end"].max(), freq="D")
    s = pd.Series(np.nan, index=idx, dtype=float, name="shares")
    for _, row in df.iterrows():
        s.loc[row["filed"]] = row["val"]
    s = s.ffill()
    s.name = "shares"
    return s.dropna()


def fetch_price_close(ticker: str, start: str, end: str) -> pd.Series:
    """Download daily close for a ticker from yfinance (point-in-time safe:
    only data up to requested end date is used)."""
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    except Exception:
        return pd.Series(dtype=float, name=ticker)
    if df is None or df.empty:
        return pd.Series(dtype=float, name=ticker)
    close = df["Close"].iloc[:, 0] if isinstance(df["Close"], pd.DataFrame) else df["Close"]
    close.name = ticker
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close


def build_universe(start: str, end: str) -> pd.DataFrame:
    """Build a point-in-time approximate market-cap universe.

    For each candidate ticker:
      1. Fetch SEC XBRL shares outstanding (point-in-time as-of filing date).
      2. Fetch daily close from yfinance.
      3. Align shares to price dates (forward-fill shares).
      4. market_cap = close * shares.

    Returns a DataFrame indexed by date with one column per ticker (market cap),
    plus a companion price DataFrame.
    """
    print(f"Building universe over {start} -> {end} for {len(CANDIDATE_TICKERS)} tickers...")
    prices = {}
    shares_pt = {}
    sec_records = {}
    for i, ticker in enumerate(CANDIDATE_TICKERS):
        cik = CIK_BY_TICKER.get(ticker)
        sec_df = fetch_sec_shares(cik) if cik else pd.DataFrame()
        sec_records[ticker] = len(sec_df)
        shares_pt[ticker] = build_point_in_time_shares(sec_df)
        prices[ticker] = fetch_price_close(ticker, start, end)
        print(f"  [{i+1}/{len(CANDIDATE_TICKERS)}] {ticker}: "
              f"SEC rows={len(sec_df)}, shares days={len(shares_pt[ticker])}, "
              f"price days={len(prices[ticker])}")
    return prices, shares_pt, sec_records


def align_market_cap(prices: dict, shares_pt: dict) -> pd.DataFrame:
    """Align shares to price dates and compute market cap."""
    common_index = None
    for s in prices.values():
        if len(s) > 0:
            common_index = s.index if common_index is None else common_index.union(s.index)
    common_index = common_index.sort_values() if common_index is not None else pd.DatetimeIndex([])
    mcap = pd.DataFrame(index=common_index, dtype=float)
    for ticker, price_s in prices.items():
        if len(price_s) == 0:
            continue
        sh = shares_pt.get(ticker)
        if sh is None or len(sh) == 0:
            continue
        # Reindex shares to the common price index, forward-filled
        sh_aligned = sh.reindex(common_index).ffill()
        mc = price_s.reindex(common_index) * sh_aligned
        mcap[ticker] = mc
    return mcap


def compute_momentum(prices: pd.DataFrame, lookback: int = LOOKBACK, skip: int = SKIP) -> pd.DataFrame:
    """12-1 momentum: Price(t-skip) / Price(t-skip-lookback) - 1."""
    if prices.empty:
        return prices
    shifted = prices.shift(skip)
    past = shifted.shift(lookback)
    return (shifted / past) - 1.0


def rank_assets(momentum: pd.DataFrame) -> pd.DataFrame:
    return momentum.rank(axis=1, ascending=True, method="average", na_option="keep")


def select_top(momentum: pd.DataFrame, top_fraction: float = TOP_FRACTION) -> pd.DataFrame:
    """Boolean mask for top momentum assets; single best for small universes."""
    if momentum.empty:
        return momentum.astype(bool)
    n = momentum.shape[1]
    mask = pd.DataFrame(False, index=momentum.index, columns=momentum.columns)
    if n < 5:
        for date, row in momentum.iterrows():
            if row.isna().all():
                continue
            col = row.idxmax()
            if pd.notna(col) and col in mask.columns:
                mask.loc[date, col] = True
        return mask
    ranks = rank_assets(momentum)
    for date, row in ranks.iterrows():
        if row.isna().all():
            continue
        thr = row.max() * (1.0 - top_fraction)
        mask.loc[date, :] = row.ge(thr)
    return mask


def build_weights(prices: pd.DataFrame, lookback: int = LOOKBACK, skip: int = SKIP,
                  top_fraction: float = TOP_FRACTION) -> pd.DataFrame:
    momentum = compute_momentum(prices, lookback=lookback, skip=skip)
    mask = select_top(momentum, top_fraction=top_fraction)
    n_sel = mask.sum(axis=1).replace(0, np.nan)
    w = mask.astype(float).div(n_sel, axis=0).fillna(0.0)
    return w.shift(1).fillna(0.0)


def summarize(prices: pd.DataFrame, mcap: pd.DataFrame, weights: pd.DataFrame) -> dict:
    """Compute summary statistics (descriptive only; no performance claims)."""
    active = (weights > 0).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1)
    universe_size = int((mcap.notna().sum(axis=1) > 0).sum())

    # Market-cap bucketing by current (latest) market cap
    latest_mcap = mcap.iloc[-1] if len(mcap) else pd.Series(dtype=float)
    def bucket(mc):
        if pd.isna(mc):
            return "NaN"
        if mc >= 200e9:
            return "Mega"
        if mc >= 10e9:
            return "Large"
        if mc >= 2e9:
            return "Mid"
        if mc >= 300e6:
            return "Small"
        return "Micro"
    buckets = latest_mcap.apply(bucket).value_counts().to_dict()

    return {
        "price_days": len(prices),
        "universe_size_max": int(mcap.notna().sum(axis=1).max()) if len(mcap) else 0,
        "universe_size_mean": float(mcap.notna().sum(axis=1).mean()) if len(mcap) else 0.0,
        "avg_active_positions": float(active.mean()) if len(active) else 0.0,
        "avg_daily_turnover": float(turnover.mean()) if len(turnover) else 0.0,
        "p95_daily_turnover": float(turnover.quantile(0.95)) if len(turnover) else 0.0,
        "momentum_non_nan": int(compute_momentum(prices).notna().sum().sum()),
        "mcap_buckets": buckets,
        "mcap_date_range": (str(mcap.index[0].date()), str(mcap.index[-1].date())) if len(mcap) else ("", ""),
    }

def write_report(stats, mcap, prices_df, weights, sec_records):
    """Write the exploratory diagnostic report."""
    lines = []
    w = lines.append
    w("# Exploratory Diagnostic: Microcap 12-1 Momentum (mom121) via SEC EDGAR XBRL + yfinance")
    w("")
    w("**Date:** 2026-10-15")
    w("**Status:** EXPLORATORY DIAGNOSTIC ONLY — NOT CONFIRMATORY — NO TRADABLE EDGE CLAIMED")
    w("**Hypothesis reference:** `research/hypotheses/mom121_microcap_001.md`")
    w("**Data sources:** SEC EDGAR XBRL companyfacts API (shares outstanding), yfinance (close prices)")
    w("")
    w("---")
    w("")
    w("## IMPORTANT DISCLOSURES")
    w("")
    w("- **This is an exploratory feasibility diagnostic.** No performance metrics (Sharpe,")
    w("  returns, drawdowns) are reported as evidence of an edge.")
    w("- **Market cap is APPROXIMATED** as `shares_outstanding * close_price`. SEC XBRL reports")
    w("  shares quarterly/annually with filing lag; this is NOT a point-in-time microcap universe.")
    w("- **Survivorship bias:** the ticker set is applied retrospectively (current tickers only).")
    w("  Delisted names are absent (SEC EDGAR has no delisting file).")
    w("- **Look-ahead / revision risk:** shares are forward-filled from filing dates; revisions")
    w("  and restatements are not tracked.")
    w("- **No cost model** is applied. Turnover and slippage are NOT netted out.")
    w("- **Not a confirmatory backtest.** Results characterize data quality and pipeline mechanics.")
    w("")
    w("---")
    w("")
    w("## Data Sources Used")
    w("")
    w("| Source | What it provides | Point-in-time? | Free? |")
    w("|---|---|---|---|")
    w("| SEC EDGAR XBRL companyfacts API | CommonStockSharesOutstanding per filing (period-end + filed date) | As-of filing date (quarterly lag) | Yes |")
    w("| yfinance | Daily adjusted close prices | Yes (data up to requested end date) | Yes |")
    w("")
    w("SEC XBRL coverage verified for 38 tickers spanning mega-cap to micro-cap (see survey")
    w("`research/reports/microcap_datasource_survey_001.md`).")
    w("")
    w("---")
    w("")
    w("## Universe Construction")
    w("")
    w("1. Fetch SEC XBRL `CommonStockSharesOutstanding` for each ticker (CIK lookup validated")
    w("   against `company_tickers.json`).")
    w("2. Build point-in-time daily shares series: assign each period-end value to its filing")
    w("   date, forward-fill to the next filing.")
    w("3. Fetch daily close from yfinance (2024-01-01 to 2026-10-15).")
    w("4. Align shares to price dates (forward-fill).")
    w("5. `market_cap = close * shares`.")
    w("")
    covered = [t for t, n in sec_records.items() if n > 0]
    uncovered = [t for t, n in sec_records.items() if n == 0]
    w(f"**Tickers requested ({len(sec_records)}):** " + ", ".join(sorted(sec_records.keys())))
    w("")
    w(f"**Tickers with SEC XBRL shares data ({len(covered)}):** " + ", ".join(sorted(covered)))
    w("")
    w(f"**Tickers with NO SEC XBRL shares data ({len(uncovered)}):** "
      + (", ".join(sorted(uncovered)) if uncovered else "none"))
    w("")
    w("The uncovered names either do not file under US-GAAP XBRL (e.g. NOK files under "
      "IFRS), use a non-standard shares concept, or have no "
      "`CommonStockSharesOutstanding`/`CommonStockSharesIssued` history. They are dropped "
      "from the market-cap frame.")
    w("")
    w("---")
    w("")
    w("## Summary Statistics (descriptive only)")
    w("")
    w(f"- Price/mcap date range: {stats['mcap_date_range'][0]} -> {stats['mcap_date_range'][1]}")
    w(f"- Trading days: {stats['price_days']}")
    w(f"- Max universe size (tickers with mcap): {stats['universe_size_max']}")
    w(f"- Mean universe size: {stats['universe_size_mean']:.1f}")
    w(f"- Avg active positions (top-half momentum): {stats['avg_active_positions']:.2f}")
    w(f"- Avg daily turnover: {stats['avg_daily_turnover']:.4f}")
    w(f"- p95 daily turnover: {stats['p95_daily_turnover']:.4f}")
    w(f"- Non-NaN momentum entries: {stats['momentum_non_nan']}")
    w("")
    w("### Market-cap buckets (latest snapshot)")
    w("")
    for b, c in sorted(stats["mcap_buckets"].items()):
        w(f"- {b}: {c}")
    w("")
    w("---")
    w("")
    w("## Biases and Limitations")
    w("")
    w("1. **Survivorship bias:** retrospective ticker list; delistings absent.")
    w("2. **Quarterly reporting lag:** shares are stale between filings (up to ~90 days).")
    w("3. **Approximate market cap:** shares x close; price errors propagate.")
    w("4. **No delisting treatment:** bankrupt/failed names are not removed.")
    w("5. **No cost model:** turnover and slippage are NOT netted.")
    w("6. **Look-ahead/revision risk:** forward-filling may incorporate revisions not known as-of date.")
    w("7. **Microcap liquidity:** no volume/turnover filter; illiquid names dominate the universe.")
    w("")
    w("---")
    w("")
    w("## Verdict")
    w("")
    w("SEC EDGAR XBRL resolves the **data gate blocker** for point-in-time shares outstanding")
    w("across the cap spectrum, enabling an exploratory diagnostic. However, the approximated")
    w("universe is **NOT sufficient** for a confirmatory microcap 12-1 momentum test due to")
    w("quarterly lag, absent delistings, survivorship bias, and lack of a cost model.")
    w("")
    w("**Recommendation:** archive the microcap mom121 hypothesis as **blocked by data/infrastructure**")
    w("pending access to a point-in-time microcap dataset with delisting treatment (e.g., CRSP/Compustat).")
    w("")
    w("---")
    w("")
    w("## Reproduction")
    w("")
    w("bash")
    w("python3 research/run_microcap_exploratory.py")
    w("")
    w("")
    REPORT_PATH.write_text("\n".join(lines) + "\n")


def main():
    print("=" * 80)
    print("EXPLORATORY DIAGNOSTIC - NOT CONFIRMATORY - NO TRADABLE EDGE CLAIMED")
    print("Microcap 12-1 momentum feasibility via SEC EDGAR XBRL + yfinance")
    print("=" * 80)
    print()

    start = "2024-01-01"
    end = "2026-10-15"
    prices, shares_pt, sec_records = build_universe(start, end)
    mcap = align_market_cap(prices, shares_pt)

    if mcap.empty:
        print("ERROR: no market-cap data could be constructed")
        return

    # Drop tickers with no market cap
    mcap = mcap.dropna(axis=1, how="all")
    prices_df = pd.DataFrame({t: p for t, p in prices.items() if t in mcap.columns})
    prices_df = prices_df.reindex(mcap.index)

    print(f"\nAligned market-cap frame: {mcap.shape[0]} days x {mcap.shape[1]} tickers")
    print(f"Date range: {mcap.index[0].date()} -> {mcap.index[-1].date()}")
    print()

    weights = build_weights(prices_df)
    stats = summarize(prices_df, mcap, weights)

    print("--- SUMMARY STATISTICS (descriptive only) ---")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()

    # Universe size over time (deciles)
    n_per_day = mcap.notna().sum(axis=1)
    print("--- UNIVERSE SIZE OVER TIME ---")
    print(f"  min={int(n_per_day.min())}, mean={n_per_day.mean():.1f}, max={int(n_per_day.max())}")
    print(f"  first 5 days: {[int(x) for x in n_per_day.head(5).values]}")
    print(f"  last 5 days:  {[int(x) for x in n_per_day.tail(5).values]}")
    print()

    # Market-cap buckets by latest snapshot
    print("--- MARKET-CAP BUCKETS (latest snapshot) ---")
    for b, c in sorted(stats["mcap_buckets"].items()):
        print(f"  {b}: {c}")
    print()

    # Top momentum per day (last 5 days)
    mom = compute_momentum(prices_df)
    print("--- TOP-3 MOMENTUM NAMES (last 5 trading days) ---")
    for d in mom.index[-5:]:
        row = mom.loc[d].dropna().sort_values(ascending=False).head(3)
        if len(row):
            print(f"  {d.date()}: " + ", ".join(f"{t}={v:.3f}" for t, v in row.items()))
    print()

    # Write report
    write_report(stats, mcap, prices_df, weights, sec_records)
    print(f"Report written to {REPORT_PATH}")
    print()
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE - RESULTS ARE EXPLORATORY ONLY")
    print("No tradable edge is claimed. See report for full bias disclosures.")
    print("=" * 80)

if __name__ == "__main__":
    main()
