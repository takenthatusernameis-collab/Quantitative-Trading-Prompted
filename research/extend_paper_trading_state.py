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
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.yfinance_fetcher import fetch_universe
from src.simulation.paper_trading import (
    PaperTradingConfig,
    PaperTradingState,
    generate_paper_report,
    run_daily_paper_update,
)

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


def next_trading_session(
    d: pd.Timestamp, tz: ZoneInfo | None = None
) -> pd.Timestamp:
    """Next Mon-Fri session strictly after ``d`` (weekends excluded).

    Market holidays are NOT modelled: the returned date is the next business
    day on the wall-clock calendar, which is the conservative upper bound on
    when a new US equity session can exist.
    """
    tz = tz or ZoneInfo("America/New_York")
    nxt = pd.Timestamp(d).normalize() + pd.Timedelta(days=1)
    while nxt.weekday() >= 5:  # Saturday=5, Sunday=6
        nxt += pd.Timedelta(days=1)
    return nxt


def build_readiness(
    state: PaperTradingState,
    now_et: datetime,
    close_hour: int = 16,
    tz: ZoneInfo | None = None,
) -> dict:
    """Explicit, testable readiness diagnostic for the extension path.

    Reports the last processed session, the clock-gate state, and the next
    expected US trading session together with the local time at which that
    session becomes usable. Pure function: it touches no files, no network
    state, and no configuration.
    """
    tz = tz or ZoneInfo("America/New_York")
    local_now = now_et.astimezone(tz)
    last_run = state.last_run_date

    if last_run is None:
        next_calendar = None
        gate_released = True  # fresh state: fall through to the candidate scan
    else:
        next_calendar = (pd.Timestamp(last_run) + pd.Timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        gate_released = session_is_complete(
            next_calendar, now_et, close_hour=close_hour, tz=tz
        )

    if last_run is None:
        next_session = pd.Timestamp(local_now.date())
    else:
        next_session = next_trading_session(pd.Timestamp(last_run), tz=tz)

    next_session_str = next_session.strftime("%Y-%m-%d")
    complete_time = (
        f"{close_hour + 1:02d}:00 ET on {next_session_str} "
        "(or the start of the following local day)"
    )
    next_session_complete = session_is_complete(
        next_session_str, now_et, close_hour=close_hour, tz=tz
    )

    return {
        "last_run_date": last_run,
        "now_et_iso": now_et.isoformat(),
        "now_et_str": local_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "next_calendar_day": next_calendar,
        "clock_gate_released": gate_released,
        "next_expected_session": next_session_str,
        "next_session_weekday": next_session.strftime("%A"),
        "next_session_complete_time": complete_time,
        "next_session_already_complete": next_session_complete,
        "required_completeness": (
            "the clock gate releases once the calendar day after last_run_date "
            "has started, or the local clock passes "
            f"{close_hour + 1:02d}:00 ET on a session date; a candidate session "
            "is then usable only once it is itself complete"
        ),
        "holidays_note": "weekends are excluded; market holidays are not modelled",
    }


def print_readiness(report: dict) -> None:
    print("=== paper-trading extension readiness ===")
    print(f"last processed session:   {report['last_run_date']}")
    print(f"current time (ET):       {report['now_et_str']}")
    print(f"clock gate:              "
          f"{'released' if report['clock_gate_released'] else 'NOT released'}")
    if report["next_calendar_day"] is not None:
        print(f"gate checks day after:   {report['next_calendar_day']}")
    print(f"next expected session:    "
          f"{report['next_expected_session']} ({report['next_session_weekday']})")
    print(f"session usable after:     {report['next_session_complete_time']}")
    print(f"session already complete: {report['next_session_already_complete']}")
    print(f"completeness rule:       {report['required_completeness']}")
    print(f"note:                    {report['holidays_note']}")


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
    now_et = datetime.now(UTC)

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

    # Explicit readiness diagnostic (acceptance criterion 2): the same clock
    # gate the extension logic uses, surfaced as a stable report. It is
    # computed from the committed state and the live clock only; nothing under
    # data/ or config/ is read or written by it.
    readiness = build_readiness(
        PaperTradingState.from_yaml(state_path),
        now_et,
        close_hour=close_hour,
        tz=tz,
    )
    print_readiness(readiness)

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
