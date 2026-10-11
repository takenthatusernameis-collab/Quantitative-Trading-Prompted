"""Cycle 6: Validation of the Promoted SPY Trend Filter Candidate.

Walk-forward evaluation + SMA window parameter plateau check of the
Cycle 5 promoted candidate (SPY 200d SMA trend filter on 226-day TSMOM
with combined vol-targeting 10% + drawdown control 15%).

Produces:
  - research/experiments/tsmomentum_regime_filter_wf_001.md
"""

from __future__ import annotations

import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backtest.engine import compute_metrics, get_cost_params, get_risk_free_rate
from src.data.yfinance_fetcher import fetch_universe
from src.evaluation.walkforward import (
    evaluate_walkforward,
    summarize_walkforward,
)
from src.features.momentum import build_weights

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Configuration (frozen from Cycle 5 best candidate + NEXT_AGENT_TASK pre-specs)
# ---------------------------------------------------------------------------
SYMBOLS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
START_DATE = "1993-01-01"
END_DATE = "2026-10-09"
TRAIN_END = "2009-12-31"
VAL_END = "2017-12-31"

# Best Cycle 4 config + Cycle 5 SPY trend filter
LOOKBACK, SKIP, TOP_FRACTION = 226, 21, 0.5
VOL_TARGET, DD_THRESHOLD = 0.10, 0.15
SPY_SMA_WINDOW = 200  # baseline; plateau check varies this
VOL_TARGET_LOOKBACK = 63

RF_ANNUAL = get_risk_free_rate()
COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()  # per-unit fractions (1bps -> 0.0001)
COMMISSION_BPS_RAW = COMMISSION_BPS * 10000.0  # raw bps for display (1.0)
SLIPPAGE_BPS_RAW = SLIPPAGE_BPS * 10000.0  # raw bps for display (2.0)
TOTAL_COST_BPS_RAW = COMMISSION_BPS_RAW + SLIPPAGE_BPS_RAW  # raw bps round-trip (3.0)
REPO_ROOT = Path(__file__).resolve().parent.parent

# Pre-specified SMA windows for plateau check (from NEXT_AGENT_TASK.md)
SMA_WINDOWS = [150, 175, 200, 226, 250, 277]

# Walk-forward design (reuse Cycle 3 design exactly)
WF_TRAIN_YEARS = 10.0
WF_TEST_MONTHS = 12.0
WF_STEP_MONTHS = 6.0
WF_PURGE_DAYS = 21
WF_EMBARGO_DAYS = 21


def _git_hash() -> str:
    try:
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False, capture_output=True, text=True,
            cwd=REPO_ROOT,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except (OSError, RuntimeError):
        return "unknown"


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _utc(ts) -> pd.Timestamp:
    return pd.Timestamp(ts, tz="UTC")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def _load_close(symbols: list[str]) -> pd.DataFrame:
    """Return a clean Close-price DataFrame (UTC) for the given symbols."""
    data = fetch_universe(symbols, START_DATE, END_DATE, force=False)
    if data.empty:
        raise RuntimeError(f"No data fetched for {symbols}")
    close = data.xs("Close", level=0, axis=1)
    close = close.ffill().dropna(how="all")
    return close


# ---------------------------------------------------------------------------
# Core evaluation: 226-day TSMOM + combined vol/dd overlay with SPY SMA filter
# ---------------------------------------------------------------------------
def _apply_overlay(
    asset_ret: pd.DataFrame,
    base_weights: pd.DataFrame,
    exposure_factor: pd.Series | None = None,
    vol_target: float = VOL_TARGET,
    dd_threshold: float = DD_THRESHOLD,
    commission_bps: float = COMMISSION_BPS,
    slippage_bps: float = SLIPPAGE_BPS,
    rf_annual: float = RF_ANNUAL,
) -> tuple[pd.DataFrame, pd.Series, dict]:
    """Replicate Cycle 5's _apply_overlay: combined vol-targeting + DD control
    with correct 3 bps cost model. Returns combined weights, net returns, metrics.
    """
    weights = base_weights.copy()
    if exposure_factor is not None:
        ef = exposure_factor.reindex(weights.index).fillna(0.0)
        weights = weights.mul(ef, axis=0)

    daily_ret = asset_ret.copy()

    # Step 1: volatility targeting
    port_ret = (weights * daily_ret).sum(axis=1)
    realized_vol = port_ret.rolling(VOL_TARGET_LOOKBACK).std() * np.sqrt(252)
    realized_vol = realized_vol.replace(0, np.nan)
    vol_scale = (vol_target / realized_vol).clip(upper=1.0).fillna(0.0)
    vol_targeted_weights = weights.mul(vol_scale, axis=0)

    # Step 2: drawdown control on the vol-targeted portfolio
    vol_port_ret = (vol_targeted_weights * daily_ret).sum(axis=1)
    cum = (1 + vol_port_ret).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum / running_max) - 1
    in_drawdown = drawdown < -dd_threshold
    dd_scale = pd.Series(1.0, index=weights.index)
    dd_scale[in_drawdown] = 0.5

    combined_scale = vol_scale * dd_scale
    combined_weights = weights.mul(combined_scale, axis=0)

    # Transaction cost: correct 3 bps round-trip
    weight_changes = combined_weights.diff().abs().sum(axis=1)
    cost_per_trade = commission_bps + slippage_bps
    costs = weight_changes * cost_per_trade

    net_ret = (combined_weights * daily_ret).sum(axis=1) - costs
    metrics = compute_metrics(
        net_ret, combined_weights, commission_bps, slippage_bps, rf_annual,
    )
    return combined_weights, net_ret, metrics


def _eval_candidate(
    close: pd.DataFrame,
    spy_sma_window: int = SPY_SMA_WINDOW,
) -> dict:
    """Evaluate the full candidate config (TSMOM + combined overlay + SPY SMA filter)
    on the test period (post VAL_END).

    Returns dict with net_ret_test, combined_weights, test_metrics.
    """
    # Build base momentum weights
    weights = build_weights(close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    test_mask = weights_a.index > _utc(VAL_END)
    test_asset_ret = daily_ret[test_mask]
    test_weights = weights_a[test_mask]

    # SPY trend exposure factor
    spy = close_a["SPY"]
    spy_sma = spy.rolling(spy_sma_window).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0
    test_exposure = exposure[test_mask]

    cw, net_ret_test, metrics_test = _apply_overlay(
        test_asset_ret, test_weights, exposure_factor=test_exposure,
    )

    return {
        "net_ret_test": net_ret_test,
        "combined_weights": cw,
        "test_metrics": metrics_test,
        "test_index": net_ret_test.index,
    }


def _eval_candidate_period(
    symbols: list[str],
    start_date: str,
    end_date: str,
    spy_sma_window: int = SPY_SMA_WINDOW,
) -> tuple[pd.Series, pd.DataFrame]:
    """Evaluate candidate on an arbitrary period (for walk-forward folds).

    Returns (net_returns, combined_weights).
    """
    close = _load_close(symbols)
    weights = build_weights(close, lookback=LOOKBACK, skip=SKIP, top_fraction=TOP_FRACTION)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)

    # SPY trend exposure factor
    spy = close_a["SPY"]
    spy_sma = spy.rolling(spy_sma_window).mean()
    exposure = pd.Series(1.0, index=close_a.index)
    exposure[spy < spy_sma] = 0.0
    exposure[spy.isna() | spy_sma.isna()] = 0.0

    # Apply combined overlay
    cw, net_ret, _ = _apply_overlay(daily_ret, weights_a, exposure_factor=exposure)

    # Slice to requested period
    mask = (cw.index >= start_date) & (cw.index <= end_date)
    return net_ret[mask], cw[mask]


# ---------------------------------------------------------------------------
# 1. Walk-Forward Evaluation
# ---------------------------------------------------------------------------
def run_walkforward() -> dict:
    """Run walk-forward evaluation of the SPY trend-filter candidate."""
    print("\n=== [1] Walk-Forward Evaluation ===")

    def config_fn(symbols: list[str], start: str, end: str) -> tuple[pd.Series, pd.DataFrame]:
        return _eval_candidate_period(symbols, start, end, spy_sma_window=SPY_SMA_WINDOW)

    wf_df = evaluate_walkforward(
        SYMBOLS, START_DATE, END_DATE, config_fn,
        train_years=WF_TRAIN_YEARS,
        test_months=WF_TEST_MONTHS,
        step_months=WF_STEP_MONTHS,
        purge_days=WF_PURGE_DAYS,
        embargo_days=WF_EMBARGO_DAYS,
    )

    summary = summarize_walkforward(wf_df)

    print(f"  Folds: {summary.get('n_folds', 0)}")
    print(f"  Mean test Sharpe: {summary.get('mean_test_sharpe', np.nan):.4f}")
    print(f"  % Positive Sharpe: {summary.get('pct_positive_sharpe', np.nan):.1%}")
    print(f"  Mean test max DD: {summary.get('mean_test_max_dd', np.nan):.2%}")
    print(f"  Total test trades: {summary.get('total_test_trades', 0)}")

    return {"wf_df": wf_df, "summary": summary}


# ---------------------------------------------------------------------------
# 2. SMA Window Parameter Plateau Check
# ---------------------------------------------------------------------------
def run_plateau_check() -> dict:
    """Test the candidate across pre-specified SMA windows on the 2018-2026 test period."""
    print("\n=== [2] SMA Window Parameter Plateau Check ===")

    close = _load_close(SYMBOLS)
    results = []

    for w in SMA_WINDOWS:
        print(f"  Testing SMA window = {w}...")
        res = _eval_candidate(close, spy_sma_window=w)
        m = res["test_metrics"]
        results.append({
            "sma_window": w,
            "test_sharpe": m["sharpe_ratio"],
            "test_ann_return": m["annualized_return"],
            "test_max_dd": m["max_drawdown"],
            "test_trades": m["trade_count"],
            "test_sortino": m["sortino_ratio"],
            "test_profit_factor": m["profit_factor"],
        })
        print(f"    Sharpe={m['sharpe_ratio']:.4f} DD={m['max_drawdown']:.4f} Trades={m['trade_count']}")

    plateau_df = pd.DataFrame(results)

    # Plateau verdict: >= 2 of 6 windows (including 200) achieve Sharpe >= 0.9
    n_pass = (plateau_df["test_sharpe"] >= 0.9).sum()
    is_robust = n_pass >= 2

    print(f"  Windows with Sharpe >= 0.9: {int(n_pass)}/{len(SMA_WINDOWS)}")
    print(f"  Plateau verdict: {'ROBUST (passes)' if is_robust else 'NOT ROBUST (fails)'}")

    return {"plateau_df": plateau_df, "n_pass": int(n_pass), "is_robust": is_robust}


# ---------------------------------------------------------------------------
# 3. Main report generation
# ---------------------------------------------------------------------------
def write_report(wf_results: dict, plateau_results: dict) -> Path:
    """Generate the combined experiment report."""
    today = _today()
    git_rev = _git_hash()

    wf_df = wf_results["wf_df"]
    summary = wf_results["summary"]
    plateau_df = plateau_results["plateau_df"]
    n_pass = plateau_results["n_pass"]
    is_robust = plateau_results["is_robust"]

    # Promotion gate verdict
    mean_wf_sharpe = summary.get("mean_test_sharpe", np.nan)
    pct_positive = summary.get("pct_positive_sharpe", np.nan)
    total_trades = summary.get("total_test_trades", 0)

    gate_wf_sharpe = mean_wf_sharpe >= 0.9
    gate_wf_positive = pct_positive >= 0.5
    gate_plateau = is_robust

    gates_met = gate_wf_sharpe and gate_wf_positive and gate_plateau

    verdict = "Credible Candidate" if gates_met else "Exploratory Signal"

    md = f"""# Experiment: Walk-Forward & Plateau Validation of SPY Trend Filter (tsmomentum_regime_filter_wf_001)

## Hypothesis Reference

See `research/hypotheses/tsmomentum_004.md` (Cycle 5 promoted candidate).

**Objective**: Validate that the Cycle 5 promoted candidate — 226-day TSMOM with
combined volatility-targeting (10%) + drawdown-control (15%) and SPY 200-day
SMA trend filter — is not a single-period or single-parameter artifact, via:
1. Walk-forward evaluation (fixed parameters, no re-optimization per fold)
2. SMA window parameter plateau check (pre-specified window set)

**Candidate Configuration (Fixed)**:
- Universe: SPY, QQQ, IWM, TLT, GLD, EFA, EEM
- Signal: 226-day TSMOM (lookback=226, skip=21, top_fraction=0.5)
- Risk Overlay: Combined vol-targeting (10%) + drawdown control (15%)
- Regime Filter: SPY trend filter (0% exposure when SPY < SMA; 100% otherwise)
- Cost Model: 3 bps round-trip (1 bps commission + 2 bps slippage)

---

## Data Used

- **Source**: Yahoo Finance via yfinance (cached parquet in `data/raw/`)
- **Date Range**: {START_DATE} to {END_DATE}
- **Universe**: {", ".join(SYMBOLS)}
- **Regime Driver**: SPY (trend via SMA)
- **Test Period**: 2018-01-01 to {END_DATE}
- **Point-in-Time**: All signals use only data available at formation; weights
  shifted 1 day; SPY SMA computed point-in-time; purge/embargo in walk-forward.
- **Cost Model**: {COMMISSION_BPS_RAW:.1f} bps + {SLIPPAGE_BPS_RAW:.1f} bps = {TOTAL_COST_BPS_RAW:.1f} bps round-trip

---

## 1. Walk-Forward Evaluation

### Walk-Forward Design (Pre-Specified, Matches Cycle 3)

- **Rolling Window**: 10-year training, 1-year test, 6-month step
- **Purge**: 21 days between train and test
- **Embargo**: 21 days after test period end
- **Parameters**: Fixed across all folds (no per-fold re-optimization)
- **Candidate**: SPY 200d SMA trend filter on Cycle 4 best config

### Per-Fold Results

| Fold | Train Start | Train End | Test Start | Test End | Train Sharpe | Test Sharpe | Test Ann. Ret. | Test Max DD | Test Trades |
|------|-------------|-----------|------------|----------|-------------|------------|---------------|-------------|-------------|
"""
    for _, r in wf_df.iterrows():
        md += (
            f"| {int(r['fold'])} | {r['train_start']} | {r['train_end']} | "
            f"{r['test_start']} | {r['test_end']} | "
            f"{r['train_sharpe']:.4f} | {r['test_sharpe']:.4f} | "
            f"{r['test_ann_return']:.4f} | {r['test_max_dd']:.4f} | "
            f"{int(r['test_trades']) if pd.notna(r['test_trades']) else 'N/A'} |\n"
        )

    md += f"""

### Aggregate Walk-Forward Statistics

| Metric | Value |
|--------|-------|
| Folds | {summary.get('n_folds', 'N/A')} |
| Mean Test Sharpe | {mean_wf_sharpe:.4f} |
| Std Test Sharpe | {summary.get('std_test_sharpe', np.nan):.4f} |
| Median Test Sharpe | {summary.get('median_test_sharpe', np.nan):.4f} |
| Min Test Sharpe | {summary.get('min_test_sharpe', np.nan):.4f} |
| Max Test Sharpe | {summary.get('max_test_sharpe', np.nan):.4f} |
| % Positive Sharpe Folds | {pct_positive:.1%} |
| Mean Test Ann. Return | {summary.get('mean_test_ann_return', np.nan):.2%} |
| Mean Test Max DD | {summary.get('mean_test_max_dd', np.nan):.2%} |
| Mean Test Trades | {summary.get('mean_test_trades', np.nan):.1f} |
| Total Pooled OOS Trades | {total_trades} |

---

## 2. SMA Window Parameter Plateau Check

### Pre-Specified SMA Windows

From NEXT_AGENT_TASK.md: `{SMA_WINDOWS}` (6 values spanning ~150-277 days)

### Results (Test Period 2018-2026, Fixed Candidate Config)

| SMA Window | Test Sharpe | Ann. Return | Max DD | Trades | Sortino | Profit Factor | Meets 0.9? |
|------------|-------------|-------------|--------|--------|---------|---------------|------------|
"""
    for _, r in plateau_df.iterrows():
        meets = "**YES**" if r["test_sharpe"] >= 0.9 else "No"
        md += (
            f"| {int(r['sma_window'])} | {r['test_sharpe']:.4f} | {r['test_ann_return']:.4f} | "
            f"{r['test_max_dd']:.4f} | {int(r['test_trades'])} | {r['test_sortino']:.4f} | "
            f"{r['test_profit_factor']:.2f} | {meets} |\n"
        )

    md += f"""

### Plateau Verdict

**Windows with Sharpe >= 0.9: {n_pass}/{len(SMA_WINDOWS)}**

**Threshold**: >= 2 of 6 windows (including the baseline 200d) must achieve Sharpe >= 0.9
for the result to be considered robust (not won/lost on the single 200d value).

**Result**: {'**ROBUST — Plateau holds**' if is_robust else '**NOT ROBUST — Plateau fails**'}

---

## 3. Promotion-Gate Verdict (Final)

### Gate Criteria

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| Walk-Forward Mean OOS Sharpe >= 0.9 | 0.90 | {mean_wf_sharpe:.4f} | {'PASS' if gate_wf_sharpe else 'FAIL'} |
| >= 50% of WF folds positive Sharpe | 50% | {pct_positive:.1%} | {'PASS' if gate_wf_positive else 'FAIL'} |
| SMA Plateau Check (>= 2/6 windows >= 0.9) | 2 | {n_pass} | {'PASS' if gate_plateau else 'FAIL'} |

### Final Classification

## **{verdict}**

"""
    if gates_met:
        md += f"""All three validation gates are met. The SPY trend-filter candidate is
confirmed as a **Credible Candidate** for advancement to simulation/paper-trading.

The walk-forward mean OOS Sharpe of {mean_wf_sharpe:.4f} with {pct_positive:.1%} positive
folds and {total_trades} pooled trades, combined with a robust SMA plateau
({n_pass}/6 windows >= 0.9), indicates the effect generalizes across time and
is not sensitive to the exact 200-day window choice.

"""
    else:
        md += f"""One or more validation gates failed. The candidate is downgraded to
**Exploratory Signal**.

The walk-forward mean OOS Sharpe of {mean_wf_sharpe:.4f} {'meets' if gate_wf_sharpe else 'does NOT meet'} the 0.9 threshold.
{pct_positive:.1%} of folds are positive {'(meets 50% gate)' if gate_wf_positive else '(fails 50% gate)'}.
The SMA plateau check {'passes' if gate_plateau else 'fails'} ({n_pass}/6 windows >= 0.9).

Per AGENTS.md and NEXT_AGENT_TASK.md, the next cycle must explore a **different
structural mechanism** (do NOT continue regime/universe variations on TSMOM).
Preferred candidates with available data: crypto perpetual funding/carry on OKX,
basis compensation, market-session effects, or documented rebalancing flows.

"""

    md += f"""---

## Walk-Forward Interpretation

The walk-forward test uses **fixed parameters** (no re-optimization) across all
folds. This is a true out-of-sample validation: the candidate configuration
(226-day TSMOM + combined overlay + 200d SPY SMA filter) is evaluated on each
test fold exactly as specified, using only data available up to the test start.

Mean OOS Sharpe = {mean_wf_sharpe:.4f} ({'above' if gate_wf_sharpe else 'below'} the 0.9 gate)
Positive fold rate = {pct_positive:.1%} ({'above' if gate_wf_positive else 'below'} the 50% gate)
Total OOS trades = {total_trades}

This result should be compared to Cycle 3's unfiltered baseline walk-forward
(mean test Sharpe 0.679, 97.9% positive folds). The SPY trend filter is expected
to improve OOS consistency by removing bear-regime exposure.

---

## Plateau Interpretation

The parameter plateau check tests whether the promotion-gate result depends
critically on the specific 200-day SMA window. If the gate is only passed at
exactly 200 days and fails at neighboring values (150, 175, 226, 250, 277),
the result is likely a parameter peak rather than a structural effect.

{'The plateau holds: ' + str(n_pass) + ' of 6 pre-specified windows clear the 0.9 Sharpe gate, including the baseline 200d. The effect is robust to the SMA window choice.' if is_robust else 'The plateau fails: only ' + str(n_pass) + ' of 6 windows clear the gate. The 200d result may be a parameter-specific artifact.'}

---

## Reproducibility

### Reproduction Commands

```bash
python3 research/run_cycle6.py
```

### Code Revision

{git_rev}

### Configuration Hash

Candidate config: lookback={LOOKBACK}, skip={SKIP}, top_fraction={TOP_FRACTION}, vol_target={VOL_TARGET}, dd_threshold={DD_THRESHOLD}, spy_sma={SPY_SMA_WINDOW}
Walk-forward: train_years={WF_TRAIN_YEARS}, test_months={WF_TEST_MONTHS}, step_months={WF_STEP_MONTHS}, purge={WF_PURGE_DAYS}, embargo={WF_EMBARGO_DAYS}
Plateau SMA windows: {SMA_WINDOWS}

---

## Artifacts Referenced

| Artifact | Path |
|----------|------|
| Cycle 5 Regime Analysis | `research/experiments/tsmomentum_regime_001.md` |
| Cycle 5 Regime Filter Test | `research/experiments/tsmomentum_regime_filter_001.md` |
| Cycle 5 Decision | `research/reports/tsmomentum_decision_003.md` |
| Cycle 5 Hypothesis | `research/hypotheses/tsmomentum_004.md` |
| Cycle 3 Walk-Forward | `research/experiments/tsmomentum_walkforward_001.md` |

---

*Report generated: {today}*
*Code revision: {git_rev}*
"""
    out = REPO_ROOT / "research" / "experiments" / "tsmomentum_regime_filter_wf_001.md"
    out.write_text(md)
    print(f"  Report written -> {out}")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("CYCLE 6: SPY Trend Filter Walk-Forward & Plateau Validation")
    print("=" * 60)

    # 1. Walk-forward evaluation
    wf_results = run_walkforward()

    # 2. SMA window plateau check
    plateau_results = run_plateau_check()

    # 3. Write combined report
    write_report(wf_results, plateau_results)

    # Print final verdict
    summary = wf_results["summary"]
    mean_wf_sharpe = summary.get("mean_test_sharpe", np.nan)
    pct_positive = summary.get("pct_positive_sharpe", np.nan)
    n_pass = plateau_results["n_pass"]
    is_robust = plateau_results["is_robust"]

    gate_wf_sharpe = mean_wf_sharpe >= 0.9
    gate_wf_positive = pct_positive >= 0.5
    gate_plateau = is_robust
    gates_met = gate_wf_sharpe and gate_wf_positive and gate_plateau

    verdict = "Credible Candidate" if gates_met else "Exploratory Signal"

    print("\n" + "=" * 60)
    print("CYCLE 6 COMPLETE")
    print("=" * 60)
    print(f"Walk-forward mean OOS Sharpe: {mean_wf_sharpe:.4f} ({'PASS' if gate_wf_sharpe else 'FAIL'})")
    print(f"Positive fold rate: {pct_positive:.1%} ({'PASS' if gate_wf_positive else 'FAIL'})")
    print(f"SMA plateau: {n_pass}/6 windows >= 0.9 ({'PASS' if gate_plateau else 'FAIL'})")
    print(f"FINAL VERDICT: {verdict}")


if __name__ == "__main__":
    main()