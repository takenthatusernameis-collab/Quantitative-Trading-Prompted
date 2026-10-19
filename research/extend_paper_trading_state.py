"""Incremental, session-safe extension of paper-trading state.

Contract: incremental, single state write, idempotent, no strategy change.
Appends at most one completed US trading session per invocation to the
existing paper-trading state, using run_daily_paper_update with market data
sliced to the target session date. Frozen strategy/config/cost model untouched.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.simulation.paper_trading import (
    PaperTradingConfig,
    PaperTradingState,
    generate_paper_report,
    run_daily_paper_update,
)
from src.data.yfinance_fetcher import fetch_universe


def session_is_complete(bar_date: str, now_et: datetime) -> bool:
    """Pure function: True iff the US session for bar_date is complete."""
    tz = ZoneInfo("America/New_York")
    d = pd.Timestamp(bar_date).date()
    now_date = now_et.astimezone(tz).date()
    now_hour = now_et.astimezone(tz).hour
    close_hour = 16
    if now_date > d:
        return True
    if now_date == d and now_hour >= close_hour + 1:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--through", default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / "config" / "paper_trading_config.yaml"
    config = PaperTradingConfig.from_paper_config_yaml(config_path)
    state_path = repo_root / config.state_path if hasattr(config, "state_path") else repo_root / "data/processed/paper_trading_state.yaml"
    # resolve state_path from yaml
    import yaml as _y
    with open(config_path) as f:
        raw_cfg = _y.safe_load(f)
    state_path = repo_root / raw_cfg["state_path"]
    report_path = repo_root / raw_cfg["report_path"]

    tz = ZoneInfo(raw_cfg["data_refresh"]["timezone"])
    close_hour = raw_cfg["data_refresh"]["market_close_hour"]

    def session_complete(bar_date, now_et):
        d = pd.Timestamp(bar_date).date()
        now_date = now_et.astimezone(tz).date()
        now_hour = now_et.astimezone(tz).hour
        if now_date > d:
            return True
        if now_date == d and now_hour >= close_hour + 1:
            return True
        return False

    state = PaperTradingState.from_yaml(state_path)
    last_run = pd.Timestamp(state.last_run_date).date()

    # Determine candidate next sessions from a forced fetch of universe
    now_et = datetime.now(timezone.utc)
    # fetch up to last_run + a buffer to find new completed sessions
    end_fetch = (pd.Timestamp(state.last_run_date) + pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    # exclusive end: +1 day handled in fetch call? fetch_universe end is exclusive per yfinance; request +1
    data = fetch_universe(config.universe, config.history_start, end_fetch, force=True)
    # candidate new session dates strictly after last_run
    candidate_dates = sorted(d for d in data.index.unique() if pd.Timestamp(d).date() > last_run)

    # filter by --through
    if args.through:
        thr = pd.Timestamp(args.through).date()
        candidate_dates = [d for d in candidate_dates if pd.Timestamp(d).date() <= thr]

    # find first completed session
    target = None
    for d in candidate_dates:
        ds = pd.Timestamp(d).strftime("%Y-%m-%d")
        if session_complete(ds, now_et):
            target = ds
            break

    if target is None:
        print("no new completed session")
        print("sessions extended: 0")
        print(f"NAV before: {state.current_nav}")
        print(f"NAV after: {state.current_nav}")
        print("state write count: 0")
        return 0

    print(f"target session: {target}")

    if args.dry_run:
        print("DRY RUN: would extend to", target)
        print("sessions extended: 1 (dry-run, no write)")
        return 0

    # backup
    backup_path = Path(str(state_path) + ".backup")
    import shutil
    shutil.copy2(state_path, backup_path)

    # fetch exact data with exclusive end
    target_ts = pd.Timestamp(target)
    fetch_end = (target_ts + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    all_data = fetch_universe(config.universe, config.history_start, fetch_end, force=True)
    assert pd.Timestamp(all_data.index.max()).strftime("%Y-%m-%d") == target, "captured index max mismatch"

    market_slice = all_data.loc[:target]
    before_nav = state.current_nav
    new_state, artifacts = run_daily_paper_update(config, state, market_data=market_slice)

    # single write
    new_state.to_yaml(state_path)
    generate_paper_report(new_state, config)

    # drift flags diff
    print("sessions extended: 1")
    print(f"NAV before: {before_nav}")
    print(f"NAV after: {new_state.current_nav}")
    print(f"state write count: 1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
