"""Cycle 7: Simulation Framework & Paper-Trading Preparation.

Builds the simulation framework for the Cycle 6 validated candidate
(226-day TSMOM + combined vol-targeting 10% / drawdown-control 15%
+ SPY 200-day SMA trend filter, 3 bps round-trip costs) and verifies
that the simulation engine reproduces the backtest exactly.

Verification is performed against the original Cycle 5/6 code paths
(imported from research/run_cycle5.py and research/run_cycle6.py):

  1. Test-period replication (2018-2026): simulation (slice-mode
     overlay state) vs Cycle 5 `_eval_candidate` — Sharpe diff
     < 0.02, max-DD diff < 0.5%, exact trade count.
  2. Walk-forward replication: per-fold simulation (full-mode
     overlay state) vs Cycle 6 `_eval_candidate_period` — mean
     OOS Sharpe diff < 0.02.
  3. SMA plateau replication: 6 pre-specified windows, simulation
     vs Cycle 6 `_eval_candidate`.
  4. Determinism: identical outputs across repeated runs.

Artifacts produced:
  - src/simulation/engine.py            (simulation engine)
  - config/simulation_candidate_001.yaml (frozen candidate config)
  - data/processed/simulation_candidate_001.parquet (daily series)
  - data/processed/trades_candidate_001.parquet     (trade log)
  - research/reports/simulation_verification_001.md  (this report)
"""

from __future__ import annotations

import hashlib
import sys
import warnings
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.run_cycle5 import _load_close
from research.run_cycle6 import _eval_candidate, _eval_candidate_period
from src.data.yfinance_fetcher import fetch_universe
from src.evaluation.utils import period_metrics
from src.evaluation.walkforward import generate_walkforward_splits
from src.simulation.engine import SimulationConfig, SimulationResult, run_simulation

warnings.filterwarnings("ignore", category=RuntimeWarning)

SYMBOLS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
START_DATE = "1993-01-01"
END_DATE = "2026-10-09"
VAL_END = "2017-12-31"
OOS_START = "2018-01-01"

SMA_WINDOWS = [150, 175, 200, 226, 250, 277]

WF_TRAIN_YEARS = 10.0
WF_TEST_MONTHS = 12.0
WF_STEP_MONTHS = 6.0
WF_PURGE_DAYS = 21
WF_EMBARGO_DAYS = 21

TOL_SHARPE = 0.02
TOL_DD = 0.005
TOL_ANNRET = 0.005

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
SIM_PARQUET = REPO_ROOT / "data" / "processed" / "simulation_candidate_001.parquet"
TRADES_PARQUET = REPO_ROOT / "data" / "processed" / "trades_candidate_001.parquet"
REPORT_PATH = REPO_ROOT / "research" / "reports" / "simulation_verification_001.md"

DOCUMENTED = {
    "test_sharpe": 1.4178,
    "test_max_dd": -0.0779,
    "test_trades": 1196,
    "test_ann_return": 0.1446,
    "wf_mean_oos_sharpe": 0.9473,
}


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _git_hash() -> str:
    try:
        import subprocess

        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except (OSError, RuntimeError):
        return "unknown"


def _config_hash() -> str:
    return hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()[:12]


def _fmt_pct(x: float) -> str:
    return f"{x:.2%}"


def _fmt_num(x: float, nd: int = 4) -> str:
    return f"{x:.{nd}f}"


# ---------------------------------------------------------------------------
# 1. Test-period replication vs Cycle 5 backtest
# ---------------------------------------------------------------------------
def verify_test_period(config: SimulationConfig, close: pd.DataFrame) -> dict:
    print("\n=== [1] Test-Period Replication (2018-2026) ===")

    ref = _eval_candidate(close)
    ref_m = ref["test_metrics"]

    sim = run_simulation(config, OOS_START, END_DATE)
    sim_m = sim.metrics

    checks = {
        "Test Sharpe": {
            "ref": ref_m["sharpe_ratio"],
            "sim": sim_m["sharpe_ratio"],
            "diff": abs(sim_m["sharpe_ratio"] - ref_m["sharpe_ratio"]),
            "tol": TOL_SHARPE,
        },
        "Max Drawdown": {
            "ref": ref_m["max_drawdown"],
            "sim": sim_m["max_drawdown"],
            "diff": abs(sim_m["max_drawdown"] - ref_m["max_drawdown"]),
            "tol": TOL_DD,
        },
        "Ann. Return": {
            "ref": ref_m["annualized_return"],
            "sim": sim_m["annualized_return"],
            "diff": abs(sim_m["annualized_return"] - ref_m["annualized_return"]),
            "tol": TOL_ANNRET,
        },
        "Trades": {
            "ref": float(ref_m["trade_count"]),
            "sim": float(sim_m["trade_count"]),
            "diff": abs(float(sim_m["trade_count"]) - float(ref_m["trade_count"])),
            "tol": 0.0,
        },
    }
    for name, c in checks.items():
        status = "PASS" if c["diff"] <= c["tol"] else "FAIL"
        print(
            f"  {name}: backtest={c['ref']:.4f} simulation={c['sim']:.4f} "
            f"diff={c['diff']:.6f} (tol {c['tol']}) -> {status}"
        )

    all_pass = all(c["diff"] <= c["tol"] for c in checks.values())
    print(f"  Test-period replication: {'PASS' if all_pass else 'FAIL'}")
    return {
        "checks": checks,
        "ref_metrics": ref_m,
        "sim_metrics": sim_m,
        "sim_result": sim,
        "all_pass": all_pass,
    }


# ---------------------------------------------------------------------------
# 2. Walk-forward replication vs Cycle 6
# ---------------------------------------------------------------------------
def verify_walkforward(config: SimulationConfig, data: pd.DataFrame) -> dict:
    print("\n=== [2] Walk-Forward Replication ===")
    splits = generate_walkforward_splits(
        START_DATE,
        END_DATE,
        WF_TRAIN_YEARS,
        WF_TEST_MONTHS,
        WF_STEP_MONTHS,
        WF_PURGE_DAYS,
        WF_EMBARGO_DAYS,
    )
    wf_config = replace(config, overlay_warmup="full")

    rows = []
    for i, sp in enumerate(splits):
        ref_ret, ref_w = _eval_candidate_period(
            SYMBOLS, sp["test_start"], sp["test_end"]
        )
        ref_m = period_metrics(ref_ret, ref_w)

        sim = run_simulation(
            wf_config, sp["test_start"], sp["test_end"], data=data
        )
        sim_m = sim.metrics

        rows.append(
            {
                "fold": i + 1,
                "test_start": sp["test_start"],
                "test_end": sp["test_end"],
                "ref_sharpe": ref_m["sharpe_ratio"],
                "sim_sharpe": sim_m["sharpe_ratio"],
                "ref_max_dd": ref_m["max_drawdown"],
                "sim_max_dd": sim_m["max_drawdown"],
                "ref_trades": ref_m["trade_count"],
                "sim_trades": sim_m["trade_count"],
            }
        )
        print(
            f"  Fold {i+1:2d} [{sp['test_start']}..{sp['test_end']}]: "
            f"ref={ref_m['sharpe_ratio']:.4f} sim={sim_m['sharpe_ratio']:.4f}"
        )

    wf_df = pd.DataFrame(rows)
    ref_mean = float(wf_df["ref_sharpe"].mean())
    sim_mean = float(wf_df["sim_sharpe"].mean())
    diff = abs(sim_mean - ref_mean)
    status = "PASS" if diff <= TOL_SHARPE else "FAIL"
    print(
        f"  Mean OOS Sharpe: backtest={ref_mean:.4f} simulation={sim_mean:.4f} "
        f"diff={diff:.6f} (tol {TOL_SHARPE}) -> {status}"
    )
    return {
        "wf_df": wf_df,
        "ref_mean": ref_mean,
        "sim_mean": sim_mean,
        "diff": diff,
        "status": status,
    }


# ---------------------------------------------------------------------------
# 3. SMA plateau replication vs Cycle 6
# ---------------------------------------------------------------------------
def verify_plateau(config: SimulationConfig, close: pd.DataFrame) -> dict:
    print("\n=== [3] SMA Window Plateau Replication ===")
    rows = []
    for w in SMA_WINDOWS:
        ref_m = _eval_candidate(close, spy_sma_window=w)["test_metrics"]
        sim = run_simulation(replace(config, regime_window=w), OOS_START, END_DATE)
        sim_m = sim.metrics
        rows.append(
            {
                "sma_window": w,
                "ref_sharpe": ref_m["sharpe_ratio"],
                "sim_sharpe": sim_m["sharpe_ratio"],
                "ref_max_dd": ref_m["max_drawdown"],
                "sim_max_dd": sim_m["max_drawdown"],
                "ref_trades": ref_m["trade_count"],
                "sim_trades": sim_m["trade_count"],
            }
        )
        print(
            f"  SMA={w}: ref={ref_m['sharpe_ratio']:.4f} "
            f"sim={sim_m['sharpe_ratio']:.4f} "
            f"trades ref={ref_m['trade_count']} sim={sim_m['trade_count']}"
        )

    plateau_df = pd.DataFrame(rows)
    plateau_df["diff"] = (
        plateau_df["sim_sharpe"] - plateau_df["ref_sharpe"]
    ).abs()
    max_diff = float(plateau_df["diff"].max())
    ref_n_pass = int((plateau_df["ref_sharpe"] >= 0.9).sum())
    sim_n_pass = int((plateau_df["sim_sharpe"] >= 0.9).sum())
    status = (
        "PASS"
        if max_diff <= TOL_SHARPE and ref_n_pass == sim_n_pass
        else "FAIL"
    )
    print(
        f"  Max per-window Sharpe diff={max_diff:.6f}; "
        f"windows >= 0.9: backtest={ref_n_pass}/6 simulation={sim_n_pass}/6 "
        f"-> {status}"
    )
    return {
        "plateau_df": plateau_df,
        "max_diff": max_diff,
        "ref_n_pass": ref_n_pass,
        "sim_n_pass": sim_n_pass,
        "status": status,
    }


# ---------------------------------------------------------------------------
# 4. Determinism check
# ---------------------------------------------------------------------------
def verify_determinism(config: SimulationConfig) -> dict:
    print("\n=== [4] Determinism Check ===")
    sim_a = run_simulation(config, OOS_START, END_DATE)
    sim_b = run_simulation(config, OOS_START, END_DATE)
    daily_equal = sim_a.daily.equals(sim_b.daily)
    trades_equal = sim_a.trade_log.equals(sim_b.trade_log)
    weights_equal = sim_a.weights.equals(sim_b.weights)
    status = "PASS" if (daily_equal and trades_equal and weights_equal) else "FAIL"
    print(
        f"  Daily series identical: {daily_equal}; trade log identical: "
        f"{trades_equal}; weights identical: {weights_equal} -> {status}"
    )
    return {
        "daily_equal": daily_equal,
        "trades_equal": trades_equal,
        "weights_equal": weights_equal,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def write_report(
    config: SimulationConfig,
    test_res: dict,
    wf_res: dict,
    plateau_res: dict,
    determinism_res: dict,
    full_sim: SimulationResult,
) -> Path:
    today = _today()
    git_rev = _git_hash()
    cfg_hash = _config_hash()

    checks = test_res["checks"]
    test_res["ref_metrics"]
    sim_m = test_res["sim_metrics"]
    sim = test_res["sim_result"]
    risk = sim.risk_metrics

    rows = []
    for name, c in checks.items():
        status = "PASS" if c["diff"] <= c["tol"] else "FAIL"
        if name == "Trades":
            rows.append(
                f"| {name} | {int(c['ref']):,} | {int(c['sim']):,} | "
                f"{int(c['diff']):,} | 0 | {status} |"
            )
        elif name == "Max Drawdown" or name == "Ann. Return":
            rows.append(
                f"| {name} | {_fmt_pct(c['ref'])} | {_fmt_pct(c['sim'])} | "
                f"{_fmt_pct(c['diff'])} | 0.5% | {status} |"
            )
        else:
            rows.append(
                f"| {name} | {_fmt_num(c['ref'])} | {_fmt_num(c['sim'])} | "
                f"{_fmt_num(c['diff'], 6)} | {c['tol']} | {status} |"
            )
    verification_table = "\n".join(rows)

    wf_rows = []
    for _, r in wf_res["wf_df"].iterrows():
        wf_rows.append(
            f"| {int(r['fold'])} | {r['test_start']} | {r['test_end']} | "
            f"{_fmt_num(r['ref_sharpe'])} | {_fmt_num(r['sim_sharpe'])} | "
            f"{_fmt_num(abs(r['sim_sharpe'] - r['ref_sharpe']), 6)} |"
        )
    wf_table = "\n".join(wf_rows)

    plateau_rows = []
    for _, r in plateau_res["plateau_df"].iterrows():
        meets = "YES" if r["sim_sharpe"] >= 0.9 else "No"
        plateau_rows.append(
            f"| {int(r['sma_window'])} | {_fmt_num(r['ref_sharpe'])} | "
            f"{_fmt_num(r['sim_sharpe'])} | "
            f"{_fmt_num(abs(r['sim_sharpe'] - r['ref_sharpe']), 6)} | "
            f"{int(r['sim_trades'])} | {meets} |"
        )
    plateau_table = "\n".join(plateau_rows)

    all_pass = (
        test_res["all_pass"]
        and wf_res["status"] == "PASS"
        and plateau_res["status"] == "PASS"
        and determinism_res["status"] == "PASS"
    )
    verdict = "PASS — simulation verified" if all_pass else "FAIL"

    md = f"""# Simulation Verification Report (simulation_verification_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_004.md` and
`research/experiments/tsmomentum_regime_filter_wf_001.md` (Cycle 6
validation of the promoted candidate).

**Candidate**: `tsmomentum_spytrend_001` — 226-day TSMOM (lookback=226,
skip=21, top_fraction=0.5) with combined volatility-targeting (10%,
63-day lookback) + drawdown control (15% threshold, 50% reduction) and
SPY 200-day SMA trend filter (0% exposure below SMA). Cost model:
3 bps round-trip (1 bps commission + 2 bps slippage) applied to
absolute weight changes.

**Objective**: verify that the new simulation engine
(`src/simulation/engine.py`) reproduces the validated backtest within
tolerance, and produce the daily position/return series and trade log
required for Cycle 8 paper-trading (prospective) validation.

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached parquet in `data/raw/`)
- **Date Range**: {START_DATE} to {END_DATE} ({sim.data_info['n_price_rows']} trading days)
- **Universe**: {", ".join(SYMBOLS)}
- **Execution convention**: signal computed on T-1 close (1-day lag),
  executed at T close (EOD) — identical to the backtest convention.
  The engine also supports `"Open"` execution for prospective
  next-open studies.
- **Cost Model**: {config.commission_bps:.1f} bps commission +
  {config.slippage_bps:.1f} bps slippage =
  {config.commission_bps + config.slippage_bps:.1f} bps round-trip
- **Point-in-time**: overlay state conventions replicate the validated
  code paths — `slice` mode (Cycle 5 test-period evaluation) and
  `full` mode (Cycle 6 walk-forward fold evaluation).

---

## Methodology

The simulation engine re-implements the candidate as a deterministic,
point-in-time pipeline:

1. **Signal**: `src.features.momentum.build_weights` (226-day TSMOM,
   21-day skip, top-50% equal weight, 1-day lag).
2. **Regime filter**: SPY 200-day SMA exposure gate (0% below SMA),
   computed point-in-time on the full price history.
3. **Risk overlay**: volatility targeting (63-day realized vol,
   10% annualized target, capped at 1.0) and drawdown control
   (15% threshold, 0.5 exposure multiplier), followed by a gross
   leverage cap of {config.max_leverage:.1f}.
4. **Execution**: weights changes executed daily (backtest-exact);
   an explicit month-end calendar (`rebalance_schedule: "M"`) is
   supported for paper-trading studies.
5. **Costs**: absolute weight change x 3 bps round-trip, identical
   to the backtest cost model.

Verification compares the simulation against the **original
Cycle 5/6 code paths** (`research/run_cycle5.py::_eval_candidate`
and `research/run_cycle6.py::_eval_candidate_period`), imported
directly — i.e. two independent implementations of the same
validated logic.

---

## 1. Backtest Replication (Test Period 2018-2026)

Simulation uses `overlay_warmup="slice"` (overlay state initializes
at the simulation start date), exactly matching the Cycle 5
test-period evaluation.

| Metric | Backtest (Cycle 5/6) | Simulation | Diff | Tolerance | Status |
|--------|---------------------|------------|------|-----------|--------|
{verification_table}

**Documented Cycle 5/6 values for cross-check**: test Sharpe
{DOCUMENTED['test_sharpe']:.4f}, max DD {_fmt_pct(DOCUMENTED['test_max_dd'])},
{DOCUMENTED['test_trades']:,} trades, annualized return
{_fmt_pct(DOCUMENTED['test_ann_return'])}.

---

## 2. Walk-Forward Replication

Simulation uses `overlay_warmup="full"` (overlay state initializes
at `history_start`, then sliced to each fold), exactly matching the
Cycle 6 walk-forward fold evaluation. Walk-forward design: 10-year
train, 12-month test, 6-month step, 21-day purge, 21-day embargo;
parameters fixed across folds.

| Fold | Test Start | Test End | Backtest Sharpe | Simulation Sharpe | Diff |
|------|------------|----------|-----------------|-------------------|------|
{wf_table}

**Mean OOS Sharpe**: backtest {_fmt_num(wf_res['ref_mean'])},
simulation {_fmt_num(wf_res['sim_mean'])},
diff {_fmt_num(wf_res['diff'], 6)} (tolerance {TOL_SHARPE}) —
**{wf_res['status']}**

Documented Cycle 6 walk-forward mean OOS Sharpe for cross-check:
{DOCUMENTED['wf_mean_oos_sharpe']:.4f}.

---

## 3. SMA Window Plateau Replication

| SMA Window | Backtest Sharpe | Simulation Sharpe | Diff | Trades (sim) | Sharpe >= 0.9 |
|------------|-----------------|-------------------|------|--------------|---------------|
{plateau_table}

**Windows with Sharpe >= 0.9**: backtest {plateau_res['ref_n_pass']}/6,
simulation {plateau_res['sim_n_pass']}/6; max per-window diff
{_fmt_num(plateau_res['max_diff'], 6)} (tolerance {TOL_SHARPE}) —
**{plateau_res['status']}**

---

## 4. Determinism Check

The OOS simulation was executed twice from the same configuration:

- Daily series identical: {determinism_res['daily_equal']}
- Trade log identical: {determinism_res['trades_equal']}
- Weights identical: {determinism_res['weights_equal']}

**Result**: **{determinism_res['status']}** (the engine uses no
random number generator; the `seed` field is reserved for API
compatibility).

---

## 5. Paper-Trading Baseline (OOS 2018-2026)

Key metrics from the verified simulation, for prospective tracking:

| Metric | Value |
|--------|-------|
| Sharpe | {sim_m['sharpe_ratio']:.4f} |
| Sortino | {sim_m['sortino_ratio']:.4f} |
| Annualized return | {_fmt_pct(sim_m['annualized_return'])} |
| Annualized volatility | {_fmt_pct(sim_m['annualized_volatility'])} |
| Max drawdown | {_fmt_pct(sim_m['max_drawdown'])} |
| Total return | {_fmt_pct(sim_m['total_return'])} |
| Trades | {sim_m['trade_count']:,} |
| Annualized turnover | {sim_m['annualized_turnover']:.2f} |
| Avg exposure | {sim_m['avg_exposure']:.4f} |
| Profit factor | {sim_m['profit_factor']:.2f} |
| Daily VaR (95%) | {_fmt_pct(risk['var_95_daily'])} |
| Daily CVaR (95%) | {_fmt_pct(risk['cvar_95_daily'])} |
| Max exposure | {_fmt_pct(risk['max_exposure'])} |
| Current exposure | {_fmt_pct(risk['current_exposure'])} |
| Total transaction costs | {risk['total_cost']:.6f} (of unit capital) |
| Avg daily cost | {risk['avg_daily_cost']:.8f} |

---

## Artifacts

| Artifact | Path | Contents |
|----------|------|----------|
| Simulation engine | `src/simulation/engine.py` | `SimulationConfig`, `SimulationResult`, `run_simulation` |
| Frozen config | `config/simulation_candidate_001.yaml` | Candidate parameters (sha256[:12]={cfg_hash}) |
| Daily series | `data/processed/simulation_candidate_001.parquet` | Full-history (1993-2026) daily returns, positions, risk state |
| Trade log | `data/processed/trades_candidate_001.parquet` | Full-history per-trade log (date, symbol, side, weight, price, cost) |

Daily series: {len(full_sim.daily):,} rows,
{full_sim.daily.index.min().date()} to {full_sim.daily.index.max().date()}.
Trade log: {len(full_sim.trade_log):,} trades.
Rebalancing events: {len(full_sim.rebalance_events):,} days with nonzero turnover.

---

## Reproducibility

```bash
python3 research/run_cycle7.py
```

Configuration: `config/simulation_candidate_001.yaml`
(sha256[:12]={cfg_hash}). Code revision: {git_rev}.

---

## Classification

**{verdict}**

The simulation engine reproduces the Cycle 5/6 backtest within
tolerance (test-period Sharpe diff {_fmt_num(checks['Test Sharpe']['diff'], 6)}
< {TOL_SHARPE}; max-DD diff {_fmt_pct(checks['Max Drawdown']['diff'])} < 0.5%;
identical trade count; walk-forward mean OOS Sharpe diff
{_fmt_num(wf_res['diff'], 6)}; plateau {plateau_res['sim_n_pass']}/6 windows
>= 0.9). The candidate is ready for **Cycle 8: paper-trading
(prospective) validation** — daily simulation runs with current
market data, position/return tracking, drift monitoring, and a
go/no-go decision after a 3-6 month paper track record.

---

*Report generated: {today}*
*Code revision: {git_rev}*
*Config hash: {cfg_hash}*
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    print(f"\n  Report written -> {REPORT_PATH}")
    return REPORT_PATH


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("CYCLE 7: Simulation Framework & Paper-Trading Preparation")
    print("=" * 60)

    config = SimulationConfig.from_yaml(CONFIG_PATH)
    print(f"Candidate: {config.candidate_id}")
    print(f"Universe: {', '.join(config.universe)}")
    print(
        f"Signal: {config.signal_type} lookback={config.lookback} "
        f"skip={config.skip} top_fraction={config.top_fraction}"
    )
    print(
        f"Overlay: vol_target={config.vol_target} "
        f"vol_lookback={config.vol_lookback} "
        f"dd_threshold={config.dd_threshold} "
        f"dd_reduction={config.dd_reduction}"
    )
    print(
        f"Regime filter: {config.regime_type} window={config.regime_window} "
        f"execution: {config.price_field} lag={config.signal_lag_days}d"
    )
    print(
        f"Costs: {config.commission_bps}bps + {config.slippage_bps}bps = "
        f"{config.commission_bps + config.slippage_bps}bps round-trip"
    )

    close = _load_close(SYMBOLS)
    data = fetch_universe(SYMBOLS, config.history_start, END_DATE, force=False)

    test_res = verify_test_period(config, close)
    wf_res = verify_walkforward(config, data)
    plateau_res = verify_plateau(config, close)
    determinism_res = verify_determinism(config)

    print("\n=== [5] Full-History Simulation (artifact export) ===")
    full_sim = run_simulation(config, START_DATE, END_DATE, data=data)
    print(f"  {full_sim.summary()}")
    print(
        f"  Daily rows: {len(full_sim.daily):,} "
        f"({full_sim.daily.index.min().date()} to "
        f"{full_sim.daily.index.max().date()})"
    )
    print(f"  Trades: {len(full_sim.trade_log):,}")
    print(f"  Rebalancing events: {len(full_sim.rebalance_events):,}")

    SIM_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    full_sim.daily.to_parquet(SIM_PARQUET)
    full_sim.trade_log.to_parquet(TRADES_PARQUET)
    print(f"  Daily series -> {SIM_PARQUET}")
    print(f"  Trade log -> {TRADES_PARQUET}")

    write_report(config, test_res, wf_res, plateau_res, determinism_res, full_sim)

    all_pass = (
        test_res["all_pass"]
        and wf_res["status"] == "PASS"
        and plateau_res["status"] == "PASS"
        and determinism_res["status"] == "PASS"
    )

    print("\n" + "=" * 60)
    print("CYCLE 7 COMPLETE")
    print("=" * 60)
    print(f"Test-period replication: {'PASS' if test_res['all_pass'] else 'FAIL'}")
    print(f"Walk-forward replication: {wf_res['status']}")
    print(f"Plateau replication: {plateau_res['status']}")
    print(f"Determinism: {determinism_res['status']}")
    print(f"OVERALL: {'PASS — simulation verified' if all_pass else 'FAIL'}")


if __name__ == "__main__":
    main()
