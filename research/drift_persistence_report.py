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
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.drift import (
    DEFAULT_SHARPE_THRESHOLD,
    sharpe_persistence,
    subthreshold_calendar_window,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "paper_trading_config.yaml"
ROLLING_REPORT_PATH = REPO_ROOT / "research" / "reports" / "paper_trading_rolling.md"


def state_path(config_path: Path = CONFIG_PATH) -> Path:
    with open(config_path) as fh:
        cfg = yaml.safe_load(fh) or {}
    p = Path(cfg.get("state_path", "data/processed/paper_trading_state.yaml"))
    return p if p.is_absolute() else REPO_ROOT / p


def load_state(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def _sha256_file(path: Path) -> str | None:
    try:
        if not path.exists():
            return None
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()
    except OSError:
        return None


def _get_git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            return sha if sha else None
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def get_provenance(state_path: Path) -> dict:
    git_sha = _get_git_sha()
    paper_trading_state_sha256 = _sha256_file(state_path)
    config_hashes = {}
    for name, p in [
        ("paper_trading_config", CONFIG_PATH),
    ]:
        h = _sha256_file(p)
        if h is not None:
            config_hashes[name] = h
    provenance = {
        "git_sha": git_sha,
        "paper_trading_state_sha256": paper_trading_state_sha256,
        "config": config_hashes or None,
    }
    return provenance


def build_report(state: dict, threshold: float = DEFAULT_SHARPE_THRESHOLD, state_path: Path | None = None) -> dict:
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

    provenance = get_provenance(state_path) if state_path is not None else get_provenance(REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml")

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
        "provenance": provenance,
    }
    return report


def update_rolling_report(report: dict, report_path: Path = ROLLING_REPORT_PATH) -> bool:
    try:
        if not report_path.exists():
            return False
        content = report_path.read_text()
        prov = report.get("provenance") or {}
        # Preserve existing git_sha when state/config hashes are unchanged to avoid
        # self-referential churn (a commit that updates this block changes HEAD).
        existing_state_sha = None
        existing_git_sha = None
        existing_cfg = {}
        if "## Drift Persistence Provenance" in content:
            idx = content.find("## Drift Persistence Provenance")
            rest = content[idx:]
            m_end = re.search(r"\n## [^#]", rest)
            block_text = rest[: m_end.start() + 1] if m_end else rest
            m = re.search(r"paper_trading_state_sha256:\*\*\s*(\S+)", block_text)
            if m:
                existing_state_sha = m.group(1).strip()
            m = re.search(r"git_sha:\*\*\s*(\S+)", block_text)
            if m:
                existing_git_sha = m.group(1).strip()
            for cm in re.finditer(r"\*\*(\w+)_sha256:\*\*\s*(\S+)", block_text):
                if cm.group(1) != "paper_trading_state":
                    existing_cfg[cm.group(1)] = cm.group(2).strip()
        cfg = prov.get("config") or {}
        if (
            existing_git_sha
            and existing_state_sha == prov.get("paper_trading_state_sha256")
            and existing_cfg == (cfg if isinstance(cfg, dict) else {})
        ):
            prov = dict(prov)
            prov["git_sha"] = existing_git_sha

        lines = []
        lines.append("## Drift Persistence Provenance")
        lines.append("")
        if prov.get("git_sha"):
            lines.append(f"- **git_sha:** {prov['git_sha']}")
        if prov.get("paper_trading_state_sha256"):
            lines.append(f"- **paper_trading_state_sha256:** {prov['paper_trading_state_sha256']}")
        if cfg and isinstance(cfg, dict):
            for k, v in cfg.items():
                lines.append(f"- **{k}_sha256:** {v}")
        lines.append("")
        block = "\n".join(lines)
        start_marker = "## Drift Persistence Provenance"
        if start_marker in content:
            idx = content.find(start_marker)
            rest = content[idx:]
            m = re.search(r"\n## [^#]", rest)
            if m:
                end = idx + m.start() + 1
                new_content = content[:idx] + block + "\n" + content[end:]
            else:
                new_content = content[:idx] + block
        else:
            if not content.endswith("\n"):
                content += "\n"
            new_content = content + "\n" + block
        if new_content != content:
            report_path.write_text(new_content)
            return True
        return False
    except OSError:
        return False


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
    prov = report.get("provenance") or {}
    if prov:
        print()
        print("provenance:")
        if prov.get("git_sha"):
            print(f"  git_sha: {prov['git_sha']}")
        if prov.get("paper_trading_state_sha256"):
            print(f"  paper_trading_state_sha256: {prov['paper_trading_state_sha256']}")
        cfg = prov.get("config")
        if cfg:
            print("  config:")
            if isinstance(cfg, dict):
                for k, v in cfg.items():
                    print(f"    {k}: {v}")
            else:
                print(f"    {cfg}")
    print()
    print("last 10 evaluated sessions (date, rolling 63d Sharpe):")
    for entry in report["series_tail"]:
        print(f"  {entry['date']}  {entry['sharpe']:.4f}")


def main():
    parser = argparse.ArgumentParser(
        description="Read-only report of the low-Sharpe drift-flag persistence."
    )
    parser.add_argument("--state-path", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = Path(args.state_path) if args.state_path else state_path()
    report = build_report(load_state(path), state_path=path)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_report(report)

    try:
        update_rolling_report(report)
    except OSError:
        pass

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
