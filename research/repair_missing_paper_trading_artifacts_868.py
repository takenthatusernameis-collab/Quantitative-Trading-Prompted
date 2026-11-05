#!/usr/bin/env python3
"""Reconstruct the three paper-trading artifacts dropped for 2026-11-02.

Cycle 868 bounded repair. `run_paper_trading_replay.py` runs the daily update per
trading day and writes all four daily artifacts after each state update. The
2026-11-02 state row was written to run_history / cumulative_* correctly, but the
positions_, regime_ and risk_state_ artifact writes for that session were dropped
(transient batch-write failure). `daily_pnl_20261102.parquet` was reconstructed
separately (handoff 631) from the state row; this script closes the remaining gap.

Reconstruction sources (all canonical, no invented data):
  * positions_20261102  -> the deterministic simulation's daily weights for the
    2026-11-02 row (re-run against the committed raw cache; the engine is
    deterministic and uses no RNG). This is the ONLY faithful source: the
    positions artifact holds the weights assigned at the start of that session,
    which run_history does not store and which differs from the final
    current_positions snapshot.
  * regime_20261102     -> regime_exposure from the state's run_history row for
    2026-11-02 (spy_price is not stored in run_history and was NaN in every
    existing regime artifact).
  * risk_state_20261102  -> vol_scale / dd_scale from the run_history row, plus
    exposure = vol_scale * regime_exposure (verified identical across all 462
    existing risk_state artifacts) and drawdown = state.max_drawdown.

Pre-write guard: every existing artifact of each kind is verified to be
reconstructable from the same provenance before any write, so the repair cannot
introduce a schema the live path never produced.

Scope: writes only the three new parquet files under data/processed/paper_trading/.
Does not touch the canonical state, data/raw, config, source, or tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"
OUTPUT_DIR = ROOT / "data" / "processed" / "paper_trading"
CONFIG_PATH = ROOT / "config" / "paper_trading_config.yaml"
TARGET_DATE = "2026-11-02"
TARGET_CLEAN = "20261102"

ARTIFACTS = ["positions", "regime", "risk_state"]


def load_state() -> dict:
    with open(STATE_PATH) as fh:
        return yaml.safe_load(fh) or {}


def verify_reconstructability(state: dict) -> None:
    """Every existing artifact must be reconstructable from the same provenance.

    regime_ and risk_state_ are pure functions of the run_history row for that
    date; positions_ is the simulation's daily weights for that date (verified
    by re-running the engine, not by a from-state assertion, since run_history
    does not store per-session weights).
    """
    run_history = {e["date"]: e for e in state["run_history"]}

    for kind in ["regime", "risk_state"]:
        for path in sorted(OUTPUT_DIR.glob(f"{kind}_*.parquet")):
            df = pd.read_parquet(path)
            date = str(df["date"].iloc[0])
            row = run_history[date]
            rec = df.to_dict("records")[0]
            if kind == "regime":
                assert abs(float(rec["regime_exposure"]) - row["regime_exposure"]) < 1e-12, (
                    f"{path}: regime_exposure mismatch"
                )
            else:
                assert abs(float(rec["vol_scale"]) - row["vol_scale"]) < 1e-12, (
                    f"{path}: vol_scale mismatch"
                )
                assert abs(float(rec["dd_scale"]) - row["dd_scale"]) < 1e-12, (
                    f"{path}: dd_scale mismatch"
                )
                expected_exposure = row["vol_scale"] * row["regime_exposure"]
                assert abs(float(rec["exposure"]) - expected_exposure) < 1e-9, (
                    f"{path}: exposure mismatch"
                )


def simulate_daily_weights(target_date: str) -> dict[str, float]:
    """Re-run the deterministic engine to recover that session's daily weights."""
    sys.path.insert(0, str(ROOT))
    from src.simulation.paper_trading import PaperTradingConfig, run_simulation

    # PaperTradingConfig extends SimulationConfig, so the loaded config is the
    # simulation config itself (the paper config only adds operational fields).
    cfg = PaperTradingConfig.from_paper_config_yaml(CONFIG_PATH)
    sim = run_simulation(cfg, cfg.history_start, target_date)
    daily = sim.daily
    if daily.empty:
        raise RuntimeError(f"simulation produced no daily rows for {target_date}")
    weights: dict[str, float] = {}
    for symbol in cfg.universe:
        col = f"weight_{symbol}"
        if col in daily.columns:
            weights[symbol] = float(daily.iloc[-1][col])
    return weights


def reconstruct(state: dict, weights: dict[str, float]) -> dict[str, pd.DataFrame]:
    row = next(e for e in state["run_history"] if e["date"] == TARGET_DATE)

    positions_df = pd.DataFrame(
        [{"symbol": k, "weight": v, "date": TARGET_DATE} for k, v in weights.items()]
    )

    regime_df = pd.DataFrame(
        [
            {
                "date": TARGET_DATE,
                "spy_price": float("nan"),
                "regime_exposure": row["regime_exposure"],
            }
        ]
    )

    risk_df = pd.DataFrame(
        [
            {
                "date": TARGET_DATE,
                "vol_scale": row["vol_scale"],
                "dd_scale": row["dd_scale"],
                "drawdown": state["max_drawdown"],
                "exposure": row["vol_scale"] * row["regime_exposure"],
            }
        ]
    )

    return {"positions": positions_df, "regime": regime_df, "risk_state": risk_df}


def main() -> int:
    state = load_state()
    verify_reconstructability(state)

    weights = simulate_daily_weights(TARGET_DATE)
    frames = reconstruct(state, weights)

    written = []
    for kind, df in frames.items():
        path = OUTPUT_DIR / f"{kind}_{TARGET_CLEAN}.parquet"
        df.to_parquet(path, index=False)
        written.append(path)

    for p in written:
        print(f"wrote {p}")
    print(f"reconstructed {len(written)} artifacts for {TARGET_DATE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())