"""Read-only check of the drift falsification conditions.

``research/reports/drift_decision_20261118.md`` §7 lists the three observations
that would overturn an ``observe`` decision for a stored drift flag:

1. a session with ``turnover > signal_turnover_pct`` that is *not* a regime
   transition (would indicate unintended trading rather than filter-driven
   rebalancing);
2. a stored drift flag that does not reproduce from the committed state (would
   indicate a write-order/accounting defect);
3. a recorded regime exposure that disagrees with the persisted regime
   artifact (would indicate an artifact/state mismatch).

This module evaluates those three conditions against the committed paper-trading
state and artifacts. It is pure read-only: it never writes the state, the
artifact directory, ``data/raw`` or any config. Exit code is ``0`` when every
condition holds, ``1`` when a violation is reported.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.drift import (
    DEFAULT_SHARPE_THRESHOLD,
    DEFAULT_WINDOW,
    sharpe_persistence,
)
from src.evaluation.sharpe import sharpe_ratio

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"
CONFIG_PATH = ROOT / "config" / "paper_trading_config.yaml"
PAPER_DIR = ROOT / "data" / "processed" / "paper_trading"

TOL = 1e-9


def check_turnover_regime_coupling(
    history: list[dict], threshold: float
) -> list[str]:
    """Return violations of "high turnover is always a regime transition"."""
    violations: list[str] = []
    for prev, cur in itertools.pairwise(history):
        turnover = float(cur.get("turnover", 0.0) or 0.0)
        flipped = float(cur.get("regime_exposure", 1.0)) != float(
            prev.get("regime_exposure", 1.0)
        )
        if turnover > threshold and not flipped:
            violations.append(
                f"{cur.get('date')}: turnover {turnover:.6f} > {threshold} "
                "without a regime transition"
            )
    return violations


def _reproduce_flags(state: dict, threshold: float) -> list[str]:
    history = state.get("run_history") or []
    flags = state.get("drift_flags") or {}
    violations: list[str] = []
    if len(history) < 2:
        return violations

    last, prev = history[-1], history[-2]
    last_date = last.get("date")

    for name, flag in flags.items():
        if flag.get("date") != last_date:
            violations.append(
                f"{name}: flag date {flag.get('date')} != last session {last_date}"
            )

    turnover = float(last.get("turnover", 0.0) or 0.0)
    if "high_turnover" in flags:
        stored = float(flags["high_turnover"]["value"])
        if abs(stored - turnover) > TOL or turnover <= threshold:
            violations.append(
                f"high_turnover: stored {stored:.12f} != recomputed {turnover:.12f}"
            )
    elif turnover > threshold:
        violations.append(
            f"high_turnover: session turnover {turnover:.6f} > {threshold} "
            "but no flag stored"
        )

    exposure_from = float(prev.get("regime_exposure", 1.0))
    exposure_to = float(last.get("regime_exposure", 1.0))
    if "regime_flip" in flags:
        if (
            abs(float(flags["regime_flip"]["from"]) - exposure_from) > TOL
            or abs(float(flags["regime_flip"]["to"]) - exposure_to) > TOL
        ):
            violations.append(
                "regime_flip: stored from/to "
                f"{flags['regime_flip']['from']}->{flags['regime_flip']['to']} "
                f"!= recomputed {exposure_from}->{exposure_to}"
            )
    elif exposure_from != exposure_to:
        violations.append(
            f"regime_flip: exposure {exposure_from}->{exposure_to} but no flag stored"
        )

    if state.get("previous_regime_exposure") is not None and (
        abs(float(state["previous_regime_exposure"]) - exposure_to) > TOL
    ):
        violations.append(
            "previous_regime_exposure: stored "
            f"{state['previous_regime_exposure']} != last session {exposure_to}"
        )

    returns = [float(x) for x in (state.get("cumulative_returns") or [])]
    cum_dates = [str(d) for d in (state.get("cumulative_dates") or [])]
    if cum_dates and cum_dates[-1] != last_date:
        returns.append(float(last.get("daily_return", 0.0) or 0.0))
        cum_dates.append(last_date)
    recent = np.asarray(returns[-DEFAULT_WINDOW:])
    recomputed_sharpe = sharpe_ratio(recent)
    if "low_rolling_sharpe" in flags:
        stored = float(flags["low_rolling_sharpe"]["value"])
        if abs(stored - recomputed_sharpe) > 1e-12:
            violations.append(
                f"low_rolling_sharpe: stored {stored:.12f} != recomputed "
                f"{recomputed_sharpe:.12f}"
            )
        streak = int(sharpe_persistence(cum_dates, returns)["streak_days"])
        stored_streak = int(flags["low_rolling_sharpe"].get("persistence_days", -1))
        if stored_streak != streak:
            violations.append(
                f"low_rolling_sharpe: stored persistence {stored_streak} "
                f"!= recomputed {streak}"
            )
        if recomputed_sharpe >= DEFAULT_SHARPE_THRESHOLD:
            violations.append(
                "low_rolling_sharpe: flag stored but recomputed Sharpe "
                f"{recomputed_sharpe:.12f} >= {DEFAULT_SHARPE_THRESHOLD}"
            )

    if exposure_from != exposure_to:
        expected_persistence = 1
        if int(state.get("regime_persistence_days", -1)) != expected_persistence:
            violations.append(
                "regime_persistence_days: flipped session stored "
                f"{state.get('regime_persistence_days')} != 1"
            )
        if "regime_persistence_low" in flags and int(
            flags["regime_persistence_low"]["value"]
        ) != expected_persistence:
            violations.append(
                "regime_persistence_low: flipped session stored value "
                f"{flags['regime_persistence_low']['value']} != 1"
            )
    return violations


def check_flag_reproduction(state: dict, threshold: float) -> list[str]:
    """Return violations of "stored flags reproduce from the committed state"."""
    return _reproduce_flags(state, threshold)


def check_artifact_agreement(state: dict, paper_dir: Path) -> list[str]:
    """Return violations of "recorded exposure matches the persisted artifact"."""
    history = state.get("run_history") or []
    violations: list[str] = []
    if not history:
        return ["run_history is empty; cannot check artifacts"]
    last = history[-1]
    stamp = str(last.get("date", "")).replace("-", "")
    regime_file = paper_dir / f"regime_{stamp}.parquet"
    if not regime_file.exists():
        return [f"missing regime artifact {regime_file.name}"]
    artifact = pd.read_parquet(regime_file)
    if "regime_exposure" not in artifact.columns:
        return [f"{regime_file.name}: no regime_exposure column"]
    recorded = float(last.get("regime_exposure", 1.0))
    persisted = float(artifact["regime_exposure"].iloc[-1])
    if abs(recorded - persisted) > TOL:
        violations.append(
            f"{regime_file.name}: artifact exposure {persisted} != recorded {recorded}"
        )

    positions_file = paper_dir / f"positions_{stamp}.parquet"
    if recorded == 0.0 and positions_file.exists():
        positions = pd.read_parquet(positions_file)
        weight_cols = [c for c in positions.columns if c.startswith("weight_")]
        if weight_cols:
            max_weight = float(np.abs(positions[weight_cols].to_numpy()).max())
            if max_weight > TOL:
                violations.append(
                    f"{positions_file.name}: zero exposure but max |weight| "
                    f"{max_weight:.12f}"
                )
    return violations


def main() -> int:
    state = yaml.safe_load(STATE_PATH.read_text())
    config = yaml.safe_load(CONFIG_PATH.read_text())
    threshold = float(config["alert_thresholds"]["signal_turnover_pct"])
    history = state.get("run_history") or []

    sections = [
        (
            "high turnover implies regime transition",
            check_turnover_regime_coupling(history, threshold),
        ),
        ("stored flags reproduce from state", check_flag_reproduction(state, threshold)),
        ("recorded exposure matches artifact", check_artifact_agreement(state, PAPER_DIR)),
    ]

    failed = 0
    for name, violations in sections:
        if violations:
            failed += 1
            print(f"FAIL {name}")
            for item in violations:
                print(f"  - {item}")
        else:
            print(f"OK   {name}")

    sessions = len(history)
    transitions = sum(
        1
        for prev, cur in itertools.pairwise(history)
        if float(cur.get("regime_exposure", 1.0))
        != float(prev.get("regime_exposure", 1.0))
    )
    high_turnover = sum(
        1 for row in history if float(row.get("turnover", 0.0) or 0.0) > threshold
    )
    print(
        f"SUMMARY sessions={sessions} regime_transitions={transitions} "
        f"high_turnover_sessions={high_turnover} threshold={threshold}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
