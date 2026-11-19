"""Read-only audit: which committed paper-trading sessions are re-derivable from ``data/raw``?

Why this exists
---------------
The paper-trading record advances through ``research/extend_paper_trading_state.py``,
which (by contract, Cycle 854) downloads market data into a scratch directory and
NEVER writes ``data/raw``. The committed raw cache was last refreshed on
2026-11-11 and ends at session **2026-11-10** (``research/reports/
raw_cache_integrity_manifest.json``), yet the record has advanced six sessions
further (2026-11-11 .. 2026-11-18). Those sessions are stored in
``data/processed/paper_trading_state.yaml`` but cannot be re-derived from any
committed file: every drift metric, including the rolling-63d Sharpe that drives
the current ``low_rolling_sharpe`` decision, is computed over a window that
partly covers uncommitted data.

That is a reproducibility gap of the exact class the research contract puts
first ("independently checkable provenance"). It is invisible to
``research/drift_invariant_check.py`` because that tool reconciles the stored
flags with the stored state, not with the committed cache. This audit makes the
gap an explicit, deterministic number and shows whether the decision would
change if only committed data were used.

Checks (all read-only; no network, no writes outside the report files):
  1. ``raw_coverage_end``: the last session present in EVERY incumbent-universe
     parquet under ``data/raw`` (the conservative minimum, so one lagging symbol
     cannot inflate coverage).
  2. Coverage split: record sessions on/before the coverage end are "covered",
     the rest are "unverified".
  3. Metric recurrence: the stored ``rolling_sharpe_63d`` reproduces from the
     stored return series with the live formula
     (``src.evaluation.drift.annualized_sharpe`` over the last 63 returns).
  4. Decision sensitivity: the rolling-63d Sharpe computed at the coverage end
     (covered sessions only) is compared with the same alert threshold
     (``0.5``); the flag persists / does not persist under both conventions.

Exit codes:
  0  audit ran; output is internally consistent (an "unverified" count > 0 is a
     documented coverage gap, not an error)
  1  the state is internally inconsistent (stored Sharpe does not reproduce, or
     the parallel arrays disagree in length)
  2  usage / environment error (missing state, config or raw cache)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.drift import (
    DEFAULT_MIN_PERIODS,
    DEFAULT_SHARPE_THRESHOLD,
    DEFAULT_WINDOW,
    annualized_sharpe,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"
CONFIG_PATH = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
REPORT_PATH = REPO_ROOT / "research" / "reports" / "paper_record_raw_coverage_001.md"


def _normalize_index(index: pd.Index) -> pd.DatetimeIndex:
    """Timezone-agnostic, day-normalized DatetimeIndex."""
    idx = pd.to_datetime(index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    return idx.normalize()


def universe_from_config(config_path: Path) -> list[str]:
    cfg = yaml.safe_load(config_path.read_text())
    universe = cfg.get("universe") or []
    if not universe:
        raise ValueError(f"no universe defined in {config_path}")
    return [str(s) for s in universe]


def symbol_last_date(parquet_path: Path) -> str | None:
    df = pd.read_parquet(parquet_path)
    if df.empty:
        return None
    return _normalize_index(df.index).max().strftime("%Y-%m-%d")


def raw_coverage_end(raw_dir: Path, symbols: list[str]) -> tuple[str, dict[str, str]]:
    """Last session present in *every* symbol's committed parquet (the minimum)."""
    per_symbol: dict[str, str] = {}
    missing: list[str] = []
    for sym in symbols:
        path = raw_dir / f"{sym}.parquet"
        if not path.exists():
            missing.append(sym)
            continue
        last = symbol_last_date(path)
        if last is None:
            missing.append(sym)
            continue
        per_symbol[sym] = last
    if missing:
        raise FileNotFoundError(
            f"raw cache missing/empty for universe symbol(s): {', '.join(sorted(missing))}"
        )
    return min(per_symbol.values()), per_symbol


def record_series(state: dict) -> tuple[list[str], np.ndarray]:
    dates = [str(d)[:10] for d in state["cumulative_dates"]]
    returns = np.asarray(state["cumulative_returns"], dtype=float)
    if len(dates) != len(returns):
        raise ValueError(
            f"state inconsistency: {len(dates)} dates vs {len(returns)} cumulative_returns"
        )
    for key in ("run_history", "cumulative_pnl"):
        seq = state.get(key)
        if seq is not None and len(seq) != len(dates):
            raise ValueError(
                f"state inconsistency: {key} has {len(seq)} entries, expected {len(dates)}"
            )
    return dates, returns


def split_coverage(dates: list[str], coverage_end: str) -> tuple[list[str], list[str]]:
    covered = [d for d in dates if d <= coverage_end]
    unverified = [d for d in dates if d > coverage_end]
    return covered, unverified


def rolling_sharpe_at(
    returns: np.ndarray,
    window: int = DEFAULT_WINDOW,
    min_periods: int = DEFAULT_MIN_PERIODS,
) -> float:
    series = np.asarray(returns, dtype=float)[-window:]
    if len(series) < min_periods:
        return float("nan")
    return annualized_sharpe(series)


def audit(state_path: Path, config_path: Path, raw_dir: Path) -> dict:
    state = yaml.safe_load(state_path.read_text())
    symbols = universe_from_config(config_path)
    coverage_end, per_symbol = raw_coverage_end(raw_dir, symbols)
    dates, returns = record_series(state)

    covered, unverified = split_coverage(dates, coverage_end)
    if not covered:
        raise ValueError(f"no record session on/before coverage end {coverage_end}")

    stored_sharpe = float(state["rolling_sharpe_63d"])
    reproduced_sharpe = rolling_sharpe_at(returns)
    reproduced_ok = bool(
        np.isfinite(stored_sharpe)
        and np.isfinite(reproduced_sharpe)
        and abs(stored_sharpe - reproduced_sharpe) < 1e-9
    )
    covered_sharpe = rolling_sharpe_at(returns[: len(covered)])

    return {
        "symbols": symbols,
        "per_symbol_last_date": per_symbol,
        "coverage_end": coverage_end,
        "record_start": dates[0],
        "record_end": dates[-1],
        "n_sessions": len(dates),
        "n_covered": len(covered),
        "n_unverified": len(unverified),
        "unverified_sessions": unverified,
        "stored_rolling_sharpe_63d": stored_sharpe,
        "reproduced_rolling_sharpe_63d": reproduced_sharpe,
        "reproduced_ok": reproduced_ok,
        "covered_only_rolling_sharpe_63d": covered_sharpe,
        "threshold": DEFAULT_SHARPE_THRESHOLD,
        "flag_under_full_window": bool(stored_sharpe < DEFAULT_SHARPE_THRESHOLD),
        "flag_under_covered_only": bool(covered_sharpe < DEFAULT_SHARPE_THRESHOLD),
        "stored_last_run_date": str(state.get("last_run_date")),
    }


def render_report(result: dict) -> str:
    unverified = result["unverified_sessions"]
    unverified_lines = "\n".join(f"  - {d}" for d in unverified) if unverified else "  - (none)"
    symbol_lines = "\n".join(
        f"| `{sym}` | `{last}` |" for sym, last in sorted(result["per_symbol_last_date"].items())
    )
    verdict = (
        "the `low_rolling_sharpe` verdict is **unchanged** under the covered-only window"
        if result["flag_under_covered_only"] == result["flag_under_full_window"]
        else "the verdict **differs** between conventions — investigate before acting"
    )
    return f"""# Paper record vs committed raw-cache coverage

Read-only audit produced by `research/paper_record_raw_coverage_audit.py`.
No file under `data/` or `config/` is written; values are re-derived from the
committed state and cache.

## Coverage

| quantity | value |
|---|---|
| universe checked | {', '.join(f'`{s}`' for s in result['symbols'])} |
| committed raw coverage end (min across universe) | `{result['coverage_end']}` |
| record window | `{result['record_start']}` .. `{result['record_end']}` |
| record sessions | `{result['n_sessions']}` |
| sessions covered by committed raw | `{result['n_covered']}` |
| sessions **not** re-derivable from `data/raw` | `{result['n_unverified']}` |

Per-symbol last committed session:

| symbol | last session |
|---|---|
{symbol_lines}

Unverified record sessions:
{unverified_lines}

The extension path (`research/extend_paper_trading_state.py`, Cycle 854
contract) never writes `data/raw`; it fetches into a scratch directory that is
discarded. Sessions listed above therefore rest only on the state file itself.

## Metric recurrence and decision sensitivity

| quantity | value |
|---|---|
| stored `rolling_sharpe_63d` | `{result['stored_rolling_sharpe_63d']!r}` |
| reproduced from stored returns (last 63) | `{result['reproduced_rolling_sharpe_63d']!r}` |
| reproduced exactly | `{result['reproduced_ok']}` |
| covered-only `rolling_sharpe_63d` (through `{result['coverage_end']}`) | `{result['covered_only_rolling_sharpe_63d']!r}` |
| alert threshold | `{result['threshold']}` |
| `low_rolling_sharpe` under full window | `{result['flag_under_full_window']}` |
| `low_rolling_sharpe` under covered-only window | `{result['flag_under_covered_only']}` |

Interpretation: {verdict}.

## Reproduce

```
python research/paper_record_raw_coverage_audit.py
```
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default=str(STATE_PATH))
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args(argv)

    try:
        result = audit(Path(args.state), Path(args.config), Path(args.raw_dir))
    except FileNotFoundError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(result))

    print(
        "SUMMARY "
        f"sessions={result['n_sessions']} "
        f"covered={result['n_covered']} "
        f"unverified={result['n_unverified']} "
        f"coverage_end={result['coverage_end']} "
        f"stored_sharpe={result['stored_rolling_sharpe_63d']!r} "
        f"covered_sharpe={result['covered_only_rolling_sharpe_63d']!r}"
    )
    if not result["reproduced_ok"]:
        print(
            "FAIL: stored rolling_sharpe_63d does not reproduce from stored returns",
            file=sys.stderr,
        )
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
