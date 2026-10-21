#!/usr/bin/env python3
"""Read-only PSR reachability for SMA-175 candidate (Cycle 921)."""

from __future__ import annotations

import argparse
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.tsmomentum_sma175_promotion_gate_eval import (
    CANDIDATE_ID,
    PSR_BLOCK_SIZE,
    PSR_N_BOOTSTRAP,
    PSR_SEED,
    PSR_TARGET_BACKTEST_SCALE,
    _eval_full_period,
    evaluate,
    load_close_from_cache,
)
from src.evaluation.sharpe import sharpe_ratio
from src.evaluation.statistics import compute_psr

Z_95 = float(stats.norm.ppf(0.95))


def main(argv=None) -> int:
    payload = evaluate()
    m = payload["metrics"]
    sr_obs = float(m["full_period_sharpe"])
    se = float(m["sharpe_se"])
    n0 = int(m["track_record_length"])
    sr_target = float(payload["psr_target"])

    required_sr = sr_target + Z_95 * se
    gap = required_sr - sr_obs
    delta_sr = sr_obs - sr_target

    if delta_sr <= 0 or se <= 0:
        additional = None
        attainable = False
        horizon_note = "Not attainable: observed Sharpe does not exceed the PSR target."
    else:
        ratio = (se * Z_95) / delta_sr
        n_needed = int(math.ceil(n0 * ratio * ratio))
        additional = max(0, n_needed - n0)
        attainable = True
        horizon_note = (
            f"Attainable at the record's observed mean return and dispersion: "
            f"{n_needed} total sessions ({additional} additional) needed."
        )

    print(f"OBSERVED_SHARPE|{sr_obs:.6f}")
    print(f"SHARPE_SE|{se:.6f}")
    print(f"PSR_TARGET|{sr_target:.4f}")
    print(f"Z_95|{Z_95:.6f}")
    print(f"REQUIRED_SHARPE_FOR_PSR_0.95|{required_sr:.6f}")
    print(f"GAP_TO_OBSERVED_SHARPE|{gap:.6f}")
    print(f"TRACK_RECORD_SESSIONS|{n0}")
    if attainable:
        print(f"SESSIONS_NEEDED_TOTAL|{n_needed}")
        print(f"ADDITIONAL_SESSIONS_NEEDED|{additional}")
    else:
        print("SESSIONS_NEEDED_TOTAL|not attainable")
        print("ADDITIONAL_SESSIONS_NEEDED|not attainable")
    print(f"ATTAINABLE|{'YES' if attainable else 'NO'}")
    print(horizon_note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
