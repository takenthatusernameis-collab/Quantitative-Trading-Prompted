# -*- coding: utf-8 -*-
"""Cycle 890 net-of-cost evaluation of cryptofunding_001."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
PROC = REPO / "data" / "processed" / "crypto"

COST_BPS = 3.0  # repository flat cost model per unit weight change
SLIP_BPS = 0.0


def load(sym):
    return pd.read_parquet(PROC / f"{sym}USDT_carry_path.parquet")


def main():
    out = {}
    for sym in ("BTC", "ETH"):
        df = load(sym)
        # always-on carry: gross_carry series already = spot-long/perp-short daily return
        gross_on = df["gross_carry"].astype(float)
        # rule (b): hold only while funding positive -> zero out days with no positive funding
        funding = df["funding_cashflow"].astype(float)
        pos_mask = (funding > 0).astype(float)
        gross_pos = gross_on * pos_mask
        # turnover: one entry + daily drift rebalance. Approximate as daily position change
        # position is constant notional 1.0 -> rebalance turnover = |spot_return|+|perp_return| scaled?
        # Use weight-change units: each day the notional drifts; rebalance to constant notional
        # turnover per day = abs(spot_return) + abs(perp_return) (two legs) approximated.
        turn_on = (df["spot_return"].abs() + df["perp_return"].abs()).astype(float)
        turn_pos = turn_on * pos_mask
        # net
        def net(g, t):
            return g - t * (COST_BPS / 10000.0)
        for name, g, t in [("always_on", gross_on, turn_on), ("funding_positive", gross_pos, turn_pos)]:
            r = net(g, t)
            ann = (1 + r).prod() ** (252 / len(r)) - 1
            vol = r.std() * np.sqrt(252)
            sh = (r.mean() / r.std()) * np.sqrt(252) if r.std() > 0 else float("nan")
            dd = ( (1+r).cumprod() / (1+r).cumprod().cummax() - 1).min()
            to_ann = t.mean() * 252
            out[f"{sym}_{name}"] = {
                "n": len(r),
                "ann_net_return": float(ann),
                "sharpe": float(sh),
                "max_dd": float(dd),
                "ann_turnover": float(to_ann),
                "rebalances": int((t > 1e-12).sum()),
            }
            print(sym, name, out[f"{sym}_{name}"])
    (REPO / "research" / "experiments" / "cryptofunding_002_evaluation.md").write_text(
        "# cryptofunding_002 evaluation\n\n" + json.dumps(out, indent=2) + "\n"
    )
    print("written")


if __name__ == "__main__":
    main()