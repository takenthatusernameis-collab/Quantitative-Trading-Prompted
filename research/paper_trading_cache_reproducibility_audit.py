"""Read-only reproducibility audit: canonical state vs canonical raw cache.

The paper-trading state (``data/processed/paper_trading_state.yaml``) records one
row per processed session. Every one of those sessions must be reproducible from
the committed raw cache (``data/raw/*.parquet``), because the cache is the
authoritative, committed dataset and the state is derived from it.

This module measures the gap between the two frontiers:

  * ``state_frontier``  -- the last session the state claims to have processed
  * ``cache_frontier``  -- the last session for which the FULL universe is
    observable in the committed cache (the minimum across universe symbols, since
    the simulation needs every symbol on every date)

If the state frontier is later than the cache frontier, the trailing state
sessions are NOT reproducible from the committed cache alone: they were produced
by a run that fetched live data into a scratch directory and never refreshed the
cache. That is a reproducibility gap, not a runtime error -- the extension tool
still behaves correctly (it re-fetches live data), but offline verification
cannot reach the frontier and the committed state cannot be regenerated from
committed data.

Pure and read-only: this module never writes state, never writes the raw cache,
and never touches the network.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from collections.abc import Sequence

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "paper_trading_config.yaml"
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"


def _safe_symbol(s: str) -> str:
    return s.replace("/", "-").replace("=", "-")


def universe_symbols() -> list[str]:
    with open(CONFIG_PATH) as fh:
        cfg = yaml.safe_load(fh) or {}
    sim_path = REPO_ROOT / cfg.get(
        "simulation_config", "config/simulation_candidate_001.yaml"
    )
    with open(sim_path) as fh:
        sim = yaml.safe_load(fh) or {}
    return list(sim.get("universe", []))


def state_frontier(state: dict | None = None) -> str | None:
    """Last session date recorded in the canonical paper-trading state."""
    if state is None:
        with open(STATE_PATH) as fh:
            state = yaml.safe_load(fh) or {}
    dates = [str(d) for d in (state.get("cumulative_dates") or [])]
    if not dates:
        return None
    return max(dates)


def symbol_frontier(raw_dir: Path, symbol: str) -> str | None:
    """Max session date for one symbol's committed cache frame."""
    path = raw_dir / f"{_safe_symbol(symbol)}.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
    except (OSError, ValueError, ImportError):
        return None
    if len(df) == 0:
        return None
    return pd.Timestamp(df.index.max()).strftime("%Y-%m-%d")


def cache_frontier(
    raw_dir: Path = RAW_DIR, symbols: Sequence[str] | None = None
) -> str | None:
    """Last session for which the FULL universe is observable in the cache.

    The minimum across universe symbols: the simulation needs every symbol on
    every date, so the binding constraint is the symbol with the shortest
    history. Returns None if any universe symbol is missing entirely.
    """
    symbols = list(symbols) if symbols is not None else universe_symbols()
    frontiers = [symbol_frontier(raw_dir, s) for s in symbols]
    if any(f is None for f in frontiers):
        return None
    return min(frontiers)  # type: ignore[arg-type]


def missing_sessions(
    state: dict | None = None, symbols: Sequence[str] | None = None
) -> list[str]:
    """State sessions that fall after the committed cache frontier.

    Empty list iff the state is fully reproducible from the committed cache.
    """
    if state is None:
        with open(STATE_PATH) as fh:
            state = yaml.safe_load(fh) or {}
    dates = [str(d) for d in (state.get("cumulative_dates") or [])]
    frontier = cache_frontier(symbols=symbols)
    if frontier is None or not dates:
        return []
    return [d for d in dates if d > frontier]


def build_audit(
    state: dict | None = None, symbols: Sequence[str] | None = None
) -> dict:
    """Pure diagnostic: state frontier, cache frontier, and the gap."""
    if state is None:
        with open(STATE_PATH) as fh:
            state = yaml.safe_load(fh) or {}
    sf = state_frontier(state)
    cf = cache_frontier(symbols=symbols)
    missing = missing_sessions(state, symbols=symbols)
    return {
        "state_frontier": sf,
        "cache_frontier": cf,
        "state_sessions": len([d for d in (state.get("cumulative_dates") or [])]),
        "missing_sessions": missing,
        "missing_count": len(missing),
        "reproducible_from_committed_cache": len(missing) == 0,
        "universe": universe_symbols(),
    }


def print_audit(audit: dict) -> None:
    print("=== paper-trading state vs raw-cache reproducibility ===")
    print(f"state frontier:          {audit['state_frontier']}")
    print(f"cache frontier:          {audit['cache_frontier']}")
    print(f"state sessions:          {audit['state_sessions']}")
    print(f"missing from cache:      {audit['missing_count']}")
    if audit["missing_sessions"]:
        print(
            "missing sessions:        "
            + ", ".join(audit["missing_sessions"])
        )
    print(
        "reproducible from committed cache: "
        f"{'yes' if audit['reproducible_from_committed_cache'] else 'NO'}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only reproducibility audit of the canonical "
        "paper-trading state against the committed raw cache."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if the state is not reproducible from the committed cache",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="universe symbols to audit (default: read from the sim config)",
    )
    args = parser.parse_args()

    audit = build_audit(symbols=args.symbols)
    print_audit(audit)
    if args.strict and not audit["reproducible_from_committed_cache"]:
        print()
        print(
            "BLOCKER: the canonical state is not reproducible from the "
            "committed raw cache; refresh data/raw before trusting offline "
            "verification of the frontier extension."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())