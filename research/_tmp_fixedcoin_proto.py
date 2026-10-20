"""Temporary prototype: validate the fixed-coin construction math."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import research.eval_cryptofunding as ev  # noqa: E402


def fixed_coin_gross(path, rule, weight=1.0):
    """Clean fixed-coin construction returning a gross return Series.

    Entry at the close of the day on which the position turns on: q is set
    from that day's close, and the pair is held until the position turns off.
    While held, the daily P&L is the change of the basis level (q coins long
    spot, q coins short perp) plus the funding paid on the prior day's perp
    notional. Equity compounds.
    """
    position = ev.position_series(path, rule)
    S = path["spot_close"].astype(float)
    P = path["perp_close"].astype(float)
    f = path["funding_cashflow"].astype(float)
    index = path.index
    gross = pd.Series(np.nan, index=index, dtype=float)
    equity = 1.0
    q = 0.0
    held = False
    prev_perp = np.nan
    entries = 0
    exits = 0
    for i, ts in enumerate(index):
        pos = float(position.iloc[i])
        s = float(S.iloc[i])
        p = float(P.iloc[i])
        if pos > 0.5 and not held:
            # enter at today's close: q set so the spot notional is w*equity
            q = weight * equity / s if s != 0 else 0.0
            held = True
            entries += 1
            prev_perp = p
            # the pair is held from today's close; P&L starts tomorrow
            gross.iloc[i] = 0.0
            continue
        if pos < 0.5 and held:
            held = False
            exits += 1
            q = 0.0
            gross.iloc[i] = 0.0
            continue
        if held:
            # P&L from yesterday's close to today's close
            basis_today = q * (s - p)
            basis_yest = q * (prev_perp * 0.0)  # placeholder, set below
            # we track basis level at yesterday's close via prev_perp and prev_spot
            price_pnl = q * ((s - p) - (prev_spot - prev_perp))
            fund_pnl = f.iloc[i] * q * prev_perp
            pnl = price_pnl + fund_pnl
            ret = pnl / equity if equity != 0 else 0.0
            gross.iloc[i] = ret
            equity += pnl
            prev_spot = s
            prev_perp = p
        else:
            gross.iloc[i] = 0.0
    return gross, entries, exits


def fixed_coin_gross_v2(path, rule, weight=1.0):
    """Cleaner version tracking prev_spot and prev_perp explicitly."""
    position = ev.position_series(path, rule)
    S = path["spot_close"].astype(float)
    P = path["perp_close"].astype(float)
    f = path["funding_cashflow"].astype(float)
    index = path.index
    gross = pd.Series(np.nan, index=index, dtype=float)
    equity = 1.0
    q = 0.0
    held = False
    prev_spot = np.nan
    prev_perp = np.nan
    entries = 0
    exits = 0
    for i, ts in enumerate(index):
        pos = float(position.iloc[i])
        s = float(S.iloc[i])
        p = float(P.iloc[i])
        if pos > 0.5 and not held:
            q = weight * equity / s if s != 0 else 0.0
            held = True
            entries += 1
            prev_spot = s
            prev_perp = p
            gross.iloc[i] = 0.0
            continue
        if pos < 0.5 and held:
            held = False
            exits += 1
            q = 0.0
            gross.iloc[i] = 0.0
            continue
        if held:
            price_pnl = q * ((s - p) - (prev_spot - prev_perp))
            fund_pnl = f.iloc[i] * q * prev_perp
            pnl = price_pnl + fund_pnl
            ret = pnl / equity if equity != 0 else 0.0
            gross.iloc[i] = ret
            equity += pnl
            prev_spot = s
            prev_perp = p
        else:
            gross.iloc[i] = 0.0
    return gross, entries, exits


if __name__ == "__main__":
    for base in ev.BASE_SYMBOLS:
        path = ev.load_carry_path(base)
        for rule in ev.RULES:
            g2, e2, x2 = fixed_coin_gross_v2(path, rule)
            cn = ev.build_book(path, rule, weight=1.0, symbol=base)  # constant-notional gross
            cn_g = cn.gross
            # align: drop the entry day (0) from the fixed-coin series for compare
            g2c = g2.iloc[1:]
            cn_aligned = cn_g.iloc[1:]
            mask = g2c.notna() & cn_aligned.notna()
            diff = (g2c - cn_aligned).abs()
            print(
                f"{base} {rule.rule_id:24s} entries={e2} exits={x2} "
                f"max|fc-cn|={diff[mask].max():.2e} mean|fc-cn|={diff[mask].mean():.2e} "
                f"corr={np.corrcoef(g2c[mask], cn_aligned[mask])[0,1]:.4f}"
            )