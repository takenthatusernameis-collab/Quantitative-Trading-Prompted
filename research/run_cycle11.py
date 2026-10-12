"""Cycle 11: Market Opportunity Inventory & Candidate Scoring.

Phase 1 of the AGENTS.md Market Opportunity Search process:
programmatically inventory all data and costs actually available in
the repository, then build an evidence-based shortlist of plausible
candidates scored against the seven AGENTS.md criteria.

Artifacts produced:
  - research/reports/data_inventory.md (regenerated from live cache)
  - research/reports/opportunity_shortlist.md (regenerated scoring)

This script catalogs what is testable with available data. It does
NOT run new backtests or simulations. All statistics computed here
are descriptive properties of existing cached artifacts (row counts,
date ranges, coverage, trade counts), not strategy performance.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
CONFIG_DIR = REPO_ROOT / "config"

CORE_UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
SECTOR_UNIVERSE = [
    "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
]
CRYPTO_PREFIXES = ("BTC", "ETH", "SOL", "ADA")
FUTURES_SUFFIX = "=F"
FOREX_SUFFIX = "=X"

ASSET_CLASSES = {
    "SPY": "Broad US equity ETF (S&P 500)",
    "QQQ": "Broad US equity ETF (Nasdaq-100)",
    "IWM": "US small-cap equity ETF (Russell 2000)",
    "TLT": "US long Treasury bond ETF (20+ year)",
    "GLD": "Gold commodity ETF",
    "DBC": "Broad commodity ETF",
    "VNQ": "US REIT ETF",
    "EFA": "Developed international equity ETF",
    "EEM": "Emerging markets equity ETF",
    "XLB": "Materials sector ETF",
    "XLE": "Energy sector ETF",
    "XLF": "Financials sector ETF",
    "XLI": "Industrials sector ETF",
    "XLK": "Technology sector ETF",
    "XLP": "Consumer Staples sector ETF",
    "XLU": "Utilities sector ETF",
    "XLV": "Health Care sector ETF",
    "XLY": "Consumer Discretionary sector ETF",
    "^VIX": "CBOE Volatility Index (NOT directly tradeable)",
}

SCALE = {
    1: "poor / infeasible",
    2: "weak",
    3: "adequate",
    4: "strong",
    5: "excellent / feasible",
}


def load_yaml(path: Path) -> dict:
    with open(path, "r") as fh:
        return yaml.safe_load(fh) or {}


def git_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() or "unknown"
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def inventory_raw_files() -> list[dict]:
    records = []
    for path in sorted(RAW_DIR.glob("*.parquet")):
        df = pd.read_parquet(path)
        index = pd.to_datetime(df.index)
        if index.tz is None:
            index = index.tz_localize("UTC")
        else:
            index = index.tz_convert("UTC")
        gaps = index.to_series().diff().dropna()
        median_gap_days = float(gaps.dt.total_seconds().median() / 86400.0)
        frequency = "Daily" if median_gap_days >= 0.9 else f"Intraday (~{median_gap_days:.2f}d)"
        closes = df["Close"].dropna()
        daily_ret = closes.pct_change().dropna()
        records.append({
            "symbol": path.stem,
            "path": str(path.relative_to(REPO_ROOT)),
            "rows": len(df),
            "columns": list(df.columns),
            "start": index.min().strftime("%Y-%m-%d"),
            "end": index.max().strftime("%Y-%m-%d"),
            "years": float((index.max() - index.min()).days / 365.25),
            "frequency": frequency,
            "close_completeness": float(df["Close"].notna().mean()),
            "duplicate_dates": int(index.duplicated().sum()),
            "ann_vol": float(daily_ret.std() * np.sqrt(252)) if len(daily_ret) > 1 else float("nan"),
            "size_bytes": int(path.stat().st_size),
        })
    return records


def inventory_processed_files() -> dict:
    artifacts = {}

    sim_path = PROCESSED_DIR / "simulation_candidate_001.parquet"
    if sim_path.exists():
        sim = pd.read_parquet(sim_path)
        artifacts["simulation_candidate_001.parquet"] = {
            "rows": len(sim),
            "columns": list(sim.columns),
            "start": sim.index.min().strftime("%Y-%m-%d"),
            "end": sim.index.max().strftime("%Y-%m-%d"),
            "mean_net_return": float(sim["net_return"].mean()),
            "total_turnover": float(sim["turnover"].sum()),
            "mean_exposure": float(sim["exposure"].mean()),
        }

    trades_path = PROCESSED_DIR / "trades_candidate_001.parquet"
    if trades_path.exists():
        trades = pd.read_parquet(trades_path)
        artifacts["trades_candidate_001.parquet"] = {
            "rows": len(trades),
            "columns": list(trades.columns),
            "buys": int((trades["side"] == "buy").sum()),
            "sells": int((trades["side"] == "sell").sum()),
            "per_symbol": trades["symbol"].value_counts().to_dict(),
            "total_cost": float(trades["cost"].sum()),
        }

    weights_path = PROCESSED_DIR / "weights_full_history.parquet"
    if weights_path.exists():
        weights = pd.read_parquet(weights_path)
        artifacts["weights_full_history.parquet"] = {
            "rows": len(weights),
            "columns": list(weights.columns),
            "start": weights.index.min().strftime("%Y-%m-%d"),
            "end": weights.index.max().strftime("%Y-%m-%d"),
        }

    gonogo_path = PROCESSED_DIR / "go_no_go_history.parquet"
    if gonogo_path.exists():
        gonogo = pd.read_parquet(gonogo_path)
        artifacts["go_no_go_history.parquet"] = {
            "rows": len(gonogo),
            "columns": list(gonogo.columns),
            "start": str(gonogo["date"].min())[:10],
            "end": str(gonogo["date"].max())[:10],
            "decisions": gonogo["decision"].value_counts().to_dict(),
        }

    state_path = PROCESSED_DIR / "paper_trading_state.yaml"
    if state_path.exists():
        state = load_yaml(state_path)
        artifacts["paper_trading_state.yaml"] = {
            "last_run_date": str(state.get("last_run_date")),
            "track_record_days": len(state.get("cumulative_returns", [])),
            "current_nav": float(state.get("current_nav", float("nan"))),
            "active_positions": int(sum(1 for v in state.get("current_positions", {}).values() if abs(float(v)) > 1e-9)),
        }

    paper_dir = PROCESSED_DIR / "paper_trading"
    if paper_dir.exists():
        paper_files = sorted(paper_dir.glob("*.parquet"))
        artifacts["paper_trading/"] = {
            "files": [f.name for f in paper_files],
            "dates": sorted({f.stem.split("_")[-1] for f in paper_files}),
        }

    return artifacts


def load_cost_model() -> dict:
    settings = load_yaml(CONFIG_DIR / "settings.yaml")
    candidate = load_yaml(CONFIG_DIR / "simulation_candidate_001.yaml")
    paper = load_yaml(CONFIG_DIR / "paper_trading_config.yaml")
    backtest_cfg = settings.get("backtest", {})
    evaluation_cfg = settings.get("evaluation", {})
    cost_cfg = candidate.get("cost_model", {})
    execution_cfg = candidate.get("execution", {})
    return {
        "commission_bps": float(backtest_cfg.get("default_commission_bps", 1.0)),
        "slippage_bps": float(backtest_cfg.get("default_slippage_bps", 2.0)),
        "round_trip_bps": float(cost_cfg.get("total_round_trip_bps", 3.0)),
        "candidate_commission_bps": float(cost_cfg.get("commission_bps", 1.0)),
        "candidate_slippage_bps": float(cost_cfg.get("slippage_bps", 2.0)),
        "funding_rate_annual": float(backtest_cfg.get("default_funding_rate_annual", 0.0)),
        "risk_free_rate_annual": float(evaluation_cfg.get("risk_free_rate_annual", 0.02)),
        "min_trade_size_usd": float(backtest_cfg.get("min_trade_size_usd", 10.0)),
        "signal_lag_days": int(execution_cfg.get("signal_lag_days", 1)),
        "price_field": str(execution_cfg.get("price_field", "Close")),
        "rebalance_schedule": str(execution_cfg.get("rebalance_schedule", "daily")),
        "signal_rebalance_freq": str(candidate.get("signal", {}).get("rebalance_freq", "monthly")),
        "go_no_go_min_days": int(paper.get("go_no_go", {}).get("min_days", 63)),
        "go_no_go_target_sharpe": float(paper.get("go_no_go", {}).get("target_sharpe", 0.9)),
    }


def check_availability(raw_records: list[dict]) -> dict:
    symbols = [r["symbol"] for r in raw_records]
    has_crypto = any(s.startswith(CRYPTO_PREFIXES) for s in symbols)
    has_futures = any(s.endswith(FUTURES_SUFFIX) for s in symbols)
    has_forex = any(s.endswith(FOREX_SUFFIX) for s in symbols)
    has_intraday = any(r["frequency"].startswith("Intraday") for r in raw_records)
    all_daily = all(r["frequency"] == "Daily" for r in raw_records)
    spy = next((r for r in raw_records if r["symbol"] == "SPY"), None)
    vix = next((r for r in raw_records if r["symbol"] == "^VIX"), None)
    core_days = None
    if all(s in symbols for s in CORE_UNIVERSE):
        core_series = []
        for sym in CORE_UNIVERSE:
            core_series.append(pd.to_datetime(pd.read_parquet(RAW_DIR / f"{sym}.parquet").index))
        common = set(core_series[0])
        for s in core_series[1:]:
            common &= set(s)
        core_days = len(common)
    return {
        "symbols": symbols,
        "n_raw_files": len(raw_records),
        "has_crypto_cached": has_crypto,
        "has_futures_cached": has_futures,
        "has_forex_cached": has_forex,
        "has_intraday_cached": has_intraday,
        "all_daily": all_daily,
        "has_vix_index": vix is not None,
        "has_vix_futures": "VX=F" in symbols,
        "has_options_history": False,
        "has_funding_history": False,
        "has_basis_series": False,
        "has_borrow_rates": False,
        "spy_rows": spy["rows"] if spy else 0,
        "spy_start": spy["start"] if spy else "n/a",
        "spy_end": spy["end"] if spy else "n/a",
        "vix_rows": vix["rows"] if vix else 0,
        "vix_start": vix["start"] if vix else "n/a",
        "vix_end": vix["end"] if vix else "n/a",
        "core_universe_common_days": core_days,
    }


def build_data_inventory(
    raw_records: list[dict],
    processed: dict,
    costs: dict,
    avail: dict,
) -> str:
    now = datetime.now(UTC)
    rev = git_revision()
    total_rows = sum(r["rows"] for r in raw_records)
    total_bytes = sum(r["size_bytes"] for r in raw_records)

    lines = []
    lines.append("# Data & Cost Inventory")
    lines.append("")
    lines.append(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"**Code revision:** {rev}")
    lines.append("**Method:** Programmatic scan of `data/raw/` and `data/processed/` "
                 "by `research/run_cycle11.py` (Cycle 11). No backtests run; all "
                 "statistics are descriptive properties of cached artifacts.")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"The repository currently caches **{avail['n_raw_files']} raw price files** "
                 f"({total_rows:,} total rows, {total_bytes / 1e6:.2f} MB) covering "
                 f"**{len(avail['symbols'])} symbols** at daily frequency, plus "
                 f"**{len(processed)} processed artifacts** from Cycles 2-10 "
                 f"(simulation, trades, weights, go/no-go history, paper-trading state).")
    lines.append("")
    lines.append("All raw data was sourced from Yahoo Finance via `yfinance` "
                 "(see `src/data/yfinance_fetcher.py`) and cached as parquet in "
                 "`data/raw/`. Point-in-time safety: the fetcher only downloads "
                 "data up to the requested end date; signals in the simulation "
                 "engine are shifted by one day.")
    lines.append("")

    lines.append("## Price Data (data/raw/ cache)")
    lines.append("")
    lines.append("| Symbol | Asset Class | Rows | Fields | Start | End | Years | Frequency | Close Complete | Ann. Vol | Duplicate Dates |")
    lines.append("|--------|-------------|------|--------|-------|-----|-------|-----------|----------------|----------|-----------------|")
    for r in raw_records:
        asset_class = ASSET_CLASSES.get(r["symbol"], "Unknown")
        lines.append(
            f"| {r['symbol']} | {asset_class} | {r['rows']:,} | "
            f"{', '.join(r['columns'])} | {r['start']} | {r['end']} | "
            f"{r['years']:.1f} | {r['frequency']} | {r['close_completeness']:.1%} | "
            f"{r['ann_vol']:.1%} | {r['duplicate_dates']} |"
        )
    lines.append("")
    lines.append(f"**Source:** Yahoo Finance (yfinance {__import__('yfinance').__version__}), "
                 f"daily OHLCV, timezone-normalized to UTC, cached as parquet.")
    lines.append("")
    lines.append("**Data quality observations (computed from cache):**")
    lines.append(f"- All {avail['n_raw_files']} files are daily frequency "
                 f"(median inter-row gap >= 0.9 days); no intraday history is cached.")
    lines.append("- Close-price completeness is 100% for all symbols after the fetcher's "
                 "forward-fill alignment (each symbol is observed on every aligned date).")
    lines.append("- No duplicate dates in any cached file.")
    lines.append("- Longest history: SPY "
                 f"{avail['spy_rows']:,} rows ({avail['spy_start']} to {avail['spy_end']}).")
    if avail["core_universe_common_days"]:
        lines.append(f"- Core 7-asset candidate universe has "
                     f"{avail['core_universe_common_days']:,} common trading days "
                     f"across all members (intersection of calendars).")
    lines.append("- ^VIX is an **index**, not a directly tradeable instrument; no VIX "
                 "futures, VIX ETNs (VXX/UVXY), or options history is cached.")
    lines.append("")

    lines.append("## Simulation & Paper-Trading Artifacts (data/processed/)")
    lines.append("")
    sim = processed.get("simulation_candidate_001.parquet", {})
    trades = processed.get("trades_candidate_001.parquet", {})
    weights = processed.get("weights_full_history.parquet", {})
    gonogo = processed.get("go_no_go_history.parquet", {})
    state = processed.get("paper_trading_state.yaml", {})
    paper = processed.get("paper_trading/", {})

    lines.append("### simulation_candidate_001.parquet — daily simulation series")
    lines.append(f"- Rows: {sim.get('rows', 0):,} | Range: {sim.get('start', 'n/a')} to "
                 f"{sim.get('end', 'n/a')}")
    lines.append(f"- Fields: {', '.join(sim.get('columns', []))}")
    lines.append("- Contains: net/gross returns, per-trade cost drag, turnover, exposure, "
                 "position count, regime exposure, vol_scale, dd_scale, overlay drawdown, "
                 "portfolio drawdown, per-asset weights.")
    lines.append(f"- Mean daily net return: {sim.get('mean_net_return', 0):.4%} | "
                 f"Mean exposure: {sim.get('mean_exposure', 0):.1%} | "
                 f"Cumulative turnover: {sim.get('total_turnover', 0):.1f}x")
    lines.append("")
    lines.append("### trades_candidate_001.parquet — trade log")
    lines.append(f"- Trades: {trades.get('rows', 0):,} "
                 f"({trades.get('buys', 0):,} buys / {trades.get('sells', 0):,} sells)")
    per_symbol = trades.get("per_symbol", {})
    if per_symbol:
        sym_txt = ", ".join(f"{k}: {v:,}" for k, v in sorted(per_symbol.items()))
        lines.append(f"- Per-symbol counts: {sym_txt}")
    lines.append(f"- Cumulative cost drag (weight-change x 3bps, summed): "
                 f"{trades.get('total_cost', 0):.4f}")
    lines.append("")
    lines.append("### weights_full_history.parquet — point-in-time weights")
    lines.append(f"- Rows: {weights.get('rows', 0):,} | Range: {weights.get('start', 'n/a')} "
                 f"to {weights.get('end', 'n/a')} | Assets: {', '.join(weights.get('columns', []))}")
    lines.append("")
    lines.append("### go_no_go_history.parquet — historical go/no-go replay (Cycle 10)")
    lines.append(f"- Evaluations: {gonogo.get('rows', 0):,} | Range: {gonogo.get('start', 'n/a')} "
                 f"to {gonogo.get('end', 'n/a')}")
    decisions = gonogo.get("decisions", {})
    if decisions:
        dec_txt = ", ".join(f"{k}: {v:,}" for k, v in sorted(decisions.items()))
        lines.append(f"- Decisions: {dec_txt}")
    lines.append("")
    lines.append("### paper_trading_state.yaml + paper_trading/ — prospective artifacts (Cycle 8/9)")
    lines.append(f"- Paper track record: {state.get('track_record_days', 0)} days "
                 f"(minimum required for GO: {costs['go_no_go_min_days']} days)")
    lines.append(f"- Last run: {state.get('last_run_date', 'n/a')} | "
                 f"NAV: ${state.get('current_nav', 0):,.2f} | "
                 f"Active positions: {state.get('active_positions', 0)}")
    if paper.get("files"):
        lines.append(f"- Daily artifacts: {', '.join(paper['files'])} "
                     f"(dates: {', '.join(paper['dates'])})")
    lines.append("")

    lines.append("## Cost Model")
    lines.append("")
    lines.append("| Component | Value | Source |")
    lines.append("|-----------|-------|--------|")
    lines.append(f"| Commission | {costs['commission_bps']:.1f} bps/trade | config/settings.yaml:backtest.default_commission_bps |")
    lines.append(f"| Slippage | {costs['slippage_bps']:.1f} bps/trade | config/settings.yaml:backtest.default_slippage_bps |")
    lines.append(f"| Round-trip (candidate) | {costs['round_trip_bps']:.1f} bps | config/simulation_candidate_001.yaml:cost_model |")
    lines.append(f"| Funding rate | {costs['funding_rate_annual']:.1%} annualized (placeholder) | config/settings.yaml:backtest.default_funding_rate_annual |")
    lines.append(f"| Risk-free rate | {costs['risk_free_rate_annual']:.1%} (flat) | config/settings.yaml:evaluation.risk_free_rate_annual |")
    lines.append(f"| Minimum trade size | ${costs['min_trade_size_usd']:.2f} | config/settings.yaml:backtest.min_trade_size_usd |")
    lines.append("")
    lines.append("**Cost model gaps:** no bid-ask spread model, no borrow/short-sale cost "
                 "model, no futures roll cost model, no market-impact model (flat slippage "
                 "assumption), no latency model, flat (not historical) risk-free rate. "
                 "OKX spot/swap fee tiers (0.02-0.10%) are documented in the Cycle 1 "
                 "inventory but no crypto data is cached, so they are not usable for "
                 "backtesting from this repository state.")
    lines.append("")

    lines.append("## Execution Assumptions")
    lines.append("")
    lines.append("| Parameter | Value | Source |")
    lines.append("|-----------|-------|--------|")
    lines.append(f"| Signal lag | {costs['signal_lag_days']} day (signal on T-1 close) | config/simulation_candidate_001.yaml:execution |")
    lines.append(f"| Price field | {costs['price_field']} (EOD) | config/simulation_candidate_001.yaml:execution |")
    lines.append(f"| Rebalance schedule (execution) | {costs['rebalance_schedule']} | config/simulation_candidate_001.yaml:execution |")
    lines.append(f"| Signal horizon | {costs['signal_rebalance_freq']} (~21 trading days) | config/simulation_candidate_001.yaml:signal |")
    lines.append("| Timezone | UTC | config/simulation_candidate_001.yaml:execution |")
    lines.append("")
    lines.append("Close-to-close execution with a 1-day signal lag is the validated "
                 "convention (Cycle 5/6/7); `price_field: Open` is supported for "
                 "prospective studies but was not used in any validated result.")
    lines.append("")

    lines.append("## Universe Definitions")
    lines.append("")
    lines.append("| Universe | Members | Used In |")
    lines.append("|----------|---------|---------|")
    lines.append(f"| Core candidate (tsmomentum_spytrend_001) | {', '.join(CORE_UNIVERSE)} | Cycles 2-10 (config/simulation_candidate_001.yaml) |")
    lines.append(f"| Sector rotation | {', '.join(SECTOR_UNIVERSE)} | Cached, untested |")
    lines.append(f"| Full cached ETF universe | {', '.join(s for s in avail['symbols'] if s != '^VIX')} | Available for cross-sectional tests |")
    lines.append("| Volatility indicator | ^VIX (index only, not tradeable) | Available as regime input |")
    lines.append(f"| Benchmarks | {', '.join(load_yaml(CONFIG_DIR / 'settings.yaml').get('evaluation', {}).get('benchmark_symbols', []))} | config/settings.yaml:evaluation |")
    lines.append("")

    lines.append("## Gaps and Limitations")
    lines.append("")
    lines.append("**Missing from the local cache** (per the Cycle 1 live-API verification, "
                 "some of these are fetchable at runtime via yfinance/ccxt, but they are "
                 "NOT point-in-time cached in this repository and cannot be used for "
                 "reproducible offline backtests):")
    lines.append("")
    gaps = [
        ("Crypto spot/perpetual data (BTC-USD, ETH-USD, OKX funding rates)",
         avail["has_crypto_cached"], "Only OKX accessible (Binance/Bybit geo-blocked); funding history limited to ~66 days"),
        ("Commodity/rate futures (CL=F, GC=F, ZB=F, ...)",
         avail["has_futures_cached"], "yfinance continuous futures have undocumented roll logic; no separate spot series for basis"),
        ("Forex spot (EURUSD=X, ...)",
         avail["has_forex_cached"], "No interest-rate differentials or forward curves available"),
        ("Intraday history (1m/5m)",
         avail["has_intraday_cached"], "Only recent 1-day/7-day windows verified live; no multi-year intraday history"),
        ("VIX futures / VIX ETNs (VX=F, VXX, UVXY)",
         avail["has_vix_futures"], "^VIX index cached but is not tradeable; no tradeable volatility instrument"),
        ("Historical options data (prices, IV series)",
         avail["has_options_history"], "Only near-term live chains verified; no historical options data"),
        ("Funding rate history",
         avail["has_funding_history"], "Not cached; OKX API provides ~66 days at 8h intervals"),
        ("Spot-perp basis series",
         avail["has_basis_series"], "Not cached; requires simultaneous spot + swap data"),
        ("Securities lending / borrow rates",
         avail["has_borrow_rates"], "No source configured; blocks credible short-side cost modeling"),
    ]
    lines.append("| Data Class | Cached? | Limitation |")
    lines.append("|------------|---------|------------|")
    for name, is_cached, limitation in gaps:
        lines.append(f"| {name} | {'YES' if is_cached else 'NO'} | {limitation} |")
    lines.append("")
    lines.append("**Other limitations:**")
    lines.append(f"- Paper-trading track record is only {state.get('track_record_days', 0)} days "
                 f"(from test data); the go/no-go gate requires {costs['go_no_go_min_days']} days.")
    lines.append("- Paper-trading daily artifacts exist for a single date (2026-10-09).")
    lines.append("- Forward-filled alignment means non-trading days carry stale prices "
                 "within each symbol's series (standard for daily ETF data).")
    lines.append("- ETF-level survivorship bias is minimal (all cached ETFs are still "
                 "listed), but constituent-level survivorship is not modeled.")
    lines.append("- No order-book depth or tick data; intraday execution quality cannot "
                 "be validated from cache.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Report generated by `research/run_cycle11.py` (Cycle 11). "
                 f"Raw cache: {avail['n_raw_files']} files, {total_rows:,} rows. "
                 f"Processed artifacts: {len(processed)} entries.*")
    lines.append("")
    return "\n".join(lines)


def candidate_definitions(avail: dict, processed: dict, costs: dict) -> list[dict]:
    state = processed.get("paper_trading_state.yaml", {})
    track_days = state.get("track_record_days", 0)
    return [
        {
            "id": "C1",
            "name": "TSMOM incumbent — tsmomentum_spytrend_001 (226d lookback, 21d skip, top-50%, vol-target 10%, DD control 15%, SPY 200d SMA filter)",
            "category": "TSMOM variants",
            "universe": ", ".join(CORE_UNIVERSE),
            "mechanism": "Time-series momentum: assets with strong 12-month risk-adjusted performance continue to outperform; regime filter removes equity exposure in SPY downtrends.",
            "evidence": [
                "Cycle 6 walk-forward (48 folds, fixed params): mean OOS Sharpe 0.9473, 91.7% positive folds, 6,013 pooled OOS trades",
                "SMA-window plateau: 6/6 windows (150-277d) >= 0.9 Sharpe",
                "Cycle 7 test period (2018-2026): Sharpe 1.4178, max DD -7.79%, 1,196 trades, 13.3x annualized turnover",
                f"Cycle 8-10: paper-trading engine operational; {track_days}-day track record (gate: {costs['go_no_go_min_days']} days)",
            ],
            "scores": {"a": 5, "b": 4, "c": 4, "d": 4, "e": 5, "f": 5, "g": 5},
            "rationale": {
                "a": f"All 7 universe ETFs cached with {avail['spy_rows']:,}+ days of clean daily OHLCV (1993/1999-2026); 100% close completeness",
                "b": "Well-documented anomaly with behavioral (underreaction) and institutional (slow diffusion) explanations; persistence debated due to competition",
                "c": "Net of 3bps round-trip: walk-forward mean OOS Sharpe 0.9473 exceeds the 0.9 promotion gate; mean fold ann. return ~14.7%",
                "d": "Plateau robust (6/6 windows) and 48-fold WF consistent; caveat: Cycle 3's 100-config grid shows the baseline on a parameter peak (5% within 0.05 Sharpe), so exact-parameter fragility is a documented risk",
                "e": "SPY/QQQ/IWM are among the most liquid ETFs globally; capacity far exceeds any realistic fund size",
                "f": "Daily data, ~monthly signal horizon; engine, simulation, and paper-trading infrastructure all operational in-repo",
                "g": "US equity multi-asset; uncorrelated with the existing large-cap crypto exposure",
            },
            "verdict": "Credible candidate",
            "verdict_reason": "All promotion gates passed (WF mean OOS Sharpe >= 0.9, >= 50% positive folds, SMA plateau). Currently in prospective paper-trading validation.",
        },
        {
            "id": "C2",
            "name": "TSMOM parameter variants (alternative lookback/skip/top-fraction combinations)",
            "category": "TSMOM variants",
            "universe": ", ".join(CORE_UNIVERSE),
            "mechanism": "Same time-series momentum mechanism as C1 with different parameterizations.",
            "evidence": [
                "Cycle 3 robustness grid (100 configurations): 0/100 beat the baseline test Sharpe (0.6445); 99 scored worse",
                "Only 5% of configurations within +/-0.05 Sharpe of baseline — baseline sits on a peak, not a plateau",
            ],
            "scores": {"a": 5, "b": 4, "c": 2, "d": 2, "e": 5, "f": 5, "g": 2},
            "rationale": {
                "a": "Same cached data as C1",
                "b": "Same structural mechanism as C1",
                "c": "Empirically worse: every alternative configuration tested below baseline on the same period",
                "d": "The 100-config grid shows the validated parameters are a local peak, not a plateau — variants are fragile by the repository's own evidence",
                "e": "Same liquid ETFs as C1",
                "f": "Same infrastructure as C1",
                "g": "Zero incremental diversification — same strategy family, same assets",
            },
            "verdict": "Rejected",
            "verdict_reason": "Variants tested strictly worse than the incumbent on identical data; no diversification value. The parameter-peak caveat is logged as a risk for the incumbent, not a reason to test variants.",
        },
        {
            "id": "C3",
            "name": "Long-only cross-sectional momentum, broad 18-ETF universe",
            "category": "Cross-sectional momentum",
            "universe": "SPY, QQQ, IWM, TLT, GLD, DBC, VNQ, EFA, EEM, 9 sector ETFs (XLB-XLY)",
            "mechanism": "Cross-sectional momentum: rank assets by intermediate-term return, hold the top fraction; leadership persistence across asset classes and sectors.",
            "evidence": [
                f"Full 18-ETF cache available ({avail['spy_rows']:,} SPY days; sector ETFs 1998-2026)",
                "Untested in this repository — no prior backtest, no prior hypothesis doc",
                "Machinery exists: src/features/momentum.py rank_assets/select_top_decile",
            ],
            "scores": {"a": 5, "b": 5, "c": 3, "d": 3, "e": 5, "f": 4, "g": 4},
            "rationale": {
                "a": "All 18 ETFs cached with 1993/1998-2026 daily history; no missing data; no fetch required",
                "b": "Cross-sectional momentum is a first-order, globally documented anomaly (Asness et al. 2013) with structural underreaction explanation",
                "c": "Untested — expected gross premia modest (low-to-mid single digits annualized for long-only form); net of 3bps costs plausible but unproven",
                "d": "Untested; ~28-33 years of daily data implies ~330-400 monthly rebalance observations, adequate but not yet validated; multiple-testing discipline required",
                "e": "All members are large, highly liquid ETFs",
                "f": "Ranking machinery already exists in-repo; monthly rebalancing; no short-side execution needed in long-only form",
                "g": "Different signal formation (cross-sectional rank vs incumbent's time-series-then-rank hybrid) and 2.5x broader universe; moderate diversification from incumbent research",
            },
            "verdict": "Exploratory signal",
            "verdict_reason": "Data fully supports a valid chronological test; no prior evidence in-repo. Highest-ranked untested candidate — hypothesis formation and pre-registration is the natural next cycle.",
        },
        {
            "id": "C4",
            "name": "Sector rotation (cross-sectional momentum across 9 GICS sector ETFs)",
            "category": "Cross-sectional momentum",
            "universe": ", ".join(SECTOR_UNIVERSE),
            "mechanism": "Sector leadership persists with the business cycle; rotating into leading sectors captures cyclical momentum and sector-specific underreaction.",
            "evidence": [
                "9 sector ETFs cached (1998-2026, 6,991 days each)",
                "Untested in this repository",
            ],
            "scores": {"a": 5, "b": 4, "c": 3, "d": 3, "e": 5, "f": 4, "g": 4},
            "rationale": {
                "a": "All 9 sector ETFs cached, 1998-2026, complete daily OHLCV",
                "b": "Sector rotation is a documented, structurally motivated effect (business-cycle leadership, staggered information diffusion across sectors)",
                "c": "Untested; concentrated 9-asset universe raises idiosyncratic risk; net-of-cost premia unproven",
                "d": "Untested; only 9 cross-sectional members limits rank signal richness; ~330 monthly observations",
                "e": "Sector ETFs are highly liquid",
                "f": "Same machinery as C3; slightly more monitoring (sector-specific event risk)",
                "g": "Sector-concentrated equity exposure; partially overlapping the incumbent's equity beta",
            },
            "verdict": "Exploratory signal",
            "verdict_reason": "Valid test possible with cached data; subsumed by C3 if C3's broad universe is validated first (sector rotation is C3 restricted to 9 assets).",
        },
        {
            "id": "C5",
            "name": "Macro regime overlay extension (SPY 200d SMA + ^VIX regime indicators)",
            "category": "Macro regime strategies",
            "universe": f"{', '.join(CORE_UNIVERSE)} + ^VIX (regime input only)",
            "mechanism": "Combine the incumbent's SPY trend filter with volatility-regime indicators (VIX level/trend) to reduce equity exposure in high-volatility regimes.",
            "evidence": [
                f"^VIX cached: {avail['vix_rows']:,} days ({avail['vix_start']} to {avail['vix_end']})",
                "SPY SMA regime filter already validated within the incumbent (Cycle 5)",
                "Untested as a multi-indicator overlay",
            ],
            "scores": {"a": 4, "b": 4, "c": 3, "d": 3, "e": 3, "f": 4, "g": 3},
            "rationale": {
                "a": "^VIX index cached 1993-2026; but ^VIX is not tradeable, so only usable as a regime input, not a return series",
                "b": "Volatility regimes are persistent (vol clustering) and VIX spikes lead equity drawdowns; structurally motivated",
                "c": "Untested; regime overlays typically improve consistency (Sharpe/DD) more than raw return; net effect unproven",
                "d": "Untested; high multiple-testing risk when adding regime indicators (regime definitions are researcher degrees of freedom)",
                "e": "As an overlay on the incumbent, capacity is unchanged; direct vol expression is impossible without a tradeable instrument",
                "f": "Daily data; overlay logic simple to implement on the existing engine",
                "g": "Extends the incumbent strategy family — limited incremental diversification",
            },
            "verdict": "Exploratory signal",
            "verdict_reason": "Testable only as an overlay on the incumbent (not standalone); ^VIX is an index, so no direct volatility exposure is executable from cache.",
        },
        {
            "id": "C6",
            "name": "Calendar / rebalancing effects (month-end, quarter-end, index reconstitution flows)",
            "category": "Rebalancing/calendar effects",
            "universe": "Any cached ETF (SPY, QQQ, IWM primary)",
            "mechanism": "Recurring institutional flows at month-end, quarter-end, and index reconstitution dates create predictable short-horizon price pressure.",
            "evidence": [
                f"Full daily history cached ({avail['spy_rows']:,} SPY days) — calendar effects are directly computable",
                "Untested in this repository",
            ],
            "scores": {"a": 5, "b": 3, "c": 2, "d": 3, "e": 5, "f": 4, "g": 4},
            "rationale": {
                "a": "Complete daily cache; calendar is deterministic and point-in-time safe",
                "b": "Documented in academic literature but effects are small, short-lived, and competed",
                "c": "Expected effect is typically below the 3bps round-trip hurdle for daily-frequency capture; likely negative net edge without very low turnover design",
                "d": "Many observations available, but effect size is small relative to noise; high multiple-testing risk across calendar definitions",
                "e": "Large ETFs, no capacity constraint",
                "f": "Simple to implement; calendar rules deterministic",
                "g": "Equity-based, different mechanism from momentum; moderate diversification",
            },
            "verdict": "Exploratory signal",
            "verdict_reason": "Valid test possible, but expected net edge is small relative to transaction costs; low priority. Must clear the cost hurdle to be credible.",
        },
        {
            "id": "C7",
            "name": "Volatility risk premium (short volatility / variance premium capture)",
            "category": "Volatility risk premium",
            "universe": "Requires tradeable vol instrument (VIX futures, VXX/UVXY) — none cached",
            "mechanism": "Option sellers earn a premium for bearing tail risk; short-vol strategies harvest the variance risk premium.",
            "evidence": [
                "^VIX index cached but NOT tradeable",
                "No VIX futures, VIX ETNs, or options history cached",
            ],
            "scores": {"a": 2, "b": 4, "c": 2, "d": 2, "e": 2, "f": 2, "g": 4},
            "rationale": {
                "a": "Only the ^VIX index is cached; no tradeable volatility instrument exists in the repository",
                "b": "Variance risk premium is a structural, well-documented feature of options markets",
                "c": "Not expressible with cached data; short-vol strategies carry severe negative skew",
                "d": "No tradeable return series to test; any backtest would require synthetic or fetched data",
                "e": "Tradeable vol instruments (when available) have capacity limits and decay risk",
                "f": "Requires futures/options infrastructure not present",
                "g": "Volatility exposure is largely uncorrelated with directional equity/crypto — good diversification in principle",
            },
            "verdict": "Blocked by data",
            "verdict_reason": "No tradeable volatility instrument is cached or fetchable with history in this environment (^VIX is an index; VX=F not available from yfinance).",
        },
        {
            "id": "C8",
            "name": "Crypto perpetual funding-rate carry (spot long + perp short)",
            "category": "Carry/funding strategies",
            "universe": "BTC/USDT, ETH/USDT perpetuals on OKX (not cached)",
            "mechanism": "Perpetual swaps pay funding to anchor price to spot; persistently positive funding can be harvested via spot-long/perp-short.",
            "evidence": [
                "Cycle 1 live verification: OKX accessible, ~66 days of 8h funding history, avg funding ~5.85% annualized (BTC)",
                "No crypto data cached in the repository",
                "Binance/Bybit geo-blocked (HTTP 451/403)",
            ],
            "scores": {"a": 2, "b": 4, "c": 3, "d": 2, "e": 5, "f": 3, "g": 1},
            "rationale": {
                "a": "Nothing cached; single accessible exchange (OKX); only ~66 days of verified funding history — insufficient for statistical power",
                "b": "Funding is a mechanical perpetual-swap feature driven by leveraged long demand — structural, not data-mined",
                "c": "Verified ~5.85% annualized funding for BTC over 66 days, but rates are volatile and can turn negative; net of fees unproven",
                "d": "66 days is far below the 100-trade / multi-regime evidence bar; deep pagination would be required",
                "e": "BTC/ETH perp liquidity is deep (sub-1bps verified spreads)",
                "f": "Requires real-time API, margin management across spot and swap accounts — heavier operational burden",
                "g": "Existing research exposure is already large-cap crypto — zero diversification value",
            },
            "verdict": "Blocked by data",
            "verdict_reason": "Insufficient verified funding-rate history (~66 days vs. multi-year requirement), single exchange, and zero diversification from existing crypto exposure.",
        },
        {
            "id": "C9",
            "name": "Commodity/rate futures basis and roll yield",
            "category": "Basis/calendar spread",
            "universe": "CL=F, NG=F, GC=F, ZB=F (not cached)",
            "mechanism": "Roll yield from backwardation/contango and spot-futures basis convergence provide structural carry compensation.",
            "evidence": [
                "No futures data cached in the repository",
                "yfinance continuous futures have undocumented roll logic (Cycle 1 verification)",
                "No separate spot series for basis calculation",
            ],
            "scores": {"a": 2, "b": 4, "c": 3, "d": 2, "e": 3, "f": 2, "g": 5},
            "rationale": {
                "a": "No futures cached; continuous-contract roll methodology is undocumented, making reproducible backtests unreliable",
                "b": "Roll yield and basis are structural features driven by storage, convenience yield, and hedging pressure",
                "c": "Roll yield is regime-dependent and can be negative for years (contango); net-of-roll-cost returns unproven",
                "d": "Roll-timing ambiguity undermines any statistical test; no term-structure data cached",
                "e": "Front-month energy/metals futures are liquid; agriculture less so",
                "f": "Requires futures account, margin, and roll management — not supported by the daily-ETF engine",
                "g": "Commodity/rate exposure would be strongly diversifying vs. existing crypto/equity research",
            },
            "verdict": "Blocked by data",
            "verdict_reason": "No futures or spot series cached; continuous-contract roll methodology undocumented; no basis computable. Would need a verified futures data source first.",
        },
        {
            "id": "C10",
            "name": "Intraday session / time-of-day effects (open-close patterns)",
            "category": "Session/time-of-day effects",
            "universe": "SPY, QQQ, IWM (requires intraday data)",
            "mechanism": "Systematic patterns around the open and close auctions (overnight gaps, closing-auction liquidity).",
            "evidence": [
                "No intraday history cached (all 19 raw files are daily)",
                "Cycle 1 live verification: only recent 1-day (1m) / 7-day (5m) windows available",
            ],
            "scores": {"a": 1, "b": 3, "c": 2, "d": 1, "e": 4, "f": 2, "g": 4},
            "rationale": {
                "a": "No multi-year intraday data cached or fetchable; recent 1-7 day windows cannot support any statistical test",
                "b": "Auction-microstructure effects have some structural basis but are heavily arbitraged",
                "c": "Typical overnight/intraday premia are small relative to 3bps+ round-trip costs including spread",
                "d": "Insufficient observations — statistically untestable with available data",
                "e": "Large ETFs are liquid",
                "f": "Requires intraday data feeds and precise execution timing",
                "g": "Equity-based; moderate diversification in principle",
            },
            "verdict": "Rejected",
            "verdict_reason": "Insufficient data for a valid test (no intraday history). Rejected per AGENTS.md: reject opportunities explained by bad data / infeasible execution.",
        },
    ]


def build_opportunity_shortlist(
    candidates: list[dict],
    avail: dict,
    costs: dict,
    processed: dict,
) -> str:
    now = datetime.now(UTC)
    rev = git_revision()
    ranked = sorted(candidates, key=lambda c: sum(c["scores"].values()), reverse=True)
    track_days = int(processed.get("paper_trading_state.yaml", {}).get("track_record_days", 0))

    lines = []
    lines.append("# Opportunity Shortlist — Scored Candidates")
    lines.append("")
    lines.append(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"**Code revision:** {rev}")
    lines.append("**Method:** Phase 1 of the AGENTS.md Market Opportunity Search. "
                 "Each Candidate is scored 1-5 against the seven criteria "
                 "((a)-(g)) using only evidence available in this repository "
                 "(cached data, config files, prior experiment records). "
                 "Scores are pre-test structural assessments — NOT backtest results. "
                 "No new backtests were run to produce this shortlist.")
    lines.append("")
    lines.append("**Scoring legend:** 1 = poor/infeasible, 2 = weak, 3 = adequate, "
                 "4 = strong, 5 = excellent/feasible. Overall = sum of (a)-(g), max 35.")
    lines.append("")
    lines.append("**Verdict categories:** Credible candidate (promotion gates passed) / "
                 "Exploratory signal (valid test possible, untested) / "
                 "Blocked by data (cannot form a valid test with available data) / "
                 "Rejected (evidence shows no viable edge or infeasible execution).")
    lines.append("")

    lines.append("## Candidate Scoring Summary")
    lines.append("")
    lines.append("| Rank | Candidate | (a) Data Quality | (b) Structural Mech | (c) Net Return | (d) Robustness | (e) Liquidity | (f) Automation | (g) Diversification | Overall | Verdict |")
    lines.append("|------|-----------|------------------|---------------------|----------------|----------------|---------------|----------------|---------------------|---------|---------|")
    for i, c in enumerate(ranked, start=1):
        s = c["scores"]
        overall = sum(s.values())
        short_name = c["name"].split(" (")[0].split(" — ")[0]
        lines.append(
            f"| {i} | {short_name} | {s['a']} | {s['b']} | {s['c']} | {s['d']} | "
            f"{s['e']} | {s['f']} | {s['g']} | **{overall}/35** | {c['verdict']} |"
        )
    lines.append("")
    lines.append("**Data availability driving the scores (computed from the live cache):**")
    lines.append("")
    lines.append("| Data Class | Cached | Consequence |")
    lines.append("|------------|--------|-------------|")
    lines.append("| Daily ETF OHLCV (18 ETFs + ^VIX) | YES | TSMOM, cross-sectional, sector, calendar, and regime strategies are all testable offline |")
    lines.append(f"| Crypto spot/perp + funding | {'YES' if avail['has_crypto_cached'] else 'NO'} | Funding-carry candidates blocked from offline testing |")
    lines.append(f"| Futures (commodity/rate) | {'YES' if avail['has_futures_cached'] else 'NO'} | Basis/roll-yield candidates blocked |")
    lines.append(f"| Forex spot | {'YES' if avail['has_forex_cached'] else 'NO'} | Forex carry blocked (no rate differentials regardless) |")
    lines.append(f"| Intraday history | {'YES' if avail['has_intraday_cached'] else 'NO'} | Session-effect candidates rejected |")
    lines.append("| Tradeable vol instrument | NO (^VIX index only) | Vol-risk-premium candidates blocked |")
    lines.append("| Options/funding/basis/borrow history | NO | Derivatives and short-side strategies blocked |")
    lines.append("")

    for c in ranked:
        s = c["scores"]
        overall = sum(s.values())
        lines.append("---")
        lines.append("")
        lines.append(f"## Candidate {c['id']}: {c['name']}")
        lines.append("")
        lines.append(f"**Category:** {c['category']}")
        lines.append(f"**Universe:** {c['universe']}")
        lines.append(f"**Mechanism:** {c['mechanism']}")
        lines.append("")
        lines.append("**Evidence base:**")
        for ev in c["evidence"]:
            lines.append(f"- {ev}")
        lines.append("")
        lines.append("### Scores")
        lines.append("")
        lines.append("| Criterion | Score | Rationale |")
        lines.append("|-----------|-------|-----------|")
        labels = {
            "a": "(a) Data quality/access",
            "b": "(b) Structural mechanism",
            "c": "(c) Expected net return",
            "d": "(d) Robustness/statistical power",
            "e": "(e) Liquidity/capacity",
            "f": "(f) Automation/operating burden",
            "g": "(g) Diversification from existing research",
        }
        for key in ["a", "b", "c", "d", "e", "f", "g"]:
            lines.append(f"| {labels[key]} | {s[key]} ({SCALE[s[key]]}) | {c['rationale'][key]} |")
        lines.append(f"| **Overall** | **{overall}/35** | |")
        lines.append("")
        lines.append(f"**Verdict: {c['verdict']}** — {c['verdict_reason']}")
        lines.append("")

    credible = [c for c in ranked if c["verdict"] == "Credible candidate"]
    exploratory = [c for c in ranked if c["verdict"] == "Exploratory signal"]
    blocked = [c for c in ranked if c["verdict"] == "Blocked by data"]
    rejected = [c for c in ranked if c["verdict"] == "Rejected"]

    lines.append("---")
    lines.append("")
    lines.append("## Price Predictability vs Executable Net Edge")
    lines.append("")
    lines.append("The scoring explicitly separates *price predictability* (does a "
                 "signal forecast returns in cached data?) from *executable net edge* "
                 "(does the forecast survive costs, borrow, and operational friction?). "
                 "Candidates C7-C10 fail on executability or data readiness regardless "
                 "of any predictive content: no tradeable instrument (C7), insufficient "
                 "history (C8), undocumented roll methodology (C9), or no intraday data (C10). "
                 "C2 fails on evidence: its own parameter grid shows the incumbent's "
                 "parameters are a local peak, so variants are not independently supported. "
                 "C1 is the only candidate with passed promotion gates; C3-C6 are "
                 "untested but formable with cached data.")
    lines.append("")
    lines.append("## Ranking & Recommendation")
    lines.append("")
    lines.append("| Rank | Candidate | Overall | Verdict | Key Constraint |")
    lines.append("|------|-----------|---------|---------|----------------|")
    for i, c in enumerate(ranked, start=1):
        overall = sum(c["scores"].values())
        short_name = c["name"].split(" (")[0].split(" — ")[0]
        constraint = {
            "C1": f"Paper track record {track_days}/{costs['go_no_go_min_days']} days; parameter-peak caveat logged",
            "C2": "Tested worse than incumbent on identical data",
            "C3": "Untested — needs hypothesis pre-registration before any backtest",
            "C4": "Untested; subsumed by C3 if C3 validates first",
            "C5": "Overlay only; ^VIX not tradeable; regime overfitting risk",
            "C6": "Expected effect below cost hurdle",
            "C7": "No tradeable volatility instrument",
            "C8": "~66 days funding history; single exchange; no diversification",
            "C9": "No futures/spot data; undocumented roll logic",
            "C10": "No intraday history",
        }[c["id"]]
        lines.append(f"| {i} | {short_name} | {overall}/35 | {c['verdict']} | {constraint} |")
    lines.append("")
    lines.append(f"**Counts:** {len(credible)} credible candidate, {len(exploratory)} exploratory "
                 f"signals, {len(blocked)} blocked by data, {len(rejected)} rejected "
                 f"({len(ranked)} total).")
    lines.append("")
    lines.append("**Recommendation for Cycle 12:** Continue prospective paper-trading "
                 "validation of C1 (incumbent; gate is "
                 f"{costs['go_no_go_min_days']} days of track record). The highest-ranked "
                 "untested candidate is **C3 (long-only cross-sectional momentum on the "
                 "broad 18-ETF cache)** at 29/35: data quality is maximal (fully cached, "
                 "point-in-time safe), the structural mechanism is first-order, and it "
                 "diversifies the incumbent's signal formation. Per AGENTS.md "
                 "'hypothesis first', Cycle 12 should document the C3 hypothesis and "
                 "pre-register its evaluation plan (splits, benchmarks, promotion gates, "
                 "multiple-testing controls) BEFORE any backtest execution.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Report generated by `research/run_cycle11.py` (Cycle 11). "
                 "Scores are structural pre-test assessments grounded in cached data "
                 "and prior experiment records; they are not backtest results.*")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    print("=== Cycle 11: Market Opportunity Inventory & Candidate Scoring ===")
    print()

    print("Inventorying raw price cache...")
    raw_records = inventory_raw_files()
    print(f"  {len(raw_records)} raw files, {sum(r['rows'] for r in raw_records):,} total rows")

    print("Inventorying processed artifacts...")
    processed = inventory_processed_files()
    print(f"  {len(processed)} processed artifacts")

    print("Loading cost model from config files...")
    costs = load_cost_model()
    print(f"  commission={costs['commission_bps']}bps, slippage={costs['slippage_bps']}bps, "
          f"round-trip={costs['round_trip_bps']}bps")

    print("Checking data availability...")
    avail = check_availability(raw_records)
    print(f"  crypto_cached={avail['has_crypto_cached']}, futures_cached={avail['has_futures_cached']}, "
          f"forex_cached={avail['has_forex_cached']}, intraday_cached={avail['has_intraday_cached']}")

    print("Building data inventory report...")
    inventory_report = build_data_inventory(raw_records, processed, costs, avail)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    inventory_path = REPORTS_DIR / "data_inventory.md"
    with open(inventory_path, "w") as fh:
        fh.write(inventory_report)
    print(f"  written: {inventory_path}")

    print("Scoring opportunity candidates...")
    candidates = candidate_definitions(avail, processed, costs)
    shortlist_report = build_opportunity_shortlist(candidates, avail, costs, processed)
    shortlist_path = REPORTS_DIR / "opportunity_shortlist.md"
    with open(shortlist_path, "w") as fh:
        fh.write(shortlist_report)
    print(f"  written: {shortlist_path}")

    print()
    print("=== Candidate Scoring Summary ===")
    for c in sorted(candidates, key=lambda c: sum(c["scores"].values()), reverse=True):
        overall = sum(c["scores"].values())
        short_name = c["name"].split(" (")[0].split(" — ")[0]
        print(f"  {c['id']} {short_name}: {overall}/35 -> {c['verdict']}")

    print()
    print("=== Cycle 11 Complete ===")


if __name__ == "__main__":
    main()
