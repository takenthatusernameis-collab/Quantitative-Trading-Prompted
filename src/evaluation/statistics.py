"""Statistical significance analysis for the time-series momentum strategy.

Implements:
  - Block bootstrap estimation of Sharpe ratio distribution
  - Deflated Sharpe Ratio (DSR) with multiple-testing correction
  - Probabilistic Sharpe Ratio (PSR) against a benchmark
  - Parameter plateau analysis via +/- perturbation
  - Probability of Backtest Overfitting (PBO) / CSCV
  - False Discovery Rate (Benjamini-Hochberg) control
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from arch.bootstrap import MovingBlockBootstrap
from scipy import stats

from src.evaluation.sharpe import backtest_sharpe_ratio, sharpe_ratio
from src.evaluation.utils import (
    annualize_return,
    get_cost_params,
    max_drawdown,
)
from src.features.momentum import build_weights


def block_bootstrap_sharpe(
    returns: pd.Series,
    n_samples: int = 1000,
    block_size: int = 22,
    seed: int | None = None,
) -> np.ndarray:
    """Estimate the Sharpe ratio distribution via moving block bootstrap.

    Returns an array of ``n_samples`` annualized Sharpe ratios computed on
    block-bootstrapped resamples of *returns*. Pass ``seed`` for a
    reproducible bootstrap distribution.
    """
    arr = np.asarray(returns.values, dtype=float)
    n = len(arr)
    effective_block = min(block_size, max(1, n // 10))
    mbb = MovingBlockBootstrap(effective_block, arr, seed=seed)

    results: list[float] = []
    for posdata, _ in mbb.bootstrap(n_samples):
        sample = posdata[0]
        s = _safe_sharpe(sample)
        if s is not None:
            results.append(s)
    if len(results) < n_samples * 0.5:
        results.extend([_safe_sharpe(arr)] * (n_samples - len(results)))
    return np.array(results) if results else np.array([0.0])


def _safe_sharpe(sample: np.ndarray) -> float | None:
    """Canonical Sharpe of a 1-D return array, or None if it is degenerate.

    Uses the repository's single Sharpe convention
    (:func:`src.evaluation.sharpe.sharpe_ratio`), so the bootstrap
    distribution and the PSR numerator measure the same statistic. The
    convention compounds no wealth path, so it cannot overflow on a
    resample with a non-positive growth factor.
    """
    sample = np.asarray(sample, dtype=float).ravel()
    if sample.size < 2:
        return None
    std = sample.std(ddof=1)
    if std == 0 or np.isnan(std) or std < 1e-12:
        return None
    sharpe = sharpe_ratio(sample)
    if not np.isfinite(sharpe):
        return None
    return sharpe


def compute_psr(
    returns: pd.Series,
    sr_target: float = 0.0,
    n_bootstrap: int = 1000,
    block_size: int = 22,
    seed: int | None = None,
) -> dict:
    """Probabilistic Sharpe Ratio (PSR) against *sr_target*.

    Uses the block bootstrap to estimate the Sharpe ratio standard error,
    then computes PSR = Φ((SR − SR_target) / SE) and an empirical PSR.

    The observed Sharpe (the numerator) and every bootstrap resample (the
    distribution behind the standard error) are computed with the *same*
    estimator, the repository's canonical Sharpe convention
    (:func:`src.evaluation.sharpe.sharpe_ratio`). Before Cycle 861 the
    numerator used the geometric, risk-free-adjusted estimator while the
    bootstrap used an arithmetic one, so the PSR mixed two statistics.

    Note that *sr_target* is an external reference expressed on the
    backtest-baseline scale (CAGR-based, rf 2%); it is not restated here.
    See ``config/promotion_gates.yaml`` (``sharpe_convention``) and
    ``research/reports/monitoring_cycle_861.md`` for the quantified effect of
    that residual scale mismatch.
    """
    sharpes = block_bootstrap_sharpe(returns, n_bootstrap, block_size, seed=seed)
    se = float(np.std(sharpes, ddof=1)) if len(sharpes) > 1 else 0.0
    sr_obs = sharpe_ratio(returns)

    if se > 0:
        z = (sr_obs - sr_target) / se
        psr_normal = float(stats.norm.cdf(z))
    else:
        psr_normal = 1.0 if sr_obs > sr_target else 0.0

    psr_empirical = float((sharpes > sr_target).mean()) if len(sharpes) else 0.0

    return {
        "psr_normal": psr_normal,
        "psr_empirical": psr_empirical,
        "sharpe_observed": sr_obs,
        "sharpe_se": se,
        "sr_target": sr_target,
        "bootstrap_mean": float(np.mean(sharpes)),
        "bootstrap_std": se,
        "ci_lower": float(np.percentile(sharpes, 2.5)),
        "ci_upper": float(np.percentile(sharpes, 97.5)),
        "n_bootstrap": n_bootstrap,
        "bootstrap_sharpes": sharpes,
    }


def compute_dsr(
    returns: pd.Series,
    n_configs: int,
    sr_target: float = 0.0,
    n_bootstrap: int = 1000,
    block_size: int = 22,
    seed: int | None = None,
) -> dict:
    """Deflated Sharpe Ratio (DSR).

    Adjusts the observed Sharpe for the multiple-comparisons / selection bias
    arising from testing *n_configs* parameter configurations.

    DSR = (SR − SR_threshold) / SE
    where  SR_threshold = SR_target + SE × E[max of N iid N(0,1)].
    """
    bs = compute_psr(returns, sr_target, n_bootstrap, block_size, seed=seed)
    se = bs["sharpe_se"]
    sr = bs["sharpe_observed"]

    ln_n = math.log(max(n_configs, 2))
    e_max = math.sqrt(2.0 * ln_n) - (math.log(ln_n) + math.log(4.0 * math.pi)) / (
        2.0 * math.sqrt(2.0 * ln_n)
    )

    sr_threshold = sr_target + se * e_max
    if se > 0:
        dsr = (sr - sr_threshold) / se
    else:
        dsr = 0.0
    dsr_probability = float(stats.norm.cdf(dsr))

    return {
        "dsr": float(dsr),
        "dsr_probability": dsr_probability,
        "n_configs": n_configs,
        "sr_observed": sr,
        "sharpe_se": se,
        "sr_threshold": float(sr_threshold),
        "e_max": float(e_max),
        "sr_target": sr_target,
        "n_bootstrap": n_bootstrap,
        "bootstrap_mean": bs["bootstrap_mean"],
        "bootstrap_std": bs["bootstrap_std"],
        "ci_lower": bs["ci_lower"],
        "ci_upper": bs["ci_upper"],
        "bootstrap_sharpes": bs["bootstrap_sharpes"],
    }


def _evaluate_config(
    close: pd.DataFrame,
    lookback: int,
    skip: int,
    top_fraction: float,
    cost: float,
    train_end_dt: pd.Timestamp,
    val_end_dt: pd.Timestamp,
) -> dict:
    """Run one (lookback, skip, top_fraction) configuration and return its
    train/validation/test Sharpe, annualized return and max drawdown.

    Extracted so the baseline reference point can be evaluated with the same
    code path as the perturbations (see parameter_perturbation).

    Returns
    -------
    dict
        The per-period Sharpe ratios of the configuration.

    Notes
    -----
    The per-period Sharpe ratios are computed on the *backtest-baseline*
    scale (:func:`src.evaluation.sharpe.backtest_sharpe_ratio`), because the
    parameter-plateau, PBO and FDR analyses are compared against the
    recorded backtest baseline (Sharpe 1.4178) and against the published
    backtest artifacts. Promotion gates, the drift flag and the PSR use the
    canonical convention instead.
    """
    weights = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    common = close.index.intersection(weights.index)
    close_a = close.loc[common]
    weights_a = weights.loc[common]
    daily_ret = close_a.pct_change().fillna(0.0)
    port_ret = (weights_a * daily_ret).sum(axis=1)
    wc = weights_a.diff().abs().sum(axis=1)
    net_ret = port_ret - wc * cost

    tr_mask = net_ret.index <= train_end_dt
    va_mask = (net_ret.index > train_end_dt) & (net_ret.index <= val_end_dt)
    te_mask = net_ret.index > val_end_dt

    tr_ret = net_ret[tr_mask]
    va_ret = net_ret[va_mask]
    te_ret = net_ret[te_mask]

    return {
        "lookback": lookback,
        "skip": skip,
        "top_fraction": top_fraction,
        "train_sharpe": backtest_sharpe_ratio(tr_ret) if len(tr_ret) > 1 else np.nan,
        "val_sharpe": backtest_sharpe_ratio(va_ret) if len(va_ret) > 1 else np.nan,
        "test_sharpe": backtest_sharpe_ratio(te_ret) if len(te_ret) > 1 else np.nan,
        "test_ann_return": annualize_return(te_ret) if len(te_ret) > 0 else np.nan,
        "test_max_dd": max_drawdown(te_ret) if len(te_ret) > 0 else np.nan,
    }


def parameter_perturbation(
    close: pd.DataFrame,
    baseline: tuple[int, int, float] = (252, 21, 0.5),
    pct: float = 0.10,
    train_end: str = "2009-12-31",
    val_end: str = "2017-12-31",
) -> pd.DataFrame:
    """Perturb baseline parameters by +/- *pct* and measure sensitivity.

    Tests individual parameter perturbations and all 2^3 joint perturbations
    (each parameter either high or low). Returns a DataFrame indexed by
    (lookback, skip, top_fraction) with train/validation/test Sharpe ratios.
    """
    lb0, sk0, tf0 = baseline
    commission_bps, slippage_bps = get_cost_params()
    cost = commission_bps + slippage_bps

    perturbations = []
    # Individual perturbations
    perturbations.append((int(lb0 * (1 - pct)), sk0, tf0, "lookback_low"))
    perturbations.append((int(lb0 * (1 + pct)), sk0, tf0, "lookback_high"))
    perturbations.append((lb0, int(sk0 * (1 - pct)), tf0, "skip_low"))
    perturbations.append((lb0, int(sk0 * (1 + pct)), tf0, "skip_high"))
    perturbations.append((lb0, sk0, round(tf0 * (1 - pct), 4), "topfrac_low"))
    perturbations.append((lb0, sk0, round(tf0 * (1 + pct), 4), "topfrac_high"))
    # Joint perturbations (all 2^3 = 8 combinations)
    for lb in [int(lb0 * (1 - pct)), int(lb0 * (1 + pct))]:
        for sk in [int(sk0 * (1 - pct)), int(sk0 * (1 + pct))]:
            for tf in [round(tf0 * (1 - pct), 4), round(tf0 * (1 + pct), 4)]:
                perturbations.append((lb, sk, tf, "joint"))

    rows = []
    train_end_dt = pd.Timestamp(train_end, tz="UTC")
    val_end_dt = pd.Timestamp(val_end, tz="UTC")

    # Evaluate the baseline itself first. The perturbation set is only a
    # meaningful factorial design when the unperturbed reference point is
    # present: without it the plateau summary has no row to anchor the
    # "within +/-10% of baseline" stability statistic, and the markdown
    # formatter silently drops both the baseline row and the stability
    # paragraph (see format_plateau_markdown).
    baseline_row = _evaluate_config(
        close, lb0, sk0, tf0, cost, train_end_dt, val_end_dt
    )
    baseline_row["label"] = "baseline"
    rows.append(baseline_row)

    for lb, sk, tf, label in perturbations:
        try:
            row = _evaluate_config(close, lb, sk, tf, cost, train_end_dt, val_end_dt)
            row["label"] = label
            rows.append(row)
        except (ValueError, KeyError, RuntimeError) as exc:
            print(f"    Perturbation error ({lb},{sk},{tf}): {exc}")
            rows.append({
                "lookback": lb, "skip": sk, "top_fraction": tf, "label": label,
                "train_sharpe": np.nan, "val_sharpe": np.nan, "test_sharpe": np.nan,
                "test_ann_return": np.nan, "test_max_dd": np.nan,
            })

    cols = ["lookback", "skip", "top_fraction", "label", "train_sharpe", "val_sharpe",
            "test_sharpe", "test_ann_return", "test_max_dd"]
    df = pd.DataFrame(rows)[cols]
    return df.set_index(["lookback", "skip", "top_fraction"])


def compute_pbo(
    config_results: pd.DataFrame,
    threshold: float = 0.0,
    alpha: float = 0.05,
) -> dict:
    """Probability of Backtest Overfitting (PBO) via logit-normal model.

    Parameters
    ----------
    config_results:
        DataFrame with columns ``train_sharpe`` and ``test_sharpe``.
    threshold:
        OOS Sharpe threshold below which a config is considered "overfitted"
        (default 0).
    alpha:
        Significance level for FDR correction applied to individual config
        p-values.
    """
    df = config_results.dropna(subset=["train_sharpe", "test_sharpe"]).copy()
    n = len(df)
    if n < 10:
        return {"pbo": np.nan, "error": "insufficient configurations", "n_configs": n}

    df_sorted = df.sort_values("train_sharpe", ascending=False).reset_index(drop=True)

    # Probability that top-k IS configs have OOS Sharpe below threshold
    ks = np.arange(1, n + 1)
    logits = []
    valid_ks = []
    for k in ks:
        top_k_oos = df_sorted["test_sharpe"].iloc[:k]
        p = float((top_k_oos < threshold).mean())
        if 1e-6 < p < 1 - 1e-6:
            logits.append(math.log(p / (1 - p)))
            valid_ks.append(k)

    pbo = float("nan")
    if len(logits) >= 3:
        x = (np.array(valid_ks) - (n + 1) / 2.0) / n
        y = np.array(logits)
        beta, alpha_fit = np.polyfit(x, y, 1)
        x_best = (1 - (n + 1) / 2.0) / n
        logit_pbo = alpha_fit + beta * x_best
        pbo = float(1.0 / (1.0 + math.exp(-logit_pbo)))
    elif len(logits) > 0:
        pbo = float(np.mean(logits > 0))

    # Classic PBO: best IS config has OOS below threshold?
    best_is_oos = df_sorted["test_sharpe"].iloc[0]
    best_is_config = {
        "train_sharpe": float(df_sorted["train_sharpe"].iloc[0]),
        "test_sharpe": float(best_is_oos),
        "is_below_threshold": bool(best_is_oos < threshold),
    }

    # FDR control across all configs
    sharpe_se = df["test_sharpe"].std(ddof=1) / math.sqrt(n) if n > 1 else 1.0
    p_values = pd.Series(2 * (1 - stats.norm.cdf(df["test_sharpe"].abs() / max(sharpe_se, 1e-10))), index=df.index)
    p_values = p_values.clip(0, 1)
    fdr_reject = _benjamini_hochberg(p_values, alpha)

    # Summary statistics
    train_sharpes = df["train_sharpe"]
    test_sharpes = df["test_sharpe"]
    rank_corr = float(stats.spearmanr(train_sharpes, test_sharpes)[0])

    return {
        "pbo": pbo,
        "n_configs": n,
        "n_configs_oos_positive": int((test_sharpes > threshold).sum()),
        "n_configs_best_is_oos_positive": int(best_is_oos > threshold),
        "best_is_config": best_is_config,
        "rank_correlation_is_oos": rank_corr,
        "mean_is_sharpe": float(train_sharpes.mean()),
        "mean_oos_sharpe": float(test_sharpes.mean()),
        "std_is_sharpe": float(train_sharpes.std(ddof=1)),
        "std_oos_sharpe": float(test_sharpes.std(ddof=1)),
        "overfit_ratio": float((train_sharpes.mean() - test_sharpes.mean()) / max(train_sharpes.std(ddof=1), 1e-10)),
        "fdr_alpha": alpha,
        "n_significant_after_fdr": int(fdr_reject.sum()),
        "n_rejected_fdr": int(fdr_reject.sum()),
        "p_values": p_values.values,
        "fdr_rejected": fdr_reject.values,
        "alpha_fit": float(alpha_fit) if len(logits) >= 3 else np.nan,
        "beta_fit": float(beta) if len(logits) >= 3 else np.nan,
    }


def _benjamini_hochberg(p_values: pd.Series, alpha: float = 0.05) -> pd.Series:
    """Apply Benjamini-Hochberg FDR correction.

    Returns a boolean Series (True = reject null = significant).
    """
    p = np.asarray(p_values)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    thresholds = (np.arange(1, n + 1) / n) * alpha
    rejected_sorted = ranked <= thresholds

    # Propagate rejections from the largest p-value downward
    for i in range(n - 2, -1, -1):
        if rejected_sorted[i]:
            rejected_sorted[i + 1 :] = True

    rejected = np.zeros(n, dtype=bool)
    rejected[order] = rejected_sorted
    return pd.Series(rejected, index=p_values.index)


def compute_fdr(
    config_results: pd.DataFrame,
    alpha: float = 0.05,
) -> dict:
    """False Discovery Rate control across tested configurations.

    For each configuration, computes a p-value for the test-period Sharpe
    ratio (two-sided, from the normal approximation). Then applies the
    Benjamini-Hochberg procedure to control FDR at *alpha*.
    """
    df = config_results.dropna(subset=["test_sharpe"]).copy()
    n = len(df)
    if n == 0:
        return {"n_tested": 0, "n_significant": 0}

    test_sharpes = df["test_sharpe"].values
    sharpe_se = np.std(test_sharpes, ddof=1) / math.sqrt(n) if n > 1 else 1.0
    sharpe_se = max(sharpe_se, 1e-10)
    p_values = 2 * (1 - stats.norm.cdf(np.abs(test_sharpes) / sharpe_se))
    p_values = np.clip(p_values, 0, 1)

    rejected = _benjamini_hochberg(pd.Series(p_values), alpha).values

    return {
        "n_tested": n,
        "n_significant": int(rejected.sum()),
        "alpha": alpha,
        "mean_p_value": float(np.mean(p_values)),
        "min_p_value": float(np.min(p_values)),
        "p_values": p_values,
        "rejected": rejected,
        "sharpe_se": float(sharpe_se),
    }


def format_plateau_markdown(pert_df: pd.DataFrame, baseline: tuple = (252, 21, 0.5)) -> str:
    """Format parameter perturbation results as markdown."""
    lines = ["## Parameter Plateau Analysis\n"]
    lines.append(f"Baseline: lookback={baseline[0]}, skip={baseline[1]}, top_fraction={baseline[2]}\n")
    lines.append("| Perturbation | Lookback | Skip | Top Fraction | Train Sharpe | Val Sharpe | Test Sharpe |")
    lines.append("|-------------|----------|------|--------------|-------------|-----------|------------|")

    bl_row = None
    for idx, row in pert_df.reset_index().iterrows():
        if int(row["lookback"]) == baseline[0] and int(row["skip"]) == baseline[1] and abs(row["top_fraction"] - baseline[2]) < 1e-6:
            bl_row = row
        label = row["label"]
        lines.append(
            f"| {label} | {int(row['lookback'])} | {int(row['skip'])} | {row['top_fraction']:.2f} | "
            f"{row['train_sharpe']:.4f} | {row['val_sharpe']:.4f} | {row['test_sharpe']:.4f} |"
        )

    if bl_row is not None:
        lines.append("")
        lines.append(
            f"\n**Baseline (train, val, test Sharpe):** "
            f"{bl_row['train_sharpe']:.3f}, {bl_row['val_sharpe']:.3f}, {bl_row['test_sharpe']:.3f}\n"
        )
        test_vals = pert_df["test_sharpe"].dropna()
        baseline_test = float(bl_row["test_sharpe"])
        threshold_val = max(0.1, baseline_test * 0.10) if baseline_test > 0 else 0.1
        within_10pct = int(((test_vals - baseline_test).abs() <= threshold_val).sum()) if not test_vals.empty else 0
        lines.append(
            f"**Stability:** {within_10pct} of {len(test_vals)} perturbed configs "
            f"within ±10% of baseline test Sharpe ({baseline_test:.3f}).\n"
        )
    return "\n".join(lines)
