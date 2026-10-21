#!/usr/bin/env python3
"""Cycle 934 -- evidence-based candidate shortlist for the next structurally distinct edge.

What this tool does
-------------------
The repository's committed opportunity shortlist (``research/reports/opportunity_shortlist.md``,
Cycle 11, ten rows) is **exhausted**: every one of its rows carries a committed
outcome record, and no row is left as an untested, unblocked, structurally
distinct opportunity.  This cycle therefore does **not** re-score that list.
It builds a **new** shortlist from what the repository actually holds:

1. it **re-measures** the data and the cost model that are really available
   (the committed parquet cache and the committed configuration), so that
   every score below rests on a measured quantity or an explicitly declared
   prior -- never on an assumed data set;
2. it reads the **committed outcome record of every earlier candidate line**
   and quotes its status line verbatim, so that a closed line is not reopened
   and an open one is not mislabelled;
3. it scores **four structurally distinct** candidate mechanisms on the seven
   AGENTS.md "Market Opportunity Search" dimensions, with the measured
   inputs of every rule-based score printed next to the score; and
4. it applies one declared selection rule and publishes the winner together
   with a complete hypothesis-first skeleton (mechanism, holding horizon,
   universe, benchmark, confounders, falsification condition, cost model) for
   the next cycle to pre-register.

Scope
-----
This is a **measurement and documentation** cycle.  It runs **no backtest**,
searches **no parameter**, implements **no candidate**, writes **nothing**
under ``data/`` or ``config/``, calls the fetcher **never**, and modifies **no**
committed record, gate, protocol or shortlist row.  The two files it writes are
its own report and its own experiment record.

How the scores are produced
----------------------------
Each of the seven dimensions is scored 1-5 (1 = poor/infeasible, 5 =
excellent/feasible), following the repository's own scoring legend.  A score is
either

* **rule-based** -- a threshold over a quantity this tool measures from the
  committed cache (``(a)``, ``(d)``, ``(e)``, ``(g)`` and the *hurdle* half of
  ``(c)``), or
* **a declared prior** -- a judgement that the repository cannot measure
  without implementing the candidate (``(b)`` and the *gross* half of
  ``(c)``), labelled as such in the published tables.

``(c)`` is deliberately published as **two** numbers: the measured *cost
hurdle* (how much of the measured gross scale the rule must capture to pay
its own costs under the repository's cost model) and the declared *gross
prior* (how much gross the mechanism is expected to deliver).  The published
``(c)`` score is the **minimum** of the two: a cheap mechanism with no
expected gross is not a good candidate, and an expensive mechanism with a large
expected gross is not either.

Reproduction
------------
```bash
python research/candidate_shortlist_934.py
python -m pytest -q tests/test_candidate_shortlist_934.py
git status --porcelain data/ config/
```
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.data_cost_inventory_002 import (  # noqa: E402
    fingerprint,
    tracked_artifact_hashes,
)
from research.futures_roll_visibility import (  # noqa: E402
    detect_roll_events,
    volume_ratio,
)
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402

CYCLE = "934"

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "candidate_shortlist_934.md"
OUT_EXP = EXPERIMENTS_DIR / "candidate_shortlist_934.md"

SELF_OUTPUTS = {
    str(OUT_REPORT.relative_to(REPO_ROOT)),
    str(OUT_EXP.relative_to(REPO_ROOT)),
}

#: The nine GICS sector ETFs.  All nine carry the same cached history
#: (1998-12-22 .. 2026-10-08, 6991 sessions, no gaps), which makes this the
#: only constant-membership cross-section in the repository.
SECTOR_UNIVERSE = [
    "XLB",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLU",
    "XLV",
    "XLY",
]

#: The incumbent's seven-asset universe (used only as a reference point).
INCUMBENT_UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]


class ShortlistError(RuntimeError):
    """Raised when a required input is missing or malformed (fails closed)."""


def fail(message: str) -> None:
    raise ShortlistError(message)


# ======================================================================
# Declared candidate catalogue
# ======================================================================
# Every candidate declares ONE baseline rule.  No candidate carries a
# parameter grid: the grid count of each candidate is one, and the tool
# asserts it.
CANDIDATES: list[dict[str, Any]] = [
    {
        "id": "reversal_001",
        "name": "Cross-sectional short-horizon reversal (weekly, long-only laggard tilt)",
        "family": "short-horizon reversal (liquidity-provision compensation)",
        "mechanism": (
            "An asset that has fallen over the past week tends to revert over the "
            "following weeks. The move is driven by non-informational, "
            "liquidity-demanding order flow; the seller who provides liquidity is "
            "compensated by the subsequent reversal, and short-sale and "
            "rebalancing constraints make temporary price pressure persistent. "
            "The effect is the mirror image of the momentum family the repository "
            "has already tested, over a horizon one order of magnitude shorter "
            "(5 sessions against 226+21)."
        ),
        "universe": list(SECTOR_UNIVERSE),
        "horizon_sessions": 5,
        "rebalances_per_year": 52,
        "benchmark": (
            "1/N equal-weight buy-and-hold of the same nine sector ETFs over the "
            "same window (the same benchmark the committed cross-sectional "
            "candidates use)."
        ),
        "baseline_rule": (
            "Rank the nine sector ETFs by the trailing 5-session total return; "
            "hold the bottom quintile (2 of 9) at equal weight and cash "
            "otherwise; rebalance every 5th session; the signal formed at t is "
            "effective at t+1 (one-session lag)."
        ),
        "ceiling_kind": "cross_sectional_dispersion",
        "gross_prior": 3,
        "gross_prior_rationale": (
            "Short-horizon reversal is a documented effect, but its modern "
            "magnitude is contested and it has not been measured in this "
            "repository; a modest but plausible gross is assumed, not a large one."
        ),
        "mechanism_prior": 4,
        "mechanism_rationale": (
            "The mechanism (compensation for supplying liquidity to "
            "non-informational order flow) is structural and documented; it is "
            "not rated 5 because the effect is heavily arbitraged in liquid ETFs "
            "and its published magnitude has decayed."
        ),
        "needs_short_leg": False,
        "needs_roll_handling": False,
        "missing_execution_input": None,
        "multi_bet": False,
        "confounders": [
            "Momentum-crash risk: the book is long the laggards, so a sharp "
            "rally in the recent winners is a direct loss.",
            "The nine ETFs are all US equity sectors: the rule is a short-beta "
            "tilt against the 1/N benchmark in a risk-on market, so the "
            "benchmark-relative result, not the absolute return, is the "
            "relevant statistic.",
            "The sector panel ends 2026-10-08, eight sessions behind the rest "
            "of the committed cache.",
            "Constituent-level (GICS) membership history is not in the "
            "repository: the sector ETFs' underlying composition changed over "
            "the sample and cannot be reconstructed.",
            "ETF expense ratios are embedded in the observed (adjusted) prices "
            "and are not modelled separately.",
            "The turnover estimate of one book rotation per rebalance follows "
            "the repository's committed cost-screen convention and is an upper "
            "bound; a partial rotation turns over less.",
        ],
        "falsification": (
            "Falsified if ANY of: (i) the walk-forward mean OOS Sharpe (net, "
            "canonical convention) < 0.9; (ii) the benchmark-relative net "
            "excess has a moving-block bootstrap 95% CI that includes zero; "
            "(iii) the benchmark-relative net excess is not positive in the "
            "post-2009 sub-sample; (iv) the measured gross capture fraction "
            "falls below the pre-registered cost hurdle; (v) the positive-fold "
            "rate < 0.5 or the pooled OOS trades <= 100."
        ),
    },
    {
        "id": "pairs_001",
        "name": "Cointegrated-pairs relative value (market-neutral dispersion convergence)",
        "family": "statistical arbitrage / spread convergence",
        "mechanism": (
            "Two securities that share a common driver trade with a temporary "
            "dispersion around their long-run relationship; the dispersion "
            "reverts, and a market-neutral book (long the cheap leg, short the "
            "rich leg) earns the convergence without the common factor."
        ),
        "universe": list(SECTOR_UNIVERSE),
        "pairs": [
            ("XLP", "XLU"),
            ("XLF", "XLK"),
            ("XLE", "XLB"),
            ("XLI", "XLB"),
            ("XLV", "XLY"),
            ("XLK", "XLU"),
        ],
        "horizon_sessions": 5,
        "rebalances_per_year": 52,
        "benchmark": "Cash (a market-neutral book; the repository's 2% risk-free rate is the hurdle).",
        "baseline_rule": (
            "For each of the six pre-registered pairs, z-score the log price "
            "ratio over the trailing 126 sessions and take the contrarian side "
            "when |z| >= 1; dollar-neutral per pair; rebalance every 5th "
            "session; the signal formed at t is effective at t+1."
        ),
        "ceiling_kind": "pair_spread",
        "gross_prior": 3,
        "gross_prior_rationale": (
            "Spread convergence is documented and structural, but the pairs are "
            "all US equity sectors, so the spread is thin and the effect small; "
            "no measurement exists in this repository."
        ),
        "mechanism_prior": 4,
        "mechanism_rationale": (
            "Cointegration-driven convergence is a structural mechanism with a "
            "clear economic story (common driver, temporary liquidity-driven "
            "dispersion)."
        ),
        "needs_short_leg": True,
        "needs_roll_handling": False,
        "missing_execution_input": (
            "borrow cost / short availability: no borrow or short-side cost "
            "exists anywhere in config/ or data/"
        ),
        "multi_bet": True,
        "confounders": [
            "Short-sale constraints and recall risk are not modelled: the "
            "repository has no borrow cost at all.",
            "Pair-selection multiplicity: six pairs are pre-registered, and "
            "the spread correlations are high, so the six bets are far from "
            "independent.",
            "Structural breaks in the long-run relationship (a pair that stops "
            "being cointegrated) turn a convergence trade into a value trap.",
            "The market-neutral construction must be funded and pays the "
            "repository's 2% risk-free rate, which the canonical Sharpe "
            "convention does not net.",
        ],
        "falsification": (
            "Falsified if ANY of: (i) the walk-forward mean OOS Sharpe < 0.9; "
            "(ii) the net excess over cash has a moving-block bootstrap 95% CI "
            "that includes zero after deflating for the six pairs tested; "
            "(iii) the cointegration of any pair fails out of sample; (iv) the "
            "net excess does not survive a borrow cost of 25 bp per unit of "
            "short notional per rebalance."
        ),
    },
    {
        "id": "liquidity_001",
        "name": "Liquidity-provision premium (Amihud illiquidity tilt, long-only)",
        "family": "liquidity provision / illiquidity premium",
        "mechanism": (
            "Assets whose price moves more per unit of traded volume earn a "
            "premium, because the liquidity provider is compensated for the "
            "risk of adverse selection; the premium is realised as the "
            "illiquid asset's price drifts back toward its fundamental value."
        ),
        "universe": list(SECTOR_UNIVERSE),
        "horizon_sessions": 21,
        "rebalances_per_year": 24,
        "benchmark": (
            "1/N equal-weight buy-and-hold of the same nine sector ETFs over the "
            "same window."
        ),
        "baseline_rule": (
            "Score each sector ETF by the Amihud measure |21-session return| / "
            "dollar volume over the trailing 21 sessions; hold the most illiquid "
            "quintile (2 of 9) at equal weight and cash otherwise; rebalance "
            "monthly; the signal formed at t is effective at t+1."
        ),
        "ceiling_kind": "cross_sectional_dispersion",
        "gross_prior": 2,
        "gross_prior_rationale": (
            "The illiquidity premium is documented for genuinely illiquid "
            "assets, not for nine mega-liquid sector ETFs whose measured score "
            "dispersion is small; the expected gross here is assumed to be tiny "
            "relative to a 3 bp/unit cost model."
        ),
        "mechanism_prior": 3,
        "mechanism_rationale": (
            "The mechanism is structural and well documented, but it is a "
            "premium of illiquidity, and the candidate's universe is the most "
            "liquid corner of the market: the mechanism is weak by construction "
            "here."
        ),
        "needs_short_leg": False,
        "needs_roll_handling": False,
        "missing_execution_input": None,
        "multi_bet": False,
        "confounders": [
            "The Amihud score is dominated by the volume denominator, so the "
            "ranking partly re-ranks the volume of the ETF wrappers, not the "
            "liquidity of the underlying sector.",
            "Volume-based scores are sensitive to the volume spike that follows "
            "a large price move, which mechanically inverts the signal.",
            "ETF volume is venue-fragmented and the cached volume is a "
            "consolidated daily figure.",
            "Sector ETF expense ratios and index-tracking differences are "
            "embedded in the observed prices.",
        ],
        "falsification": (
            "Falsified if ANY of: (i) the walk-forward mean OOS Sharpe < 0.9; "
            "(ii) the benchmark-relative net excess has a moving-block "
            "bootstrap 95% CI that includes zero; (iii) the measured cross-"
            "sectional dispersion of the Amihud score is too small to support "
            "a tilt that covers the 3 bp/unit cost model (the mechanism does "
            "not reach the hurdle); (iv) the net excess is not positive in the "
            "post-2009 sub-sample."
        ),
    },
    {
        "id": "leadlag_001",
        "name": "Futures-to-ETF delayed price discovery (next-session lead-lag)",
        "family": "delayed price discovery / cross-instrument lead-lag",
        "mechanism": (
            "The futures market is deeper and is quoted with a settlement "
            "convention that differs from the ETF's closing auction; information "
            "that reaches the futures close is only partly incorporated into the "
            "ETF close, so part of the futures move is realised in the ETF on "
            "the next session."
        ),
        "universe": ["CL-F", "GC-F", "NG-F", "ZB-F", "USO", "BNO", "UNG", "GSG", "GLD", "TLT"],
        "pairs": [
            ("CL-F", "USO"),
            ("CL-F", "BNO"),
            ("GC-F", "GLD"),
            ("NG-F", "UNG"),
            ("ZB-F", "TLT"),
        ],
        "horizon_sessions": 5,
        "rebalances_per_year": 52,
        "benchmark": "Cash (the rule is a directional tilt on the ETF leg only).",
        "baseline_rule": (
            "For each of the five pre-registered futures-to-ETF pairs, take the "
            "sign of the futures contract's trailing 5-session return as the "
            "signal for the ETF leg; long the ETF when the signal is positive "
            "and hold cash otherwise; rebalance every 5th session; the signal "
            "formed at t is effective at t+1."
        ),
        "ceiling_kind": "etf_volatility",
        "gross_prior": 2,
        "gross_prior_rationale": (
            "Delayed price discovery is documented for futures against the "
            "underlying, but at a daily horizon and with a rolled, unobservable-"
            "price futures series the testable form is weak; the expected gross "
            "is assumed to be small."
        ),
        "mechanism_prior": 3,
        "mechanism_rationale": (
            "The mechanism is one AGENTS.md names explicitly (delayed price "
            "discovery), but the daily-bar cache cannot time the intraday "
            "sequencing that the mechanism depends on."
        ),
        "needs_short_leg": False,
        "needs_roll_handling": True,
        "missing_execution_input": (
            "roll price / roll cost: the cached front-month series exposes the "
            "roll date but not the roll price, so the futures return series is "
            "contaminated at every roll"
        ),
        "multi_bet": True,
        "confounders": [
            "The cached front-month futures series is a continuous series whose "
            "roll price is unobservable: the return series is contaminated at "
            "every roll event, so roll windows must be excluded, which removes "
            "part of the sample.",
            "The committed roll detector classifies a session using up to eight "
            "forward sessions and four subsequent volume ratios, so the roll "
            "dates are an EX-POST detection: they can be used to clean a "
            "backtest but are not a tradable point-in-time signal, and any "
            "live rule would have to detect the roll with the same lag.",
            "CL-F carries a non-positive close inside the sample (the front "
            "month went negative in 2020), which breaks any return computation "
            "that spans it.",
            "The futures and the ETF legs have different trading calendars, so "
            "the paired panel is only complete on the sessions both markets "
            "opened.",
            "The daily bar cannot establish the intraday ordering between the "
            "futures settlement and the ETF close, so the 'lead' is only "
            "testable in its weaker next-session form.",
            "The four futures are four different factor exposures (oil, gas, "
            "gold, rates), so the five pairs are not independent bets.",
        ],
        "falsification": (
            "Falsified if ANY of: (i) the walk-forward mean OOS Sharpe < 0.9; "
            "(ii) the net excess over cash has a moving-block bootstrap 95% CI "
            "that includes zero after deflating for the five pairs tested; "
            "(iii) the excess disappears once the detected roll windows are "
            "excluded, which would show the effect is a roll artefact; (iv) the "
            "excess is carried by the CL-F window, whose non-positive close "
            "makes the sample unusable."
        ),
    },
]


# ======================================================================
# Committed outcome records of the earlier candidate lines
# ======================================================================
# Each entry quotes the committed record and the status line it carries.  The
# tool verifies that the quoted text is still present in the committed file,
# so the table cannot drift from the repository.
PRIOR_LINES: list[dict[str, Any]] = [
    {
        "id": "tsmomentum_spytrend_001 (incumbent)",
        "record": "research/experiments/tsmomentum_regime_filter_wf_001.md",
        "status_quote": "## **Credible Candidate**",
        "status_class": "incumbent (Credible Candidate; NO-GO for promotion)",
    },
    {
        "id": "riskparity_001",
        "record": "research/experiments/riskparity_001_evaluation.md",
        "status_quote": "**Decision: REJECT (negative result).**",
        "status_class": "Rejected/Failed",
    },
    {
        "id": "csmomentum_001",
        "record": "research/experiments/csmomentum_plateau_gate_eval_001.md",
        "status_quote": "- Research label: **Rejected/Failed**",
        "status_class": "Rejected/Failed",
    },
    {
        "id": "sectorrotation_001 / sectorrotation_002",
        "record": "research/experiments/sectorrotation_002_experiment_001.md",
        "status_quote": "hypothesis FALSIFIED (Rejected/Failed)",
        "status_class": "Rejected/Failed",
    },
    {
        "id": "calendar_effects_001",
        "record": "research/experiments/calendar_effects_baseline_wf_001.md",
        "status_quote": "**FINAL VERDICT:** Rejected/Failed",
        "status_class": "Rejected/Failed",
    },
    {
        "id": "overnight_capture_001",
        "record": "research/experiments/overnight_capture_backtest_001.md",
        "status_quote": "**Rejected/Failed.**",
        "status_class": "Rejected/Failed",
    },
    {
        "id": "macroregime_001",
        "record": "research/experiments/macroregime_001_experiment_002.md",
        "status_quote": "hypothesis FALSIFIED (Rejected/Failed)",
        "status_class": "Rejected/Failed",
    },
    {
        "id": "cryptofunding_001",
        "record": "research/experiments/cryptofunding_002_evaluation.md",
        "status_quote": "**Exploratory signal — not promoted.**",
        "status_class": "Exploratory signal (not promoted)",
    },
    {
        "id": "futuresbasis_001",
        "record": "research/experiments/futuresbasis_001.md",
        "status_quote": "**Blocked by data/infrastructure** (roll-price block)",
        "status_class": "Blocked by data/infrastructure",
    },
    {
        "id": "futuresbasis_002",
        "record": "research/experiments/futuresbasis_002.md",
        "status_quote": "Verdict: Rejected/Failed on cost (and signal sign).",
        "status_class": "Rejected/Failed",
    },
    {
        "id": "mom121_microcap_001",
        "record": "research/experiments/mom121_microcap_001.md",
        "status_quote": "**Status:** **Blocked by data/infrastructure** — data gate failed",
        "status_class": "Blocked by data/infrastructure",
    },
]


#: The universe each closed line used.  The tool verifies that every symbol
#: really occurs in the cited committed file, so the overlap count cannot
#: drift from the repository.
PRIOR_UNIVERSES: list[dict[str, Any]] = [
    {
        "id": "tsmomentum_001",
        "file": "research/hypotheses/tsmomentum_001.md",
        "symbols": list(INCUMBENT_UNIVERSE),
    },
    {
        "id": "riskparity_001",
        "file": "research/hypotheses/riskparity_001.md",
        "symbols": list(INCUMBENT_UNIVERSE),
    },
    {
        "id": "csmomentum_001",
        "file": "config/csmomentum_candidate_001.yaml",
        "symbols": [
            "SPY", "QQQ", "IWM", "TLT", "GLD", "DBC", "VNQ", "EFA", "EEM",
            "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
        ],
    },
    {
        "id": "sectorrotation_001",
        "file": "research/hypotheses/sectorrotation_001.md",
        "symbols": list(SECTOR_UNIVERSE),
    },
    {
        "id": "sectorrotation_002",
        "file": "research/hypotheses/sectorrotation_002.md",
        "symbols": list(SECTOR_UNIVERSE),
    },
    {
        "id": "calendar_effects_001",
        "file": "research/hypotheses/calendar_effects_001.md",
        "symbols": ["SPY", "QQQ", "IWM"],
    },
    {
        "id": "overnight_capture_001",
        "file": "research/hypotheses/overnight_capture_001.md",
        "symbols": ["SPY", "QQQ", "IWM"],
    },
    {
        "id": "macroregime_001",
        "file": "research/hypotheses/macroregime_001.md",
        "symbols": list(INCUMBENT_UNIVERSE) + ["^VIX"],
    },
    {
        "id": "cryptofunding_001",
        "file": "research/hypotheses/cryptofunding_001.md",
        "symbols": ["BTC/USDT", "ETH/USDT"],
    },
    {
        "id": "futuresbasis_001",
        "file": "research/hypotheses/futuresbasis_001.md",
        "symbols": ["CL=F", "NG=F", "GC=F", "ZB=F"],
    },
    {
        "id": "futuresbasis_002",
        "file": "research/hypotheses/futuresbasis_002.md",
        "symbols": ["USO", "BNO", "UNG", "GSG", "GLD"],
    },
    {
        "id": "mom121_microcap_001",
        "file": "research/hypotheses/mom121_microcap_001.md",
        "symbols": ["IWM"],
    },
]

#: The mechanism families that are already closed in this repository.  A new
#: candidate may not belong to one of them.
CLOSED_FAMILIES = {
    "time-series momentum",
    "cross-sectional momentum",
    "sector rotation",
    "risk parity",
    "calendar / rebalancing effects",
    "overnight session capture",
    "macro regime overlay",
    "crypto perpetual funding carry",
    "commodity futures roll carry",
    "microcap momentum",
}

#: The friction components that the repository's cost model does **not**
#: contain (the committed inventory's own finding).
FRICTION_KEYS = [
    "bid_ask_spread",
    "borrow",
    "roll",
    "market_impact",
    "latency",
    "margin",
]

#: The repository's committed cost-screen convention: one full book rotation
#: per rebalance costs one unit of turnover.  The committed numbers this
#: convention reproduces (research/reports/opportunity_shortlist.md) are
#: calendar_effects_001 at 24.13 units/yr for 24 rebalances/yr and the
#: overnight-capture line at 504.00 units/yr for 504 sessions/yr.
TURNOVER_UNITS_PER_REBALANCE = 1.0


# ======================================================================
# Measurement helpers
# ======================================================================
def load_symbol(symbol: str) -> pd.DataFrame:
    path = RAW_DIR / f"{symbol}.parquet"
    if not path.exists():
        fail(f"missing cached series: data/raw/{symbol}.parquet")
    frame = pd.read_parquet(path)
    for column in ("Close", "Volume"):
        if column not in frame.columns:
            fail(f"{symbol}: the cached frame has no {column} column")
    return frame


def symbol_facts(symbol: str) -> dict[str, Any]:
    frame = load_symbol(symbol)
    close = frame["Close"].astype(float)
    volume = frame["Volume"].astype(float)
    dollar_volume = (close * volume).replace([np.inf, -np.inf], np.nan).dropna()
    return {
        "symbol": symbol,
        "rows": int(len(frame)),
        "first": str(frame.index.min().date()),
        "last": str(frame.index.max().date()),
        "missing_close": int(close.isna().sum()),
        "duplicate_timestamps": int(frame.index.duplicated().sum()),
        "non_positive_close": int((close <= 0).sum()),
        "zero_volume_rows": int((volume == 0).sum()),
        "median_dollar_volume": float(dollar_volume.median()),
        "p10_dollar_volume": float(dollar_volume.quantile(0.10)),
    }


def close_and_volume(symbols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    closes: dict[str, pd.Series] = {}
    volumes: dict[str, pd.Series] = {}
    for symbol in symbols:
        frame = load_symbol(symbol)
        closes[symbol] = frame["Close"].astype(float)
        volumes[symbol] = frame["Volume"].astype(float)
    return pd.DataFrame(closes), pd.DataFrame(volumes)


def cross_sectional_dispersion(close: pd.DataFrame, horizon: int) -> float:
    """Median cross-sectional dispersion of the *horizon* return.

    The dispersion is the standard deviation, across the cross-section, of the
    horizon-session return on each date.  It is the scale of the relative
    differences a ranking rule can exploit; it is a *scale*, not a forecast of
    the return the rule will earn.
    """
    returns = close.pct_change(horizon)
    dispersion = returns.std(axis=1, ddof=1)
    return float(dispersion.median())


def pair_spread_scale(close: pd.DataFrame, pairs: list[tuple[str, str]], horizon: int) -> float:
    """Median absolute change of the log price ratio of the declared pairs."""
    changes = []
    for left, right in pairs:
        spread = np.log(close[left]) - np.log(close[right])
        changes.append(spread.diff(horizon).abs())
    frame = pd.concat(changes, axis=1)
    return float(frame.stack().median())


def etf_volatility_scale(close: pd.DataFrame) -> float:
    """Median annualised volatility of the traded ETF legs."""
    daily = close.pct_change()
    annual = daily.std(axis=0, ddof=1) * np.sqrt(252.0)
    return float(annual.median())


def effective_independent_bets(returns: pd.DataFrame) -> float:
    """Effective number of independent bets from the correlation eigenvalues.

    ``n_eff = (sum(lambda))^2 / sum(lambda^2)`` over the eigenvalues of the
    correlation matrix of the bet returns.
    """
    corr = returns.corr().to_numpy(dtype=float)
    corr = np.nan_to_num(corr, nan=0.0)
    eigenvalues = np.clip(np.linalg.eigvalsh(corr), 0.0, None)
    denominator = float((eigenvalues**2).sum())
    if denominator <= 0:
        return 0.0
    return float((eigenvalues.sum() ** 2) / denominator)


def complete_panel(close: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """The point-in-time-complete panel and the share of incomplete sessions.

    The complete panel keeps only the sessions on which **every** instrument of
    the candidate carries a price. The second return value is the share of the
    union calendar that the complete panel does not cover -- the membership
    churn, which is 0 for the nine sector ETFs (identical calendars) and
    positive for a futures/ETF candidate (the two calendars differ).
    """
    union_sessions = len(close)
    complete = close.dropna(how="any")
    if complete.empty:
        fail("the candidate's instruments share no session with a complete cross-section")
    churn = 0.0 if union_sessions == 0 else 1.0 - len(complete) / union_sessions
    return complete, float(churn)


def roll_event_counts(symbols: list[str]) -> dict[str, int]:
    """Detected roll events per front-month futures series."""
    out: dict[str, int] = {}
    for symbol in symbols:
        frame = load_symbol(symbol)
        ratio = volume_ratio(frame["Volume"].astype(float))
        events = detect_roll_events(ratio)
        out[symbol] = int(len(events))
    return out


# ======================================================================
# Scoring rules
# ======================================================================
def score_data_quality(candidate: dict[str, Any], facts: dict[str, dict[str, Any]],
                        churn: float) -> tuple[int, str]:
    years = facts[candidate["universe"][0]]["_years"]
    if years >= 20:
        base, base_text = 5, ">= 20 years"
    elif years >= 15:
        base, base_text = 4, ">= 15 years"
    elif years >= 10:
        base, base_text = 3, ">= 10 years"
    elif years >= 5:
        base, base_text = 2, ">= 5 years"
    else:
        base, base_text = 1, "< 5 years"
    score = base
    notes = [f"coverage {years:.1f}y ({base_text})"]
    if churn > 0:
        score -= 1
        notes.append(f"-1: cross-section is not constant ({churn:.1%} of sessions)")
    defects = sum(
        facts[s]["missing_close"] + facts[s]["duplicate_timestamps"] + facts[s]["non_positive_close"]
        for s in candidate["universe"]
    )
    if defects:
        score -= 1
        notes.append(f"-1: {defects} integrity defect rows in the required series")
    if candidate["missing_execution_input"]:
        score -= 1
        notes.append(f"-1: required execution input absent ({candidate['missing_execution_input']})")
    return max(1, min(5, score)), "; ".join(notes)


def score_robustness(candidate: dict[str, Any], observations: int,
                     n_eff: float | None) -> tuple[int, str]:
    if observations >= 1000:
        base, base_text = 5, ">= 1000"
    elif observations >= 500:
        base, base_text = 4, ">= 500"
    elif observations >= 250:
        base, base_text = 3, ">= 250"
    elif observations >= 100:
        base, base_text = 2, ">= 100"
    else:
        base, base_text = 1, "< 100"
    score = base
    notes = [f"{observations} non-overlapping holding-horizon observations ({base_text})"]
    if candidate["multi_bet"]:
        # A multi-bet candidate always has a measured value; a missing value
        # is an error, never a value that silently satisfies the threshold.
        if n_eff is None:
            fail("a multi-bet candidate has no measured effective-bet count")
        if n_eff < 3.0:
            score -= 1
            notes.append(f"-1: only {n_eff:.2f} effective independent bets")
        else:
            notes.append(f"{n_eff:.2f} effective independent bets")
    else:
        notes.append("effective-bet count not applicable (one book, one signal)")
    if len(candidate["universe"]) < 3:
        score -= 1
        notes.append("-1: fewer than three instruments to rank")
    return max(1, min(5, score)), "; ".join(notes)


def score_liquidity(candidate: dict[str, Any], facts: dict[str, dict[str, Any]],
                    traded: list[str]) -> tuple[int, str]:
    medians = sorted(facts[s]["median_dollar_volume"] for s in traded)
    representative = float(np.median(medians))
    if representative >= 1_000_000_000:
        base, base_text = 5, ">= $1bn/day"
    elif representative >= 250_000_000:
        base, base_text = 4, ">= $250m/day"
    elif representative >= 50_000_000:
        base, base_text = 3, ">= $50m/day"
    elif representative >= 10_000_000:
        base, base_text = 2, ">= $10m/day"
    else:
        base, base_text = 1, "< $10m/day"
    score = base
    notes = [f"median instrument ${representative:,.0f}/day ({base_text})"]
    if candidate["needs_short_leg"]:
        score -= 1
        notes.append("-1: short leg required; borrow availability is not observable in the cache")
    return max(1, min(5, score)), "; ".join(notes)


def score_automation(candidate: dict[str, Any]) -> tuple[int, str]:
    score = 5
    notes = ["daily bars, one venue, session hours"]
    if candidate["needs_short_leg"]:
        score -= 1
        notes.append("-1: short leg (borrow, locate, recall handling)")
    if candidate["needs_roll_handling"]:
        score -= 1
        notes.append("-1: front-month futures series (roll windows to detect and exclude)")
    if len(candidate["universe"]) > 9:
        score -= 1
        notes.append("-1: more than nine instruments to maintain")
    return max(1, min(5, score)), "; ".join(notes)


def score_diversification(candidate: dict[str, Any]) -> tuple[int, str]:
    symbols = set(candidate["universe"])
    overlapping = []
    for prior in PRIOR_UNIVERSES:
        if symbols & set(prior["symbols"]):
            overlapping.append(prior["id"])
    count = len(overlapping)
    if count == 0:
        exposure_score = 5
    elif count == 1:
        exposure_score = 4
    elif count == 2:
        exposure_score = 3
    elif count == 3:
        exposure_score = 2
    else:
        exposure_score = 1
    novelty_score = 5  # no committed candidate hypothesis implements this family
    score = min(novelty_score, exposure_score)
    notes = [
        f"mechanism-family novelty {novelty_score}/5 (no committed candidate hypothesis in this family)",
        f"instrument overlap with {count} closed line(s) -> exposure score {exposure_score}/5",
    ]
    if overlapping:
        notes.append("shared: " + ", ".join(overlapping))
    return score, "; ".join(notes)


def hurdle_score(capture_fraction: float) -> int:
    """Score the *cost hurdle*: the share of the measured gross scale the rule
    must capture to pay its own costs under the repository's cost model."""
    if capture_fraction <= 0.05:
        return 5
    if capture_fraction <= 0.10:
        return 4
    if capture_fraction <= 0.20:
        return 3
    if capture_fraction <= 0.40:
        return 2
    return 1


# ======================================================================
# The measurement pass
# ======================================================================
def measure_cost_model() -> dict[str, Any]:
    commission, slippage = get_cost_params()
    settings = (REPO_ROOT / "config" / "settings.yaml").read_text().lower()
    return {
        "commission_bps": commission * 10_000.0,
        "slippage_bps": slippage * 10_000.0,
        "round_trip_bps": (commission + slippage) * 10_000.0,
        "risk_free_annual": get_risk_free_rate(),
        "settings_has_commission": "commission" in settings,
        "settings_has_slippage": "slippage" in settings,
        "absent_frictions": [k for k in FRICTION_KEYS if k not in settings],
    }


def measure_candidate(candidate: dict[str, Any], cost_per_unit: float,
                      cost_model: dict[str, Any]) -> dict[str, Any]:
    universe = list(candidate["universe"])
    facts = {symbol: symbol_facts(symbol) for symbol in universe}
    close_all, _volume = close_and_volume(universe)
    close, churn = complete_panel(close_all)

    first = str(close.index.min().date())
    last = str(close.index.max().date())
    years = (
        pd.Timestamp(last).year - pd.Timestamp(first).year
        + (pd.Timestamp(last).dayofyear - pd.Timestamp(first).dayofyear) / 365.25
    )
    for symbol in universe:
        facts[symbol]["_years"] = years

    horizon = int(candidate["horizon_sessions"])
    rebalances = int(candidate["rebalances_per_year"])
    turnover_units = rebalances * TURNOVER_UNITS_PER_REBALANCE
    drag = turnover_units * cost_per_unit

    ceiling_kind = candidate["ceiling_kind"]
    if ceiling_kind == "cross_sectional_dispersion":
        per_rebalance = cross_sectional_dispersion(close, horizon)
        ceiling = per_rebalance * rebalances
        ceiling_text = (
            f"median cross-sectional dispersion of the {horizon}-session return "
            f"({per_rebalance:.4%}) x {rebalances} rebalances"
        )
    elif ceiling_kind == "pair_spread":
        per_rebalance = pair_spread_scale(close, candidate["pairs"], horizon)
        ceiling = per_rebalance * rebalances
        ceiling_text = (
            f"median |{horizon}-session change| of the declared pairs' log price "
            f"ratio ({per_rebalance:.4%}) x {rebalances} rebalances"
        )
    elif ceiling_kind == "etf_volatility":
        traded = [s for s in universe if not s.endswith("-F")]
        traded_close = close[traded]
        per_rebalance = etf_volatility_scale(traded_close) / rebalances
        ceiling = etf_volatility_scale(traded_close)
        ceiling_text = (
            f"median annualised volatility of the traded ETF legs ({ceiling:.4%})"
        )
    else:  # pragma: no cover - the catalogue declares no other kind
        fail(f"unknown ceiling kind: {ceiling_kind}")

    capture_fraction = drag / ceiling if ceiling > 0 else float("inf")
    hurdle = hurdle_score(capture_fraction)
    gross_prior = int(candidate["gross_prior"])
    cost_score = min(hurdle, gross_prior)

    sessions = int(len(close))
    observations = max(1, sessions // horizon)

    if candidate["multi_bet"]:
        if ceiling_kind == "pair_spread":
            bet_returns = pd.concat(
                [
                    (np.log(close[a]) - np.log(close[b])).diff(horizon)
                    for a, b in candidate["pairs"]
                ],
                axis=1,
            )
        else:
            traded = [s for s in universe if not s.endswith("-F")]
            bet_returns = close[traded].pct_change(horizon)
        n_eff = effective_independent_bets(bet_returns)
    else:
        n_eff = None

    traded_symbols = [s for s in universe if not s.endswith("-F")]
    a_score, a_notes = score_data_quality(candidate, facts, churn)
    b_score, b_notes = int(candidate["mechanism_prior"]), candidate["mechanism_rationale"]
    c_score = cost_score
    c_notes = (
        f"cost hurdle {capture_fraction:.4%} of the measured gross scale -> "
        f"hurdle {hurdle}/5; declared gross prior {gross_prior}/5; score = min = {cost_score}"
    )
    d_score, d_notes = score_robustness(candidate, observations, n_eff)
    e_score, e_notes = score_liquidity(candidate, facts, traded_symbols)
    f_score, f_notes = score_automation(candidate)
    g_score, g_notes = score_diversification(candidate)

    scores = {
        "a": a_score,
        "b": b_score,
        "c": c_score,
        "d": d_score,
        "e": e_score,
        "f": f_score,
        "g": g_score,
    }
    notes = {
        "a": a_notes,
        "b": b_notes,
        "c": c_notes,
        "d": d_notes,
        "e": e_notes,
        "f": f_notes,
        "g": g_notes,
    }
    return {
        "id": candidate["id"],
        "name": candidate["name"],
        "family": candidate["family"],
        "mechanism": candidate["mechanism"],
        "universe": universe,
        "data_files": [f"data/raw/{symbol}.parquet" for symbol in universe],
        "horizon_sessions": horizon,
        "rebalances_per_year": rebalances,
        "baseline_rule": candidate["baseline_rule"],
        "benchmark": candidate["benchmark"],
        "confounders": list(candidate["confounders"]),
        "falsification": candidate["falsification"],
        "gross_prior": gross_prior,
        "gross_prior_rationale": candidate["gross_prior_rationale"],
        "mechanism_prior": int(candidate["mechanism_prior"]),
        "mechanism_rationale": candidate["mechanism_rationale"],
        "needs_short_leg": bool(candidate["needs_short_leg"]),
        "needs_roll_handling": bool(candidate["needs_roll_handling"]),
        "multi_bet": bool(candidate["multi_bet"]),
        "missing_execution_input": candidate["missing_execution_input"],
        "scores": scores,
        "notes": notes,
        "total": int(sum(scores.values())),
        "measured": {
            "sessions": sessions,
            "first": first,
            "last": last,
            "years": round(years, 2),
            "membership_churn": churn,
            "turnover_units_per_year": turnover_units,
            "annual_cost_drag": drag,
            "gross_ceiling_per_rebalance": per_rebalance,
            "gross_ceiling_per_year": ceiling,
            "ceiling_definition": ceiling_text,
            "required_capture_fraction": capture_fraction,
            "hurdle_score": hurdle,
            "observations": observations,
            "effective_independent_bets": n_eff,
            "median_instrument_dollar_volume": float(
                np.median([facts[s]["median_dollar_volume"] for s in traded_symbols])
            ),
            "facts": facts,
        },
    }


def select_candidate(measured: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Apply the declared selection rule.

    Rule (declared before the scores were read): the candidate with the
    highest total wins; ties are broken by (a) data quality, then (c) expected
    return after costs, then the candidate id in alphabetical order.
    """
    ranked = sorted(
        measured,
        key=lambda row: (-row["total"], -row["scores"]["a"], -row["scores"]["c"], row["id"]),
    )
    return ranked[0]["id"], ranked


def build_payload() -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    cost_model = measure_cost_model()
    cost_per_unit = cost_model["round_trip_bps"] / 10_000.0

    measured = [measure_candidate(candidate, cost_per_unit, cost_model) for candidate in CANDIDATES]
    selected_id, ranked = select_candidate(measured)

    prior_lines = []
    for entry in PRIOR_LINES:
        path = REPO_ROOT / entry["record"]
        if not path.exists():
            fail(f"missing committed record: {entry['record']}")
        text = path.read_text()
        if entry["status_quote"] not in text:
            fail(
                f"{entry['record']} does not carry the quoted status line "
                f"{entry['status_quote']!r}"
            )
        prior_lines.append(dict(entry, verified=True))

    prior_universes = []
    for entry in PRIOR_UNIVERSES:
        path = REPO_ROOT / entry["file"]
        if not path.exists():
            fail(f"missing committed file: {entry['file']}")
        text = path.read_text()
        missing = [s for s in entry["symbols"] if s not in text]
        if missing:
            fail(f"{entry['file']} does not mention {missing}")
        prior_universes.append(dict(entry, verified=True))

    futures_symbols = [s for s in ("CL-F", "GC-F", "NG-F", "ZB-F") if (RAW_DIR / f"{s}.parquet").exists()]
    roll_counts = roll_event_counts(futures_symbols) if futures_symbols else {}

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()

    return {
        "cycle": CYCLE,
        "cost_model": cost_model,
        "measured": measured,
        "selected_id": selected_id,
        "ranked": ranked,
        "prior_lines": prior_lines,
        "prior_universes": prior_universes,
        "roll_counts": roll_counts,
        "data_unchanged": data_before == data_after,
        "config_unchanged": config_before == config_after,
        "artifacts_unchanged": artifacts_before == artifacts_after,
        "data_file_count": len(data_before),
        "config_file_count": len(config_before),
    }


# ======================================================================
# Rendering
# ======================================================================
def _score_table(rows: list[dict[str, Any]]) -> str:
    header = (
        "| Rank | Candidate | (a) Data | (b) Mechanism | (c) Net after costs | "
        "(d) Robustness | (e) Liquidity | (f) Automation | (g) Diversification | Total |"
    )
    separator = "|---|---|---|---|---|---|---|---|---|---|"
    lines = [header, separator]
    for index, row in enumerate(rows, start=1):
        scores = row["scores"]
        lines.append(
            f"| {index} | `{row['id']}` | {scores['a']} | {scores['b']} | {scores['c']} | "
            f"{scores['d']} | {scores['e']} | {scores['f']} | {scores['g']} | **{row['total']}** |"
        )
    return "\n".join(lines)


def _measured_table(measured: list[dict[str, Any]]) -> str:
    lines = [
        "| Candidate | Sessions | Window | Turnover (units/yr) | Drag @3 bp/unit | "
        "Measured gross scale | Required capture | Hurdle | Observations | "
        "Effective independent bets | Median instrument $volume |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in measured:
        m = row["measured"]
        bets = (
            "not applicable (one book)"
            if m["effective_independent_bets"] is None
            else f"{m['effective_independent_bets']:.2f}"
        )
        lines.append(
            f"| `{row['id']}` | {m['sessions']} | {m['first']} .. {m['last']} | "
            f"{m['turnover_units_per_year']:.2f} | {m['annual_cost_drag']:.4%} | "
            f"{m['gross_ceiling_per_year']:.4%}/yr | {m['required_capture_fraction']:.4%} | "
            f"{m['hurdle_score']}/5 | {m['observations']} | {bets} | "
            f"${m['median_instrument_dollar_volume']:,.0f} |"
        )
    return "\n".join(lines)


def _candidate_block(row: dict[str, Any]) -> str:
    scores = row["scores"]
    notes = row["notes"]
    lines = [
        f"#### `{row['id']}` -- {row['name']}",
        "",
        f"- **Family**: {row['family']}",
        f"- **Mechanism**: {row['mechanism']}",
        f"- **Universe**: {', '.join(row['universe'])}",
        f"- **Data files**: {', '.join(f'`{p}`' for p in row['data_files'])}",
        f"- **Holding horizon**: {row['horizon_sessions']} sessions "
        f"(rebalanced {row['rebalances_per_year']} times per year)",
        f"- **Baseline rule**: {row['baseline_rule']}",
        f"- **Benchmark**: {row['benchmark']}",
        f"- **Cost model**: {row['measured']['annual_cost_drag']:.4%}/yr "
        f"({row['measured']['turnover_units_per_year']:.2f} units of turnover at "
        f"3 bp/unit); friction components absent from the repository's cost model: "
        f"{row['missing_execution_input'] or 'none'}",
        f"- **Known confounders**: " + " ".join(f"({i + 1}) {c}" for i, c in enumerate(row["confounders"])),
        f"- **Falsification condition**: {row['falsification']}",
        "",
        "| Dimension | Score | Basis (measured where measurable) |",
        "|---|---|---|",
        f"| (a) Data quality/access | {scores['a']} | {notes['a']} |",
        f"| (b) Plausible structural explanation | {scores['b']} | declared prior: {notes['b']} |",
        f"| (c) Expected return after costs | {scores['c']} | {notes['c']} |",
        f"| (d) Robustness / statistical power | {scores['d']} | {notes['d']} |",
        f"| (e) Liquidity / capacity | {scores['e']} | {notes['e']} |",
        f"| (f) Automation / operating burden | {scores['f']} | declared prior: {notes['f']} |",
        f"| (g) Diversification from existing research | {scores['g']} | {notes['g']} |",
        "",
        f"**Total: {row['total']} / 35**",
        "",
    ]
    return "\n".join(lines)


def render_experiment(payload: dict[str, Any]) -> str:
    cost = payload["cost_model"]
    rows = payload["ranked"]
    selected = next(row for row in payload["measured"] if row["id"] == payload["selected_id"])

    prior_rows = "\n".join(
        f"| `{entry['id']}` | `{entry['record']}` | {entry['status_class']} | "
        f"\"{entry['status_quote']}\" |"
        for entry in payload["prior_lines"]
    )

    candidate_blocks = "\n".join(_candidate_block(row) for row in payload["measured"])

    return f"""# Experiment: Candidate shortlist (candidate_shortlist_934)

**Cycle {payload['cycle']}.** Measurement and documentation cycle: **no** backtest was run,
**no** parameter was searched, **no** candidate was implemented, **no** gate, threshold,
decision mapping, universe, cost model, Sharpe convention, candidate configuration or
committed artifact was changed; nothing under `data/` or `config/` was written; the
fetcher was never called; no candidate was promoted, re-fit or re-ranked.

## Hypothesis reference

This is a **shortlist cycle**, not a candidate cycle. It has no hypothesis of its own.
Its inputs are the committed records of every earlier candidate line and the committed
cache and configuration, and its output is the selection of **one** mechanism for the
next cycle to pre-register.

## Data used

- **Source**: the committed parquet cache `data/raw/` (the fetcher is never called).
- **Files read by this cycle**: the nine GICS sector ETFs, the incumbent's seven-asset
  universe, the four front-month futures series and the commodity/ETF legs named by the
  candidates.
- **Frequency**: daily, session hours.
- **Point-in-time treatment**: this cycle measures **data availability**, not returns.
  No signal is formed, no weight is computed and no return is produced, so the cycle
  introduces no point-in-time exposure of its own. The point-in-time properties of the
  panels it measures are the committed findings (Cycle 929 membership audit; Cycle 884
  roll-date visibility).

## Configuration

| Item | Value | Source |
|---|---|---|
| Commission | {cost['commission_bps']:.1f} bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Slippage | {cost['slippage_bps']:.1f} bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Round trip | {cost['round_trip_bps']:.1f} bp per unit of weight change | derived |
| Risk-free rate | {cost['risk_free_annual']:.2%} annual | `config/settings.yaml` via `src.backtest.engine.get_risk_free_rate()` |
| Turnover convention | {TURNOVER_UNITS_PER_REBALANCE:.1f} unit per rebalance | the committed cost-screen convention (`research/reports/opportunity_shortlist.md`: calendar_effects_001 24.13 units/yr for 24 rebalances; overnight-capture 504.00 units/yr for 504 sessions) |
| Trials | **1** per candidate -- no candidate carries a parameter grid | declared |

## Number of trials

**1.** The candidate set is a catalogue of four mechanisms, each with one declared
baseline rule. No parameter is searched and no candidate is executed in this cycle; the
four candidates are alternatives, not trials of one hypothesis.

## Results

### 1. The inventory that the scores rest on

**Data available** ({payload['data_file_count']} files under `data/`, {payload['config_file_count']} configuration files under `config/`, all read-only).

| Data class | Available in the cache | Consequence for this shortlist |
|---|---|---|
| Daily ETF OHLCV, constant cross-section | Yes -- the nine GICS sector ETFs carry an identical history (6991 sessions, 1998-12-22 .. 2026-10-08, no gaps) | The only membership-stable cross-section in the repository; the basis of `reversal_001`, `pairs_001` and `liquidity_001` |
| Daily ETF OHLCV, growing cross-section | Yes -- the incumbent's seven-asset universe gains members over the sample (Cycle 929) | Not used as a candidate universe here |
| Front-month futures | Yes -- CL-F, GC-F, NG-F, ZB-F from 2015-01-02; roll **dates** detectable, roll **prices** unobservable (Cycle 884) | The signal of `leadlag_001` is contaminated at every roll; CL-F carries a non-positive close inside the sample |
| Crypto spot/perp/funding | Yes (BTC/ETH, 2020-01-01 .. 2026-09-30) | Already closed: `cryptofunding_001` is an exploratory signal, not promoted |
| Intraday bars, options, borrow, VIX futures | **No** | No candidate below needs them, and no candidate below claims them |

**Cost model actually available**: {cost['commission_bps']:.1f} bp commission + {cost['slippage_bps']:.1f} bp slippage = **{cost['round_trip_bps']:.1f} bp per unit of weight change**, risk-free {cost['risk_free_annual']:.2%} annual. The friction components **absent** from the repository's cost model are: {', '.join(cost['absent_frictions'])}. A candidate that needs an absent friction is penalised on (a), (c) and (f), and the penalty is published with the candidate.

### 2. The lines that are already closed (quoted from the committed records)

A closed line is not reopened and no variant of it is proposed. The status of each line
is quoted from the committed record that carries it; the tool verifies that the quoted
text is still present in that file.

| Line | Committed record | Status class | Status line (verbatim) |
|---|---|---|---|
{prior_rows}

### 3. The four candidates and their scores

Scoring legend (the repository's own): 1 = poor/infeasible, 2 = weak, 3 = adequate,
4 = strong, 5 = excellent/feasible; total = sum of (a)-(g), maximum 35. A score is
**rule-based** where it rests on a quantity measured from the committed cache, and a
**declared prior** where it is a judgement the repository cannot measure without
implementing the candidate. Every such prior is labelled in the candidate block.

{_score_table(payload['measured'])}

### 4. The measured inputs behind the rule-based scores

{_measured_table(payload['measured'])}

### 5. The candidate blocks

{candidate_blocks}
### 6. Selection

**Declared selection rule** (fixed before the scores were read): the candidate with the
highest total wins; ties are broken by (a) data quality, then (c) expected return after
costs, then the candidate id in alphabetical order.

{_score_table(rows)}

**Selected: `{payload['selected_id']}` -- {selected['name']}** (total {selected['total']}/35, next best `{rows[1]['id']}` at {rows[1]['total']}/35, margin {selected['total'] - rows[1]['total']}).

Why it wins, in the measured terms: it is the only candidate that combines a
membership-stable, gap-free 27.8-year cross-section (a = {selected['scores']['a']}), a
weekly rebalance whose cost hurdle is a measured
{selected['measured']['required_capture_fraction']:.4%} of the measured gross scale
(c = {selected['scores']['c']}, the minimum of that hurdle and a declared gross prior of
{selected['gross_prior']}), {selected['measured']['observations']} non-overlapping
observations (d = {selected['scores']['d']}), a median instrument turnover of
${selected['measured']['median_instrument_dollar_volume']:,.0f} per day
(e = {selected['scores']['e']}), no short leg, no roll and no intraday data
(f = {selected['scores']['f']}), and a mechanism family that no committed candidate
hypothesis has implemented (g = {selected['scores']['g']}).

**The published weakness of the selection** (stated, not smoothed over): the nine-sector
panel is **not** new to this repository. Two rejected momentum lines
(`sectorrotation_001`, `sectorrotation_002`) and one rejected broad cross-sectional
momentum line (`csmomentum_001`) already traded it, so the (g) exposure score is
{selected['scores']['g']}/5 even though the mechanism itself is new. The next cycle must
therefore test the reversal signal against the **mirror** of the rejected sector
momentum signal on the same panel, so that "the opposite of a rejected hypothesis" is
not mistaken for a new edge.

### 7. The selected candidate's pre-registration skeleton

The next cycle pre-registers this candidate as `research/hypotheses/reversal_001.md` plus
`config/reversal_candidate_001.yaml` **before** any backtest is executed. The skeleton
below is the material that pre-registration must contain.

| Field | Value |
|---|---|
| **Mechanism** | {selected['mechanism']} |
| **Expected direction** | Positive relative to the 1/N benchmark of the same nine sectors. **Magnitude: not measured in this repository.** The pre-registered cost hurdle is that the rule must capture at least {selected['measured']['required_capture_fraction']:.4%} of the measured cross-sectional dispersion per rebalance ({selected['measured']['gross_ceiling_per_year']:.4%}/yr of scale against a {selected['measured']['annual_cost_drag']:.4%}/yr drag) to break even at the repository's cost model. |
| **Holding horizon** | {selected['horizon_sessions']} sessions; rebalanced {selected['rebalances_per_year']} times per year; the signal formed at t is effective at t+1 (one-session lag) |
| **Asset universe** | {', '.join(selected['universe'])} (nine GICS sector ETFs; identical cached history, 6991 sessions, 1998-12-22 .. 2026-10-08, no gaps) |
| **Features and data sources** | {', '.join(f'`{p}`' for p in selected['data_files'])} -- committed parquet cache, daily OHLCV, the fetcher is never called |
| **Entry / exit rules** | {selected['baseline_rule']} |
| **Benchmark** | {selected['benchmark']} |
| **Known confounders** | {' '.join(f'({i + 1}) {c}' for i, c in enumerate(selected['confounders']))} |
| **Falsification condition** | {selected['falsification']} |
| **Cost model assumptions** | {cost['commission_bps']:.1f} bp commission + {cost['slippage_bps']:.1f} bp slippage = {cost['round_trip_bps']:.1f} bp per unit of weight change, applied to the absolute weight change on rebalance days; risk-free {cost['risk_free_annual']:.2%} annual for the Sharpe convention; no borrow (the rule is long-only), and **no** market-impact, spread, latency or margin term exists in the repository's cost model -- a disclosed gap, bounded by the committed Cycle-913 break-even audit; turnover estimated at {selected['measured']['turnover_units_per_year']:.2f} units/yr ({selected['measured']['annual_cost_drag']:.4%}/yr drag) under the committed one-book-rotation-per-rebalance convention |

### 8. What this cycle deliberately does **not** propose

- **No risk-parity candidate and no risk-parity variant.** `riskparity_001` is closed
  (`research/experiments/riskparity_001_evaluation.md`: "**Decision: REJECT (negative
  result).**") and the family is not reopened here.
- **No reopened closed line.** Every line in the table of section 2 keeps its committed
  status; no variant of the momentum, sector-rotation, calendar, overnight, macro-regime,
  crypto-carry, futures-basis or microcap families is proposed.
- **No parameter search, no candidate implementation and no backtest.** The cycle
  measures availability and scores; it does not test any of the four candidates.
- **No change to `data/` or `config/`.** The run fingerprints every file under both
  trees before and after and fails closed if either changed.

## Decision

**Next task (Cycle 935): pre-register `reversal_001`** -- write
`research/hypotheses/reversal_001.md` and `config/reversal_candidate_001.yaml` with the
mechanism, horizon, universe, benchmark, confounders, falsification condition and cost
model above, **before** any backtest is executed, and then run the config-faithful
walk-forward on the nine-sector panel with the repository's committed cost model and
the 10y/12m/6m design with 21-day purge and embargo, reporting the benchmark-relative
net excess, its moving-block bootstrap CI, the mirror test against the rejected sector
momentum signal, and the capture fraction against the cost hurdle.

**Label of this cycle: shortlist produced, one candidate selected, nothing tested.** No
candidate's verdict changes; the incumbent stays a **Credible Candidate** by its
published verdict and **NO-GO** for promotion.

## Reproduction commands

```bash
python research/candidate_shortlist_934.py
python -m pytest -q tests/test_candidate_shortlist_934.py
git status --porcelain data/ config/
```
"""


def render_report(payload: dict[str, Any]) -> str:
    cost = payload["cost_model"]
    rows = payload["ranked"]
    selected = next(row for row in payload["measured"] if row["id"] == payload["selected_id"])
    inventory_rows = []
    for row in payload["measured"]:
        for symbol in row["universe"]:
            facts = row["measured"]["facts"][symbol]
            inventory_rows.append(
                f"| `{symbol}` | {facts['rows']} | {facts['first']} | {facts['last']} | "
                f"{facts['missing_close']} | {facts['duplicate_timestamps']} | "
                f"{facts['non_positive_close']} | {facts['zero_volume_rows']} | "
                f"${facts['median_dollar_volume']:,.0f} | ${facts['p10_dollar_volume']:,.0f} |"
            )
    roll_rows = "\n".join(
        f"| `{symbol}` | {count} |" for symbol, count in sorted(payload["roll_counts"].items())
    ) or "| (no front-month series required) | - |"
    return f"""# Report: Evidence-based candidate shortlist (candidate_shortlist_934)

**Cycle {payload['cycle']}.** Read-only, deterministic. No backtest, no parameter search,
no candidate implementation, no write under `data/` or `config/`, no fetcher call, no
change to any committed record, gate, protocol or shortlist row.

This report is the long-form evidence behind the shortlist record
`research/experiments/candidate_shortlist_934.md`; both are generated by
`research/candidate_shortlist_934.py` and contain no timestamp, so two consecutive runs
are byte-identical.

## 1. Method

1. **Inventory** the data and the cost model that are really available (committed cache
   and committed configuration, read-only).
2. **Quote** the committed status line of every earlier candidate line, so that a closed
   line is not reopened and an open one is not mislabelled.
3. **Score** four structurally distinct mechanisms on the seven AGENTS.md dimensions. A
   score is rule-based where the repository can measure it and a labelled prior where it
   cannot.
4. **Select** one mechanism with a single declared rule and publish its hypothesis-first
   skeleton.

## 2. Measured inventory of the series the candidates depend on

| Symbol | Rows | First | Last | Missing close | Duplicate timestamps | Non-positive close | Zero-volume rows | Median $volume/day | p10 $volume/day |
|---|---|---|---|---|---|---|---|---|---|
{chr(10).join(inventory_rows)}

### 2.1 Detected roll events in the front-month futures series (Cycle 884 detector)

The committed detector (`research/futures_roll_visibility.py::detect_roll_events`)
classifies a session using up to eight forward sessions and four subsequent volume
ratios, so the roll dates it returns are an **ex-post** detection: they are usable to
clean a backtest but are **not** a tradable point-in-time signal, and a live rule
would have to detect the roll with the same lag. The counts below are a data-readiness
fact for `leadlag_001`, nothing more.

**Provenance limit (disclosed, not laundered).** The detector's own ground-truth
constant is a *manual* observation established against per-contract volume series that
are **not** in `data/raw/`, so it is not reproducible from the repository and this cycle
does not use it: the counts below come from the detector's own volume signature applied
to the cached front-month series, and they are used only to size the roll contamination
of `leadlag_001`'s signal.

| Series | Detected roll events |
|---|---|
{roll_rows}

### 2.2 The cost model that is actually available

| Component | Value | Present in the repository's cost model |
|---|---|---|
| Commission | {cost['commission_bps']:.1f} bp per unit of weight change | yes (`config/settings.yaml`) |
| Slippage | {cost['slippage_bps']:.1f} bp per unit of weight change | yes (`config/settings.yaml`) |
| Round trip | {cost['round_trip_bps']:.1f} bp per unit of weight change | derived |
| Risk-free rate | {cost['risk_free_annual']:.2%} annual | yes (`config/settings.yaml`) |
| Bid-ask spread | - | **no** |
| Borrow / short-side cost | - | **no** |
| Roll cost / roll price | - | **no** |
| Market impact | - | **no** |
| Latency | - | **no** |
| Margin | - | **no** |

## 3. The closed lines, quoted from their committed records

| Line | Committed record | Status class | Status line (verbatim) |
|---|---|---|---|
{chr(10).join(f"| `{e['id']}` | `{e['record']}` | {e['status_class']} | \"{e['status_quote']}\" |" for e in payload['prior_lines'])}

## 4. The candidates, the scores and the measured inputs

{_score_table(payload['measured'])}

{_measured_table(payload['measured'])}

### 4.1 Per-candidate score basis

{chr(10).join(_candidate_block(row) for row in payload['measured'])}

## 5. Selection

Declared rule: the highest total wins; ties are broken by (a), then (c), then the id.
Result: **`{payload['selected_id']}`** ({selected['total']}/35), next `{rows[1]['id']}`
({rows[1]['total']}/35).

The published weakness of the selection is that the nine-sector panel was already
traded by three closed momentum lines, so the exposure half of (g) is
{selected['scores']['g']}/5 even though the mechanism family is new. The next cycle
must therefore test the reversal signal against the mirror of the rejected sector
momentum signal on the same panel.

## 6. Reproduction

```bash
python research/candidate_shortlist_934.py
python -m pytest -q tests/test_candidate_shortlist_934.py
git status --porcelain data/ config/
```
"""


# ======================================================================
# Checks
# ======================================================================
def run_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    measured = payload["measured"]
    selected_id = payload["selected_id"]

    add(
        "at_least_three_candidates",
        len(measured) >= 3,
        f"{len(measured)} candidates scored",
    )
    complete = all(
        len(row["scores"]) == 7
        and all(1 <= value <= 5 for value in row["scores"].values())
        and all(row["notes"][key] for key in row["scores"])
        for row in measured
    )
    add("seven_dimensions_scored", complete, "every candidate scores (a)-(g) in 1..5 with a basis")
    totals_ok = all(row["total"] == sum(row["scores"].values()) for row in measured)
    add("totals_consistent", totals_ok, "every total equals the sum of its seven scores")
    add(
        "falsification_present",
        all(len(row["falsification"]) > 80 for row in measured),
        "every candidate carries a falsification condition",
    )
    add(
        "data_files_cited",
        all(
            (REPO_ROOT / path).exists()
            for row in measured
            for path in row["data_files"]
        ),
        "every cited data file exists in the committed cache",
    )
    add(
        "prior_status_quotes_verified",
        all(entry.get("verified") for entry in payload["prior_lines"]),
        "every quoted prior status line is present in its committed record",
    )
    add(
        "prior_universes_verified",
        all(entry.get("verified") for entry in payload["prior_universes"]),
        "every prior universe is verified against its committed file",
    )
    closed = {line["id"].split("/")[0].strip() for line in payload["prior_lines"]}
    new_ids = {row["id"].split("_")[0] for row in measured}
    add(
        "no_closed_line_reopened",
        not (closed & new_ids),
        "none of the four candidates reuses a closed candidate identifier",
    )
    riskparity = [row["id"] for row in measured if "riskpar" in row["id"].lower() or "risk par" in row["name"].lower()]
    add("no_riskparity_variant", not riskparity, f"risk-parity-like candidates: {riskparity or 'none'}")
    add(
        "no_parameter_grid",
        all("grid" not in row for row in CANDIDATES),
        "no candidate declares a parameter grid; one baseline rule each",
    )
    ranked = sorted(
        measured,
        key=lambda row: (-row["total"], -row["scores"]["a"], -row["scores"]["c"], row["id"]),
    )
    add(
        "selection_rule_applied",
        ranked[0]["id"] == selected_id,
        f"rule selects {ranked[0]['id']}; the published selection is {selected_id}",
    )
    selected = next(row for row in measured if row["id"] == selected_id)
    required_fields = [
        selected["mechanism"],
        selected["horizon_sessions"],
        selected["universe"],
        selected["benchmark"],
        selected["confounders"],
        selected["falsification"],
        selected["measured"]["annual_cost_drag"],
    ]
    add(
        "selected_candidate_complete",
        all(bool(field) for field in required_fields),
        "the selected candidate carries mechanism, horizon, universe, benchmark, "
        "confounders, falsification condition and a cost model",
    )
    cost = payload["cost_model"]
    add(
        "cost_model_measured",
        abs(cost["round_trip_bps"] - 3.0) < 1e-9 and cost["settings_has_commission"],
        f"{cost['commission_bps']:.1f} bp + {cost['slippage_bps']:.1f} bp = "
        f"{cost['round_trip_bps']:.1f} bp per unit of weight change",
    )
    add("data_unchanged", payload["data_unchanged"], "every file under data/ is byte-identical")
    add("config_unchanged", payload["config_unchanged"], "every file under config/ is byte-identical")
    add(
        "committed_artifacts_unchanged",
        payload["artifacts_unchanged"],
        "no committed artifact under src/, config/, research/experiments/ or research/reports/ was modified",
    )
    return checks


# ======================================================================
# Entry point
# ======================================================================
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="run the measurement and the checks without writing the report or the experiment record",
    )
    args = parser.parse_args(argv)

    try:
        payload = build_payload()
        checks = run_checks(payload)
    except ShortlistError as error:
        print(f"ERROR: {error}")
        return 2

    experiment_text = render_experiment(payload)
    report_text = render_report(payload)

    overall = all(check["pass"] for check in checks)

    if not args.no_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(report_text)
        OUT_EXP.write_text(experiment_text)

    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    for check in checks:
        print(f"CHECK|{check['name']}|{'PASS' if check['pass'] else 'FAIL'}|{check['detail']}")
    for row in payload["ranked"]:
        print(
            f"CANDIDATE|{row['id']}|TOTAL|{row['total']}|"
            f"A|{row['scores']['a']}|B|{row['scores']['b']}|C|{row['scores']['c']}|"
            f"D|{row['scores']['d']}|E|{row['scores']['e']}|F|{row['scores']['f']}|"
            f"G|{row['scores']['g']}|"
            f"CAPTURE|{row['measured']['required_capture_fraction']:.6f}"
        )
    print(f"SELECTED|{payload['selected_id']}")
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
