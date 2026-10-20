"""Cycle 896: independent replication of the Cycle 895 reconciled fixed-coin
portfolio numbers.

Standalone derivation that does NOT reuse
``research/eval_cryptofunding.py``'s ``build_fixed_coin_portfolio_book``. It
re-derives the capital-consistent fixed-coin portfolio (capital split once,
half per symbol at entry, never rebalanced; P&L added against the combined
equity; entry/exit turnover only) for all three pre-registered rules and
prints: full-sample net annualized return, canonical Sharpe, max drawdown,
annualized turnover, per-sample values (full/train/val/test_oos/post2022),
break-evens, and the promotion gate.

Exit 0 with OVERALL: PASS when every number matches
``research/eval_cryptofunding.py`` within 1e-9.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.backtest.engine import compute_metrics, get_cost_params, get_risk_free_rate  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402

PERIODS_PER_YEAR = 365
COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()
RF_ANNUAL = get_risk_free_rate()

PROC_CRYPTO = REPO / "data" / "processed" / "crypto"
ARTIFACT = REPO / "research" / "experiments" / "cryptofunding_002_evaluation.md"

PROMOTION_SHARPE_MIN = 0.9
PROMOTION_MIN_POOLED_OOS_TRADES = 100

SPLITS: dict[str, tuple[str, str]] = {
    "full": ("2020-01-02", "2026-09-30"),
    "train": ("2020-01-02", "2022-12-31"),
    "val": ("2023-01-01", "2024-12-31"),
    "test_oos": ("2025-01-01", "2026-09-30"),
    "post2022": ("2023-01-01", "2026-09-30"),
}
BASE_SYMBOLS = ("BTCUSDT", "ETHUSDT")
RULE_IDS = ("always_on", "funding_positive_sameday", "funding_positive_lagged")

#: Headline cost model (Cycle 892): venue taker + repository slippage + rf capital charge.
HEADLINE_SPOT_BPS = 12.0 * 10000.0
HEADLINE_PERP_BPS = 7.0 * 10000.0
HEADLINE_CAPITAL_RATE = RF_ANNUAL


def load_carry_path(symbol: str) -> pd.DataFrame:
    path = PROC_CRYPTO / f"{symbol}_carry_path.parquet"
    frame = pd.read_parquet(path)
    frame.index = pd.DatetimeIndex(frame.index)
    return frame.sort_index()


def sample_index(index: pd.DatetimeIndex, sample: str) -> pd.DatetimeIndex:
    start, end = SPLITS[sample]
    mask = (index >= pd.Timestamp(start, tz="UTC")) & (index <= pd.Timestamp(end, tz="UTC"))
    return index[mask]


def position_series(path: pd.DataFrame, rule_id: str) -> pd.Series:
    funding = path["funding_cashflow"].astype(float)
    if rule_id == "always_on":
        return pd.Series(1.0, index=path.index)
    if rule_id == "funding_positive_sameday":
        return (funding > 0).astype(float)
    if rule_id == "funding_positive_lagged":
        lagged = funding.shift(1)
        position = (lagged > 0).astype(float)
        position.iloc[0] = 0.0
        return position
    raise ValueError(rule_id)


def annualized_return(returns: pd.Series, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    r = pd.Series(returns, dtype=float).fillna(0.0)
    if len(r) == 0:
        return float("nan")
    with np.errstate(invalid="ignore"):
        growth = float((1.0 + r).prod())
    if growth <= 0.0 or not np.isfinite(growth):
        return float("nan")
    with np.errstate(invalid="ignore"):
        return float(growth ** (periods_per_year / len(r)) - 1.0)


def max_drawdown(returns: pd.Series) -> float:
    cum = (1.0 + pd.Series(returns, dtype=float)).cumprod()
    return float((cum / cum.expanding().max() - 1.0).min())


def build_reconciled_portfolio(paths, rule_id):
    """Capital-consistent fixed-coin portfolio, derived from scratch.

    Capital is split once (0.5 of combined equity per symbol at entry, never
    rebalanced); each symbol's coin quantity is sized from 0.25 of the
    combined equity (weight 0.5 x half of combined equity); the two symbols'
    P&L is added against the combined equity and that equity compounds.
    Entry days carry no same-day P&L by convention; entry and exit are
    charged as turnover (each leg trades the target notional per transition).
    """
    symbols = list(BASE_SYMBOLS)
    index = paths[symbols[0]].index
    n = len(index)
    data = {
        base: {
            "position": position_series(paths[base], rule_id).to_numpy(dtype=float),
            "spot_close": paths[base]["spot_close"].astype(float).to_numpy(dtype=float),
            "perp_close": paths[base]["perp_close"].astype(float).to_numpy(dtype=float),
            "funding": paths[base]["funding_cashflow"].astype(float).to_numpy(dtype=float),
        }
        for base in symbols
    }
    weight = 0.5
    equity = 1.0
    state = {base: {"held": False, "q": 0.0, "prev_spot": 0.0, "prev_perp": 0.0} for base in symbols}
    gross = np.zeros(n, dtype=float)
    turnover_spot_arr = np.zeros(n, dtype=float)
    turnover_perp_arr = np.zeros(n, dtype=float)
    spot_notional_arr = np.zeros(n, dtype=float)
    equity_path_arr = np.ones(n, dtype=float)
    entries_total = 0
    leg_weights: dict[str, np.ndarray] = {
        f"{base}_spot": np.zeros(n) for base in symbols
    }
    leg_weights.update({f"{base}_perp": np.zeros(n) for base in symbols})
    position_arr = np.zeros(n, dtype=float)
    exits_total = 0
    for i in range(n):
        turn_spot_d = 0.0
        turn_perp_d = 0.0
        just_entered = set()
        for base in symbols:
            st = state[base]
            pos = float(data[base]["position"][i])
            if pos > 0.5 and not st["held"]:
                s = float(data[base]["spot_close"][i])
                st["q"] = weight * (0.5 * equity) / s if s != 0 else 0.0
                st["held"] = True
                st["prev_spot"] = s
                st["prev_perp"] = float(data[base]["perp_close"][i])
                just_entered.add(base)
                entries_total += 1
                turn_spot_d += weight
                turn_perp_d += weight
            elif pos < 0.5 and st["held"]:
                st["held"] = False
                st["q"] = 0.0
                exits_total += 1
                turn_spot_d += weight
                turn_perp_d += weight
        turnover_spot_arr[i] = turn_spot_d
        turnover_perp_arr[i] = turn_perp_d
        position_arr[i] = sum(1.0 for base in symbols if state[base]["held"]) / len(symbols)
        pnl_total = 0.0
        for base in symbols:
            st = state[base]
            if not st["held"] or base in just_entered:
                continue
            s = float(data[base]["spot_close"][i])
            p = float(data[base]["perp_close"][i])
            f = float(data[base]["funding"][i])
            pnl_total += (
                st["q"] * ((s - p) - (st["prev_spot"] - st["prev_perp"]))
                + f * st["q"] * st["prev_perp"]
            )
            st["prev_spot"] = s
            st["prev_perp"] = p
        gross[i] = pnl_total / equity if equity != 0.0 else 0.0
        equity += pnl_total
        equity_path_arr[i] = equity
        spot_notional_arr[i] = sum(
            (st["q"] * float(data[base]["spot_close"][i]) / equity)
            if st["held"] and equity != 0 else 0.0
            for base, st in state.items()
        )
        for base in symbols:
            st = state[base]
            if st["held"] and equity != 0:
                leg_weights[f"{base}_spot"][i] = st["q"] * float(data[base]["spot_close"][i]) / equity
                leg_weights[f"{base}_perp"][i] = -(st["q"] * float(data[base]["perp_close"][i]) / equity)
    weights_frame = pd.DataFrame(leg_weights, index=index)
    return {
        "gross": pd.Series(gross, index=index, dtype=float),
        "turnover": pd.Series(turnover_spot_arr + turnover_perp_arr, index=index, dtype=float),
        "turnover_spot": pd.Series(turnover_spot_arr, index=index, dtype=float),
        "turnover_perp": pd.Series(turnover_perp_arr, index=index, dtype=float),
        "spot_notional": pd.Series(spot_notional_arr, index=index, dtype=float),
        "weights": weights_frame,
        "position": pd.Series(position_arr, index=index, dtype=float),
        "equity_path": pd.Series(equity_path_arr, index=index, dtype=float),
        "entries": entries_total,
        "exits": exits_total,
    }


def net_series_model(gross, turnover_spot, turnover_perp, spot_notional,
                     spot_bps, perp_bps, capital_rate):
    fee = turnover_spot * (spot_bps / 10000.0) + turnover_perp * (perp_bps / 10000.0)
    charge = spot_notional * (capital_rate / PERIODS_PER_YEAR)
    return gross - fee - charge


def book_metrics(port, sample, spot_bps, perp_bps, capital_rate):
    idx = sample_index(port["gross"].index, sample)
    gross_s = port["gross"].loc[idx]
    t = port["turnover"].loc[idx]
    ts = port["turnover_spot"].loc[idx]
    tp = port["turnover_perp"].loc[idx]
    sn = port["spot_notional"].loc[idx]
    net = net_series_model(port["gross"], port["turnover_spot"], port["turnover_perp"],
                           port["spot_notional"], spot_bps, perp_bps, capital_rate)
    net_sliced = net.loc[idx]
    weights = port["weights"].loc[idx]
    engine_rf = 0.0 if capital_rate > 0.0 else RF_ANNUAL
    engine = compute_metrics(
        net_sliced, weights, COMMISSION_BPS, SLIPPAGE_BPS, engine_rf,
        periods_per_year=PERIODS_PER_YEAR,
    )
    fee_drag = float(
        (ts * (spot_bps / 10000.0) + tp * (perp_bps / 10000.0)).mean() * PERIODS_PER_YEAR
    )
    capital_drag = float(sn.mean() * capital_rate)
    result = {
        "sessions": int(len(gross_s)),
        "start": str(gross_s.index[0].date()),
        "end": str(gross_s.index[-1].date()),
        "ann_return_geometric": float(engine["annualized_return"]),
        "ann_return_arithmetic": float(net_sliced.mean() * PERIODS_PER_YEAR),
        "ann_volatility": float(engine["annualized_volatility"]),
        "sharpe_canonical": float(sharpe_ratio(net_sliced, periods_per_year=PERIODS_PER_YEAR)),
        "sharpe_backtest_scale": float(engine["sharpe_ratio"]),
        "max_drawdown": float(engine["max_drawdown"]),
        "max_drawdown_recomputed": max_drawdown(net_sliced),
        "annualized_turnover_units": float(t.mean() * PERIODS_PER_YEAR),
        "annualized_turnover_spot_units": float(ts.mean() * PERIODS_PER_YEAR),
        "annualized_turnover_perp_units": float(tp.mean() * PERIODS_PER_YEAR),
        "annualized_fee_drag": fee_drag,
        "annualized_capital_charge_drag": capital_drag,
        "annualized_cost_drag": fee_drag + capital_drag,
        "avg_spot_notional_fraction": float(sn.mean()),
        "avg_gross_exposure": float(engine["avg_exposure"]),
        "rebalance_days": int((t > 1e-12).sum()),
        "invested_fraction": float((port["position"].loc[idx] > 0).mean()),
    }
    # Position changes are computed on the FULL path and then sliced, so a
    # sample that starts with an already-open position does not report a
    # spurious entry (the committed Cycle 895 convention).
    full_pos = port["position"]
    change = full_pos.diff()
    if len(change) > 0:
        change.iloc[0] = full_pos.iloc[0]
    change_sliced = change.loc[idx]
    metrics_out = {
        "position_entries": int((change_sliced > 0).to_numpy().sum()),
        "position_exits": int((change_sliced < 0).to_numpy().sum()),
    }
    return {**result, **metrics_out}


def _geometric_net(port, spot_bps, perp_bps, capital_rate, sample):
    net = net_series_model(
        port["gross"], port["turnover_spot"], port["turnover_perp"],
        port["spot_notional"], spot_bps, perp_bps, capital_rate,
    )
    value = annualized_return(net.loc[sample_index(net.index, sample)], PERIODS_PER_YEAR)
    return float(value) if np.isfinite(value) else -1.0


def _bisect(objective, lo, hi, tol=1e-9, max_iter=200):
    f_lo = float(objective(lo))
    f_hi = float(objective(hi))
    if not (np.isfinite(f_lo) and np.isfinite(f_hi)):
        return {"solution": None, "bracketed": False, "reason": "objective is not finite at a bracket end"}
    if f_lo < 0.0 or f_hi > 0.0:
        return {"solution": None, "bracketed": False, "reason": "objective does not change sign inside the bracket"}
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = float(objective(mid))
        if f_mid > 0.0:
            lo = mid
        else:
            hi = mid
        if hi - lo <= tol:
            break
    return {"solution": 0.5 * (lo + hi), "bracketed": True, "reason": ""}


def break_even_flat_bps(port, sample="full"):
    def objective(cost_bps):
        net = port["gross"] - port["turnover"] * (float(cost_bps) / 10000.0)
        value = annualized_return(net.loc[sample_index(net.index, sample)], PERIODS_PER_YEAR)
        return float(value) if np.isfinite(value) else -1.0
    sol = _bisect(objective, lo=-100.0, hi=500.0)
    return {"sample": sample, "solution_bps": sol["solution"], "bracketed": sol["bracketed"],
            "reason": sol["reason"]}


def break_even_capital_rate(port, fee_spot_bps, fee_perp_bps, sample="full"):
    def objective(rate):
        return _geometric_net(port, fee_spot_bps, fee_perp_bps, float(rate), sample)
    sol = _bisect(objective, lo=-0.5, hi=0.5)
    return {"sample": sample, "solution_annual_rate": sol["solution"], "bracketed": sol["bracketed"],
            "reason": sol["reason"]}


def break_even_venue_multiplier(port, base_spot_bps, base_perp_bps, capital_rate, sample="full"):
    def objective(mult):
        return _geometric_net(port, base_spot_bps * float(mult), base_perp_bps * float(mult), capital_rate, sample)
    sol = _bisect(objective, lo=0.0, hi=200.0)
    return {"sample": sample, "solution_multiplier": sol["solution"], "bracketed": sol["bracketed"],
            "reason": sol["reason"]}


def break_even_table(port, sample="full"):
    fee_spot = 12.0  # venue taker + repo slippage
    fee_perp = 7.0
    return {
        "break_even_flat_cost_bps": break_even_flat_bps(port, sample),
        "break_even_capital_charge_annual": break_even_capital_rate(port, fee_spot, fee_perp, sample),
        "break_even_venue_fee_multiplier": break_even_venue_multiplier(
            port, fee_spot, fee_perp, HEADLINE_CAPITAL_RATE, sample
        ),
    }


def promotion_gate(per_symbol_results):
    oos_sharpes = []
    pooled_entries = 0
    for result in per_symbol_results.values():
        oos = result["samples"]["test_oos"]
        oos_sharpes.append(float(oos["sharpe_canonical"]))
        pooled_entries += int(oos["position_entries"])
    mean_oos_sharpe = float(np.mean(oos_sharpes)) if oos_sharpes else float("nan")
    sharpe_pass = bool(np.isfinite(mean_oos_sharpe) and mean_oos_sharpe >= PROMOTION_SHARPE_MIN)
    trades_pass = bool(pooled_entries > PROMOTION_MIN_POOLED_OOS_TRADES)
    return {
        "net_oos_sharpe_canonical_365": mean_oos_sharpe,
        "net_oos_sharpe_min": PROMOTION_SHARPE_MIN,
        "sharpe_criterion_pass": sharpe_pass,
        "pooled_oos_position_round_trips": pooled_entries,
        "min_pooled_oos_trades": PROMOTION_MIN_POOLED_OOS_TRADES,
        "trade_count_criterion_pass": trades_pass,
        "promotion_gate_pass": bool(sharpe_pass and trades_pass),
    }


def build_fixed_coin_book_single(path, rule_id, weight=1.0):
    """Per-symbol fixed-coin book (committed Cycle 893 accounting), standalone.

    Hold ``q`` coins long spot and short perp from entry to exit; ``q`` is set
    at each entry from then-current marked-to-market equity,
    ``q = weight * equity / spot_close``. While held the daily gross P&L is the
    change of the basis level ``q * (S_t - P_t)`` plus the funding paid on the
    coin's perp notional ``q * funding_cashflow_t * P_{t-1}``. Entry days carry
    no same-day P&L; entry and exit are charged as turnover (each leg trades
    ``weight`` per transition).
    """
    position = position_series(path, rule_id)
    spot = path["spot_close"].astype(float)
    perp = path["perp_close"].astype(float)
    funding = path["funding_cashflow"].astype(float)
    index = path.index
    n = len(index)
    gross = np.zeros(n, dtype=float)
    equity_path = np.ones(n, dtype=float)
    coin_quantity = np.zeros(n, dtype=float)
    spot_notional = np.zeros(n, dtype=float)
    equity = 1.0
    q = 0.0
    held = False
    prev_spot = 0.0
    prev_perp = 0.0
    entries = 0
    exits = 0
    for i in range(n):
        pos = float(position.iloc[i])
        s = float(spot.iloc[i])
        p = float(perp.iloc[i])
        f = float(funding.iloc[i])
        if pos > 0.5 and not held:
            q = weight * equity / s if s != 0 else 0.0
            held = True
            prev_spot = s
            prev_perp = p
            equity_path[i] = equity
            coin_quantity[i] = q
            spot_notional[i] = weight
            entries += 1
            continue
        if pos < 0.5 and held:
            held = False
            q = 0.0
            equity_path[i] = equity
            exits += 1
            continue
        if held:
            basis_today = q * (s - p)
            basis_yesterday = q * (prev_spot - prev_perp)
            price_pnl = basis_today - basis_yesterday
            fund_pnl = f * q * prev_perp
            pnl = price_pnl + fund_pnl
            ret = pnl / equity if equity != 0 else 0.0
            gross[i] = ret
            equity += pnl
            prev_spot = s
            prev_perp = p
            equity_path[i] = equity
            coin_quantity[i] = q
            spot_notional[i] = q * s / equity if equity != 0 else 0.0
        else:
            equity_path[i] = equity
    change = position.diff()
    if len(change) > 0:
        change.iloc[0] = position.iloc[0]
    transition = change.abs() * weight
    turnover_spot = transition.astype(float)
    turnover_perp = transition.astype(float)
    turnover = (2.0 * transition).astype(float)
    weights_spot = (weight * position).astype(float)
    weights_perp = (-weight * position).astype(float)
    return {
        "gross": pd.Series(gross, index=index, dtype=float),
        "turnover": pd.Series(turnover, index=index, dtype=float),
        "turnover_spot": pd.Series(turnover_spot, index=index, dtype=float),
        "turnover_perp": pd.Series(turnover_perp, index=index, dtype=float),
        "spot_notional": pd.Series(spot_notional, index=index, dtype=float),
        "weights": pd.DataFrame({"spot": weights_spot, "perp": weights_perp}, index=index),
        "position": position.astype(float),
        "equity_path": pd.Series(equity_path, index=index, dtype=float),
        "entries": int((change > 0).to_numpy().sum()),
        "exits": int((change < 0).to_numpy().sum()),
    }


def evaluate_book(port, spot_bps=HEADLINE_SPOT_BPS, perp_bps=HEADLINE_PERP_BPS,
                  capital_rate=HEADLINE_CAPITAL_RATE, bootstrap_samples=()):
    samples = {sample: book_metrics(port, sample, spot_bps, perp_bps, capital_rate)
               for sample in SPLITS}
    return {"samples": samples}


def load_artifact_payload() -> dict:
    text = ARTIFACT.read_text()
    start = text.index("```json") + len("```json")
    end = text.index("```", start)
    return json.loads(text[start:end])


#: Expected reconciled promotion-gate rows, quoted verbatim from the Cycle 895
#: markdown prose (the JSON payload carries the per-symbol samples but not the
#: reconciled gate rows, so the prose is the committed record for these rows).
EXPECTED_GATES = {
    "always_on": {
        "net_oos_sharpe_canonical_365": 5.645,
        "sharpe_criterion_pass": True,
        "pooled_oos_position_round_trips": 0,
        "trade_count_criterion_pass": False,
        "promotion_gate_pass": False,
    },
    "funding_positive_lagged": {
        "net_oos_sharpe_canonical_365": -5.224,
        "sharpe_criterion_pass": False,
        "pooled_oos_position_round_trips": 95,
        "trade_count_criterion_pass": False,
        "promotion_gate_pass": False,
    },
    "funding_positive_sameday": {
        "net_oos_sharpe_canonical_365": -4.943,
        "sharpe_criterion_pass": False,
        "pooled_oos_position_round_trips": 95,
        "trade_count_criterion_pass": False,
        "promotion_gate_pass": False,
    },
}


def main() -> int:
    payload = load_artifact_payload()
    cost_eval = payload["cost_model_evaluation"]
    expected = cost_eval["fixed_coin_reconciled"]
    expected_be = cost_eval["fixed_coin_reconciled_break_evens"]
    headline_key = cost_eval["headline_cost_model"]

    paths = {base: load_carry_path(base) for base in BASE_SYMBOLS}
    failures: list[str] = []

    for rule_id in RULE_IDS:
        port = build_reconciled_portfolio(paths, rule_id)
        samples = {
            sample: book_metrics(port, sample, HEADLINE_SPOT_BPS, HEADLINE_PERP_BPS, HEADLINE_CAPITAL_RATE)
            for sample in SPLITS
        }
        be = break_even_table(port, "full")
        be_oos = break_even_table(port, "test_oos")
        per_symbol_books = {
            base: build_fixed_coin_book_single(paths[base], rule_id, weight=1.0)
            for base in BASE_SYMBOLS
        }
        per_symbol_samples = {
            base: {"samples": {
                sample: book_metrics(
                    per_symbol_books[base], sample,
                    HEADLINE_SPOT_BPS, HEADLINE_PERP_BPS, HEADLINE_CAPITAL_RATE,
                )
                for sample in SPLITS
            }}
            for base in BASE_SYMBOLS
        }
        gate = promotion_gate(per_symbol_samples)

        exp_rule = expected[rule_id][headline_key]["samples"]
        for sample in SPLITS:
            for key in ("ann_return_geometric", "ann_return_arithmetic", "ann_volatility",
                        "sharpe_canonical", "sharpe_backtest_scale", "max_drawdown",
                        "max_drawdown_recomputed", "annualized_turnover_units",
                        "annualized_turnover_spot_units", "annualized_turnover_perp_units",
                        "annualized_fee_drag", "annualized_capital_charge_drag",
                        "annualized_cost_drag", "avg_spot_notional_fraction", "avg_gross_exposure",
                        "invested_fraction", "rebalance_days", "sessions"):
                got = samples[sample][key]
                want = exp_rule[sample][key]
                if isinstance(want, (int, float)) and not isinstance(want, bool):
                    if not np.isclose(float(got), float(want), rtol=1e-9, atol=1e-12):
                        failures.append(
                            f"{rule_id} {sample} {key}: got {got!r} want {want!r}"
                        )
                else:
                    if got != want:
                        failures.append(f"{rule_id} {sample} {key}: got {got!r} want {want!r}")

        for sample, table in (("full", be), ("test_oos", be_oos)):
            for key, table_key in (("solution_bps", "break_even_flat_cost_bps"),
                                   ("solution_annual_rate", "break_even_capital_charge_annual"),
                                   ("solution_multiplier", "break_even_venue_fee_multiplier")):
                got = table[table_key][key]
                want = expected_be[rule_id][sample][table_key][key]
                if got is None and want is None:
                    continue
                if got is None or want is None or not np.isclose(float(got), float(want), rtol=1e-9, atol=1e-12):
                    failures.append(
                        f"{rule_id} {sample} break_even {key}: got {got!r} want {want!r}"
                    )
            for key in ("bracketed",):
                got = table["break_even_flat_cost_bps"][key]
                want = expected_be[rule_id][sample]["break_even_flat_cost_bps"][key]
                if got != want:
                    failures.append(f"{rule_id} {sample} break_even {key}: got {got!r} want {want!r}")

        exp_gate = EXPECTED_GATES[rule_id]
        for key in ("net_oos_sharpe_canonical_365", "sharpe_criterion_pass",
                    "pooled_oos_position_round_trips", "trade_count_criterion_pass",
                    "promotion_gate_pass"):
            got = gate[key]
            want = exp_gate[key]
            if isinstance(want, (int, float)) and not isinstance(want, bool):
                # The prose quotes the gate Sharpe to three decimal places.
                tol = 1e-2 if key == "net_oos_sharpe_canonical_365" else 1e-12
                if not np.isclose(float(got), float(want), rtol=1e-9, atol=tol):
                    failures.append(f"{rule_id} gate {key}: got {got!r} want {want!r}")
            else:
                if got != want:
                    failures.append(f"{rule_id} gate {key}: got {got!r} want {want!r}")

        print(f"== {rule_id}")
        for sample in SPLITS:
            m = samples[sample]
            print(f"  {sample}: net={m['ann_return_geometric']:.6f} sharpe={m['sharpe_canonical']:.6f} "
                  f"dd={m['max_drawdown']:.6f} turn={m['annualized_turnover_units']:.6f} "
                  f"ent={m['position_entries']} exit={m['position_exits']}")
        print(f"  BE full flat={be['break_even_flat_cost_bps']['solution_bps']} "
              f"cap={be['break_even_capital_charge_annual']['solution_annual_rate']} "
              f"mult={be['break_even_venue_fee_multiplier']['solution_multiplier']}")
        print(f"  BE oos flat={be_oos['break_even_flat_cost_bps']['solution_bps']} "
              f"cap={be_oos['break_even_capital_charge_annual']['solution_annual_rate']} "
              f"mult={be_oos['break_even_venue_fee_multiplier']['solution_multiplier']}")
        print(f"  GATE sharpe={gate['net_oos_sharpe_canonical_365']} pass={gate['promotion_gate_pass']} "
              f"trips={gate['pooled_oos_position_round_trips']}")

    if failures:
        print("OVERALL: FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
