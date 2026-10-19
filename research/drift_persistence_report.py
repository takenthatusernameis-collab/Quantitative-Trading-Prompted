"""Read-only report of the low-Sharpe drift-flag persistence.

Recomputes, from the committed paper-trading state only, how many consecutive
trading sessions the rolling 63-day Sharpe has stayed below the alert
threshold, and cross-checks the result against the drift flag recorded in the
state.

Contract (Cycle 857):
  * Pure read: the state file, the raw cache and the network are never
    touched, so a monitoring run cannot mutate the canonical dataset.
  * Deterministic: the same state always yields the same numbers, which makes
    the persistence count quoted in reports reproducible instead of manually
    maintained.
  * Self-checking: the recomputed rolling Sharpe is compared with the value
    stored in ``drift_flags.low_rolling_sharpe``; a mismatch is reported as a
    failure (exit code 1) instead of being silently ignored.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.drift import (
    DEFAULT_CALENDAR_DAYS,
    DEFAULT_SHARPE_THRESHOLD,
    sharpe_persistence,
    subthreshold_calendar_window,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "paper_trading_config.yaml"


def state_path(config_path: Path = CONFIG_PATH) -> Path:
    with open(config_path) as fh:
        cfg = yaml.safe_load(fh) or {}
    p = Path(cfg.get("state_path", "data/processed/paper_trading_state.yaml"))
    return p if p.is_absolute() else REPO_ROOT / p


def load_state(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def build_report(state: dict, threshold: float = DEFAULT_SHARPE_THRESHOLD) -> dict:
    """Compute the persistence report from a paper-trading state dictionary."""
    dates = [str(d) for d in (state.get("cumulative_dates") or [])]
    returns = [float(r) for r in (state.get("cumulative_returns") or [])]

    if len(dates) != len(returns):
        raise ValueError(
            f"state is inconsistent: {len(dates)} cumulative_dates vs "
            f"{len(returns)} cumulative_returns"
        )

    persistence = sharpe_persistence(dates, returns, threshold=threshold)
    calendar = subthreshold_calendar_window(
        dates, persistence["series"], threshold=threshold
    )
    series = persistence.pop("series")

    stored_flag = (state.get("drift_flags") or {}).get("low_rolling_sharpe") or {}
    stored_value = stored_flag.get("value")
    recomputed = persistence["last_sharpe"]
    if stored_value is None or recomputed is None:
        stored_matches = None
    else:
        stored_matches = abs(float(stored_value) - float(recomputed)) <= 1e-12

    report = {
        "last_run_date": state.get("last_run_date"),
        "threshold": threshold,
        "streak_days": persistence["streak_days"],
        "streak_start_date": persistence["streak_start_date"],
        "streak_end_date": persistence["streak_end_date"],
        "last_sharpe": recomputed,
        "last_date": persistence["last_date"],
        "first_flag_date": persistence["first_flag_date"],
        "evaluated_sessions": persistence["evaluated_sessions"],
        "subthreshold_sessions": persistence["subthreshold_sessions"],
        "calendar_window": calendar,
        "stored_flag_value": stored_value,
        "stored_flag_date": stored_flag.get("date"),
        "stored_matches_recomputed": stored_matches,
        "series_tail": [
            {"date": d, "sharpe": v} for d, v in series[-10:] if v is not None
        ],
    }
    return report


def print_report(report: dict) -> None:
    print("=== low_rolling_sharpe drift-flag persistence ===")
    print(f"last_run_date:            {report['last_run_date']}")
    print(f"threshold:                {report['threshold']}")
    print(
        f"persistence (consecutive trading days below threshold): "
        f"{report['streak_days']}"
    )
    print(
        f"streak window:            {report['streak_start_date']} -> "
        f"{report['streak_end_date']}"
    )
    print(f"rolling 63d Sharpe:       {report['last_sharpe']} ({report['last_date']})")
    print(f"first flagged session:    {report['first_flag_date']}")
    print(
        f"flagged sessions (history): {report['subthreshold_sessions']} of "
        f"{report['evaluated_sessions']} evaluated"
    )
    cal = report["calendar_window"]
    print(
        f"last {cal['calendar_days']} calendar days:  "
        f"{cal['subthreshold_sessions']} of {cal['sessions_in_window']} sessions "
        f"below threshold ({cal['window_start_date']} -> {cal['window_end_date']})"
    )
    print(
        f"stored flag value:        {report['stored_flag_value']} "
        f"({report['stored_flag_date']})"
    )
    print(f"stored == recomputed:     {report['stored_matches_recomputed']}")
    print()
    print("last 10 evaluated sessions (date, rolling 63d Sharpe):")
    for entry in report["series_tail"]:
        print(f"  {entry['date']}  {entry['sharpe']:.4f}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only report of the low-Sharpe drift-flag persistence."
    )
    parser.add_argument("--state-path", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = Path(args.state_path) if args.state_path else state_path()
    report = build_report(load_state(path))

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_report(report)

    if report["stored_matches_recomputed"] is False:
        print()
        print(
            "FAIL: recomputed rolling Sharpe does not match the stored drift flag",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
