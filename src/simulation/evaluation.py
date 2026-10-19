"""Go/No-Go evaluation for paper-trading prospective validation.

Evaluates the paper-trading track record against backtest baseline
using statistical tests and drift monitoring.

The Probabilistic Sharpe Ratio is computed from a *seeded* block bootstrap
(``GoNoGoConfig.psr_seed``) so that repeated evaluations of the same record
reproduce the same PSR, Sharpe standard error and confidence interval.

Promotion gates
---------------
Every promotion gate required by the repository's validation artifacts is
defined in exactly one place: ``config/promotion_gates.yaml``. ``evaluate_go_no_go``
loads that definition and evaluates *every* gate. A record may only be labelled
"GO" when every gate passes; a failing gate can never yield "GO".

The decision mapping is conservative by default: when the PSR sits in the grey
zone (0.5-0.95) and at least one gate fails, the decision is "NO-GO" rather than
"Inconclusive", so a degraded record cannot hide behind statistical uncertainty.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.evaluation.statistics import compute_psr
from src.evaluation.utils import annualize_return, max_drawdown, sharpe_ratio
from src.simulation.paper_trading import (
    PaperTradingConfig,
    PaperTradingState,
    _ensure_path,
)


DEFAULT_PSR_SEED = 20240101

# Path to the single source of truth for the promotion gates. Loaded lazily
# inside ``_load_promotion_gates`` so the module imports cleanly even when the
# file is absent (the loader then raises a clear error at evaluation time).
_PROMOTION_GATES_PATH = (
    Path(__file__).resolve().parent.parent.parent / "config" / "promotion_gates.yaml"
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _load_promotion_gates(path: Path | str | None = None) -> dict[str, Any]:
    """Load the machine-readable promotion-gate definition from YAML.

    Returns the parsed document as a dict. Raises ``FileNotFoundError`` if the
    gate definition file is missing, so a missing gate table cannot silently
    fall back to the old, incomplete behaviour.
    """
    p = Path(path) if path is not None else _PROMOTION_GATES_PATH
    if not p.is_absolute():
        p = _project_root() / p
    if not p.exists():
        raise FileNotFoundError(
            f"promotion gates definition not found at {p}; this file is the "
            "single source of truth for the go/no-go gates"
        )
    with open(p, "r") as fh:
        data = yaml.safe_load(fh) or {}
    if "gates" not in data:
        raise ValueError(
            f"promotion gates definition at {p} is malformed: missing 'gates' key"
        )
    return data


@dataclass
class GoNoGoConfig:
    """Configuration for go/no-go evaluation."""

    min_days: int = 63
    target_sharpe: float = 0.9
    max_dd_threshold: float = 0.15
    psr_go_threshold: float = 0.95
    psr_no_go_threshold: float = 0.5
    bootstrap_samples: int = 1000
    block_size: int = 22
    psr_seed: int = DEFAULT_PSR_SEED
    backtest_sharpe: float = 1.4178
    backtest_max_dd: float = -0.0779
    backtest_trades: int = 1196
    backtest_annualized_turnover: float = 13.32
    backtest_annualized_return: float = 0.1446
    backtest_volatility: float = 0.0879
    backtest_sortino: float = 1.7477
    backtest_profit_factor: float = 1.35


@dataclass
class GateEvaluation:
    """Per-gate evaluation result exposed by ``evaluate_go_no_go``."""

    name: str
    metric: str
    value: float
    threshold: float
    comparison: str
    passed: bool
    source: str = ""

    def __getitem__(self, key):
        mapping = {
            "name": self.name,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "comparison": self.comparison,
            "passed": self.passed,
            "pass": self.passed,
            "pass_fail": "PASS" if self.passed else "FAIL",
            "source": self.source,
        }
        if key in mapping:
            return mapping[key]
        raise KeyError(key)

    @property
    def pass_fail(self) -> str:
        return "PASS" if self.passed else "FAIL"


@dataclass
class GoNoGoResult:
    """Result of go/no-go evaluation."""

    decision: str  # "GO", "NO-GO", "INCONCLUSIVE"
    candidate_id: str
    evaluation_date: str
    paper_days: int
    paper_sharpe: float
    paper_max_dd: float
    paper_total_return: float
    paper_ann_return: float
    paper_volatility: float
    paper_trade_count: int
    paper_annualized_turnover: float
    paper_sortino: float
    paper_profit_factor: float
    psr_normal: float
    psr_empirical: float
    sharpe_se: float
    sharpe_ci_lower: float
    sharpe_ci_upper: float
    regime_stable: bool
    regime_persistence_days: int
    vol_scale_min: float
    vol_scale_max: float
    dd_scale_min: float
    dd_scale_max: float
    turnover_median: float
    turnover_p95: float
    drift_flags_count: int
    rationale: str
    conditions_for_reevaluation: str
    gates: list = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def gate_results(self) -> list:
        return self.gates

    @property
    def gate_table(self) -> list:
        return self.gates


def _compute_rolling_metrics(
    returns: list[float], dates: list[str], window: int = 63
) -> dict[str, float]:
    """Compute rolling Sharpe and max DD over the last window days."""
    if len(returns) < 2:
        return {"rolling_sharpe": 0.0, "rolling_max_dd": 0.0}

    arr = np.array(returns)
    n = len(arr)

    # Rolling Sharpe
    if n >= window:
        recent = arr[-window:]
    else:
        recent = arr

    rolling_sharpe = sharpe_ratio(pd.Series(recent))

    # Rolling max DD over the trailing window
    if n >= window:
        recent_dd = arr[-window:]
    else:
        recent_dd = arr
    cum = np.cumprod(1.0 + recent_dd)
    peak = np.maximum.accumulate(cum)
    dd = (cum / peak - 1.0).min()
    rolling_max_dd = float(dd)

    return {"rolling_sharpe": rolling_sharpe, "rolling_max_dd": rolling_max_dd}


def _compute_turnover_stats(state: PaperTradingState) -> dict[str, float]:
    """Compute turnover statistics from run history."""
    if not state.run_history:
        return {"turnover_median": 0.0, "turnover_p95": 0.0}

    turnovers = [r["turnover"] for r in state.run_history if "turnover" in r]
    if not turnovers:
        return {"turnover_median": 0.0, "turnover_p95": 0.0}

    return {
        "turnover_median": float(np.median(turnovers)),
        "turnover_p95": float(np.percentile(turnovers, 95)),
    }


def _compute_risk_param_bounds(state: PaperTradingState) -> dict[str, float]:
    """Compute historical bounds of risk parameters."""
    if not state.run_history:
        return {"vol_scale_min": 1.0, "vol_scale_max": 1.0, "dd_scale_min": 1.0, "dd_scale_max": 1.0}

    vol_scales = [r["vol_scale"] for r in state.run_history if "vol_scale" in r and r["vol_scale"] > 0]
    dd_scales = [r["dd_scale"] for r in state.run_history if "dd_scale" in r and r["dd_scale"] > 0]

    return {
        "vol_scale_min": float(np.min(vol_scales)) if vol_scales else 1.0,
        "vol_scale_max": float(np.max(vol_scales)) if vol_scales else 1.0,
        "dd_scale_min": float(np.min(dd_scales)) if dd_scales else 1.0,
        "dd_scale_max": float(np.max(dd_scales)) if dd_scales else 1.0,
    }


def _compute_regime_persistence(state: PaperTradingState) -> dict[str, Any]:
    """Compute regime persistence (days since last flip)."""
    if not state.run_history:
        return {"regime_stable": True, "regime_persistence_days": 0, "current_regime": 1.0}

    current_regime = state.previous_regime_exposure
    if current_regime is None:
        current_regime = state.run_history[-1].get("regime_exposure", 1.0)

    # Count days since last regime change
    persistence = 0
    for run in reversed(state.run_history):
        if run.get("regime_exposure", 1.0) == current_regime:
            persistence += 1
        else:
            break

    regime_stable = persistence >= 5  # At least 5 days in current regime

    return {
        "regime_stable": regime_stable,
        "regime_persistence_days": persistence,
        "current_regime": current_regime,
    }


def _load_backtest_baseline() -> dict[str, Any]:
    """Load backtest baseline metrics from Cycle 7 verification."""
    # Hardcoded from simulation_verification_001.md
    return {
        "sharpe": 1.4178,
        "sortino": 1.7477,
        "annualized_return": 0.1446,
        "annualized_volatility": 0.0879,
        "max_drawdown": -0.0779,
        "total_return": 2.2612,
        "trades": 1196,
        "annualized_turnover": 13.32,
        "profit_factor": 1.35,
        "avg_exposure": 0.6506,
        "daily_var_95": 0.0090,
        "daily_cvar_95": 0.0002,
    }


def evaluate_go_no_go(
    state: PaperTradingState,
    config: PaperTradingConfig,
    backtest_baseline: dict[str, Any] | None = None,
    go_no_go_config: GoNoGoConfig | None = None,
) -> GoNoGoResult:
    """Evaluate paper-trading track record against go/no-go criteria."""

    if backtest_baseline is None:
        backtest_baseline = _load_backtest_baseline()

    if go_no_go_config is None:
        go_no_go_config = GoNoGoConfig(
            min_days=config.go_no_go_min_days,
            target_sharpe=config.go_no_go_target_sharpe,
            max_dd_threshold=config.go_no_go_max_dd_threshold,
            backtest_sharpe=backtest_baseline["sharpe"],
            backtest_max_dd=backtest_baseline["max_drawdown"],
            backtest_trades=backtest_baseline["trades"],
            backtest_annualized_turnover=backtest_baseline["annualized_turnover"],
            backtest_annualized_return=backtest_baseline["annualized_return"],
            backtest_volatility=backtest_baseline["annualized_volatility"],
            backtest_sortino=backtest_baseline["sortino"],
            backtest_profit_factor=backtest_baseline["profit_factor"],
        )

    paper_days = len(state.cumulative_returns)
    returns_series = pd.Series(state.cumulative_returns, index=pd.to_datetime(state.cumulative_dates))

    # Basic paper metrics
    paper_sharpe = sharpe_ratio(returns_series)
    paper_max_dd = max_drawdown(returns_series)
    paper_total_return = state.current_nav / 100000.0 - 1.0
    paper_ann_return = annualize_return(returns_series)
    paper_volatility = float(np.std(returns_series) * np.sqrt(252)) if len(returns_series) > 1 else 0.0

    # Sortino
    if len(returns_series) > 1:
        downside = returns_series[returns_series < 0]
        downside_std = float(downside.std(ddof=1) * np.sqrt(252)) if len(downside) > 1 else 0.0
        paper_sortino = paper_ann_return / downside_std if downside_std > 0 else 0.0
    else:
        paper_sortino = 0.0

    # Profit factor
    gains = returns_series[returns_series > 0].sum()
    losses = abs(returns_series[returns_series < 0].sum())
    paper_profit_factor = float(gains / losses) if losses > 0 else float("inf")

    # Trade count (approximate from turnover)
    # Each rebalance with turnover > threshold counts as trades
    turnover_threshold = 0.01
    paper_trade_count = sum(1 for r in state.run_history if r.get("turnover", 0) > turnover_threshold)

    # Annualized turnover
    if paper_days > 0:
        total_turnover = sum(r.get("turnover", 0) for r in state.run_history)
        paper_annualized_turnover = total_turnover * 252.0 / paper_days
    else:
        paper_annualized_turnover = 0.0

    # PSR against backtest Sharpe
    if paper_days >= 20 and np.std(returns_series) > 1e-10:
        psr_result = compute_psr(
            returns_series,
            sr_target=backtest_baseline["sharpe"],
            n_bootstrap=go_no_go_config.bootstrap_samples,
            block_size=go_no_go_config.block_size,
            seed=go_no_go_config.psr_seed,
        )
        psr_normal = psr_result["psr_normal"]
        psr_empirical = psr_result["psr_empirical"]
        sharpe_se = psr_result["sharpe_se"]
        sharpe_ci_lower = psr_result["ci_lower"]
        sharpe_ci_upper = psr_result["ci_upper"]
    else:
        psr_normal = 0.0
        psr_empirical = 0.0
        sharpe_se = 0.0
        sharpe_ci_lower = 0.0
        sharpe_ci_upper = 0.0

    # Drift monitoring
    regime_info = _compute_regime_persistence(state)
    risk_bounds = _compute_risk_param_bounds(state)
    turnover_stats = _compute_turnover_stats(state)

    drift_flags_count = len(state.drift_flags)

    # Regime flips count
    regime_flips = 0
    prev = None
    for r in state.run_history:
        cur = r.get("regime_exposure", None)
        if cur is None:
            continue
        if prev is not None and cur != prev:
            regime_flips += 1
        prev = cur

    rolling = _compute_rolling_metrics(state.cumulative_returns, state.cumulative_dates, window=63)
    rolling_sharpe_63d = float(rolling["rolling_sharpe"])
    rolling_max_dd_63d = float(rolling["rolling_max_dd"])

    # Load promotion gates (single source of truth)
    gates_doc = _load_promotion_gates()
    gate_defs = gates_doc.get("gates", [])

    metric_values = {
        "paper_days": paper_days,
        "paper_sharpe": paper_sharpe,
        "rolling_sharpe_63d": rolling_sharpe_63d,
        "paper_max_dd": paper_max_dd,
        "rolling_max_dd_63d": rolling_max_dd_63d,
        "regime_flips": regime_flips,
        "psr_normal": psr_normal,
    }

    def _compare(value, threshold, comparison):
        if comparison == "gte":
            return value >= threshold
        if comparison == "gt":
            return value > threshold
        if comparison == "lte":
            return value <= threshold
        if comparison == "lt":
            return value < threshold
        raise ValueError(comparison)

    gate_evals = []
    for g in gate_defs:
        metric = g["metric"]
        value = metric_values.get(metric, 0.0)
        passed = _compare(value, g["threshold"], g["comparison"])
        gate_evals.append(GateEvaluation(
            name=g["name"],
            metric=metric,
            value=float(value),
            threshold=float(g["threshold"]),
            comparison=g["comparison"],
            passed=bool(passed),
            source=g.get("source", ""),
        ))

    all_gates_pass = all(g.passed for g in gate_evals) if gate_evals else False

    # Decision logic
    if paper_days < 126:
        decision = "INCONCLUSIVE"
        rationale = f"Insufficient track record: {paper_days} days < 126 minimum required."
        conditions = f"Re-evaluate after {126 - paper_days} more trading days of paper track record."
    elif all_gates_pass:
        decision = "GO"
        rationale = "All promotion gates pass."
        conditions = "Monitor for regime flips, risk parameter drift, or sustained underperformance."
    elif not all_gates_pass:
        decision = "NO-GO"
        rationale = "One or more promotion gates failed."
        conditions = "Strategy fails go/no-go criteria. Do not promote to live trading without major revision."
    else:
        decision = "INCONCLUSIVE"
        rationale = "Inconclusive."
        conditions = "Continue paper trading."
    pass

    return GoNoGoResult(
        decision=decision,
        candidate_id=config.candidate_id,
        evaluation_date=datetime.now().strftime("%Y-%m-%d"),
        paper_days=paper_days,
        paper_sharpe=paper_sharpe,
        paper_max_dd=paper_max_dd,
        paper_total_return=paper_total_return,
        paper_ann_return=paper_ann_return,
        paper_volatility=paper_volatility,
        paper_trade_count=paper_trade_count,
        paper_annualized_turnover=paper_annualized_turnover,
        paper_sortino=paper_sortino,
        paper_profit_factor=paper_profit_factor,
        psr_normal=psr_normal,
        psr_empirical=psr_empirical,
        sharpe_se=sharpe_se,
        sharpe_ci_lower=sharpe_ci_lower,
        sharpe_ci_upper=sharpe_ci_upper,
        regime_stable=regime_info["regime_stable"],
        regime_persistence_days=regime_info["regime_persistence_days"],
        vol_scale_min=risk_bounds["vol_scale_min"],
        vol_scale_max=risk_bounds["vol_scale_max"],
        dd_scale_min=risk_bounds["dd_scale_min"],
        dd_scale_max=risk_bounds["dd_scale_max"],
        turnover_median=turnover_stats["turnover_median"],
        turnover_p95=turnover_stats["turnover_p95"],
        drift_flags_count=drift_flags_count,
        rationale=rationale,
        conditions_for_reevaluation=conditions,
        gates=gate_evals,
    )


def generate_evaluation_report(result: GoNoGoResult, config: GoNoGoConfig) -> str:
    """Generate markdown evaluation report."""

    decision_emoji = {"GO": "✅", "NO-GO": "❌", "INCONCLUSIVE": "⏳"}.get(result.decision, "❓")

    report = f"""# Go/No-Go Evaluation Report

**Candidate:** {result.candidate_id}
**Evaluation Date:** {result.evaluation_date}
**Paper Track Record Length:** {result.paper_days} days
**Config Hash:** {config.__dict__ if hasattr(config, '__dict__') else 'N/A'}

---

## Decision: {decision_emoji} {result.decision}

**Rationale:**
{result.rationale}

**Conditions for Re-evaluation:**
{result.conditions_for_reevaluation}

---

## Backtest Baseline (Cycle 5/6 Verified)

| Metric | Value |
|--------|-------|
| Test Sharpe | {config.backtest_sharpe:.4f} |
| Sortino | {config.backtest_sortino:.4f} |
| Annualized Return | {config.backtest_annualized_return:.2%} |
| Annualized Volatility | {config.backtest_volatility:.2%} |
| Max Drawdown | {config.backtest_max_dd:.2%} |
| Total Return | {config.backtest_max_dd:.2%} |
| Trades | {config.backtest_trades} |
| Annualized Turnover | {config.backtest_annualized_turnover:.2f} |
| Profit Factor | {config.backtest_profit_factor:.2f} |

*Source: simulation_verification_001.md (Cycle 7 verification)*

---

## Paper Performance ({result.paper_days} days)

| Metric | Paper | Backtest | Difference |
|--------|-------|----------|------------|
| Sharpe Ratio | {result.paper_sharpe:.4f} | {config.backtest_sharpe:.4f} | {result.paper_sharpe - config.backtest_sharpe:+.4f} |
| Sortino | {result.paper_sortino:.4f} | {config.backtest_sortino:.4f} | {result.paper_sortino - config.backtest_sortino:+.4f} |
| Annualized Return | {result.paper_ann_return:.2%} | {config.backtest_annualized_return:.2%} | {result.paper_ann_return - config.backtest_annualized_return:+.2%} |
| Annualized Volatility | {result.paper_volatility:.2%} | {config.backtest_volatility:.2%} | {result.paper_volatility - config.backtest_volatility:+.2%} |
| Max Drawdown | {result.paper_max_dd:.2%} | {config.backtest_max_dd:.2%} | {result.paper_max_dd - config.backtest_max_dd:+.2%} |
| Total Return | {result.paper_total_return:.2%} | {config.backtest_max_dd:.2%} | N/A |
| Trade Count (approx) | {result.paper_trade_count} | {config.backtest_trades} | N/A |
| Annualized Turnover | {result.paper_annualized_turnover:.2f} | {config.backtest_annualized_turnover:.2f} | {result.paper_annualized_turnover - config.backtest_annualized_turnover:+.2f} |
| Profit Factor | {result.paper_profit_factor:.2f} | {config.backtest_profit_factor:.2f} | {result.paper_profit_factor - config.backtest_profit_factor:+.2f} |

---

## Statistical Comparison

| Metric | Value |
|--------|-------|
| Probabilistic Sharpe Ratio (normal) | {result.psr_normal:.4f} |
| Probabilistic Sharpe Ratio (empirical) | {result.psr_empirical:.4f} |
| Sharpe Standard Error | {result.sharpe_se:.4f} |
| 95% CI Lower | {result.sharpe_ci_lower:.4f} |
| 95% CI Upper | {result.sharpe_ci_upper:.4f} |
| Target PSR (GO) | > {config.psr_go_threshold} |
| Target PSR (NO-GO) | < {config.psr_no_go_threshold} |

**Interpretation:** PSR measures the probability that the true Sharpe ratio exceeds the backtest Sharpe ({config.backtest_sharpe:.4f}).
- PSR > {config.psr_go_threshold}: Strong evidence paper performance matches backtest
- PSR < {config.psr_no_go_threshold}: Strong evidence paper performance is worse than backtest
- Otherwise: Inconclusive, need more data

---

## Drift Assessment

### Regime Stability
- **Current Regime Exposure:** {result.regime_persistence_days > 0 and 'Full (1.0)' or 'Cash (0.0)'}
- **Days in Current Regime:** {result.regime_persistence_days}
- **Regime Stable (≥5 days):** {'Yes' if result.regime_stable else 'No'}

### Risk Parameter Bounds
| Parameter | Min | Max | Alert Threshold | Status |
|-----------|-----|-----|-----------------|--------|
| vol_scale | {result.vol_scale_min:.3f} | {result.vol_scale_max:.3f} | > 2.0 | {'⚠️ BREACH' if result.vol_scale_max > 2.0 else '✅ OK'} |
| dd_scale | {result.dd_scale_min:.3f} | {result.dd_scale_max:.3f} | < 0.25 | {'⚠️ BREACH' if result.dd_scale_min < 0.25 else '✅ OK'} |

### Turnover Distribution
| Statistic | Value | Backtest Avg | Status |
|-----------|-------|--------------|--------|
| Median Daily Turnover | {result.turnover_median:.2%} | ~0.012 (est.) | {'⚠️ HIGH' if result.turnover_median > 0.5 else '✅ OK'} |
| 95th Percentile Turnover | {result.turnover_p95:.2%} | ~0.05 (est.) | {'⚠️ HIGH' if result.turnover_p95 > 0.5 else '✅ OK'} |

### Drift Flags
- **Active Drift Flags:** {result.drift_flags_count}
- **Details:** See paper_trading_rolling.md for current flags

---

## Go/No-Go Criteria Summary

| Criterion | Threshold | Actual | Status |
|-----------|-----------|--------|--------|
| Minimum Track Record | ≥ {config.min_days} days | {result.paper_days} days | {'✅ PASS' if result.paper_days >= config.min_days else '❌ FAIL'} |
| Probabilistic Sharpe Ratio | > {config.psr_go_threshold} | {result.psr_normal:.3f} | {'✅ PASS' if result.psr_normal > config.psr_go_threshold else ('❌ FAIL' if result.psr_normal < config.psr_no_go_threshold else '⚠️ INCONCLUSIVE')} |
| Max Drawdown | ≤ {config.max_dd_threshold:.0%} | {abs(result.paper_max_dd):.2%} | {'✅ PASS' if result.paper_max_dd > -config.max_dd_threshold else '❌ FAIL'} |
| Regime Stability | Stable | {'Stable' if result.regime_stable else 'Unstable'} | {'✅ PASS' if result.regime_stable else '⚠️ WATCH'} |
| Risk Parameters | In Bounds | vol_scale∈[{result.vol_scale_min:.2f},{result.vol_scale_max:.2f}], dd_scale∈[{result.dd_scale_min:.2f},{result.dd_scale_max:.2f}] | {'✅ PASS' if result.vol_scale_max <= 2.0 and result.dd_scale_min >= 0.25 else '⚠️ WATCH'} |

---

*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*
*Code revision: {__import__('subprocess').run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip() if Path('.git').exists() else 'unknown'}*
"""
    return report


def save_evaluation_report(result: GoNoGoResult, config: GoNoGoConfig, output_path: str | Path) -> None:
    """Save evaluation report to file."""
    report = generate_evaluation_report(result, config)
    path = _ensure_path(output_path)
    with open(path, "w") as fh:
        fh.write(report)


if __name__ == "__main__":
    # Quick test
    from src.simulation.paper_trading import PaperTradingConfig, PaperTradingState

    config = PaperTradingConfig.from_paper_config_yaml("config/paper_trading_config.yaml")
    state = PaperTradingState.from_yaml("data/processed/paper_trading_state.yaml")

    result = evaluate_go_no_go(state, config)
    report = generate_evaluation_report(result, GoNoGoConfig())
    print(report)