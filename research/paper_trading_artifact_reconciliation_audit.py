#!/usr/bin/env python3
"""Reconcile every paper-trading session row with its committed daily artifacts.

Why this exists
---------------
The committed paper-trading record is one ``run_history`` row per session in
``data/processed/paper_trading_state.yaml`` plus four per-session parquet
artifacts (``daily_pnl_``, ``positions_``, ``regime_``, ``risk_state_``). Nothing
in the repository verified that those two views still agree across the *whole*
history:

* ``research/audit_state_aggregates.py`` re-derives state-level aggregates from
  ``run_history`` only (it never reads the artifacts);
* ``research/drift_invariant_check.py`` checks the **latest** session's regime
  exposure against its artifact (and the zero-exposure/zero-weight implication);
* ``research/paper_record_raw_coverage_audit.py`` checks provenance against
  ``data/raw``, not artifact/state agreement.

Artifact writes have silently dropped before (see
``research/repair_missing_paper_trading_artifacts_868.py``), and a repair can
introduce a value the live path would never have written. A corrupted,
duplicated or partially written per-session parquet -- or a state row that no
longer matches its artifacts -- would therefore go undetected while every other
check stayed green. This audit treats the state row as the reference and
re-derives every artifact field from it (plus, where the record does not store
the quantity, from the record's own series: drawdown from the NAV series,
turnover from consecutive committed position vectors).

Checks per session
------------------
1. all four artifacts exist, are readable, and are dated to the session;
2. ``daily_pnl``: single row; ``daily_return`` / ``daily_pnl`` / ``nav`` match
   the row; and ``daily_pnl == nav - previous nav`` (first session: notional
   ``100000``);
3. ``risk_state``: single row; ``vol_scale`` / ``dd_scale`` match the row;
   ``exposure == vol_scale * regime_exposure``; ``drawdown`` equals the running
   maximum drawdown of the record NAV series up to that session;
4. ``regime``: single row; ``regime_exposure`` matches the row;
5. ``positions``: one row per configured universe symbol, all dated to the
   session; the number of nonzero weights equals ``n_positions``; gross
   ``sum |w|`` is at most 1; and (from the second session on) the turnover of
   the committed weights, ``sum |w_t - w_{t-1}|``, equals the row's ``turnover``.

Known defects
-------------
A mismatch that is already documented and pinned to an exact observed value is
reported as ATTESTED and does not fail the audit; any *other* mismatch (or an
attested defect whose artifact value changed) fails closed. The registry keeps
the defect visible in the audit output and report rather than hiding it.

This module is read-only: it never writes the state, the artifact directory,
``data/raw`` or any config. It writes only its own markdown report unless
``--no-report`` is given.

Exit codes: ``0`` every mismatch is attested; ``1`` an unattested mismatch;
``2`` missing state/artifact directory/config.

Usage::

    python research/paper_trading_artifact_reconciliation_audit.py
    python research/paper_trading_artifact_reconciliation_audit.py --no-report
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"
CANDIDATE_CONFIG_PATH = ROOT / "config" / "simulation_candidate_001.yaml"
PAPER_DIR = ROOT / "data" / "processed" / "paper_trading"
REPORT_PATH = ROOT / "research" / "reports" / "paper_trading_artifact_reconciliation_001.md"

ARTIFACT_KINDS = ("daily_pnl", "positions", "regime", "risk_state")
NOTIONAL = 100000.0
REL_TOL = 1e-9
ABS_TOL = 1e-9

# (session, field) -> pinned defect. ``observed`` is the value actually in the
# committed artifact, ``expected`` the value the live path would have written.
# ``risk_state_20261102.parquet`` was reconstructed by
# research/repair_missing_paper_trading_artifacts_868.py, whose docstring states
# ``drawdown = state.max_drawdown``; that is the all-time maximum drawdown at
# repair time (-0.06562469374042057), not the 2026-11-02 session's running
# maximum drawdown (-0.049857401112321176, the value stored for 2026-10-30 and
# 2026-11-03). Recorded here rather than hand-edited, so the defect stays
# visible and the record's artifacts are not rewritten to make a check pass.
KNOWN_DEFECTS: dict[tuple[str, str], dict] = {
    ("2026-11-02", "drawdown"): {
        "artifact": "risk_state",
        "observed": -0.06562469374042057,
        "expected": -0.049857401112321176,
        "reason": (
            "risk_state_20261102.parquet reconstructed by "
            "research/repair_missing_paper_trading_artifacts_868.py using "
            "drawdown = state.max_drawdown (all-time max at repair time) "
            "instead of the session's running max drawdown"
        ),
    },
}


def _close(a: float, b: float) -> bool:
    if not (np.isfinite(a) and np.isfinite(b)):
        return False
    return abs(a - b) <= ABS_TOL + REL_TOL * max(abs(a), abs(b))


def _mismatch(session: str, field: str, artifact: object, record: object) -> dict:
    return {
        "session": session,
        "field": field,
        "artifact": artifact,
        "record": record,
    }


def _weights(df: pd.DataFrame) -> dict[str, float] | None:
    if "symbol" not in df.columns or "weight" not in df.columns:
        return None
    return {str(s): float(w) for s, w in zip(df["symbol"], df["weight"])}


def _running_drawdown(navs: list[float]) -> np.ndarray:
    series = np.asarray(navs, dtype=float)
    peak = np.maximum.accumulate(series)
    return np.minimum.accumulate(np.minimum(series / peak - 1.0, 0.0))


def _read(paper_dir: Path, kind: str, stamp: str) -> pd.DataFrame | None:
    path = paper_dir / f"{kind}_{stamp}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


def reconcile_session(
    row: dict,
    prev_row: dict | None,
    prev_weights: dict[str, float] | None,
    running_dd: float,
    paper_dir: Path,
    universe: list[str],
) -> tuple[list[dict], dict[str, float] | None]:
    """Return (mismatches, committed weights) for one session."""
    session = str(row["date"])
    stamp = session.replace("-", "")
    mismatches: list[dict] = []

    frames: dict[str, pd.DataFrame | None] = {}
    for kind in ARTIFACT_KINDS:
        try:
            frames[kind] = _read(paper_dir, kind, stamp)
        except Exception as exc:  # noqa: BLE001 - corrupt parquet must fail the audit, not crash it
            frames[kind] = None
            mismatches.append(_mismatch(session, f"{kind}.unreadable", repr(exc), "readable"))
        if frames[kind] is None and not any(
            m["field"] == f"{kind}.unreadable" for m in mismatches
        ):
            mismatches.append(_mismatch(session, f"{kind}.present", None, "present"))

    def frame(kind: str) -> pd.DataFrame | None:
        df = frames.get(kind)
        return None if df is None else df

    # daily_pnl ---------------------------------------------------------------
    df = frame("daily_pnl")
    if df is not None:
        if len(df) != 1:
            mismatches.append(_mismatch(session, "daily_pnl.rows", len(df), 1))
        else:
            rec = df.iloc[0]
            if str(rec.get("date")) != session:
                mismatches.append(_mismatch(session, "daily_pnl.date", str(rec.get("date")), session))
            for field in ("daily_return", "daily_pnl", "nav"):
                if field not in df.columns:
                    mismatches.append(_mismatch(session, "daily_pnl.column", None, field))
                    continue
                artifact_value = float(rec[field])
                if not _close(artifact_value, float(row[field])):
                    mismatches.append(
                        _mismatch(session, f"daily_pnl.{field}", artifact_value, float(row[field]))
                    )
            prev_nav = NOTIONAL if prev_row is None else float(prev_row["nav"])
            if not _close(float(rec["nav"]) - prev_nav, float(row["daily_pnl"])):
                mismatches.append(
                    _mismatch(
                        session,
                        "daily_pnl.pnl_identity",
                        float(rec["nav"]) - prev_nav,
                        float(row["daily_pnl"]),
                    )
                )

    # risk_state --------------------------------------------------------------
    df = frame("risk_state")
    if df is not None:
        if len(df) != 1:
            mismatches.append(_mismatch(session, "risk_state.rows", len(df), 1))
        else:
            rec = df.iloc[0]
            if str(rec.get("date")) != session:
                mismatches.append(_mismatch(session, "risk_state.date", str(rec.get("date")), session))
            for field in ("vol_scale", "dd_scale", "exposure", "drawdown"):
                if field not in df.columns:
                    mismatches.append(_mismatch(session, "risk_state.column", None, field))
                    continue
                artifact_value = float(rec[field])
                if field == "drawdown":
                    expected = float(running_dd)
                elif field == "exposure":
                    expected = float(row["vol_scale"]) * float(row["regime_exposure"])
                else:
                    expected = float(row[field])
                if not _close(artifact_value, expected):
                    mismatches.append(
                        _mismatch(session, "drawdown" if field == "drawdown" else f"risk_state.{field}", artifact_value, expected)
                    )

    # regime ------------------------------------------------------------------
    df = frame("regime")
    if df is not None:
        if len(df) != 1:
            mismatches.append(_mismatch(session, "regime.rows", len(df), 1))
        else:
            rec = df.iloc[0]
            if str(rec.get("date")) != session:
                mismatches.append(_mismatch(session, "regime.date", str(rec.get("date")), session))
            if "regime_exposure" not in df.columns:
                mismatches.append(_mismatch(session, "regime.column", None, "regime_exposure"))
            elif not _close(float(rec["regime_exposure"]), float(row["regime_exposure"])):
                mismatches.append(
                    _mismatch(
                        session,
                        "regime.regime_exposure",
                        float(rec["regime_exposure"]),
                        float(row["regime_exposure"]),
                    )
                )

    # positions ---------------------------------------------------------------
    df = frame("positions")
    weights = None if df is None else _weights(df)
    if df is not None:
        if weights is None:
            mismatches.append(
                _mismatch(session, "positions.columns", list(df.columns), "symbol, weight, date")
            )
        else:
            if "date" in df.columns:
                dates = {str(d) for d in df["date"]}
                if dates != {session}:
                    mismatches.append(_mismatch(session, "positions.date", sorted(dates), session))
            if set(weights) != set(universe) or len(df) != len(universe):
                mismatches.append(
                    _mismatch(session, "positions.symbols", sorted(weights), sorted(universe))
                )
            nonzero = int(sum(1 for w in weights.values() if abs(w) > 0.0))
            if nonzero != int(row["n_positions"]):
                mismatches.append(_mismatch(session, "positions.n_positions", nonzero, int(row["n_positions"])))
            gross = float(sum(abs(w) for w in weights.values()))
            if gross > 1.0 + ABS_TOL:
                mismatches.append(_mismatch(session, "positions.gross", gross, "<=1.0"))
            if prev_weights is not None:
                symbols = set(weights) | set(prev_weights)
                turnover = float(
                    sum(abs(weights.get(s, 0.0) - prev_weights.get(s, 0.0)) for s in symbols)
                )
                if not _close(turnover, float(row["turnover"])):
                    mismatches.append(
                        _mismatch(session, "positions.turnover", turnover, float(row["turnover"]))
                    )

    return mismatches, weights


def audit(
    state_path: Path = STATE_PATH,
    paper_dir: Path = PAPER_DIR,
    candidate_config_path: Path = CANDIDATE_CONFIG_PATH,
) -> dict:
    if not state_path.exists():
        raise FileNotFoundError(f"state file not found: {state_path}")
    if not paper_dir.is_dir():
        raise FileNotFoundError(f"artifact directory not found: {paper_dir}")
    if not candidate_config_path.exists():
        raise FileNotFoundError(f"candidate config not found: {candidate_config_path}")

    state = yaml.safe_load(state_path.read_text()) or {}
    universe = [str(s) for s in (yaml.safe_load(candidate_config_path.read_text()) or {}).get("universe") or []]
    if not universe:
        raise ValueError(f"{candidate_config_path}: no universe configured")
    history = state.get("run_history") or []
    if not history:
        raise ValueError(f"{state_path}: run_history is empty")

    navs = [float(r["nav"]) for r in history]
    running = _running_drawdown(navs)

    mismatches: list[dict] = []
    prev_weights: dict[str, float] | None = None
    for i, row in enumerate(history):
        session_mismatches, weights = reconcile_session(
            row,
            history[i - 1] if i else None,
            prev_weights,
            float(running[i]),
            paper_dir,
            universe,
        )
        mismatches.extend(session_mismatches)
        prev_weights = weights

    attested: list[dict] = []
    unattested: list[dict] = []
    for item in mismatches:
        pinned = KNOWN_DEFECTS.get((item["session"], item["field"]))
        if pinned is not None and isinstance(item["artifact"], float) and _close(
            item["artifact"], float(pinned["observed"])
        ):
            attested.append({**item, "reason": pinned["reason"]})
        else:
            unattested.append(item)

    return {
        "n_sessions": len(history),
        "first_session": str(history[0]["date"]),
        "last_session": str(history[-1]["date"]),
        "universe": universe,
        "n_checks": len(history) * 20,
        "n_mismatches": len(mismatches),
        "attested": attested,
        "unattested": unattested,
        "ok": not unattested,
    }


def render_report(result: dict) -> str:
    lines = [
        "# Paper-trading record vs daily-artifact reconciliation",
        "",
        "Read-only audit produced by",
        "`research/paper_trading_artifact_reconciliation_audit.py`.",
        "No file under `data/` or `config/` is written; every artifact field is",
        "re-derived from the committed state and compared with the committed",
        "per-session parquet.",
        "",
        "## Coverage",
        "",
        "| quantity | value |",
        "|---|---|",
        f"| universe checked | {', '.join(f'`{s}`' for s in result['universe'])} |",
        f"| record window | `{result['first_session']}` .. `{result['last_session']}` |",
        f"| record sessions | `{result['n_sessions']}` |",
        f"| sessions with a mismatch | `{len({m['session'] for m in result['attested'] + result['unattested']})}` |",
        f"| mismatches attested (known defects) | `{len(result['attested'])}` |",
        f"| mismatches unattested | `{len(result['unattested'])}` |",
        f"| verdict | `{'PASS' if result['ok'] else 'FAIL'}` |",
        "",
        "## Checks applied per session",
        "",
        "- `daily_pnl`: single row dated to the session; `daily_return`, `daily_pnl`",
        "  and `nav` equal the state row; `daily_pnl == nav - previous nav`.",
        "- `risk_state`: `vol_scale` and `dd_scale` equal the state row;",
        "  `exposure == vol_scale * regime_exposure`; `drawdown` equals the running",
        "  maximum drawdown of the record NAV series up to that session.",
        "- `regime`: `regime_exposure` equals the state row.",
        "- `positions`: exactly the configured universe, dated to the session; the",
        "  nonzero-weight count equals `n_positions`; gross exposure is at most 1;",
        "  `sum |w_t - w_{t-1}|` equals the state row's `turnover` (from session 2).",
        "",
        "## Known defects (attested)",
        "",
    ]
    if result["attested"]:
        for item in result["attested"]:
            lines.append(
                f"- `{item['session']}` `{item['field']}`: artifact "
                f"`{item['artifact']!r}`, expected `{item['record']!r}`."
            )
            lines.append(f"  {item['reason']}.")
    else:
        lines.append("- (none)")
    lines += ["", "## Unattested mismatches", ""]
    if result["unattested"]:
        for item in result["unattested"]:
            lines.append(
                f"- `{item['session']}` `{item['field']}`: artifact "
                f"`{item['artifact']!r}`, expected `{item['record']!r}`."
            )
    else:
        lines.append("- (none)")
    lines += [
        "",
        "A defect is only exempted when both its session/field key and its exact",
        "observed value match the pinned registry entry; any drift in either fails",
        "the audit. Known defects are documented, not repaired by rewriting the",
        "committed artifacts.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default=str(STATE_PATH))
    parser.add_argument("--paper-dir", default=str(PAPER_DIR))
    parser.add_argument("--candidate-config", default=str(CANDIDATE_CONFIG_PATH))
    parser.add_argument("--report", default=str(REPORT_PATH))
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = audit(Path(args.state), Path(args.paper_dir), Path(args.candidate_config))
    except FileNotFoundError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    for item in result["attested"]:
        print(
            f"ATTESTED {item['session']} {item['field']}: artifact "
            f"{item['artifact']!r} != expected {item['record']!r} ({item['reason']})"
        )
    for item in result["unattested"]:
        print(
            f"FAIL {item['session']} {item['field']}: artifact "
            f"{item['artifact']!r} != expected {item['record']!r}"
        )

    print(
        "SUMMARY "
        f"sessions={result['n_sessions']} "
        f"attested={len(result['attested'])} "
        f"unattested={len(result['unattested'])} "
        f"window={result['first_session']}..{result['last_session']}"
    )

    if not args.no_report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(result))

    if not result["ok"]:
        print("OVERALL: FAIL", file=sys.stderr)
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
