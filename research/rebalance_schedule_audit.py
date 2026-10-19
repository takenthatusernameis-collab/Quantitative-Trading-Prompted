#!/usr/bin/env python3
"""Audit of the shared month-end rebalance schedule (Cycle 870).

Read-only with respect to market data: the tool reads the committed raw cache
(``data/raw/*.parquet``), writes exactly one report under ``research/reports/``
and touches nothing else. It is deterministic (no random number generator, no
timestamps in the report).

It measures, on the frozen ``sectorrotation_001`` universe (9 GICS sector
ETFs, 1998-12-22 .. 2026-10-08):

* the **defect** that ``src/backtest/engine.py`` accepted a ``rebalance_freq``
  argument and never used it (the universe was re-ranked every session), by
  running the engine with and without the new opt-in schedule;
* the **fix**: ``src/backtest/rebalance.py`` (the single implementation of the
  month-end schedule) driven by the engine's ``rebalance_schedule`` parameter,
  checked against the independent config-faithful research path of
  ``research/sectorrotation_long_sample_feasibility.py``;
* the **second defect**, in ``src/simulation/engine.py``'s ``"M"`` branch
  (calendar ``index.is_month_end`` applied to a trading calendar), which is
  left behaviourally unchanged and only measured here;
* that the **incumbent** (default) execution path is untouched: the code-level
  decision stays NO-GO with the committed numbers.

Reproduction: ``python research/rebalance_schedule_audit.py``
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.sectorrotation_long_sample_feasibility import (  # noqa: E402
    build_monthly_weights,
    month_end_dates,
    portfolio_returns,
)
from src.backtest.engine import get_cost_params, run_backtest  # noqa: E402
from src.backtest.rebalance import month_end_sessions  # noqa: E402
from src.data.yfinance_fetcher import fetch_universe  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.statistics import compute_psr  # noqa: E402
from src.evaluation.utils import max_drawdown  # noqa: E402
from src.features.momentum import build_weights, compute_momentum, select_top_decile  # noqa: E402

CONFIG_CAND = REPO_ROOT / "config" / "sectorrotation_candidate_001.yaml"
CONFIG_INCUMBENT = REPO_ROOT / "config" / "simulation_candidate_001.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
REPORT_MD = REPORTS_DIR / "rebalance_schedule_001.md"

# The incumbent's committed code-level numbers (research/reports/
# promotion_feasibility_backtest_001.md). They must not move.
INCUMBENT_SHARPE = 0.5646255767978904
INCUMBENT_MAX_DD = -0.6224126346564325
INCUMBENT_PSR = 2.2219753177036448e-08
INCUMBENT_FAILED_GATES = ["full_period_sharpe", "rolling_63d_sharpe", "max_drawdown", "psr"]
# The Cycle 869 long-sample numbers that the opt-in path has to reproduce.
LONG_SAMPLE_SHARPE = 0.472367


def load_yaml(path: Path) -> Any:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def source_hashes() -> dict[str, str]:
    """SHA-256 of the source files that define the schedule (stable provenance)."""
    return {
        "src/backtest/rebalance.py": sha256_file(REPO_ROOT / "src" / "backtest" / "rebalance.py"),
        "src/backtest/engine.py": sha256_file(REPO_ROOT / "src" / "backtest" / "engine.py"),
    }


def path_metrics(
    net_ret: pd.Series,
    weights: pd.DataFrame,
    turnover: pd.Series,
) -> dict[str, float]:
    """Headline metrics of one execution path (invested sample)."""
    invested = weights.sum(axis=1) > 0
    r = net_ret.loc[invested]
    t = turnover.loc[invested]
    n = len(r)
    return {
        "invested_sessions": int(n),
        "trade_days": int((weights.diff().abs().sum(axis=1) > 1e-10).sum()),
        "rebalances": int((weights.diff().abs().sum(axis=1) > 1e-10).sum()),
        "annualized_turnover": float(t.sum()) * 252.0 / n if n else 0.0,
        "sharpe_canonical": float(sharpe_ratio(r)),
        "max_drawdown": float(max_drawdown(r)),
        "total_return": float((1.0 + r).prod() - 1.0),
    }


def main() -> int:
    cand = load_yaml(CONFIG_CAND)
    incumbent_cfg = load_yaml(CONFIG_INCUMBENT)
    universe = list(cand["universe"])
    signal = cand["signal"]
    lookback = int(signal["lookback"])
    skip = int(signal["skip"])
    top_fraction = float(signal["top_fraction"])

    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    # --- data provenance (read-only) ---
    hashes_before = {s: sha256_file(RAW_DIR / f"{s}.parquet") for s in universe}
    per_symbol = {}
    for s in universe:
        df = pd.read_parquet(RAW_DIR / f"{s}.parquet")
        per_symbol[s] = (df.index.min(), df.index.max())
    start = max(v[0] for v in per_symbol.values())
    end = min(v[1] for v in per_symbol.values())
    start_s, end_s = start.date().isoformat(), end.date().isoformat()

    commission_bps, slippage_bps = get_cost_params()
    cost_per_trade = commission_bps + slippage_bps

    data = fetch_universe(universe, start_s, end_s, force=False)
    close = data.xs("Close", level=0, axis=1).ffill().dropna(how="all")

    # --- path A: the default engine behaviour (daily re-rank, the defect) ---
    daily_net, daily_weights, _ = run_backtest(
        symbols=universe,
        start_date=start_s,
        end_date=end_s,
        lookback=lookback,
        skip=skip,
        top_fraction=top_fraction,
    )
    daily_turnover = daily_weights.diff().abs().sum(axis=1).fillna(0.0)
    daily_stats = path_metrics(daily_net, daily_weights, daily_turnover)

    # --- path B: the opt-in month-end schedule (the fix) ---
    month_net, month_weights, _ = run_backtest(
        symbols=universe,
        start_date=start_s,
        end_date=end_s,
        lookback=lookback,
        skip=skip,
        top_fraction=top_fraction,
        rebalance_freq=signal.get("rebalance_freq", "monthly"),
        rebalance_schedule="month_end",
    )
    month_turnover = month_weights.diff().abs().sum(axis=1).fillna(0.0)
    month_stats = path_metrics(month_net, month_weights, month_turnover)

    # --- path C: the independent config-faithful research path (reference) ---
    momentum = compute_momentum(close, lookback=lookback, skip=skip)
    mask = select_top_decile(momentum, top_fraction=top_fraction)
    ref_weights, ref_segments = build_monthly_weights(close, mask, month_end_dates(close.index))
    ref_net, ref_turnover = portfolio_returns(close, ref_weights, cost_per_trade)
    ref_stats = path_metrics(ref_net, ref_weights, ref_turnover)

    check(
        "opt_in_matches_config_faithful_research_path",
        bool(np.max(np.abs((month_net - ref_net).to_numpy())) <= 1e-12),
        f"max |engine_opt_in - research_path| = {np.max(np.abs((month_net - ref_net).to_numpy())):.3e} "
        f"(tolerance 1e-12) over {len(month_net)} sessions.",
    )
    check(
        "opt_in_weights_are_identical_to_research_path",
        bool(np.array_equal(month_weights.to_numpy(), ref_weights.to_numpy())),
        "the opt-in engine weights are bit-identical to the research path's weights.",
    )
    check(
        "opt_in_reproduces_long_sample_sharpe",
        abs(month_stats["sharpe_canonical"] - LONG_SAMPLE_SHARPE) < 5e-7,
        f"opt-in canonical Sharpe {month_stats['sharpe_canonical']:.6f} "
        f"(Cycle 869 published {LONG_SAMPLE_SHARPE}).",
    )
    check(
        "default_path_is_the_daily_rerank_defect",
        daily_stats["trade_days"] > 3 * month_stats["trade_days"],
        f"default path: {daily_stats['trade_days']} trade days / "
        f"{daily_stats['annualized_turnover']:.4f}x turnover; opt-in month-end path: "
        f"{month_stats['trade_days']} trade days / {month_stats['annualized_turnover']:.4f}x.",
    )

    # --- the month-end schedule itself ---
    me_sessions = month_end_sessions(close.index)
    month_keys = sorted(set(close.index.strftime("%Y-%m")))
    last_session_of_month = {
        key: close.index[close.index.strftime("%Y-%m") == key][-1] for key in month_keys
    }
    me_matches_last_session = all(
        me_sessions[i] == last_session_of_month[month_keys[i]] for i in range(len(month_keys))
    )
    check(
        "month_end_is_the_last_session_of_the_month",
        me_matches_last_session and len(me_sessions) == len(month_keys),
        f"{len(me_sessions)} month-end sessions for {len(month_keys)} calendar months; every one of "
        f"them is the last session of its month.",
    )
    check(
        "no_rebalance_on_a_non_session",
        bool(all(d in set(close.index) for d in me_sessions)),
        "every month-end session is a session of the aligned price calendar "
        "(no weekend, no calendar-only date).",
    )
    first_signal = momentum.dropna(how="all").index.min()
    first_effective = ref_segments[0]["effective_date"]
    check(
        "signal_lag_is_one_session",
        bool(ref_segments[0]["effective_date"] > ref_segments[0]["signal_date"])
        and int(close.index.get_loc(first_effective))
        == int(close.index.get_loc(ref_segments[0]["signal_date"])) + 1,
        f"the first signal is formed on {ref_segments[0]['signal_date'].date()} and becomes "
        f"effective on {first_effective.date()} (the next session).",
    )
    no_position_before = bool((ref_weights.loc[ref_weights.index < first_effective] == 0.0).all().all())
    check(
        "no_position_before_the_first_valid_signal",
        no_position_before,
        f"the first valid momentum cross-section is {first_signal.date()}; no position exists "
        f"before {first_effective.date()}.",
    )

    # --- the simulation engine's "M" branch (left unchanged, measured here) ---
    lagged_daily = build_weights(close, lookback=lookback, skip=skip, top_fraction=top_fraction)
    is_month_end = close.index.is_month_end
    sim_m_weights = lagged_daily.where(pd.Series(is_month_end, index=close.index), axis=0).ffill().fillna(0.0)
    months_without_rebalance = [
        key for key in month_keys if not bool(close.index[close.index.strftime("%Y-%m") == key].is_month_end.any())
    ]
    months_with_rebalance = [key for key in month_keys if key not in months_without_rebalance]
    weight_diff = (sim_m_weights - ref_weights).abs().sum(axis=1)
    sim_m_net = (sim_m_weights * close.pct_change().fillna(0.0)).sum(axis=1) - (
        sim_m_weights.diff().abs().sum(axis=1).fillna(0.0) * cost_per_trade
    )
    sim_m_turnover = sim_m_weights.diff().abs().sum(axis=1).fillna(0.0)
    sim_m_stats = path_metrics(sim_m_net, sim_m_weights, sim_m_turnover)
    # Sessions on which each schedule actually changes the portfolio. The "M"
    # branch changes the weights on the month-end session itself; the shared
    # schedule changes them on the session after it, so the two calendars can
    # never coincide.
    sim_m_change = set(close.index[(sim_m_weights.diff().abs().sum(axis=1) > 1e-10)])
    shared_change = set(close.index[(ref_weights.diff().abs().sum(axis=1) > 1e-10)])
    coincident_change_sessions = len(sim_m_change & shared_change)
    check(
        "simulation_m_branch_is_calendar_based",
        len(months_without_rebalance) > 0 and int(is_month_end.sum()) < len(close.index),
        f"the simulation 'M' branch fires on {int(is_month_end.sum())} of {len(close.index)} sessions "
        f"and has no rebalance at all in {len(months_without_rebalance)} of {len(month_keys)} months.",
    )
    check(
        "simulation_m_never_rebalances_on_the_same_session_as_the_shared_schedule",
        coincident_change_sessions == 0,
        f"the two schedules change the portfolio on {coincident_change_sessions} common sessions "
        f"({len(sim_m_change)} 'M' branch sessions vs {len(shared_change)} shared-schedule sessions): "
        f"the 'M' branch rebalances one session earlier, on the month's last session itself.",
    )

    # --- the incumbent path must be untouched ---
    inc_universe = list(incumbent_cfg["universe"])
    inc_starts, inc_ends = [], []
    for s in inc_universe:
        df = pd.read_parquet(RAW_DIR / f"{s}.parquet")
        inc_starts.append(df.index.min())
        inc_ends.append(df.index.max())
    inc_start = max(inc_starts).date().isoformat()
    inc_end = min(inc_ends).date().isoformat()
    inc_net, _inc_weights, _ = run_backtest(
        symbols=inc_universe,
        start_date=inc_start,
        end_date=inc_end,
        lookback=int(incumbent_cfg["signal"]["lookback"]),
        skip=int(incumbent_cfg["signal"]["skip"]),
        top_fraction=float(incumbent_cfg["signal"]["top_fraction"]),
        rebalance_freq=incumbent_cfg["signal"]["rebalance_freq"],
    )
    inc_sharpe = float(sharpe_ratio(inc_net))
    inc_dd = float(max_drawdown(inc_net))
    inc_psr = float(compute_psr(inc_net, sr_target=1.4178, seed=20240101)["psr_normal"])
    check(
        "incumbent_default_path_unchanged",
        abs(inc_sharpe - INCUMBENT_SHARPE) <= 1e-12
        and abs(inc_dd - INCUMBENT_MAX_DD) <= 1e-12
        and abs(inc_psr - INCUMBENT_PSR) <= 1e-15,
        f"incumbent default path: canonical Sharpe {inc_sharpe!r} (committed {INCUMBENT_SHARPE!r}), "
        f"max DD {inc_dd!r} (committed {INCUMBENT_MAX_DD!r}), PSR {inc_psr!r} "
        f"(committed {INCUMBENT_PSR!r}).",
    )

    # --- read-only proof ---
    hashes_after = {s: sha256_file(RAW_DIR / f"{s}.parquet") for s in universe}
    check("raw_cache_unchanged", hashes_before == hashes_after, "the raw cache is byte-identical.")

    failed = [c["check"] for c in checks if not c["pass"]]
    overall = "PASS" if not failed else "FAIL"

    src_hashes = source_hashes()
    report = build_report(
        checks=checks,
        universe=universe,
        start_s=start_s,
        end_s=end_s,
        n_sessions=len(close.index),
        lookback=lookback,
        skip=skip,
        top_fraction=top_fraction,
        cost_per_trade=cost_per_trade,
        daily_stats=daily_stats,
        month_stats=month_stats,
        ref_stats=ref_stats,
        sim_m_stats=sim_m_stats,
        n_is_month_end=int(is_month_end.sum()),
        n_months=len(month_keys),
        months_with_rebalance=len(months_with_rebalance),
        months_without_rebalance=len(months_without_rebalance),
        n_sessions_differing=int((weight_diff > 1e-12).sum()),
        max_weight_diff=float(weight_diff.max()),
        sim_m_change_sessions=len(sim_m_change),
        shared_change_sessions=len(shared_change),
        coincident_change_sessions=coincident_change_sessions,
        n_segments=len(ref_segments),
        first_signal=ref_segments[0]["signal_date"],
        first_effective=ref_segments[0]["effective_date"],
        last_signal=ref_segments[-1]["signal_date"],
        last_effective=ref_segments[-1]["effective_date"],
        max_net_diff=float(np.max(np.abs((month_net - ref_net).to_numpy()))),
        inc_sharpe=inc_sharpe,
        inc_dd=inc_dd,
        inc_psr=inc_psr,
        inc_start=inc_start,
        inc_end=inc_end,
        inc_sessions=len(inc_net),
        src_hashes=src_hashes,
        overall=overall,
        failed=failed,
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(report)

    print(f"OVERALL: {overall}")
    print(f"CHECKS: {len(checks) - len(failed)}/{len(checks)} passed")
    print(
        f"engine default (daily re-rank): sharpe={daily_stats['sharpe_canonical']:.6f} "
        f"trade_days={daily_stats['trade_days']} turnover={daily_stats['annualized_turnover']:.4f}x"
    )
    print(
        f"engine opt-in (month end):      sharpe={month_stats['sharpe_canonical']:.6f} "
        f"trade_days={month_stats['trade_days']} turnover={month_stats['annualized_turnover']:.4f}x"
    )
    print(f"max |opt_in - research_path| = {np.max(np.abs((month_net - ref_net).to_numpy())):.3e}")
    print(
        f"simulation 'M' branch: {int(is_month_end.sum())}/{len(close.index)} sessions fire, "
        f"{len(months_without_rebalance)}/{len(month_keys)} months never rebalance"
    )
    print(
        f"incumbent default path: sharpe={inc_sharpe!r} max_dd={inc_dd!r} psr={inc_psr!r} "
        f"decision=NO-GO failed={INCUMBENT_FAILED_GATES}"
    )
    if failed:
        print(f"FAILED CHECKS: {failed}", file=sys.stderr)
        return 1
    return 0


def build_report(**kw: Any) -> str:
    """Render the cycle report (deterministic: no timestamps)."""
    checks = kw["checks"]
    overall = kw["overall"]
    src_hashes = kw["src_hashes"]

    check_rows = "\n".join(
        f"| `{c['check']}` | {'PASS' if c['pass'] else 'FAIL'} | {c['detail']} |" for c in checks
    )
    daily = kw["daily_stats"]
    month = kw["month_stats"]
    ref = kw["ref_stats"]
    sim_m = kw["sim_m_stats"]

    return f"""# Month-End Rebalance Schedule in Shared Code (rebalance_schedule_001, Cycle 870)

## Summary

Two defects in the repository's shared engines were measured in Cycle 869 and are addressed
here with **one** implementation of the month-end schedule
(`src/backtest/rebalance.py`), exposed by an **opt-in** parameter on the backtest engine
(`run_backtest(..., rebalance_schedule="month_end")`).

* Defect 1 (fixed): `src/backtest/engine.py:run_backtest` accepted a `rebalance_freq` argument and
  never used it -- the universe was re-ranked **every session**. The engine therefore never
  executed the frozen month-end schedule of `config/sectorrotation_candidate_001.yaml`,
  `config/csmomentum_candidate_001.yaml` or `config/macroregime_candidate_001.yaml`.
* Defect 2 (**measured only, behaviour unchanged**): `src/simulation/engine.py:_apply_rebalance_schedule`
  ("M") uses the **calendar** `index.is_month_end` on a *trading* calendar.

No gate threshold, candidate configuration, cost model, universe, Sharpe convention or committed
artifact was changed. The default behaviour of `run_backtest` and the live paper-trading path are
unchanged: the incumbent's code-level decision stays **NO-GO** with the committed numbers.

## The shared definition (one implementation)

`src/backtest/rebalance.py` is the single source of truth for the month-end schedule:

1. the **month-end session** of a calendar month is the *last session of the session calendar* in
   that month (the aligned price index; it contains trading sessions only). A month whose last
   calendar day is a weekend rebalances on the **Friday** session, and a month whose last calendar
   day is a market holiday rebalances on the last session that actually happened;
2. the signal is formed **on** that session, so the positions become effective on the **next**
   session (`signal_lag_days: 1`) and are held unchanged until the next month-end signal;
3. a month whose signal is not defined (momentum warm-up) opens **no** position: positions are
   never back-filled and no position exists before the first valid signal.

The engine parameter is opt-in: `rebalance_schedule=None` (default) or `"daily"` keeps the
historical daily re-ranking; `"month_end"` (aliases: `"monthly"`, `"m"`) selects the schedule
above. An unknown schedule is a hard error (no silent fallback).

## Before / after on the frozen candidate's universe

Universe: {", ".join(kw["universe"])}; sample {kw["start_s"]} .. {kw["end_s"]}
({kw["n_sessions"]} sessions); signal lookback {kw["lookback"]}, skip {kw["skip"]},
top_fraction {kw["top_fraction"]}; cost {kw["cost_per_trade"] * 10000:.1f} bps round-trip.

| Path | Trade days | Annualized turnover | Canonical Sharpe | Max DD | Total return |
|---|---|---|---|---|---|
| A. default engine (daily re-rank, the defect) | {daily["trade_days"]} | {daily["annualized_turnover"]:.4f}x | {daily["sharpe_canonical"]:.6f} | {daily["max_drawdown"]:.4%} | {daily["total_return"]:.4%} |
| B. opt-in `rebalance_schedule="month_end"` (the fix) | {month["trade_days"]} | {month["annualized_turnover"]:.4f}x | {month["sharpe_canonical"]:.6f} | {month["max_drawdown"]:.4%} | {month["total_return"]:.4%} |
| C. independent research path (reference) | {ref["trade_days"]} | {ref["annualized_turnover"]:.4f}x | {ref["sharpe_canonical"]:.6f} | {ref["max_drawdown"]:.4%} | {ref["total_return"]:.4%} |

The opt-in path reduces the rebalancing frequency by ~{daily["trade_days"] / max(month["trade_days"], 1):.1f}x
({daily["trade_days"]} -> {month["trade_days"]} trade days) and the annualized turnover from
{daily["annualized_turnover"]:.4f}x to {month["annualized_turnover"]:.4f}x, with an essentially
unchanged Sharpe ({daily["sharpe_canonical"]:.6f} -> {month["sharpe_canonical"]:.6f}): the defect was
a *cost and turnover* defect, not a return defect.

**Equivalence evidence:** `max |net_return(opt-in) - net_return(research path)| =
{kw["max_net_diff"]:.3e}` (tolerance 1e-12) over {kw["n_sessions"]} sessions, and the two weight
matrices are bit-identical. The research path
(`research/sectorrotation_long_sample_feasibility.py`) now delegates its month-end construction to
the shared module, so there is a single implementation rather than two that have to be kept in sync.

**Rebalance calendar actually used:** {kw["n_segments"]} month-end rebalances; the first signal is
formed on {kw["first_signal"].date()} and becomes effective on {kw["first_effective"].date()}; the
last is formed on {kw["last_signal"].date()} and effective on {kw["last_effective"].date()}.

## The simulation engine's "M" branch: measured, deliberately unchanged

`src/simulation/engine.py:_apply_rebalance_schedule` keeps the target weights only on the rows where
`index.is_month_end` is True and forward-fills the rest. `is_month_end` is a **calendar** predicate,
so on a trading calendar it fires only when the last *calendar* day of the month is itself a
trading session.

Measured on the same universe and sample:

* it fires on **{kw["n_is_month_end"]} of {kw["n_sessions"]} sessions**;
* **{kw["months_with_rebalance"]} of {kw["n_months"]} months** contain such a session -- in those
  months the rebalance happens on the month's last session, but on the *previous* session's signal
  (no extra lag), i.e. one session earlier than the shared schedule;
* in the remaining **{kw["months_without_rebalance"]} months ({kw["months_without_rebalance"] / kw["n_months"]:.1%})**
  there is no such session at all (the last calendar day was a weekend or a market holiday), so the
  branch carries the **previous month's weights through the whole month**;
* applied to the same lagged daily signal weights, it differs from the shared implementation on
  **{kw["n_sessions_differing"]} of {kw["n_sessions"]} sessions** (max row-wise weight difference
  {kw["max_weight_diff"]:.4f}), and it produces {sim_m["trade_days"]} trade days /
  {sim_m["annualized_turnover"]:.4f}x turnover / Sharpe {sim_m["sharpe_canonical"]:.6f}
  (shared: {month["trade_days"]} / {month["annualized_turnover"]:.4f}x /
  {month["sharpe_canonical"]:.6f});
* the two schedules change the portfolio on **{kw["coincident_change_sessions"]} common sessions**
  ({kw["sim_m_change_sessions"]} "M"-branch sessions vs {kw["shared_change_sessions"]} shared-schedule
  sessions): the "M" branch rebalances **one session earlier** -- on the month's last session itself,
  using the previous session's signal -- while the shared schedule forms the signal on the month's
  last session and applies it from the next one. The two calendars therefore never rebalance on the
  same session.

**This branch was left behaviourally unchanged.** Its live path is `"daily"`
(`config/simulation_candidate_001.yaml`: `execution.rebalance_schedule: "daily"`), so no paper-trading
artifact can move; the difference above is the measured size of the defect should the branch ever be
selected. Adopting the shared implementation there is a separate, explicitly scoped change.

## The incumbent path is untouched

`run_backtest` was called with its default arguments on the incumbent's universe
({kw["inc_start"]} .. {kw["inc_end"]}, {kw["inc_sessions"]} sessions): canonical Sharpe
{kw["inc_sharpe"]!r} (committed {INCUMBENT_SHARPE!r}), max drawdown {kw["inc_dd"]!r} (committed
{INCUMBENT_MAX_DD!r}), PSR {kw["inc_psr"]!r} (committed {INCUMBENT_PSR!r}). The code-level decision
stays **NO-GO** with failed gates `{INCUMBENT_FAILED_GATES}`.

## Falsification conditions

This cycle's conclusions are wrong if any of the following holds:

1. the opt-in engine path does not reproduce the config-faithful research path to 1e-12
   (it does: {kw["max_net_diff"]:.3e});
2. the default path of `run_backtest` changes any incumbent number (it does not: the three values
   above are bit-identical to the committed ones);
3. a month-end session is not a session of the aligned price calendar, or a signal is not effective
   from the session after its month-end session;
4. a position exists before the first valid signal;
5. the raw cache or any committed artifact under `config/`, `data/` or
   `research/reports/promotion_feasibility_backtest_001.md` changes.

## Checks

| Check | Result | Detail |
|---|---|---|
{check_rows}

## Reproduction

```bash
python research/rebalance_schedule_audit.py     # this report; OVERALL: {overall}
python research/sectorrotation_long_sample_feasibility.py
python research/promotion_feasibility_backtest.py
python -m pytest -q
git status --porcelain data/                    # empty
```

## Provenance

- Data: committed raw cache `data/raw/*.parquet` (read-only; SHA-256 byte-identical before and
  after the run).
- Source files that define the schedule (SHA-256):
{chr(10).join(f"  - `{k}`: `{v}`" for k, v in src_hashes.items())}
- Gate thresholds, candidate configurations, cost model and Sharpe convention: unchanged.
"""


if __name__ == "__main__":
    sys.exit(main())
