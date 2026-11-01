#!/usr/bin/env python3
"""Machine-checkable invariant for DBC/csmomentum governance blocker.
Exits 0 if consistent, exits 1 with details if inconsistent.
"""
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    dbc_path = repo / "data/raw/DBC.parquet"
    sim_path = repo / "data/processed/simulation_csmomentum_001.parquet"

    if not dbc_path.exists() or not sim_path.exists():
        print("MISSING_FILES")
        print(f"dbc_exists={dbc_path.exists()} sim_exists={sim_path.exists()}")
        return 2

    dbc = pd.read_parquet(dbc_path)
    sim = pd.read_parquet(sim_path)

    dbc_start = pd.Timestamp(dbc.index[0])
    dbc_end = pd.Timestamp(dbc.index[-1])
    sim_start = pd.Timestamp(sim.index[0])
    sim_end = pd.Timestamp(sim.index[-1])

    # Check if sim extends beyond dbc
    if sim_end > dbc_end:
        print("INCONSISTENT")
        print(f"dbc_end={dbc_end.date()} sim_end={sim_end.date()}")
        print("reason=sim_end > dbc_end (frozen artifacts vs extended DBC)")
        print("owner_decision_required=(a) truncate DBC to sim_end_cutoff or (b) regenerate artifacts or (c) amend records")
        return 1

    print("CONSISTENT")
    print(f"dbc={dbc_start.date()}..{dbc_end.date()} rows={len(dbc)}")
    print(f"sim={sim_start.date()}..{sim_end.date()} rows={len(sim)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
