"""Cycle 880: pre-registered evaluation of the overnight-session capture
candidate (`overnight_capture_001`).

Hypothesis: research/hypotheses/overnight_capture_001.md (pre-registered
before this script was executed). Config: config/overnight_capture_001.yaml.

The candidate holds a 1/3 equal-weight SPY/QQQ/IWM basket from the previous
close to the next open and is flat during the day. It is evaluated with the
repository's walk-forward, cost-aware discipline:

  * read-only: reads the committed cache in data/raw/, writes nothing;
  * 33 walk-forward folds (10y train / 12m test / 6m step, 21d purge+embargo);
  * per-fold statistic = test-period net Sharpe;
  * both benchmarks (close-to-close equal weight, intraday-only leg) are
    evaluated on the identical folds;
  * cost-sensitivity rows at 3 / 5 / 10 bp per unit of weight change
    (N = 3 for the Deflated Sharpe Ratio), never a selection grid;
  * DSR and block-bootstrap 95% CI on the pooled out-of-sample series.

`OVERALL: PASS` means the script's own self-checks passed (data integrity,
fold geometry, the exact session-leg decomposition and the benchmark
identities). It does NOT mean the candidate cleared the promotion gates: the
candidate verdict is printed separately as `DECISION:`.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.backtest.engine import compute_metrics, get_cost_params, get_risk_free_rate
from src.evaluation.sharpe import sharpe_ratio
from src.evaluation.statistics import block_bootstrap_sharpe, compute_dsr, compute_psr
from src.evaluation.walkforward import generate_walkforward_splits, summarize_walkforward

warnings.filterwarnings("ignore", category=RuntimeWarning)

CONFIG_PATH = REPO_ROOT / "config" / "overnight_capture_001.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"

with open(CONFIG_PATH) as fh:
    CFG = yaml.safe_load(fh)

UNIVERSE = list(CFG["universe"])
START_DATE = CFG["sample"]["start_date"]
END_DATE = CFG["sample"]["end_date"]
COST_ROWS_BPS = [float(b) for b in CFG["costs"]["sensitivity_rows_bps_per_unit"]]
DECISION_BPS = float(CFG["costs"]["decision_cost_bps_per_unit"])
N_TRIALS = int(CFG["costs"]["multiple_testing_n"])
GATE_SHARPE = float(CFG["gates"]["wf_mean_oos_sharpe_min"])
GATE_FOLD_RATE = float(CFG["gates"]["positive_fold_rate_min"])
GATE_TRADES = int(CFG["gates"]["pooled_oos_trades_min"])
N_BOOTSTRAP = int(CFG["statistics"]["n_bootstrap"])
BLOCK_SIZE = int(CFG["statistics"]["block_size"])
SEED = int(CFG["statistics"]["seed"])

COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()
REPO_COST_BPS = COMMISSION_BPS * 10000.0 + SLIPPAGE_BPS * 10000.0
RF_ANNUAL = get_risk_free_rate()


# ----------------------------------------------------------------------
# helpers (pure, unit-tested in tests/test_overnight_capture_backtest.py)
# ----------------------------------------------------------------------
def load_cached_ohlc(symbol: str) -> pd.DataFrame:
    """Read the committed raw OHLC cache for *symbol* (no network)."""
    path = RAW_DIR / f"{symbol}.parquet"
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df[["Open", "High", "Low", "Close"]]


def common_calendar(frames: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    """Intersection of the symbols' trading dates inside the sample window."""
    idx = None
    for df in frames.values():
        sub = df.index[(df.index >= pd.Timestamp(START_DATE, tz="UTC"))
                       & (df.index <= pd.Timestamp(END_DATE, tz="UTC"))]
        idx = sub if idx is None else idx.intersection(sub)
    return idx


def session_returns(open_: pd.DataFrame, close: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return the three session legs and verify their exact decomposition."""
    prev_close = close.shift(1)
    overnight = open_ / prev_close - 1.0
    intraday = close / open_ - 1.0
    c2c = close / prev_close - 1.0
    overnight.iloc[0] = 0.0
    c2c.iloc[0] = 0.0
    return {"overnight": overnight, "intraday": intraday, "close_to_close": c2c}


def turnover_units(n_sessions: int, per_session: float, one_off: bool = False) -> pd.Series:
    """Explicit turnover (units of weight change) for a leg."""
    if one_off:
        return pd.Series([1.0] + [0.0] * (n_sessions - 1))
    return pd.Series(per_session, index=range(n_sessions), dtype=float)


def apply_costs(gross: pd.Series, turnover: pd.Series, cost_bps_per_unit: float) -> pd.Series:
    """Subtract the explicit cost drag from a gross return series."""
    cost = turnover.reindex(gross.index).fillna(0.0) * (cost_bps_per_unit / 10000.0)
    return gross - cost


def leg_metrics(net_ret: pd.Series, weights: pd.DataFrame, turnover: pd.Series) -> dict:
    """Engine metrics with the leg's explicit turnover (the engine's weight
    frame cannot express a daily in/out cycle)."""
    m = dict(compute_metrics(net_ret, weights, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL))
    m["avg_daily_turnover"] = float(turnover.reindex(net_ret.index).fillna(0.0).mean())
    m["annualized_turnover"] = float(m["avg_daily_turnover"] * 252)
    m["trade_count"] = int((turnover.reindex(net_ret.index).fillna(0.0) > 1e-10).sum())
    m["canonical_sharpe"] = float(sharpe_ratio(net_ret))
    return m


def _git_hash() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=False,
                           capture_output=True, text=True, cwd=REPO_ROOT)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def main() -> int:
    self_checks: list[tuple[str, bool, str]] = []
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    print("=" * 78)
    print("CYCLE 880: OVERNIGHT-SESSION CAPTURE CANDIDATE (overnight_capture_001)")
    print("=" * 78)
    print(f"Generated: {today} | code revision: {_git_hash()} | config sha256[:12]: {_sha(CONFIG_PATH)}")
    print(f"Hypothesis: research/hypotheses/overnight_capture_001.md (pre-registered before this run)")
    print(f"Universe: {', '.join(UNIVERSE)} | sample {START_DATE} -> {END_DATE}")
    print(f"Cost model: commission {COMMISSION_BPS*10000:.1f} bps + slippage {SLIPPAGE_BPS*10000:.1f} bps "
          f"= {REPO_COST_BPS:.1f} bps per unit of weight change")

    # ---------------- data integrity pre-check ----------------
    print("\n" + "-" * 78)
    print("1. DATA-INTEGRITY PRE-CHECK (committed cache, no network)")
    print("-" * 78)
    frames = {s: load_cached_ohlc(s) for s in UNIVERSE}
    print(f"{'sym':<5}{'rows':>8}{'start':>13}{'end':>13}{'nanO':>6}{'nanC':>6}{'dup':>5}{'ohlc_v':>8}")
    for s, df in frames.items():
        ohlc_bad = int(((df["Open"] < df["Low"] - 1e-9) | (df["Open"] > df["High"] + 1e-9)
                        | (df["Close"] < df["Low"] - 1e-9) | (df["Close"] > df["High"] + 1e-9)).sum())
        print(f"{s:<5}{len(df):>8}{str(df.index.min().date()):>13}{str(df.index.max().date()):>13}"
              f"{int(df['Open'].isna().sum()):>6}{int(df['Close'].isna().sum()):>6}"
              f"{int(df.index.duplicated().sum()):>5}{ohlc_bad:>8}")
        self_checks.append((f"{s} has no NaN Open/Close", bool(df[["Open", "Close"]].notna().all().all()), "data"))
        self_checks.append((f"{s} has no OHLC violations", ohlc_bad == 0, "data"))
    cal = common_calendar(frames)
    print(f"common trading calendar: {len(cal)} sessions, {cal.min().date()} -> {cal.max().date()}")
    self_checks.append(("common calendar starts at IWM inception",
                         str(cal.min().date()) == START_DATE, "data"))
    self_checks.append(("common calendar ends at cache end",
                         str(cal.max().date()) == END_DATE, "data"))

    close = pd.DataFrame({s: frames[s]["Close"].reindex(cal) for s in UNIVERSE})
    open_ = pd.DataFrame({s: frames[s]["Open"].reindex(cal) for s in UNIVERSE})
    missing_open = int(open_.isna().sum().sum())
    print(f"sessions with a missing Open across the universe: {missing_open}")
    self_checks.append(("no missing Open on the common calendar", missing_open == 0, "data"))

    legs = session_returns(open_, close)
    _ident = (((1.0 + legs["overnight"]) * (1.0 + legs["intraday"]) - 1.0)
              - legs["close_to_close"]).abs().iloc[1:]
    recon = _ident.max().max()
    print(f"session-leg decomposition identity max abs error: {float(recon):.3e} "
          "((1+overnight)*(1+intraday)-1 == close-to-close)")
    self_checks.append(("session-leg decomposition identity holds", float(recon) < 1e-12, "identity"))

    w = pd.DataFrame(1.0 / len(UNIVERSE), index=cal, columns=UNIVERSE)
    gross_on = (w * legs["overnight"]).sum(axis=1)
    gross_in = (w * legs["intraday"]).sum(axis=1)
    gross_c2c = (w * legs["close_to_close"]).sum(axis=1)
    n = len(cal)
    turn_on = turnover_units(n, float(CFG["execution"]["turnover_units_per_session"]))
    turn_in = turnover_units(n, float(CFG["execution"]["turnover_units_per_session"]))
    turn_c2c = turnover_units(n, 0.0, one_off=True)
    for t in (turn_on, turn_in, turn_c2c):
        t.index = cal

    # ---------------- walk-forward geometry ----------------
    print("\n" + "-" * 78)
    print("2. WALK-FORWARD GEOMETRY (asserted)")
    print("-" * 78)
    wf = CFG["walkforward"]
    splits = generate_walkforward_splits(
        START_DATE, END_DATE, float(wf["train_years"]), float(wf["test_months"]),
        float(wf["step_months"]), int(wf["purge_days"]), int(wf["embargo_days"]))
    expected_folds = int(wf["expected_folds"])
    assert len(splits) == expected_folds, f"expected {expected_folds} folds, got {len(splits)}"
    print(f"folds: {len(splits)} (asserted == {expected_folds})")
    print(f"first fold: train {splits[0]['train_start']} -> {splits[0]['train_end']} | "
          f"test {splits[0]['test_start']} -> {splits[0]['test_end']}")
    print(f"last  fold: train {splits[-1]['train_start']} -> {splits[-1]['train_end']} | "
          f"test {splits[-1]['test_start']} -> {splits[-1]['test_end']}")
    self_checks.append(("fold count == 33", len(splits) == expected_folds, "wf"))
    self_checks.append(("first fold test window is 2010-02-22 -> 2011-02-08",
                         splits[0]["test_start"] == "2010-02-22" and splits[0]["test_end"] == "2011-02-08", "wf"))
    self_checks.append(("last fold test window is 2025-08-06 -> 2026-07-23",
                         splits[-1]["test_start"] == "2025-08-06" and splits[-1]["test_end"] == "2026-07-23", "wf"))

    # ---------------- full-sample metrics ----------------
    print("\n" + "-" * 78)
    print("3. FULL-SAMPLE METRICS (decision cost configuration)")
    print("-" * 78)
    net_on = apply_costs(gross_on, turn_on, DECISION_BPS)
    net_in = apply_costs(gross_in, turn_in, DECISION_BPS)
    net_c2c = apply_costs(gross_c2c, turn_c2c, DECISION_BPS)
    m_on = leg_metrics(net_on, w, turn_on)
    m_in = leg_metrics(net_in, w, turn_in)
    m_c2c = leg_metrics(net_c2c, w, turn_c2c)
    print(f"{'leg':<18}{'ann_ret':>10}{'sharpe':>9}{'canon_sh':>10}{'sortino':>9}{'maxDD':>9}"
          f"{'ann_turn':>10}{'cost/yr':>10}{'trades':>8}")
    for name, m, gross, turn in (("overnight", m_on, gross_on, turn_on),
                                 ("intraday", m_in, gross_in, turn_in),
                                 ("close_to_close", m_c2c, gross_c2c, turn_c2c)):
        cost_drag = float((turn.reindex(gross.index).fillna(0.0) * DECISION_BPS / 10000.0).sum() * 252 / len(gross))
        print(f"{name:<18}{m['annualized_return']:>10.4f}{m['sharpe_ratio']:>9.4f}"
              f"{m['canonical_sharpe']:>10.4f}{float(m['sortino_ratio']):>9.4f}{m['max_drawdown']:>9.4f}"
              f"{m['annualized_turnover']:>10.1f}{cost_drag:>10.4f}{m['trade_count']:>8}")
    print(f"(gross overnight annualized return, no cost: "
          f"{float((1.0+gross_on).prod() ** (252/len(gross_on)) - 1.0):.4f})")

    # ---------------- per-fold walk-forward ----------------
    print("\n" + "-" * 78)
    print("4. PER-FOLD WALK-FORWARD TABLE (net of 3 bp/unit)")
    print("-" * 78)
    rows = []
    pooled_parts = []
    for i, s in enumerate(splits):
        mask = (cal >= pd.Timestamp(s["test_start"], tz="UTC")) & (cal <= pd.Timestamp(s["test_end"], tz="UTC"))
        if not mask.any():
            continue
        idx = cal[mask]
        r_on = net_on.reindex(idx)
        r_in = net_in.reindex(idx)
        r_c2c = net_c2c.reindex(idx)
        pooled_parts.append(r_on)
        mw_on = leg_metrics(r_on, w.reindex(idx), turn_on.reindex(idx))
        mw_in = leg_metrics(r_in, w.reindex(idx), turn_in.reindex(idx))
        mw_c2c = leg_metrics(r_c2c, w.reindex(idx), turn_c2c.reindex(idx))
        rows.append({
            "fold": i + 1, "test_start": s["test_start"], "test_end": s["test_end"],
            "n_sessions": len(idx),
            "test_sharpe": mw_on["sharpe_ratio"], "canon_sharpe": mw_on["canonical_sharpe"],
            "test_ann_return": mw_on["annualized_return"], "test_max_dd": mw_on["max_drawdown"],
            "test_trades": mw_on["trade_count"],
            "sharpe_intraday": mw_in["sharpe_ratio"], "sharpe_c2c": mw_c2c["sharpe_ratio"],
            "ann_return_c2c": mw_c2c["annualized_return"],
        })
    fdf = pd.DataFrame(rows)
    print(f"{'fold':>4}{'test_start':>12}{'test_end':>12}{'n':>5}{'sharpe':>9}{'canon':>9}"
          f"{'ann_ret':>10}{'maxDD':>9}{'trades':>7}{'sharpe_c2c':>11}")
    for _, r in fdf.iterrows():
        print(f"{int(r['fold']):>4}{r['test_start']:>12}{r['test_end']:>12}{int(r['n_sessions']):>5}"
              f"{r['test_sharpe']:>9.4f}{r['canon_sharpe']:>9.4f}{r['test_ann_return']:>10.4f}"
              f"{r['test_max_dd']:>9.4f}{int(r['test_trades']):>7}{r['sharpe_c2c']:>11.4f}")
    summary = summarize_walkforward(fdf)
    pooled = pd.concat(pooled_parts).sort_index()
    print(f"\nWF mean OOS Sharpe (gate statistic): {summary['mean_test_sharpe']:.6f}")
    print(f"WF std of fold Sharpes: {summary['std_test_sharpe']:.6f} | median: {summary['median_test_sharpe']:.6f}"
          f" | min: {summary['min_test_sharpe']:.6f} | max: {summary['max_test_sharpe']:.6f}")
    print(f"positive fold rate: {summary['pct_positive_sharpe']:.4%} | pooled OOS trades: {summary['total_test_trades']}")
    print(f"pooled OOS sessions: {len(pooled)} | pooled net annualized return: "
          f"{float((1.0+pooled).prod() ** (252/len(pooled)) - 1.0):.6f}")

    # ---------------- pooled statistics ----------------
    print("\n" + "-" * 78)
    print("5. POOLED OOS STATISTICS (DSR at N=3, block-bootstrap 95% CI)")
    print("-" * 78)
    dsr = compute_dsr(pooled, n_configs=N_TRIALS, sr_target=0.0,
                      n_bootstrap=N_BOOTSTRAP, block_size=BLOCK_SIZE, seed=SEED)
    psr09 = compute_psr(pooled, sr_target=GATE_SHARPE, n_bootstrap=N_BOOTSTRAP,
                        block_size=BLOCK_SIZE, seed=SEED)
    bs = block_bootstrap_sharpe(pooled, n_samples=N_BOOTSTRAP, block_size=BLOCK_SIZE, seed=SEED)
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    pooled_bt = leg_metrics(pooled, w.reindex(pooled.index), turn_on.reindex(pooled.index))
    print(f"pooled canonical Sharpe (arithmetic, rf 0): {float(sharpe_ratio(pooled)):.6f}")
    print(f"pooled backtest-scale Sharpe (CAGR, rf 2%):  {pooled_bt['sharpe_ratio']:.6f}")
    print(f"DSR (N={N_TRIALS}, sr_target 0): {dsr['dsr']:.6f} | "
          f"PSR vs {GATE_SHARPE}: {psr09['psr_empirical']:.6f} | "
          f"PSR normal approx: {psr09['psr_normal']:.6f} | "
          f"bootstrap SE of Sharpe: {psr09['sharpe_se']:.6f}")
    print(f"block-bootstrap Sharpe 95% CI: [{lo:.6f}, {hi:.6f}] (n={N_BOOTSTRAP}, block={BLOCK_SIZE}, seed={SEED})")

    # ---------------- cost sensitivity ----------------
    print("\n" + "-" * 78)
    print("6. COST-SENSITIVITY ROW (3 / 5 / 10 bp per unit; N=3, not a selection grid)")
    print("-" * 78)
    cost_rows = []
    for bps in COST_ROWS_BPS:
        net_b = apply_costs(gross_on, turn_on, bps)
        pooled_b = pd.concat([net_b.reindex(p.index) for p in pooled_parts]).sort_index()
        fold_sharpes = []
        for i, s in enumerate(splits):
            mask = (cal >= pd.Timestamp(s["test_start"], tz="UTC")) & (cal <= pd.Timestamp(s["test_end"], tz="UTC"))
            idx = cal[mask]
            mm = leg_metrics(net_b.reindex(idx), w.reindex(idx), turn_on.reindex(idx))
            fold_sharpes.append(mm["sharpe_ratio"])
        wf_mean = float(np.mean(fold_sharpes))
        ann = float((1.0 + pooled_b).prod() ** (252 / len(pooled_b)) - 1.0)
        cost_rows.append({"bps": bps, "wf_mean_sharpe": wf_mean, "pooled_ann_return": ann,
                          "pooled_canonical_sharpe": float(sharpe_ratio(pooled_b))})
        print(f"{bps:>5.1f} bp/unit | WF mean OOS Sharpe {wf_mean:>9.4f} | pooled ann. return {ann:>9.4f}"
              f" | pooled canonical Sharpe {float(sharpe_ratio(pooled_b)):>9.4f}")
    self_checks.append(("decision cost row is 3 bp/unit", DECISION_BPS == 3.0, "cost"))
    self_checks.append(("repository cost model is 3 bp/unit", abs(REPO_COST_BPS - 3.0) < 1e-9, "cost"))

    # ---------------- benchmarks on identical folds ----------------
    print("\n" + "-" * 78)
    print("7. BENCHMARKS ON IDENTICAL FOLDS")
    print("-" * 78)
    wf_c2c = float(fdf["sharpe_c2c"].mean())
    wf_in = float(fdf["sharpe_intraday"].mean())
    print(f"overnight leg  WF mean OOS Sharpe: {summary['mean_test_sharpe']:.6f}")
    print(f"close-to-close WF mean OOS Sharpe: {wf_c2c:.6f}")
    print(f"intraday leg   WF mean OOS Sharpe: {wf_in:.6f}")
    print(f"overnight minus close-to-close (net): {summary['mean_test_sharpe'] - wf_c2c:+.6f}")

    # ---------------- gate dispersion (Cycle 879 carry-over) ----------------
    print("\n" + "-" * 78)
    print("8. ROLLING-63 GATE STATISTIC DISPERSION ON THE CANDIDATE'S OWN HISTORY")
    print("-" * 78)
    roll = pooled.rolling(63).apply(lambda x: sharpe_ratio(pd.Series(x)), raw=True).dropna()
    if len(roll):
        fn_rate = float((roll < GATE_SHARPE).mean())
        print(f"rolling-63 canonical Sharpe windows: {len(roll)} | current pooled-window value: "
              f"{float(sharpe_ratio(pooled[-63:])):.6f}")
        print(f"windows below the {GATE_SHARPE} gate: {fn_rate:.4%} | "
              f"percentile of the current window: {float((roll < float(sharpe_ratio(pooled[-63:]))).mean()):.4%}")
        print(f"rolling-window median {float(roll.median()):.6f} | p10 {float(roll.quantile(0.10)):.6f} | "
              f"p90 {float(roll.quantile(0.90)):.6f}")
    else:
        fn_rate = float("nan")
        print("insufficient pooled history for a rolling-63 dispersion estimate")

    # ---------------- gates and verdict ----------------
    print("\n" + "-" * 78)
    print("9. GATES AND PRE-REGISTERED FALSIFICATION VERDICTS")
    print("-" * 78)
    g1 = summary["mean_test_sharpe"] >= GATE_SHARPE
    g2 = summary["pct_positive_sharpe"] >= GATE_FOLD_RATE
    g3 = summary["total_test_trades"] > GATE_TRADES
    g4 = summary["mean_test_sharpe"] > wf_c2c
    g5 = float(np.mean([r["wf_mean_sharpe"] for r in cost_rows if r["bps"] == 10.0])) > 0.0
    print(f"F1 WF mean OOS Sharpe >= {GATE_SHARPE}: {summary['mean_test_sharpe']:.6f} -> {'PASS' if g1 else 'FAIL'}")
    print(f"F2 positive fold rate >= {GATE_FOLD_RATE:.0%}: {summary['pct_positive_sharpe']:.4%} -> {'PASS' if g2 else 'FAIL'}")
    print(f"F3 pooled OOS trades > {GATE_TRADES}: {summary['total_test_trades']} -> {'PASS' if g3 else 'FAIL'}")
    print(f"F4 net WF Sharpe > same-fold close-to-close: {summary['mean_test_sharpe']:.6f} vs {wf_c2c:.6f}"
          f" -> {'PASS' if g4 else 'FAIL'}")
    print(f"F5 edge survives the 10 bp/unit cost row: WF mean Sharpe {cost_rows[-1]['wf_mean_sharpe']:.6f}"
          f" -> {'PASS' if g5 else 'FAIL'}")
    print(f"DSR (N={N_TRIALS}): {dsr['dsr']:.6f} -> {'not rejected' if dsr['dsr'] > 0 else 'REJECTED'}")
    print(f"block-bootstrap 95% CI lower bound: {lo:.6f} -> {'PASS' if lo > 0 else 'FAIL'}")
    all_gates = bool(g1 and g2 and g3 and g4 and g5 and dsr["dsr"] > 0 and lo > 0)
    decision = ("Credible candidate for further validation" if all_gates else "Rejected/Failed")
    print(f"\nDECISION: {decision}")

    # ---------------- self checks ----------------
    print("\n" + "-" * 78)
    print("10. SCRIPT SELF-CHECKS")
    print("-" * 78)
    ok = True
    for name, passed, _ in self_checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and bool(passed)
    overall = ok and len(rows) == expected_folds and abs(REPO_COST_BPS - DECISION_BPS) < 1e-9
    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
