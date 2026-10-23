"""Incremental, session-safe extension of paper-trading state.

Contract: incremental, single state write, idempotent, no strategy change.
Appends at most one completed US trading session per invocation to the
existing paper-trading state, using run_daily_paper_update with market data
sliced to the target session date. Frozen strategy/config/cost model untouched.

Data-integrity contract (Cycle 854):
  * The canonical raw cache (``data/raw``) is READ-ONLY for this tool. Market
    data is downloaded into a scratch directory that is discarded on exit, so
    a monitoring/no-op run can never rewrite the committed dataset.
  * Only sessions that have already closed are used. Any in-session
    (partial) daily bar returned by the provider is dropped before slicing.
  * The state is written at most once, and only after the update is confirmed
    to have advanced the state to the intended target session.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.simulation.paper_trading import (
    PaperTradingConfig,
    PaperTradingState,
    generate_paper_report,
    run_daily_paper_update,
)
from src.data.yfinance_fetcher import fetch_universe

FetchFn = Callable[[str], pd.DataFrame]


def session_is_complete(
    bar_date: str,
    now_et: datetime,
    close_hour: int = 16,
    tz: ZoneInfo | None = None,
) -> bool:
    """Pure function: True iff the US session for bar_date is complete.

    ``bar_date`` is the *session date* (the UTC date of the daily bar index).
    A session is complete once the following local day has started, or once
    the local clock has passed ``close_hour`` (plus one hour of settlement /
    provider finalisation slack) on the session date itself.
    """
    tz = tz or ZoneInfo("America/New_York")
    d = pd.Timestamp(bar_date).date()
    local_now = now_et.astimezone(tz)
    if local_now.date() > d:
        return True
    if local_now.date() == d and local_now.hour >= close_hour + 1:
        return True
    return False


def complete_session_view(
    data: pd.DataFrame,
    now_et: datetime,
    close_hour: int = 16,
    tz: ZoneInfo | None = None,
) -> pd.DataFrame:
    """Return only the rows of ``data`` that belong to completed sessions.

    Provider daily bars for the in-progress session are partial (volume and
    high/low are still moving); they must never enter a state extension.
    """
    if data is None or len(data) == 0:
        return data
    keep = [
        session_is_complete(
            pd.Timestamp(ts).strftime("%Y-%m-%d"), now_et, close_hour=close_hour, tz=tz
        )
        for ts in data.index
    ]
    return data.loc[keep]


def run_extension(
    config: PaperTradingConfig,
    state_path: Path,
    now_et: datetime,
    fetch: FetchFn,
    dry_run: bool = False,
    through: str | None = None,
    close_hour: int = 16,
    tz: ZoneInfo | None = None,
) -> dict:
    """Extend the paper-trading state by at most one completed session.

    ``fetch(end_date)`` must return the universe market data up to (and
    including) ``end_date``; the caller owns the download location so the
    canonical raw cache can be kept read-only.
    """
    state = PaperTradingState.from_yaml(state_path)
    nav_before = state.current_nav

    # Clock gate before any download. If the local clock has not yet passed
    # close_hour+1 on the calendar day after the last processed session, no
    # candidate session can be complete, so the fetch is skipped entirely.
    # This keeps monitoring/no-op runs off the network (Cycle 854: the
    # canonical raw cache is read-only and a no-op run must not re-download
    # the universe to discover that the clock has not advanced).
    tz = tz or ZoneInfo("America/New_York")
    if state.last_run_date is None:
        # Fresh state: no prior session to extend from; fall through to the
        # normal candidate scan below.
        last_run = None
    else:
        last_run = pd.Timestamp(state.last_run_date).date()
        next_calendar = (pd.Timestamp(state.last_run_date) + pd.Timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        if not session_is_complete(next_calendar, now_et, close_hour=close_hour, tz=tz):
            return {
                "target": None,
                "sessions_extended": 0,
                "nav_before": nav_before,
                "nav_after": nav_before,
                "state_writes": 0,
            }

    # Candidate new sessions strictly after the last processed session.
    end_fetch = (
        (pd.Timestamp(state.last_run_date) + pd.Timedelta(days=7)).strftime("%Y-%m-%d")
        if state.last_run_date is not None
        else now_et.strftime("%Y-%m-%d")
    )
    data = fetch(end_fetch)
    candidate_dates = sorted(
        d for d in data.index.unique()
        if last_run is None or pd.Timestamp(d).date() > last_run
    )

    if through:
        thr = pd.Timestamp(through).date()
        candidate_dates = [d for d in candidate_dates if pd.Timestamp(d).date() <= thr]

    target = None
    for d in candidate_dates:
        ds = pd.Timestamp(d).strftime("%Y-%m-%d")
        if session_is_complete(ds, now_et, close_hour=close_hour, tz=tz):
            target = ds
            break

    result = {
        "target": target,
        "sessions_extended": 0,
        "nav_before": nav_before,
        "nav_after": nav_before,
        "state_writes": 0,
    }

    if target is None:
        return result

    if dry_run:
        result["sessions_extended"] = 1
        result["dry_run"] = True
        return result

    # Backup the state before the single write.
    shutil.copy2(state_path, Path(str(state_path) + ".backup"))

    target_ts = pd.Timestamp(target)
    fetch_end = (target_ts + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    all_data = fetch(fetch_end)
    max_date = pd.Timestamp(all_data.index.max()).strftime("%Y-%m-%d")
    if pd.Timestamp(max_date) < pd.Timestamp(target):
        raise RuntimeError(
            f"captured index max {max_date} < target session {target}"
        )

    market_slice = all_data.loc[:target]
    new_state, _artifacts = run_daily_paper_update(
        config, state, market_data=market_slice
    )

    if new_state.last_run_date != target:
        raise RuntimeError(
            f"state advanced to {new_state.last_run_date} instead of {target}; "
            "no write performed"
        )

    # Single write.
    new_state.to_yaml(state_path)
    generate_paper_report(new_state, config)

    result["sessions_extended"] = 1
    result["nav_after"] = new_state.current_nav
    result["state_writes"] = 1
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--through", default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / "config" / "paper_trading_config.yaml"
    config = PaperTradingConfig.from_paper_config_yaml(config_path)
    with open(config_path) as f:
        raw_cfg = yaml.safe_load(f)
    state_path = repo_root / raw_cfg["state_path"]

    tz = ZoneInfo(raw_cfg["data_refresh"]["timezone"])
    close_hour = raw_cfg["data_refresh"]["market_close_hour"]
    now_et = datetime.now(timezone.utc)

    # Scratch download dir: the canonical data/raw cache is never written by
    # this tool, so monitoring runs cannot mutate the committed dataset.
    with tempfile.TemporaryDirectory(prefix="paper-extend-raw-") as scratch:

        def fetch(end_date: str) -> pd.DataFrame:
            raw = fetch_universe(
                config.universe,
                config.history_start,
                end_date,
                raw_dir=scratch,
                force=True,
            )
            return complete_session_view(raw, now_et, close_hour=close_hour, tz=tz)

        result = run_extension(
            config,
            state_path,
            now_et,
            fetch,
            dry_run=args.dry_run,
            through=args.through,
            close_hour=close_hour,
            tz=tz,
        )

    target = result["target"]
    if target is None:
        print("no new completed session")
        print("sessions extended: 0")
        print(f"NAV before: {result['nav_before']}")
        print(f"NAV after: {result['nav_after']}")
        print("state write count: 0")
        print("raw cache: scratch (canonical data/raw untouched)")
        return 0

    print(f"target session: {target}")
    if args.dry_run:
        print("DRY RUN: would extend to", target)
        print("sessions extended: 1 (dry-run, no write)")
        print("raw cache: scratch (canonical data/raw untouched)")
        return 0

    print("sessions extended: 1")
    print(f"NAV before: {result['nav_before']}")
    print(f"NAV after: {result['nav_after']}")
    print("state write count: 1")
    print("raw cache: scratch (canonical data/raw untouched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
