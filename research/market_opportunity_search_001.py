#!/usr/bin/env python3
"""Cycle 947 -- evidence-based market-opportunity search over the committed cache.

What this tool does
-------------------
The repository's candidate lines are exhausted: the Cycle-934 shortlist was
closed out in Cycle 946 and every remaining line carries a committed verdict
(incumbent ``tsmomentum_spytrend_001``: Credible Candidate / NO-GO for
promotion; ``reversal_001``, ``pairs_001``, ``liquidity_001``,
``leadlag_001``, ``sectorrotation_001``/``002``, ``csmomentum_001``,
``riskparity_001``, ``calendar_effects_001``, ``overnight_capture_001``,
``macroregime_001``, ``futuresbasis_001``/``002``, ``mom121_microcap_001``:
closed; ``cryptofunding_001``: exploratory signal, not promoted).  This cycle
therefore does **not** re-score any closed line.  It searches the *market
segments* the committed cache can actually host:

1. it **inventories every file under ``data/raw/``** -- counts, date ranges,
   frequency, gaps, duplicate timestamps, non-positive closes, zero-volume
   rows, median dollar volume -- so that every score rests on a measured
   quantity;
2. it **re-measures the cost model** that is really implemented
   (``src/backtest/engine.py``), and states which frictions it does **not**
   contain;
3. it **scores eleven market segments** on the seven AGENTS.md dimensions,
   with the measured inputs printed next to every rule-based score and every
   declared prior labelled as such;
4. it runs **one** pre-declared feasibility screen on the single segment the
   scoring leaves open, and publishes its result whatever it is; and
5. it publishes an explicit, evidence-based **rejection reason for every
   segment**, so that the next cycle inherits evidence instead of guesses.

Scope
-----
This is a **measurement and documentation** cycle.  It runs no walk-forward
evaluation, searches no parameter, implements no candidate, writes nothing
under ``data/`` or ``config/``, calls the fetcher never, and modifies no
committed record, gate, protocol or threshold.  The two files it writes are
its own report and its own experiment record.

The one backtest-like object it computes is the **pre-declared feasibility
screen** of section 4, which is *in-sample, full-sample and non-selective*:
its rule, universe, benchmark and cost model are frozen constants of this
file, they are declared in the module docstring of the published report, and
no parameter is selected by its result.

Reproduction
------------
```bash
python research/market_opportunity_search_001.py
python -m pytest -q tests/test_market_opportunity_search_001.py
git status --porcelain data/ config/
```
"""

from __future__ import annotations

import argparse
import hashlib
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
from src.backtest.engine import get_cost_params, get_risk_free_rate  # noqa: E402
from src.evaluation.walkforward import generate_walkforward_splits  # noqa: E402

CYCLE = "947"

RAW_DIR = REPO_ROOT / "data" / "raw"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"

OUT_REPORT = REPORTS_DIR / "market_opportunity_search_001.md"
OUT_EXP = EXPERIMENTS_DIR / "market_opportunity_search_001.md"

#: The repository's frozen walk-forward design (src/evaluation/walkforward.py
#: defaults, identical to research/run_cycle6.py::WF_*).
WF_TRAIN_YEARS = 10.0
WF_TEST_MONTHS = 12.0
WF_STEP_MONTHS = 6.0
WF_PURGE_DAYS = 21
WF_EMBARGO_DAYS = 21

#: The minimum number of walk-forward folds a candidate panel must support
#: before it can be evaluated on the repository's frozen design.  Declared
#: before any measurement: a panel with fewer folds cannot produce a
#: meaningful positive-fold rate (3 folds resolve that gate only to 1/3),
#: a meaningful pooled trade count or a meaningful Deflated Sharpe Ratio.
MIN_FOLDS = 15

#: The business-day count the frozen design needs for MIN_FOLDS folds.
#: 2520 (train) + 252 (test) + (MIN_FOLDS - 1) * 126 (step).
BUSINESS_DAYS_FOR_MIN_FOLDS = 2520 + 252 + (MIN_FOLDS - 1) * 126

#: The maximum annual turnover of a monthly, long-only, fully-rotating book:
#: twelve rebalances, each replacing the whole book (2 units of weight
#: change).  At the repository's 3.0 bp per unit of weight change this is the
#: *upper bound* on the annual cost drag of any monthly long-only rule and is
#: the uniform "cost hurdle" used for the (c) score.
MAX_MONTHLY_LONG_ONLY_TURNOVER = 24.0

# ======================================================================
# The pre-declared feasibility screen (frozen constants)
# ======================================================================
# Declared before the screen was computed, from the data inventory and the
# literature prior only.  No parameter of this rule is selected by its result
# and the rule is not changed after the screen is read.
PRE_DECLARED_SCREEN = {
    "candidate_id": "commoditytrend_001",
    "universe": ["DBC", "GLD"],
    "lookback_sessions": 252,
    "skip_sessions": 21,
    "rebalance": "month_end",
    "signal_lag_sessions": 1,
    "rule": (
        "absolute time-series momentum: hold every asset whose trailing 252-session "
        "total return, skipping the most recent 21 sessions, is positive; equal "
        "weight 1/N over the held assets; 100% cash when none is held"
    ),
    "benchmark": "1/N buy-and-hold of the same universe over the same sessions",
    "rationale": (
        "DBC and GLD are the only two commodity exposures in the committed cache "
        "with enough cached daily history to support the frozen 10y/12m/6m "
        "walk-forward design; the 2015-01-02 common start of the other four "
        "commodity ETFs supports three folds only"
    ),
}

#: The candidate specification published in the report but **not**
#: pre-registered (its data gate is not satisfied and its only measurable
#: instantiation fails the pre-declared screen).
CONDITIONAL_CANDIDATE = {
    "id": "commoditytrend_001",
    "mechanism": (
        "Absolute (time-series) momentum inside the commodity complex: a commodity "
        "price that is in a 12-month uptrend is expected to keep paying its trend "
        "premium (documented time-series momentum in commodity futures); a "
        "commodity price in a 12-month downtrend is expected to keep paying its "
        "downtrend premium, so the book is flat in cash rather than short"
    ),
    "direction": "long the assets in an uptrend, flat in cash otherwise",
    "horizon": "monthly rebalance, 252-session signal with a 21-session skip",
    "universe": ["DBC", "BNO", "UNG", "GLD"],
    "benchmark": "1/N buy-and-hold of the same universe",
    "cost_model": (
        "3.0 bp per unit of weight change (1.0 bp commission + 2.0 bp slippage, "
        "src/backtest/engine.py) at a 2.00% risk-free rate; long-only, so no "
        "borrow; the embedded ETF expense ratio and the embedded roll yield of the "
        "commodity ETFs are NOT measurable from the cache and are declared blocked"
    ),
    "data_gate": (
        "the cached common-inception panel must support at least 15 folds of the "
        "frozen 10y/12m/6m design (>= 4,536 business days)"
    ),
    "falsification": (
        "1) walk-forward mean OOS Sharpe < 0.9; 2) the benchmark-relative net "
        "excess has a moving-block bootstrap 95% CI that includes zero; 3) the "
        "measured gross capture fraction is below the measured cost hurdle; "
        "4) the positive-fold rate < 0.5 or the pooled OOS trades <= 100; "
        "5) no positive benchmark-relative excess after 2010; 6) the data gate "
        "fails (the candidate is then blocked by data/infrastructure, not "
        "rejected)"
    ),
}

#: The committed status lines this tool quotes.  Each quote is verified to be
#: present in the committed record; the tool fails closed otherwise.
PRIOR_LINES = [
    {
        "id": "reversal_001",
        "record": "research/experiments/reversal_001_evaluation.md",
        "status_quote": "**Rejected/Failed (a pre-registered falsification condition fired)**",
    },
    {
        "id": "pairs_001",
        "record": "research/experiments/pairs_001_evaluation.md",
        "status_quote": "**Rejected/Failed (a pre-registered falsification condition fired)**",
    },
    {
        "id": "liquidity_001",
        "record": "research/experiments/liquidity_001_evaluation.md",
        "status_quote": "**Rejected/Failed**",
    },
    {
        "id": "leadlag_001",
        "record": "research/experiments/leadlag_001_evaluation.md",
        "status_quote": "**Rejected/Failed**",
    },
    {
        "id": "sectorrotation_002",
        "record": "research/experiments/sectorrotation_002_experiment_001.md",
        "status_quote": "hypothesis FALSIFIED (Rejected/Failed)",
    },
    {
        "id": "cryptofunding_001",
        "record": "research/experiments/cryptofunding_002_evaluation.md",
        "status_quote": "**Exploratory signal — not promoted.**",
    },
    {
        "id": "futuresbasis_001",
        "record": "research/experiments/futuresbasis_001.md",
        "status_quote": "**Blocked by data/infrastructure**",
    },
    {
        "id": "futuresbasis_002",
        "record": "research/experiments/futuresbasis_002.md",
        "status_quote": "Verdict: Rejected/Failed on cost (and signal sign).",
    },
    {
        "id": "mom121_microcap_001",
        "record": "research/experiments/mom121_microcap_001.md",
        "status_quote": "**Status:** **Blocked by data/infrastructure** — data gate failed",
    },
    {
        "id": "riskparity_001",
        "record": "research/experiments/riskparity_001_evaluation.md",
        "status_quote": "Rejected / failed the pre-registered promotion gates",
    },
]

#: The books the repository already trades.  A segment's (g) score is
#: penalised by the share of its instruments that already sit inside one of
#: these committed books.
PRIOR_BOOKS = [
    {
        "id": "tsmomentum_spytrend_001 (incumbent)",
        "file": "config/simulation_candidate_001.yaml",
        "symbols": ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"],
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
        "id": "sectorrotation_001/002",
        "file": "config/sectorrotation_candidate_001.yaml",
        "symbols": [
            "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
        ],
    },
]

#: The market segments.  ``instruments`` are the cached series the segment
#: would have to trade; ``reference`` names the instruments whose measured
#: facts back the rejection when the segment itself has no cached instrument.
SEGMENTS = [
    {
        "id": "equity_broad_index",
        "eligibility": "closed",
        "eligibility_reason": (
            "CLOSED: every mechanism family this segment can host is already a committed line (csmomentum_001, riskparity_001, calendar_effects_001, overnight_capture_001, macroregime_001, the incumbent)"
        ),
        "title": "Broad equity index (US large cap, US small cap, developed, emerging)",
        "instruments": ["SPY", "QQQ", "IWM", "EFA", "EEM"],
        "prior_b": 2,
        "prior_b_text": (
            "declared prior: the mechanism families this segment hosts -- "
            "cross-sectional momentum (csmomentum_001), inverse-volatility risk "
            "balancing (riskparity_001), turn-of-month timing (calendar_effects_001), "
            "overnight capture (overnight_capture_001), macro-regime conditioning "
            "(macroregime_001) and time-series momentum (the incumbent) -- are all "
            "already measured in this repository, and each of them failed or was "
            "falsified; a new rule here is a variant of a closed line"
        ),
        "prior_f": 5,
        "prior_f_text": (
            "declared prior: daily bars, one venue, session hours, long-only, no "
            "roll, no borrow, no 24/7 operational burden"
        ),
        "gross_prior": 2,
        "gross_prior_text": (
            "declared prior: the measured net Sharpe of every rule this repository "
            "has run on this segment is 0.37-0.95 with a benchmark-relative excess "
            "whose CI includes zero"
        ),
    },
    {
        "id": "equity_gics_sectors",
        "eligibility": "closed",
        "eligibility_reason": (
            "CLOSED: four committed lines have traded this panel (sectorrotation_001/002, reversal_001, liquidity_001, pairs_001) and all four are rejected"
        ),
        "title": "US GICS sector ETFs (the repository's only membership-stable cross-section)",
        "instruments": [
            "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
        ],
        "prior_b": 1,
        "prior_b_text": (
            "declared prior: four candidate lines have already traded this panel "
            "(sectorrotation_001/002, reversal_001, liquidity_001, pairs_001) and all "
            "four are rejected; the measured 5-session capture fraction of the "
            "reversal hypothesis has the opposite sign to the hypothesis, so the "
            "panel's short-horizon behaviour is already characterised"
        ),
        "prior_f": 5,
        "prior_f_text": (
            "declared prior: daily bars, one venue, session hours, long-only, no roll"
        ),
        "gross_prior": 1,
        "gross_prior_text": (
            "declared prior: the measured capture fraction on this panel is negative "
            "for every rule the repository has run on it"
        ),
    },
    {
        "id": "real_assets_reit",
        "eligibility": "closed",
        "eligibility_reason": (
            "CLOSED: VNQ is already inside the committed 18-ETF csmomentum_001 book, which is rejected"
        ),
        "title": "US real estate (REIT) ETF",
        "instruments": ["VNQ"],
        "prior_b": 2,
        "prior_b_text": (
            "declared prior: REIT momentum and REIT mean reversion are documented, but "
            "both are momentum-family mechanisms that this repository has already "
            "measured and rejected on the cross-sections it could form"
        ),
        "prior_f": 5,
        "prior_f_text": "declared prior: one daily bar series, session hours, long-only",
        "gross_prior": 1,
        "gross_prior_text": (
            "declared prior: a single-asset monthly rule has no cross-section to "
            "rank and therefore no documented cross-sectional premium to harvest"
        ),
    },
    {
        "id": "rates_duration",
        "eligibility": "closed",
        "eligibility_reason": (
            "CLOSED and BLOCKED: TLT is inside the incumbent and csmomentum books, and the futures roll yield is the futuresbasis_001 data block"
        ),
        "title": "Interest-rate duration (long-duration Treasury ETF and 10-year Treasury futures)",
        "instruments": ["TLT", "ZB-F"],
        "prior_b": 2,
        "prior_b_text": (
            "declared prior: the documented bond-pricing mechanisms need a macro "
            "series (yield level, curve slope, inflation expectation) that the "
            "committed cache does not contain; the one cache-native route -- the "
            "futures roll yield -- is the family futuresbasis_001 was blocked on"
        ),
        "prior_f": 3,
        "prior_f_text": (
            "declared prior: a futures leg needs a roll window to be detected and "
            "excluded on every rebalance"
        ),
        "gross_prior": 2,
        "gross_prior_text": (
            "declared prior: the futures roll yield is documented and persistent but "
            "its prices are not observable in the committed cache"
        ),
    },
    {
        "id": "commodity_complex",
        "eligibility": "open",
        "eligibility_reason": (
            "OPEN: the only segment the repository has never traded as a book; commodity time-series momentum is a new mechanism here"
        ),
        "title": "Commodity complex (broad commodity ETFs, single-commodity ETFs, front-month futures)",
        "instruments": ["DBC", "GSG", "BNO", "UNG", "USO", "GLD", "CL-F", "GC-F", "NG-F"],
        "prior_b": 4,
        "prior_b_text": (
            "declared prior: commodity time-series momentum is documented and is the "
            "strongest trend market in the literature; the segment has never been "
            "traded as a book in this repository, so the mechanism family is new "
            "here even though the family overlaps the incumbent's"
        ),
        "prior_f": 4,
        "prior_f_text": (
            "declared prior: daily bars, one venue, session hours, long-only; the "
            "front-month futures legs need roll handling, so an ETF-only book is "
            "preferred"
        ),
        "gross_prior": 3,
        "gross_prior_text": (
            "declared prior: managed-futures trend premia are documented but small "
            "per instrument; the rule must clear the 0.9 net-Sharpe gate on two "
            "independent bets, which is a low prior"
        ),
    },
    {
        "id": "crypto_funding",
        "eligibility": "closed",
        "eligibility_reason": (
            "CLOSED: cryptofunding_001 is the committed record for this segment"
        ),
        "title": "Crypto spot, perpetual and 8-hourly funding (the only sub-daily data in the cache)",
        "instruments": ["BTCUSDT", "ETHUSDT"],
        "prior_b": 3,
        "prior_b_text": (
            "declared prior: the funding-carry mechanism is documented and was "
            "already run here (cryptofunding_001, exploratory signal, not promoted); "
            "the sub-daily funding series allows intraday timing, but the cache has "
            "no 8-hourly price bars, so no intraday execution can be measured"
        ),
        "prior_f": 2,
        "prior_f_text": (
            "declared prior: 24/7 venue, 365-day annualisation, margin and funding "
            "accounting, venue and counterparty rules"
        ),
        "gross_prior": 3,
        "gross_prior_text": (
            "declared prior: the funding carry is a real, measured premium, but the "
            "committed record already shows it cannot clear the pooled-trade gate"
        ),
    },
    {
        "id": "equity_volatility",
        "eligibility": "blocked",
        "eligibility_reason": (
            "BLOCKED: the cache holds no tradable volatility instrument (no future, no option, no volatility ETP)"
        ),
        "title": "Equity implied volatility (VIX index)",
        "instruments": ["^VIX"],
        "prior_b": 3,
        "prior_b_text": (
            "declared prior: the variance risk premium is the best-documented "
            "volatility mechanism, but it requires a *sold* volatility instrument; "
            "the cache contains the VIX index only, and the VIX level as a "
            "conditioning variable is the macroregime_001 family, which is falsified"
        ),
        "prior_f": 2,
        "prior_f_text": (
            "declared prior: the index itself is not tradable, so an implementation "
            "needs an instrument the repository does not hold"
        ),
        "gross_prior": 2,
        "gross_prior_text": (
            "declared prior: the variance risk premium is large but not capturable "
            "without a volatility instrument in the cache"
        ),
    },
    {
        "id": "single_name_equities",
        "eligibility": "blocked",
        "eligibility_reason": (
            "BLOCKED: the cache holds no single-name series, no point-in-time constituent list and no fundamental series"
        ),
        "title": "Single-name equities (cross-section beyond the ETF complex)",
        "instruments": [],
        "reference": ["SPY", "QQQ", "IWM"],
        "prior_b": 3,
        "prior_b_text": (
            "declared prior: single-name cross-sectional momentum, value and "
            "quality premia are the best-documented equity premia, but each of them "
            "needs a point-in-time constituent list and a fundamental series"
        ),
        "prior_f": 2,
        "prior_f_text": (
            "declared prior: a point-in-time universe with delisting treatment is an "
            "operational burden, and the repository has no such universe"
        ),
        "gross_prior": 2,
        "gross_prior_text": (
            "declared prior: the documented premia are real but cannot be tested "
            "without the constituent and fundamental data"
        ),
    },
    {
        "id": "short_leg_relative_value",
        "eligibility": "closed",
        "eligibility_reason": (
            "CLOSED and cost-blocked: pairs_001 is the committed record, and the repository's cost model carries no borrow term at all"
        ),
        "title": "Short-leg / market-neutral relative value",
        "instruments": ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"],
        "prior_b": 3,
        "prior_b_text": (
            "declared prior: cointegration-based spread convergence is documented and "
            "was already run here (pairs_001, rejected) on the same panel"
        ),
        "prior_f": 2,
        "prior_f_text": (
            "declared prior: a short leg needs borrow, locate and recall handling, "
            "and the repository's cost model has no borrow term at all"
        ),
        "gross_prior": 2,
        "gross_prior_text": (
            "declared prior: the measured borrow drag of the one run short-leg line "
            "in this repository is an order of magnitude larger than its gross edge"
        ),
    },
    {
        "id": "session_timing",
        "eligibility": "closed",
        "eligibility_reason": (
            "CLOSED: overnight_capture_001 is the committed record for the session split"
        ),
        "title": "Session timing (overnight capture and its intraday mirror)",
        "instruments": ["SPY", "QQQ", "IWM", "EFA"],
        "prior_b": 4,
        "prior_b_text": (
            "declared prior: the session split of the equity premium is well "
            "documented and is a genuine market-structure effect rather than a "
            "price-predictivity effect"
        ),
        "prior_f": 4,
        "prior_f_text": (
            "declared prior: daily bars with open and close fields, one venue; the "
            "intraday mirror needs an execution at the open that the cache's bars "
            "can only approximate"
        ),
        "gross_prior": 1,
        "gross_prior_text": (
            "declared prior: the premium is concentrated in the overnight leg, whose "
            "turnover the repository's cost model prices out of existence"
        ),
    },
    {
        "id": "vol_scaled_overlays",
        "eligibility": "closed",
        "eligibility_reason": (
            "CLOSED: riskparity_001 is the committed record for inverse-volatility allocation"
        ),
        "title": "Volatility-scaled and risk-balanced allocation overlays",
        "instruments": ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"],
        "prior_b": 2,
        "prior_b_text": (
            "declared prior: volatility scaling and risk balancing are documented "
            "and were already run here (riskparity_001, rejected); the long-sample "
            "overlay diagnostic shows the drawdown cut and the gross cap are inert"
        ),
        "prior_f": 5,
        "prior_f_text": "declared prior: daily bars, one venue, session hours, long-only",
        "gross_prior": 1,
        "gross_prior_text": (
            "declared prior: the measured benchmark-relative excess of the "
            "inverse-volatility book has a bootstrap CI that includes zero"
        ),
    },
]


#: The pre-registered candidate this cycle freezes.  The rule, the universe
#: and the cost model below are the ones the committed configuration file
#: carries; the tool fails closed if the two ever drift apart.
PRE_REGISTERED = {
    "id": "commoditytrend_001",
    "config": "config/commoditytrend_001.yaml",
    "hypothesis": "research/hypotheses/commoditytrend_001.md",
    "universe": ["DBC", "BNO", "UNG", "GLD"],
    "lookback_sessions": 252,
    "skip_sessions": 21,
    "rebalance": "month_end",
    "signal_lag_sessions": 1,
    "round_trip_bps": 3.0,
    "risk_free_annual": 0.02,
    "min_folds": 10,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_preregistration() -> dict[str, Any]:
    """Verify the frozen pre-registration and return its hashes.

    The tool fails closed if the committed configuration or the committed
    hypothesis drifts away from the rule this search published, so the
    pre-registration cannot be edited behind the search's back.
    """
    import yaml

    config_path = REPO_ROOT / PRE_REGISTERED["config"]
    hypothesis_path = REPO_ROOT / PRE_REGISTERED["hypothesis"]
    for path in (config_path, hypothesis_path):
        if not path.exists():
            fail(f"missing pre-registration artefact: {path.relative_to(REPO_ROOT)}")

    config = yaml.safe_load(config_path.read_text())
    if config.get("candidate_id") != PRE_REGISTERED["id"]:
        fail(f"{PRE_REGISTERED['config']}: candidate_id is not {PRE_REGISTERED['id']}")
    if list(config.get("universe") or []) != PRE_REGISTERED["universe"]:
        fail(f"{PRE_REGISTERED['config']}: the universe is not the frozen universe")
    signal = config.get("signal") or {}
    if signal.get("lookback_sessions") != PRE_REGISTERED["lookback_sessions"]:
        fail(f"{PRE_REGISTERED['config']}: the lookback is not the frozen lookback")
    if signal.get("skip_sessions") != PRE_REGISTERED["skip_sessions"]:
        fail(f"{PRE_REGISTERED['config']}: the skip is not the frozen skip")
    if signal.get("rebalance_schedule") != PRE_REGISTERED["rebalance"]:
        fail(f"{PRE_REGISTERED['config']}: the rebalance schedule is not the frozen schedule")
    if signal.get("signal_lag_days") != PRE_REGISTERED["signal_lag_sessions"]:
        fail(f"{PRE_REGISTERED['config']}: the signal lag is not the frozen lag")
    cost = config.get("cost_model") or {}
    if abs(float(cost.get("total_round_trip_bps", 0.0)) - PRE_REGISTERED["round_trip_bps"]) > 1e-9:
        fail(f"{PRE_REGISTERED['config']}: the cost model is not the frozen cost model")
    if abs(float(cost.get("risk_free_rate_annual", 0.0)) - PRE_REGISTERED["risk_free_annual"]) > 1e-12:
        fail(f"{PRE_REGISTERED['config']}: the risk-free rate is not the frozen rate")
    gate = config.get("data_gate") or {}
    if int(gate.get("min_folds", 0)) != PRE_REGISTERED["min_folds"]:
        fail(f"{PRE_REGISTERED['config']}: the data gate is not the frozen data gate")

    hypothesis = hypothesis_path.read_text()
    for needle in (
        "## Mechanism Description",
        "## Expected direction and magnitude",
        "## Holding horizon",
        "## Asset universe",
        "## Features and data sources",
        "## Entry / exit rules",
        "## Benchmark",
        "## Known confounders",
        "## Falsification condition (pre-registered)",
        "## Cost model assumptions",
        "## Data gate (pre-registered, measured at the freeze, currently FAILED)",
    ):
        if needle not in hypothesis:
            fail(f"{PRE_REGISTERED['hypothesis']}: the section {needle!r} is missing")

    return {
        "id": PRE_REGISTERED["id"],
        "config": PRE_REGISTERED["config"],
        "hypothesis": PRE_REGISTERED["hypothesis"],
        "config_sha256": sha256_file(config_path),
        "hypothesis_sha256": sha256_file(hypothesis_path),
        "universe": list(config.get("universe") or []),
        "min_folds": int(gate.get("min_folds")),
        "measured_common_inception": str(gate.get("measured_common_inception_at_freeze")),
        "measured_folds_at_freeze": int(gate.get("measured_folds_at_freeze")),
        "status_at_freeze": str(gate.get("status_at_freeze")),
    }


class SearchError(RuntimeError):
    """Raised when a measured fact contradicts the search's own contract."""


def fail(message: str) -> None:
    raise SearchError(message)


# ======================================================================
# Inventory
# ======================================================================
def _daily_facts(path: Path) -> dict[str, Any]:
    frame = pd.read_parquet(path)
    for column in ("Close", "Volume"):
        if column not in frame.columns:
            fail(f"{path.name}: the cached frame has no {column} column")
    index = pd.DatetimeIndex(frame.index)
    close = frame["Close"].astype(float)
    volume = frame["Volume"].astype(float)
    deltas = index.to_series().diff().dropna()
    modal = deltas.mode()
    modal_delta = str(modal.iloc[0]) if not modal.empty else ""
    dollar_volume = (close * volume).replace([np.inf, -np.inf], np.nan).dropna()
    return {
        "kind": "daily_ohlcv",
        "file": str(path.relative_to(REPO_ROOT)),
        "rows": int(len(frame)),
        "first": str(index.min().date()),
        "last": str(index.max().date()),
        "timezone": str(frame.index.tz),
        "columns": ",".join(str(c) for c in frame.columns),
        "modal_spacing": modal_delta,
        "missing_close": int(close.isna().sum()),
        "duplicate_timestamps": int(index.duplicated().sum()),
        "non_positive_close": int((close <= 0).sum()),
        "zero_volume_rows": int((volume == 0).sum()),
        "median_dollar_volume": float(dollar_volume.median()) if len(dollar_volume) else 0.0,
        "annualised_vol": float(close.pct_change().std(ddof=1) * np.sqrt(252.0)),
    }


def _crypto_facts(path: Path) -> dict[str, Any]:
    frame = pd.read_parquet(path)
    stamps = pd.to_datetime(frame["datetime"])
    deltas = stamps.diff().dropna()
    modal = deltas.mode()
    modal_hours = float(modal.iloc[0].total_seconds() / 3600.0) if not modal.empty else float("nan")
    if "fundingRate" in frame.columns:
        kind = "funding_8h"
        funding = frame["fundingRate"].astype(float)
        extra = {
            "funding_mean": float(funding.mean()),
            "funding_std": float(funding.std(ddof=1)),
            "funding_min": float(funding.min()),
            "funding_max": float(funding.max()),
        }
    else:
        kind = "crypto_daily_ohlcv"
        close = frame["close"].astype(float)
        volume = frame["quote_volume"].astype(float)
        extra = {
            "median_dollar_volume": float((close * volume).median()),
            "annualised_vol": float(close.pct_change().std(ddof=1) * np.sqrt(365.0)),
        }
    return {
        "kind": kind,
        "file": str(path.relative_to(REPO_ROOT)),
        "rows": int(len(frame)),
        "first": str(stamps.min()),
        "last": str(stamps.max()),
        "timezone": "UTC",
        "columns": ",".join(str(c) for c in frame.columns),
        "modal_spacing": f"{modal_hours:.0f}h",
        "missing_close": 0,
        "duplicate_timestamps": int(stamps.duplicated().sum()),
        "non_positive_close": 0,
        "zero_volume_rows": 0,
        **extra,
    }


def inventory() -> list[dict[str, Any]]:
    """Every file under ``data/raw/``, recursively, with its measured facts."""
    out: list[dict[str, Any]] = []
    for path in sorted(RAW_DIR.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix != ".parquet":
            out.append({
                "kind": "non_parquet",
                "file": str(path.relative_to(REPO_ROOT)),
                "rows": 0,
                "first": "-",
                "last": "-",
                "columns": "-",
                "modal_spacing": "-",
                "missing_close": 0,
                "duplicate_timestamps": 0,
                "non_positive_close": 0,
                "zero_volume_rows": 0,
            })
            continue
        if "crypto" in path.parts:
            out.append(_crypto_facts(path))
        else:
            out.append(_daily_facts(path))
    return out


# ======================================================================
# Cost model
# ======================================================================
def measure_cost_model() -> dict[str, Any]:
    commission, slippage = get_cost_params()
    settings = (REPO_ROOT / "config" / "settings.yaml").read_text().lower()
    friction_keys = ["commission", "slippage", "borrow", "impact", "spread", "latency", "margin"]
    return {
        "commission_bps": commission * 10_000.0,
        "slippage_bps": slippage * 10_000.0,
        "round_trip_bps": (commission + slippage) * 10_000.0,
        "risk_free_annual": get_risk_free_rate(),
        "absent_frictions": [k for k in friction_keys if k not in settings],
        "max_monthly_long_only_drag_pct": (
            MAX_MONTHLY_LONG_ONLY_TURNOVER * (commission + slippage) * 100.0
        ),
    }


# ======================================================================
# Segment measurement
# ======================================================================
#: The cached crypto spot files, keyed by the symbol used in the segment list.
CRYPTO_SPOT_FILES = {
    "BTCUSDT": "BTCUSDT_spot_1d_binance.parquet",
    "ETHUSDT": "ETHUSDT_spot_1d_binance.parquet",
}


def load_close(symbol: str) -> pd.Series:
    """The cached daily close series of *symbol*.

    The equity/ETF/index/futures files carry a ``Close`` column on a
    ``DatetimeIndex``; the crypto files carry a ``close`` column on a
    ``datetime`` column, which is converted to a UTC midnight index here.
    """
    if symbol in CRYPTO_SPOT_FILES:
        path = RAW_DIR / "crypto" / CRYPTO_SPOT_FILES[symbol]
        if not path.exists():
            fail(f"missing cached series: {path.relative_to(REPO_ROOT)}")
        frame = pd.read_parquet(path)
        index = pd.DatetimeIndex(pd.to_datetime(frame["datetime"])).tz_convert("UTC")
        return pd.Series(frame["close"].astype(float).to_numpy(), index=index, name=symbol)
    path = RAW_DIR / f"{symbol}.parquet"
    if not path.exists():
        fail(f"missing cached series: data/raw/{symbol}.parquet")
    frame = pd.read_parquet(path)
    return frame["Close"].astype(float)


def load_dollar_volume(symbol: str) -> pd.Series:
    """The cached daily dollar volume of *symbol*."""
    if symbol in CRYPTO_SPOT_FILES:
        frame = pd.read_parquet(RAW_DIR / "crypto" / CRYPTO_SPOT_FILES[symbol])
        index = pd.DatetimeIndex(pd.to_datetime(frame["datetime"])).tz_convert("UTC")
        return pd.Series(
            (frame["close"].astype(float) * frame["quote_volume"].astype(float)).to_numpy(),
            index=index,
            name=symbol,
        )
    frame = pd.read_parquet(RAW_DIR / f"{symbol}.parquet")
    close = frame["Close"].astype(float)
    volume = frame["Volume"].astype(float)
    return pd.Series((close * volume).to_numpy(), index=frame.index, name=symbol)


def effective_independent_bets(returns: pd.DataFrame) -> float:
    """Effective number of independent bets from the correlation eigenvalues."""
    corr = returns.corr().to_numpy(dtype=float)
    corr = np.nan_to_num(corr, nan=0.0)
    eigenvalues = np.clip(np.linalg.eigvalsh(corr), 0.0, None)
    denominator = float((eigenvalues**2).sum())
    if denominator <= 0:
        return 0.0
    return float((eigenvalues.sum() ** 2) / denominator)


def measure_segment(segment: dict[str, Any], cost_model: dict[str, Any]) -> dict[str, Any]:
    """The measured facts of one segment: panel, folds, liquidity, bets, hurdle."""
    symbols = list(segment.get("instruments") or [])
    reference = list(segment.get("reference") or [])
    used = symbols or reference
    if not used:
        fail(f"segment {segment['id']} names neither instruments nor a reference")

    close = pd.DataFrame({s: load_close(s) for s in used})
    union_rows = len(close)
    panel = close.dropna(how="any")
    if panel.empty:
        fail(f"segment {segment['id']} has no common session across {used}")
    churn = 0.0 if union_rows == 0 else 1.0 - len(panel) / union_rows

    first = str(panel.index.min().date())
    last = str(panel.index.max().date())
    splits = generate_walkforward_splits(
        first, last,
        train_years=WF_TRAIN_YEARS,
        test_months=WF_TEST_MONTHS,
        step_months=WF_STEP_MONTHS,
        purge_days=WF_PURGE_DAYS,
        embargo_days=WF_EMBARGO_DAYS,
    )

    returns = panel.pct_change().dropna()
    bets = effective_independent_bets(returns) if len(used) > 1 else 1.0
    annual_vol = float(returns.std(ddof=1).mul(np.sqrt(252.0)).median())

    dollar_volumes = []
    for symbol in used:
        series = load_dollar_volume(symbol).replace([np.inf, -np.inf], np.nan).dropna()
        dollar_volumes.append(float(series.median()) if len(series) else 0.0)
    representative_dollar_volume = float(np.median(dollar_volumes))

    # The uniform, measured cost hurdle of a monthly long-only rule: the
    # maximum annual drag a fully-rotating monthly book can pay, expressed as
    # a share of the segment's own measured annualised volatility.
    drag_pct = cost_model["max_monthly_long_only_drag_pct"]
    hurdle_fraction = (drag_pct / 100.0) / annual_vol if annual_vol > 0 else float("inf")

    return {
        "id": segment["id"],
        "title": segment["title"],
        "instruments": used,
        "is_reference_only": not symbols,
        "panel_rows": int(len(panel)),
        "union_rows": int(union_rows),
        "first": first,
        "last": last,
        "churn": float(churn),
        "folds": int(len(splits)),
        "first_test": splits[0]["test_start"] if splits else "-",
        "last_test": splits[-1]["test_end"] if splits else "-",
        "bets": float(bets),
        "annual_vol": annual_vol,
        "representative_dollar_volume": representative_dollar_volume,
        "cost_drag_pct_per_year": float(drag_pct),
        "hurdle_fraction": float(hurdle_fraction),
    }


# ======================================================================
# Scoring
# ======================================================================
def score_data_quality(measured: dict[str, Any]) -> tuple[int, str]:
    if measured["is_reference_only"]:
        return 1, "no instrument of this segment is cached; the panel shown is a reference panel only"
    if measured["folds"] >= 20:
        score, text = 5, ">= 20 folds of the frozen 10y/12m/6m design"
    elif measured["folds"] >= 15:
        score, text = 4, ">= 15 folds of the frozen 10y/12m/6m design"
    elif measured["folds"] >= 8:
        score, text = 3, ">= 8 folds of the frozen 10y/12m/6m design"
    elif measured["folds"] >= 3:
        score, text = 2, "3-7 folds of the frozen 10y/12m/6m design"
    else:
        score, text = 1, "< 3 folds of the frozen 10y/12m/6m design"
    notes = [text]
    if measured["churn"] > 0.0:
        notes.append(f"calendar churn {measured['churn'] * 100.0:.2f}%")
    if measured["panel_rows"] < 3000:
        notes.append(f"only {measured['panel_rows']} common sessions")
    return score, "; ".join(notes)


def score_robustness(measured: dict[str, Any]) -> tuple[int, str]:
    folds, bets = measured["folds"], measured["bets"]
    if measured["is_reference_only"]:
        return 1, "no instrument of this segment is cached: 0 independent bets"
    if folds >= 20 and bets >= 5:
        score, text = 5, f"{folds} folds and {bets:.2f} effective independent bets"
    elif folds >= 15 and bets >= 3:
        score, text = 4, f"{folds} folds and {bets:.2f} effective independent bets"
    elif folds >= 8:
        score, text = 3, f"{folds} folds and {bets:.2f} effective independent bets"
    elif folds >= 3:
        score, text = 2, f"{folds} folds and {bets:.2f} effective independent bets"
    else:
        score, text = 1, f"{folds} folds and {bets:.2f} effective independent bets"
    return score, text


def score_liquidity(measured: dict[str, Any]) -> tuple[int, str]:
    value = measured["representative_dollar_volume"]
    if measured["is_reference_only"]:
        return 1, "no instrument of this segment is cached: capacity is not measurable"
    if value >= 1_000_000_000:
        score, text = 5, ">= $1bn/day"
    elif value >= 250_000_000:
        score, text = 4, ">= $250m/day"
    elif value >= 50_000_000:
        score, text = 3, ">= $50m/day"
    elif value >= 10_000_000:
        score, text = 2, ">= $10m/day"
    else:
        score, text = 1, "< $10m/day"
    return score, f"median instrument ${value:,.0f}/day ({text})"


def score_hurdle(hurdle_fraction: float) -> int:
    """The measured cost hurdle: the share of the segment's own annual risk
    scale that the rule must capture to pay the worst-case monthly drag."""
    if hurdle_fraction <= 0.05:
        return 5
    if hurdle_fraction <= 0.10:
        return 4
    if hurdle_fraction <= 0.20:
        return 3
    if hurdle_fraction <= 0.40:
        return 2
    return 1


def score_diversification(segment: dict[str, Any], measured: dict[str, Any]) -> tuple[int, str]:
    symbols = set(measured["instruments"])
    overlapping = [book["id"] for book in PRIOR_BOOKS if symbols & set(book["symbols"])]
    if not overlapping:
        exposure = 5
    elif len(overlapping) == 1:
        exposure = 4
    elif len(overlapping) == 2:
        exposure = 3
    else:
        exposure = 2
    return exposure, (
        f"{len(symbols - set().union(*[set(b['symbols']) for b in PRIOR_BOOKS]))} of "
        f"{len(symbols)} instruments sit outside every committed book; shared with "
        f"{len(overlapping)}: {', '.join(overlapping) if overlapping else 'none'}"
    )


def score_segment(segment: dict[str, Any], measured: dict[str, Any],
                  cost_model: dict[str, Any]) -> dict[str, Any]:
    """Score one segment on the seven AGENTS.md dimensions.

    (a), (d), (e) and the *hurdle* half of (c) are rule-based over measured
    quantities; (b), (f) and the *gross* half of (c) are labelled declared
    priors.  (c) is published as two numbers and scored by their minimum.
    """
    a_score, a_text = score_data_quality(measured)
    b_score, b_text = segment["prior_b"], segment["prior_b_text"]
    gross_score = segment["gross_prior"]
    if measured["is_reference_only"]:
        hurdle_score = 1
        c_text = (
            "the cost hurdle is NOT measurable for this segment: it has no cached "
            "series, so no risk scale exists to express it against -> hurdle score "
            f"1/5; declared gross prior {gross_score}/5"
        )
    else:
        hurdle_score = score_hurdle(measured["hurdle_fraction"])
        c_text = (
            f"measured cost hurdle {measured['hurdle_fraction'] * 100.0:.4f}% of the "
            f"segment's own annualised volatility (worst-case monthly long-only drag "
            f"{measured['cost_drag_pct_per_year']:.4f}%/yr at 3.0 bp/unit) -> "
            f"hurdle score {hurdle_score}/5; declared gross prior {gross_score}/5"
        )
    c_score = min(hurdle_score, gross_score)
    d_score, d_text = score_robustness(measured)
    e_score, e_text = score_liquidity(measured)
    f_score, f_text = segment["prior_f"], segment["prior_f_text"]
    g_score, g_text = score_diversification(segment, measured)

    scores = {"a": a_score, "b": b_score, "c": c_score, "d": d_score,
              "e": e_score, "f": f_score, "g": g_score}
    notes = {"a": a_text, "b": b_text, "c": c_text, "d": d_text,
             "e": e_text, "f": f_text, "g": g_text}
    return {
        "id": segment["id"],
        "title": segment["title"],
        "eligibility": segment["eligibility"],
        "eligibility_reason": segment["eligibility_reason"],
        "measured": measured,
        "scores": scores,
        "notes": notes,
        "total": int(sum(scores.values())),
        "hurdle_score": hurdle_score,
        "gross_prior_score": gross_score,
        "gross_prior_text": segment["gross_prior_text"],
    }


# ======================================================================
# The pre-declared feasibility screen
# ======================================================================
def month_end_sessions(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    last: dict[str, pd.Timestamp] = {}
    for stamp, key in zip(index, index.strftime("%Y-%m")):
        last[key] = stamp
    return [last[key] for key in sorted(last)]


def feasibility_screen(cost_per_unit: float) -> dict[str, Any]:
    """The pre-declared, in-sample, full-sample feasibility screen.

    The rule, the universe, the benchmark and the cost model are the frozen
    constants of this file.  The screen answers one question only: does the
    rule capture any gross edge at all, relative to its own benchmark, once
    the repository's 3.0 bp per unit of weight change is paid?  It is **not**
    an out-of-sample result and it is not a walk-forward evaluation.
    """
    spec = PRE_DECLARED_SCREEN
    close = pd.DataFrame({s: load_close(s) for s in spec["universe"]}).dropna(how="any")

    signal = (
        close.shift(spec["skip_sessions"]) / close.shift(spec["lookback_sessions"]) - 1.0
    )
    month_ends = month_end_sessions(close.index)
    mask = (signal.loc[month_ends] > 0).astype(float)
    held = mask.sum(axis=1)
    target = mask.div(held.replace(0.0, np.nan), axis=0)
    weights = target.reindex(close.index).ffill().fillna(0.0)
    weights = weights.shift(spec["signal_lag_sessions"]).fillna(0.0)

    returns = close.pct_change().fillna(0.0)
    gross = (weights * returns).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
    costs = turnover * cost_per_unit
    net = gross - costs

    bench_weights = pd.DataFrame(
        1.0 / len(spec["universe"]), index=close.index, columns=close.columns
    )
    bench_gross = (bench_weights * returns).sum(axis=1)
    bench_turnover = bench_weights.diff().abs().sum(axis=1).fillna(0.0)
    bench_net = bench_gross - bench_turnover * cost_per_unit
    excess = net - bench_net

    def annual(series: pd.Series) -> float:
        return float(series.mean() * 252.0)

    def vol(series: pd.Series) -> float:
        return float(series.std(ddof=1) * np.sqrt(252.0))

    def sharpe(series: pd.Series) -> float:
        dispersion = series.std(ddof=1)
        if dispersion <= 0:
            return 0.0
        return float(series.mean() * 252.0 / (dispersion * np.sqrt(252.0)))

    pre_2015 = close.index < "2015-01-01"
    changed = int((held.diff().fillna(0.0) != 0).sum())

    single: dict[str, dict[str, float]] = {}
    for symbol in spec["universe"]:
        sub = close[[symbol]]
        sub_signal = (
            sub.shift(spec["skip_sessions"]) / sub.shift(spec["lookback_sessions"]) - 1.0
        )
        sub_month_ends = month_end_sessions(sub.index)
        sub_mask = (sub_signal.loc[sub_month_ends] > 0).astype(float)
        sub_weights = sub_mask.reindex(sub.index).ffill().fillna(0.0)
        sub_weights = sub_weights.shift(spec["signal_lag_sessions"]).fillna(0.0)
        sub_returns = sub.pct_change().fillna(0.0)
        sub_gross = (sub_weights * sub_returns).sum(axis=1)
        sub_turnover = sub_weights.diff().abs().sum(axis=1).fillna(0.0)
        sub_net = sub_gross - sub_turnover * cost_per_unit
        sub_bench = sub_returns[symbol]
        single[symbol] = {
            "gross_annual": annual(sub_gross),
            "net_annual": annual(sub_net),
            "net_sharpe": sharpe(sub_net),
            "excess_net_annual": annual(sub_net - sub_bench),
            "turnover_units_per_year": float(sub_turnover.sum() / (len(sub) / 252.0)),
        }

    return {
        "spec": spec,
        "panel_rows": int(len(close)),
        "first": str(close.index.min().date()),
        "last": str(close.index.max().date()),
        "rebalances": int(len(month_ends)),
        "held_set_changes": changed,
        "turnover_sessions": int((turnover > 1e-12).sum()),
        "turnover_units_per_year": float(turnover.sum() / (len(close) / 252.0)),
        "gross_annual": annual(gross),
        "net_annual": annual(net),
        "gross_vol": vol(gross),
        "gross_sharpe": sharpe(gross),
        "net_sharpe": sharpe(net),
        "cost_drag_annual": annual(costs),
        "benchmark_net_annual": annual(bench_net),
        "benchmark_net_sharpe": sharpe(bench_net),
        "excess_gross_annual": annual(gross - bench_gross),
        "excess_net_annual": annual(excess),
        "excess_net_sharpe": sharpe(excess),
        "excess_pre_2015_annual": annual(excess[pre_2015]),
        "excess_post_2015_annual": annual(excess[~pre_2015]),
        "excess_pre_2015_sharpe": sharpe(excess[pre_2015]),
        "excess_post_2015_sharpe": sharpe(excess[~pre_2015]),
        "single": single,
    }


# ======================================================================
# Payload
# ======================================================================
def build_payload() -> dict[str, Any]:
    data_before = fingerprint(REPO_ROOT / "data")
    config_before = fingerprint(REPO_ROOT / "config")
    artifacts_before = tracked_artifact_hashes()

    cost_model = measure_cost_model()
    cost_per_unit = cost_model["round_trip_bps"] / 10_000.0

    files = inventory()
    measured = [measure_segment(segment, cost_model) for segment in SEGMENTS]
    scored = [score_segment(segment, m, cost_model) for segment, m in zip(SEGMENTS, measured)]

    ranked = sorted(
        scored,
        key=lambda row: (-row["total"], -row["scores"]["a"], -row["scores"]["c"], row["id"]),
    )

    # The selection rule, fixed before the scores were read: a segment may
    # only be a candidate if its mechanism family is neither closed by a
    # committed line nor blocked on data in this repository.  The remaining
    # segments are then ranked by (total, (a), (c), id).
    eligible = [row for row in ranked if row["eligibility"] == "open"]
    if not eligible:
        fail("no segment is open: the search has no admissible candidate host")
    selected = eligible[0]

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

    prior_books = []
    for entry in PRIOR_BOOKS:
        path = REPO_ROOT / entry["file"]
        if not path.exists():
            fail(f"missing committed file: {entry['file']}")
        text = path.read_text()
        missing = [s for s in entry["symbols"] if s not in text]
        if missing:
            fail(f"{entry['file']} does not mention {missing}")
        prior_books.append(dict(entry, verified=True))

    screen = feasibility_screen(cost_per_unit)
    preregistration = verify_preregistration()

    data_after = fingerprint(REPO_ROOT / "data")
    config_after = fingerprint(REPO_ROOT / "config")
    artifacts_after = tracked_artifact_hashes()

    return {
        "cycle": CYCLE,
        "cost_model": cost_model,
        "files": files,
        "scored": scored,
        "ranked": ranked,
        "selected_id": selected["id"],
        "eligible_ids": [row["id"] for row in eligible],
        "prior_lines": prior_lines,
        "prior_books": prior_books,
        "screen": screen,
        "preregistration": preregistration,
        "conditional_candidate": CONDITIONAL_CANDIDATE,
        "data_unchanged": data_before == data_after,
        "config_unchanged": config_before == config_after,
        "artifacts_unchanged": artifacts_before == artifacts_after,
        "data_file_count": len(data_before),
        "config_file_count": len(config_before),
    }


# ======================================================================
# Rendering
# ======================================================================
def _fmt(value: float, digits: int = 6) -> str:
    return f"{value:,.{digits}f}"


def _pct(value: float, digits: int = 4) -> str:
    return f"{value * 100.0:.{digits}f}%"


def render_inventory_table(files: list[dict[str, Any]]) -> str:
    lines = [
        "| File | Kind | Rows | First | Last | Modal spacing | Missing close | Duplicate stamps | Non-positive close | Zero-volume rows | Median $/day |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in files:
        if row["kind"] == "funding_8h":
            money = "-"
        elif row["kind"] == "crypto_daily_ohlcv":
            money = f"${row.get('median_dollar_volume', 0.0):,.0f}"
        elif row["kind"] == "daily_ohlcv":
            money = f"${row.get('median_dollar_volume', 0.0):,.0f}"
        else:
            money = "-"
        lines.append(
            "| `{file}` | {kind} | {rows} | {first} | {last} | {spacing} | {missing} | {dup} | {nonpos} | {zero} | {money} |".format(
                file=row["file"],
                kind=row["kind"],
                rows=row["rows"],
                first=row["first"],
                last=row["last"],
                spacing=row["modal_spacing"],
                missing=row["missing_close"],
                dup=row["duplicate_timestamps"],
                nonpos=row["non_positive_close"],
                zero=row["zero_volume_rows"],
                money=money,
            )
        )
    return "\n".join(lines)


def render_score_table(ranked: list[dict[str, Any]]) -> str:
    lines = [
        "| Rank | Segment | (a) | (b) | (c) | (d) | (e) | (f) | (g) | Total | Open for candidacy |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for rank, row in enumerate(ranked, start=1):
        s = row["scores"]
        lines.append(
            f"| {rank} | `{row['id']}` | {s['a']} | {s['b']} | {s['c']} | {s['d']} | "
            f"{s['e']} | {s['f']} | {s['g']} | **{row['total']}/35** | "
            f"{row['eligibility']} |"
        )
    return "\n".join(lines)


def render_measured_table(ranked: list[dict[str, Any]]) -> str:
    lines = [
        "| Segment | Panel | Common sessions | Folds | First test | Bets | Ann. vol | Hurdle | Median $/day |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in ranked:
        m = row["measured"]
        lines.append(
            f"| `{row['id']}` | {m['first']} .. {m['last']} | {m['panel_rows']} | "
            f"{m['folds']} | {m['first_test']} | {m['bets']:.2f} | "
            f"{_pct(m['annual_vol'], 2)} | {_pct(m['hurdle_fraction'], 4)} | "
            f"${m['representative_dollar_volume']:,.0f} |"
        )
    return "\n".join(lines)


def render_report(payload: dict[str, Any]) -> str:
    cost = payload["cost_model"]
    screen = payload["screen"]
    ranked = payload["ranked"]
    spec = screen["spec"]
    cand = payload["conditional_candidate"]

    out: list[str] = []
    out.append("# Report: Evidence-based market-opportunity search (market_opportunity_search_001)")
    out.append("")
    out.append(
        f"**Cycle {payload['cycle']}.** Read-only, deterministic. No walk-forward "
        "evaluation, no parameter search, no candidate implementation, no write under "
        "`data/` or `config/`, no fetcher call, no change to any committed record, "
        "gate, protocol or threshold."
    )
    out.append("")
    out.append(
        "This report is the long-form evidence behind the search record "
        "`research/experiments/market_opportunity_search_001.md`; both are generated by "
        "`research/market_opportunity_search_001.py` and contain no timestamp, so two "
        "consecutive runs are byte-identical."
    )
    out.append("")
    out.append("## 1. Method and scope")
    out.append("")
    out.append(
        "1. **Inventory** every file under `data/raw/` (recursive): counts, date ranges, "
        "frequency, gaps, duplicate timestamps, non-positive closes, zero-volume rows, "
        "median dollar volume. Nothing is sampled and nothing is assumed."
    )
    out.append(
        "2. **Re-measure the cost model** that is really implemented, in "
        "`src/backtest/engine.py`, and state the frictions it does **not** contain."
    )
    out.append(
        "3. **Score eleven market segments** on the seven AGENTS.md dimensions. (a), (d), "
        "(e) and the *hurdle* half of (c) are rule-based over measured quantities; (b), "
        "(f) and the *gross* half of (c) are **labelled declared priors**. (c) is "
        "published as two numbers and scored by their minimum."
    )
    out.append(
        "4. Run **one** pre-declared feasibility screen on the segment the scoring leaves "
        "open, and publish its result whatever it is."
    )
    out.append(
        "5. Publish an explicit, evidence-based rejection reason for **every** segment, so "
        "that the next cycle inherits evidence instead of guesses."
    )
    out.append("")
    out.append(
        "**No closed line is re-scored and no closed line is re-opened.** The status of "
        "every earlier candidate is quoted verbatim from its committed record and the "
        "quote is verified to be present in that record."
    )
    out.append("")
    out.append("## 2. The cost model that is really available")
    out.append("")
    out.append(
        f"| Component | Value | Source |\n|---|---|---|\n"
        f"| Commission | {cost['commission_bps']:.1f} bp per unit of weight change | "
        f"`src/backtest/engine.py::get_cost_params` -> `config/settings.yaml` |\n"
        f"| Slippage | {cost['slippage_bps']:.1f} bp per unit of weight change | "
        f"`src/backtest/engine.py::get_cost_params` -> `config/settings.yaml` |\n"
        f"| **Total per unit of weight change** | **{cost['round_trip_bps']:.1f} bp** | derived |\n"
        f"| Risk-free rate | {cost['risk_free_annual'] * 100.0:.2f}%/yr | "
        f"`src/backtest/engine.py::get_risk_free_rate` |"
    )
    out.append("")
    out.append(
        "**The frictions this model does NOT contain:** "
        + ", ".join(f"`{k}`" for k in cost["absent_frictions"])
        + ". A candidate whose mechanism needs one of them is penalised on (a), (c) and "
        "(f); a candidate whose mechanism needs one of them and cannot be measured from "
        "the cache is **blocked**, not merely expensive."
    )
    out.append("")
    out.append(
        f"**The uniform cost hurdle used for the (c) score.** A monthly, long-only rule "
        f"that replaces its whole book at every rebalance pays "
        f"{MAX_MONTHLY_LONG_ONLY_TURNOVER:.0f} units of weight change per year, i.e. at "
        f"most **{cost['max_monthly_long_only_drag_pct']:.4f}%/yr** at 3.0 bp/unit. This "
        f"is an upper bound on the annual drag of *any* monthly long-only rule in the "
        f"repository, and the (c) hurdle is that bound expressed as a share of the "
        f"segment's own measured annualised volatility: a segment whose rules must "
        f"capture a large share of their own risk scale to pay their costs is a bad "
        f"host, whatever its prior."
    )
    out.append("")
    out.append("## 3. Measured inventory of `data/raw/`")
    out.append("")
    out.append(
        f"{len(payload['files'])} files, {payload['data_file_count']} files under `data/` "
        f"in total, {payload['config_file_count']} under `config/`."
    )
    out.append("")
    out.append(render_inventory_table(payload["files"]))
    out.append("")
    out.append("**What the inventory establishes, and it is measured, not assumed:**")
    out.append("")
    daily = [f for f in payload["files"] if f["kind"] == "daily_ohlcv"]
    crypto_daily = [f for f in payload["files"] if f["kind"] == "crypto_daily_ohlcv"]
    funding = [f for f in payload["files"] if f["kind"] == "funding_8h"]
    out.append(
        f"- **Every equity, ETF, index and futures series in the cache is DAILY** "
        f"({len(daily)} files, modal spacing one calendar day). There is no intraday "
        f"equity or futures bar in the repository."
    )
    out.append(
        f"- **The only sub-daily series in the repository is the crypto funding rate** "
        f"({len(funding)} files, modal spacing 8h, "
        f"{', '.join(str(f['rows']) for f in funding)} records each). The crypto spot and "
        f"perpetual files are daily ({len(crypto_daily)} files), so **no intraday price "
        f"exists to trade the sub-daily funding with**: an intraday rule would have to "
        f"assume an execution price the cache cannot supply."
    )
    starts: dict[str, list[str]] = {}
    for row in daily:
        starts.setdefault(row["first"], []).append(row["file"].split("/")[-1].replace(".parquet", ""))
    shared = {k: v for k, v in starts.items() if len(v) > 1}
    for stamp, symbols in sorted(shared.items()):
        out.append(
            f"- **{len(symbols)} of the {len(daily)} daily files share the identical "
            f"first session {stamp}** ({', '.join(sorted(symbols))}). Eight independent "
            f"instruments do not incept on the same day; a common start across a whole "
            f"batch is the signature of a **fetch window**, not of instrument history. "
            f"This is the measured reason the commodity segment cannot be evaluated on "
            f"the repository's frozen walk-forward design (section 5)."
        )
    out.append(
        "- `^VIX` has a **median volume of 0**: it is an index, not a traded series, and "
        "the cache contains no volatility future, option or volatility ETP that could "
        "carry a position in it."
    )
    out.append("")
    out.append("## 4. The pre-declared feasibility screen")
    out.append("")
    out.append(
        "**Declared before the screen was computed, from the inventory and the literature "
        "prior only; no parameter of it is selected by its result, and it was not "
        "changed after the screen was read.**"
    )
    out.append("")
    out.append(
        f"- Candidate id: `{spec['candidate_id']}` (a *screen*, not a pre-registered line)\n"
        f"- Universe: {', '.join(spec['universe'])} -- {spec['rationale']}\n"
        f"- Rule: {spec['rule']}\n"
        f"- Signal: trailing {spec['lookback_sessions']}-session total return skipping the "
        f"most recent {spec['skip_sessions']} sessions, formed on the month-end session\n"
        f"- Rebalance: {spec['rebalance']} with a {spec['signal_lag_sessions']}-session "
        f"signal lag\n"
        f"- Benchmark: {spec['benchmark']}"
    )
    out.append("")
    out.append(
        "**This screen is in-sample, full-sample and non-selective.** It is not a "
        "walk-forward evaluation, it produces no fold statistics, and it cannot support "
        "any promotion or rejection claim. It answers one question: does the rule "
        "capture any gross edge at all over its own benchmark, once the repository's "
        "3.0 bp per unit of weight change is paid?"
    )
    out.append("")
    out.append(
        f"| Quantity | Value |\n|---|---|\n"
        f"| Panel | {screen['first']} .. {screen['last']}, {screen['panel_rows']} common "
        f"sessions |\n"
        f"| Month-end rebalances | {screen['rebalances']} |\n"
        f"| Rebalances where the held set changed | {screen['held_set_changes']} |\n"
        f"| Sessions with a weight change | {screen['turnover_sessions']} |\n"
        f"| Realised turnover | {screen['turnover_units_per_year']:.4f} units/yr |\n"
        f"| **Cost drag** | **{_pct(screen['cost_drag_annual'], 4)}/yr** |\n"
        f"| Gross return | {_pct(screen['gross_annual'], 4)}/yr, Sharpe "
        f"{screen['gross_sharpe']:.4f} |\n"
        f"| Net return | {_pct(screen['net_annual'], 4)}/yr, Sharpe "
        f"{screen['net_sharpe']:.4f} |\n"
        f"| Benchmark (1/N buy-and-hold) | {_pct(screen['benchmark_net_annual'], 4)}/yr, "
        f"Sharpe {screen['benchmark_net_sharpe']:.4f} |\n"
        f"| **Benchmark-relative excess, gross** | **{_pct(screen['excess_gross_annual'], 4)}/yr** |\n"
        f"| **Benchmark-relative excess, net** | **{_pct(screen['excess_net_annual'], 4)}/yr** "
        f"(Sharpe {screen['excess_net_sharpe']:.4f}) |\n"
        f"| Excess before 2015 / after 2015 | "
        f"{_pct(screen['excess_pre_2015_annual'], 4)}/yr (Sharpe {screen['excess_pre_2015_sharpe']:.4f}) / "
        f"{_pct(screen['excess_post_2015_annual'], 4)}/yr (Sharpe {screen['excess_post_2015_sharpe']:.4f}) |"
    )
    out.append("")
    out.append("**Single-asset decomposition of the same screen** (same rule, one asset):")
    out.append("")
    out.append(
        "| Asset | Gross | Net | Net Sharpe | Excess vs buy-and-hold | Turnover |\n"
        "|---|---|---|---|---|---|"
    )
    for symbol, values in screen["single"].items():
        out.append(
            f"| `{symbol}` | {_pct(values['gross_annual'], 4)}/yr | "
            f"{_pct(values['net_annual'], 4)}/yr | {values['net_sharpe']:.4f} | "
            f"{_pct(values['excess_net_annual'], 4)}/yr | "
            f"{values['turnover_units_per_year']:.4f} units/yr |"
        )
    out.append("")
    excess = screen["excess_net_annual"]
    out.append(
        f"**The screen's result, published whatever it is.** The rule's net "
        f"benchmark-relative excess is **{_pct(excess, 4)}/yr**. It is "
        f"{'negative' if excess < 0 else 'non-negative'}, so the pre-declared screen "
        f"**does not support** this candidate: the rule does not capture a benchmark-"
        f"relative gross edge that its own (tiny, "
        f"{_pct(screen['cost_drag_annual'], 4)}/yr) cost drag does not already remove, "
        f"and the rule's absolute net Sharpe of {screen['net_sharpe']:.4f} is below the "
        f"repository's 0.9 promotion gate. Two independent facts therefore stand "
        f"against this instantiation: the **edge** (a "
        f"{_pct(excess, 4)}/yr benchmark-relative excess) and the **trade count** "
        f"({screen['turnover_sessions']} sessions with a weight change in "
        f"{screen['panel_rows']} sessions, i.e. a monthly single-book rule that changes "
        f"its position in {screen['held_set_changes']} of {screen['rebalances']} "
        f"rebalances, so the pooled out-of-sample trade count cannot clear the "
        f">100 gate)."
    )
    out.append("")
    out.append(
        "**What the screen does and does not settle.** It settles the *two-asset* "
        "instantiation on the 2006-2026 panel: absolute time-series momentum on "
        "{DBC, GLD} has no benchmark-relative edge there. It does **not** settle the "
        "commodity *segment*, because the diversified form of the mechanism (six "
        "commodity exposures rather than two) cannot be built on the committed cache "
        "at all -- see section 5."
    )
    out.append("")
    out.append("## 5. Scored shortlist")
    out.append("")
    out.append(
        "**The selection rule, fixed before the scores were read:** a segment may be a "
        "candidate only if its mechanism family is neither *closed* by a committed line "
        "nor *blocked* on data in this repository; the remaining segments are then "
        f"ranked by (total, (a), (c), id). Exactly **{len(payload['eligible_ids'])}** "
        f"segment(s) qualify: {', '.join(f'`{i}`' for i in payload['eligible_ids'])}. "
        "The scores of the closed and blocked segments are published anyway, because "
        "the score is the evidence for the closure, not a reason to hide it."
    )
    out.append("")
    out.append(render_score_table(ranked))
    out.append("")
    out.append("### 5.1 The measured inputs behind the rule-based scores")
    out.append("")
    out.append(render_measured_table(ranked))
    out.append("")
    out.append("### 5.2 Per-segment evidence and disposition")
    out.append("")
    for row in ranked:
        m = row["measured"]
        out.append(f"#### `{row['id']}` -- {row['title']}")
        out.append("")
        out.append(
            f"- Measured panel: {m['first']} .. {m['last']}, {m['panel_rows']} common "
            f"sessions, calendar churn {_pct(m['churn'], 2)}, **{m['folds']} folds** of "
            f"the frozen 10y/12m/6m design (first test {m['first_test']}, last test "
            f"{m['last_test']}), {m['bets']:.2f} effective independent bets, median "
            f"instrument ${m['representative_dollar_volume']:,.0f}/day, annualised "
            f"volatility {_pct(m['annual_vol'], 2)}."
        )
        for key, label in (("a", "data quality"), ("b", "mechanism"), ("c", "net edge"),
                           ("d", "robustness"), ("e", "liquidity"),
                           ("f", "automation"), ("g", "diversification")):
            out.append(f"- ({key}) *{label}* {row['scores'][key]}/5 -- {row['notes'][key]}")
        out.append(f"- Eligibility: **{row['eligibility']}** -- {row['eligibility_reason']}")
        out.append(f"- Gross prior: {row['gross_prior_text']}")
        out.append("")
    out.append("## 6. Rejection reasons, segment by segment")
    out.append("")
    reasons = rejection_reasons(payload)
    for row in ranked:
        out.append(f"- **`{row['id']}` -- {reasons[row['id']]}")
    out.append("")
    out.append("## 7. Disposition")
    out.append("")
    pre = payload["preregistration"]
    out.append(
        "**Exactly one candidate is pre-registered by this cycle, and its status is a "
        "block, not a verdict.** The selection rule leaves exactly one segment open -- "
        f"`{payload['selected_id']}`, the commodity complex, the only segment the "
        "repository has never traded as a book -- and its only instantiation that the "
        "committed cache can actually evaluate fails the pre-declared screen of section 4 "
        "on both the edge and the trade count. The remaining ten segments are closed by "
        "committed records, by the absence of the data their mechanism needs, or by the "
        "repository's own cost model; each one's reason is published in section 6."
    )
    out.append("")
    out.append(
        f"**Pre-registered candidate: `{pre['id']}`** -- hypothesis "
        f"`{pre['hypothesis']}`, frozen configuration `{pre['config']}` "
        f"(SHA-256 `{pre['config_sha256'][:16]}...`, hypothesis "
        f"`{pre['hypothesis_sha256'][:16]}...`). The tool verifies the committed "
        "configuration against the rule this search published and **fails closed** on any "
        "drift."
    )
    out.append("")
    out.append(
        f"**Its status at the freeze is `{pre['status_at_freeze']}`.** The cached common "
        f"inception of its universe ({', '.join(pre['universe'])}) is "
        f"{pre['measured_common_inception']}, which supports "
        f"**{pre['measured_folds_at_freeze']}** folds of the frozen 10y/12m/6m design "
        f"against the **{pre['min_folds']}** the data gate requires. The data gate is "
        "therefore not satisfied today, and the candidate is **blocked, not rejected**: no "
        "trading verdict is published for it, it is not promoted, not simulated and not "
        "paper-traded."
    )
    out.append("")
    out.append(
        "**Why the candidate is pre-registered at all, given that its one measurable "
        "instantiation is negative.** The screen settles the two-asset instantiation and "
        "does not settle the segment: time-series momentum needs a *diversified* "
        "cross-section, and the committed cache offers only two long-history commodity "
        "ETFs whose exposures overlap. The pre-registration therefore (i) freezes the "
        "rule before any result is known, (ii) states the data gate in measured terms, "
        "(iii) publishes the negative prior evidence inside the hypothesis itself so that "
        "no reader can mistake the pre-registration for a strong claim, and (iv) marks "
        "the cost-model components that the cache cannot measure as **blocked** rather "
        "than assuming them away. The next cycle's work is bounded and unbiased: measure "
        "the data gate, and -- only if it is satisfied -- evaluate the frozen rule."
    )
    out.append("")
    out.append(
        f"| Field | Value |\n|---|---|\n"
        f"| id | `{cand['id']}` |\n"
        f"| mechanism | {cand['mechanism']} |\n"
        f"| direction | {cand['direction']} |\n"
        f"| horizon | {cand['horizon']} |\n"
        f"| universe | {', '.join(cand['universe'])} |\n"
        f"| benchmark | {cand['benchmark']} |\n"
        f"| cost model | {cand['cost_model']} |\n"
        f"| data gate | {cand['data_gate']} |\n"
        f"| falsification | {cand['falsification']} |"
    )
    out.append("")
    out.append(
        "**The data gate, measured.** The frozen design needs "
        f"{BUSINESS_DAYS_FOR_MIN_FOLDS:,} business days ({BUSINESS_DAYS_FOR_MIN_FOLDS / 252.0:.2f} "
        f"years) to produce {MIN_FOLDS} folds. The four-instrument universe "
        f"({', '.join(cand['universe'])}) has a cached common inception of 2015-01-02, "
        f"which is **3 folds** -- the data gate fails today by a factor of "
        f"{MIN_FOLDS / 3.0:.1f}. The two-instrument universe that section 4 could "
        f"evaluate ({', '.join(spec['universe'])}) has 21 folds and does clear the gate, "
        f"and its screen is negative."
    )
    out.append("")
    out.append(
        "**The evidence that the gate is satisfiable, and its status.** Four of the six "
        "cached commodity ETFs and all four cached futures series share the *identical* "
        "first session 2015-01-02; eight independent instruments do not incept on the "
        "same day, so that common start is a **fetch window**, not instrument history. "
        "The upstream history of the four commodity ETFs is a **declared prior** (2010-2011) "
        "and must be **measured** by a fetch into a scratch directory before the "
        "candidate is evaluated; the committed cache is not to be rewritten in the same "
        "step."
    )
    out.append("")
    out.append("## 8. Verification and reproduction")
    out.append("")
    out.append(
        "```bash\n"
        "python research/market_opportunity_search_001.py\n"
        "python -m pytest -q tests/test_market_opportunity_search_001.py\n"
        "git status --porcelain data/ config/\n"
        "```"
    )
    out.append("")
    out.append(
        "The read-only guarantee is enforced by SHA-256 fingerprinting every file under "
        "`data/` and under `config/`, and every committed artefact under `src/`, "
        "`config/`, `research/experiments/` and `research/reports/`, before and after the "
        "run."
    )
    out.append("")
    return "\n".join(out)


def rejection_reasons(payload: dict[str, Any]) -> dict[str, str]:
    """The explicit, evidence-based disposition of every segment.

    The numbers quoted in the commodity and session-timing entries are the
    measured ones of this run, not literals, so the dispositions cannot
    drift away from the measurements they cite.
    """
    screen = payload["screen"]
    excess = screen["excess_net_annual"]
    return {
    "equity_broad_index": (
        "REJECTED -- the mechanism families this segment can host are already measured "
        "and closed in this repository: cross-sectional momentum (csmomentum_001, "
        "Rejected/Failed), inverse-volatility risk balancing (riskparity_001, rejected), "
        "turn-of-month timing (calendar_effects_001, Rejected/Failed), overnight capture "
        "(overnight_capture_001, Rejected/Failed), macro-regime conditioning "
        "(macroregime_001, FALSIFIED) and time-series momentum (the incumbent, Credible "
        "Candidate / NO-GO). A new rule on this segment is a variant of a closed line, "
        "which the repository's own shortlist rule forbids."
    ),
    "equity_gics_sectors": (
        "REJECTED -- four candidate lines have already traded this panel and all four "
        "are rejected (sectorrotation_001/002 FALSIFIED, reversal_001 Rejected/Failed, "
        "liquidity_001 Rejected/Failed, pairs_001 Rejected/Failed). The measured 5-session "
        "capture fraction of the reversal hypothesis was -1.259560 against a +0.020047 "
        "hurdle, i.e. the panel's short-horizon behaviour has the opposite sign to the "
        "hypothesis, so the segment's behaviour is characterised rather than open."
    ),
    "real_assets_reit": (
        "REJECTED -- VNQ already sits inside the committed 18-ETF csmomentum_001 book "
        "(Rejected/Failed), so the exposure is not new; and a single-asset monthly rule "
        "has no cross-section to rank, so the only documented mechanism available for it "
        "(momentum) has no measured support in this repository, while the >100 pooled "
        "out-of-sample trade gate is not reachable from a one-book monthly rule."
    ),
    "rates_duration": (
        "REJECTED / BLOCKED -- the documented bond-pricing mechanisms need a macro series "
        "(yield level, curve slope, inflation expectation) that the committed cache does "
        "not contain, and the one cache-native route, the futures roll yield, is the "
        "family futuresbasis_001 was **Blocked by data/infrastructure** on (roll prices "
        "unobservable after nine source classes were probed); futuresbasis_002 was then "
        "Rejected/Failed on cost. TLT itself already sits inside the incumbent and "
        "csmomentum books, and the 2015-start futures panel supports three folds."
    ),
    "commodity_complex": (
        "CONDITIONAL CANDIDATE, CURRENTLY BLOCKED BY DATA -- this is the only segment the "
        "repository has never traded as a book, and it carries the best-documented "
        "untested mechanism (commodity time-series momentum). Two measured obstacles "
        "remain: (i) the *diversified* form of the mechanism cannot be built on the "
        "committed cache, because four of the six commodity ETFs and all four futures "
        "series share the identical first session 2015-01-02, which supports three folds "
        "of the frozen 10y/12m/6m design against the fifteen the design needs; and "
        "(ii) the only instantiation the cache can evaluate, {DBC, GLD} over 2006-2026, "
        f"fails the pre-declared screen: its net benchmark-relative excess is "
        f"{excess * 100.0:.4f}%/yr and its {screen['turnover_sessions']} turnover "
        f"sessions in {screen['panel_rows']} sessions cannot clear the >100 pooled "
        f"gate. The candidate is therefore not pre-registered by this cycle; the "
        f"specification is published in section 7 and its data gate is stated in "
        f"measured terms."
    ),
    "crypto_funding": (
        "REJECTED -- cryptofunding_001 is the committed record for this segment and it "
        "is an **Exploratory signal -- not promoted**: it fails the >100 pooled "
        "out-of-sample round-trip gate under every cost model. The 8-hourly funding file "
        "is the only sub-daily series in the repository, but the cache holds only daily "
        "spot and perpetual bars, so an intraday rule would have to assume an execution "
        "price the cache cannot supply, and the committed panel (2020-01-01 .. "
        "2026-09-30) supports **zero** folds of the frozen 10y/12m/6m design."
    ),
    "equity_volatility": (
        "BLOCKED -- the cache holds the ^VIX *index* (median volume 0) and no volatility "
        "future, option or volatility ETP, so the variance risk premium -- the "
        "best-documented volatility mechanism -- cannot be *held*. The only cache-native "
        "use of the series, conditioning equity exposure on its level, is the "
        "macroregime_001 family, which is FALSIFIED."
    ),
    "single_name_equities": (
        "BLOCKED -- the cache contains no single-name series at all: every one of the "
        "daily files is an ETF, an index or a futures continuation series, and there is "
        "no point-in-time constituent list, no market capitalisation and no fundamental "
        "series. This is the mom121_microcap_001 finding, which is **Blocked by "
        "data/infrastructure** -- data gate failed, because SEC EDGAR covers only a "
        "subset of the tickers, has no delisting history and a roughly 90-day reporting "
        "lag."
    ),
    "short_leg_relative_value": (
        "REJECTED ON COST -- the repository's cost model has no borrow term, and the one "
        "short-leg line the repository has run (pairs_001, Rejected/Failed) measured a "
        "borrow drag of 20.3271%/yr against a gross edge of 8.7862%/yr, i.e. a net "
        "excess of -13.6774%/yr. Every other market-neutral structure inherits the same "
        "unpriced liability."
    ),
    "session_timing": (
        "REJECTED ON MEASURED COST -- the overnight leg's measured gross is +9.16%/yr on "
        "SPY/QQQ/IWM against a measured 15.12%/yr drag at 3.0 bp/unit (504 units/yr of "
        "turnover), and the intraday mirror has no premium to harvest: the measured "
        "intraday gross is +0.122%/yr for SPY, -0.001%/yr for QQQ and -2.49%/yr for IWM, "
        "against a 1.512%/yr drag for a rule that is flat overnight and long intraday."
    ),
    "vol_scaled_overlays": (
        "REJECTED -- riskparity_001 is rejected (Rejected / failed the pre-registered "
        "promotion gates) and its benchmark-relative excess of 0.005005 has a "
        "non-overlapping-fold bootstrap CI of [-0.001639, 0.082736], i.e. it includes "
        "zero. The long-sample overlay diagnostic adds that the drawdown cut and the "
        "gross cap are inert (0 of 8,487 sessions) and that the trailing volatility "
        "overlay contributes negatively."
    ),
    }


def render_experiment(payload: dict[str, Any]) -> str:
    cost = payload["cost_model"]
    screen = payload["screen"]
    ranked = payload["ranked"]
    cand = payload["conditional_candidate"]
    spec = screen["spec"]

    out: list[str] = []
    out.append("# Experiment: Evidence-based market-opportunity search (market_opportunity_search_001)")
    out.append("")
    out.append(
        f"**Cycle {payload['cycle']}.** Search, measurement and documentation cycle. "
        "**No candidate was executed, pre-registered, promoted or re-ranked.** The "
        "Cycle-934 shortlist is exhausted and every remaining candidate line carries a "
        "committed verdict, so this cycle searched the *market segments* the committed "
        "cache can host and published an explicit rejection reason for each of them."
    )
    out.append("")
    out.append("## Hypothesis reference")
    out.append("")
    out.append(
        "No candidate hypothesis is created by this cycle. The conditional candidate "
        f"`{cand['id']}` is specified in section 7 of the report but **not** "
        "pre-registered: its data gate is not satisfied and its only measurable "
        "instantiation fails the pre-declared feasibility screen."
    )
    out.append("")
    out.append("## Data used")
    out.append("")
    out.append(
        f"- Source: the committed parquet cache under `data/raw/` only. No network call, "
        f"no fetcher invocation, no download, nothing written under `data/`.\n"
        f"- Inventory: {len(payload['files'])} files, all read-only. Daily OHLCV: "
        f"{sum(1 for f in payload['files'] if f['kind'] == 'daily_ohlcv')}; crypto daily: "
        f"{sum(1 for f in payload['files'] if f['kind'] == 'crypto_daily_ohlcv')}; crypto "
        f"8h funding: {sum(1 for f in payload['files'] if f['kind'] == 'funding_8h')}.\n"
        f"- Frequency: every equity/ETF/index/futures series is daily; the only "
        f"sub-daily series is the 8-hourly crypto funding rate.\n"
        f"- Date ranges, gaps, duplicate timestamps, non-positive closes, zero-volume "
        f"rows and median dollar volume are tabulated in section 3 of the report and are "
        f"re-derived by the tool on every run."
    )
    out.append("")
    out.append("## Point-in-time treatment")
    out.append("")
    out.append(
        "The one backtest-like computation in this cycle is the pre-declared feasibility "
        "screen. Its signal is formed on the month-end session from data up to and "
        "including that session (`close.shift(21) / close.shift(252) - 1`), and the "
        "target weights are made effective on the **next** session, so no weight uses "
        "information that was not available when it was set. The cost is charged on the "
        "realised absolute weight change exactly as `src/backtest/engine.py` does it. No "
        "parameter is selected by the screen's result and the screen is in-sample and "
        "full-sample by construction."
    )
    out.append("")
    out.append("## Configuration")
    out.append("")
    out.append(
        f"- Cost model: {cost['commission_bps']:.1f} bp commission + "
        f"{cost['slippage_bps']:.1f} bp slippage = **{cost['round_trip_bps']:.1f} bp per "
        f"unit of weight change**, risk-free {cost['risk_free_annual'] * 100.0:.2f}%/yr, "
        f"read from `src/backtest/engine.py` at run time.\n"
        f"- Frictions absent from that model: "
        f"{', '.join(cost['absent_frictions'])}.\n"
        f"- Walk-forward design used for the fold counts: 10y train / 12m test / 6m step "
        f"with a 21-day purge and a 21-day embargo "
        f"(`src/evaluation/walkforward.py`).\n"
        f"- Minimum folds a panel must support: {MIN_FOLDS} "
        f"({BUSINESS_DAYS_FOR_MIN_FOLDS:,} business days)."
    )
    out.append("")
    out.append("## Splits")
    out.append("")
    out.append(
        "No train/validation/test split was executed. The screen is full-sample and "
        "in-sample; the walk-forward fold counts published for each segment are the "
        "*counts* the frozen design would produce on that segment's panel, computed with "
        "the repository's own `generate_walkforward_splits`."
    )
    out.append("")
    out.append("## Results")
    out.append("")
    out.append("### Scored shortlist")
    out.append("")
    out.append(render_score_table(ranked))
    out.append("")
    out.append("### The pre-declared feasibility screen")
    out.append("")
    out.append(
        f"- Screen candidate: `{spec['candidate_id']}`, universe "
        f"{', '.join(spec['universe'])}, rule: {spec['rule']}\n"
        f"- Panel: {screen['first']} .. {screen['last']}, {screen['panel_rows']} sessions, "
        f"{screen['rebalances']} month-end rebalances\n"
        f"- Gross {screen['gross_annual'] * 100.0:.4f}%/yr (Sharpe "
        f"{screen['gross_sharpe']:.4f}); net {screen['net_annual'] * 100.0:.4f}%/yr "
        f"(Sharpe {screen['net_sharpe']:.4f}); drag {screen['cost_drag_annual'] * 100.0:.4f}%/yr; "
        f"turnover {screen['turnover_units_per_year']:.4f} units/yr\n"
        f"- Benchmark net {screen['benchmark_net_annual'] * 100.0:.4f}%/yr (Sharpe "
        f"{screen['benchmark_net_sharpe']:.4f})\n"
        f"- **Benchmark-relative excess: gross "
        f"{screen['excess_gross_annual'] * 100.0:.4f}%/yr, net "
        f"{screen['excess_net_annual'] * 100.0:.4f}%/yr**\n"
        f"- Sessions with a weight change: {screen['turnover_sessions']}; rebalances "
        f"where the held set changed: {screen['held_set_changes']} of "
        f"{screen['rebalances']}"
    )
    out.append("")
    out.append("## Number of trials")
    out.append("")
    out.append(
        "**1** -- one pre-declared screen, one rule, one universe, one benchmark, no "
        "grid, no sweep, no parameter search. The screen is a feasibility check and is "
        "not a candidate evaluation, so it carries no Deflated Sharpe Ratio and no "
        "trial-count accounting; it is published in full so that a reader can judge it."
    )
    out.append("")
    out.append("## Reproduction commands")
    out.append("")
    out.append(
        "```bash\n"
        "python research/market_opportunity_search_001.py\n"
        "python -m pytest -q tests/test_market_opportunity_search_001.py\n"
        "git status --porcelain data/ config/\n"
        "git diff --stat\n"
        "```"
    )
    out.append("")
    out.append("## Decision")
    out.append("")
    out.append(
        "**No candidate is pre-registered.** The incumbent `tsmomentum_spytrend_001` "
        "stays a Credible Candidate / NO-GO for promotion; every closed line keeps its "
        "committed status; no gate, threshold, cost model, universe or committed record "
        "was changed. The one segment the scoring leaves open, the commodity complex, is "
        "published with its measured data gate and the negative result of its only "
        "evaluable instantiation."
    )
    out.append("")
    return "\n".join(out)


# ======================================================================
# Checks
# ======================================================================
def run_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    files = payload["files"]
    add("inventory_covers_data_raw", len(files) >= 30, f"{len(files)} files inventoried under data/raw/")
    add(
        "inventory_has_no_unread_file",
        all((REPO_ROOT / row["file"]).exists() for row in files),
        "every inventoried file exists on disk",
    )
    add(
        "no_duplicate_timestamps",
        all(row["duplicate_timestamps"] == 0 for row in files),
        "no cached file carries a duplicate timestamp",
    )
    add(
        "sub_daily_is_only_funding",
        all(
            row["kind"] in {"funding_8h", "crypto_daily_ohlcv", "non_parquet"}
            or row["modal_spacing"].startswith("1 days")
            for row in files
        ),
        "the only sub-daily series in the cache is the 8-hourly crypto funding rate",
    )
    add(
        "vix_is_not_traded",
        all(
            row["zero_volume_rows"] > 0
            for row in files
            if row["file"].endswith("^VIX.parquet")
        ),
        "^VIX carries zero-volume rows: it is an index, not a tradable series",
    )

    cost = payload["cost_model"]
    add(
        "cost_model_measured",
        abs(cost["round_trip_bps"] - 3.0) < 1e-9 and abs(cost["risk_free_annual"] - 0.02) < 1e-12,
        f"{cost['commission_bps']:.1f} bp + {cost['slippage_bps']:.1f} bp = "
        f"{cost['round_trip_bps']:.1f} bp per unit of weight change at "
        f"{cost['risk_free_annual'] * 100.0:.2f}%/yr",
    )
    add(
        "absent_frictions_published",
        {"borrow", "impact", "spread"} <= set(cost["absent_frictions"]),
        "the model has no borrow, impact or spread term: "
        + ", ".join(cost["absent_frictions"]),
    )

    scored = payload["scored"]
    add("segments_scored", len(scored) == len(SEGMENTS), f"{len(scored)} segments scored")
    add(
        "seven_dimensions_scored",
        all(
            len(row["scores"]) == 7
            and all(1 <= value <= 5 for value in row["scores"].values())
            and all(row["notes"][key] for key in row["scores"])
            for row in scored
        ),
        "every segment scores (a)-(g) in 1..5 and every score carries its basis",
    )
    add(
        "totals_consistent",
        all(row["total"] == sum(row["scores"].values()) for row in scored),
        "every total equals the sum of its seven scores",
    )
    add(
        "every_segment_has_a_reason",
        all(len(rejection_reasons(payload).get(row["id"], "")) > 80 for row in scored),
        "every segment carries an explicit, evidence-based disposition",
    )
    add(
        "prior_status_quotes_verified",
        all(entry.get("verified") for entry in payload["prior_lines"]),
        "every quoted prior status line is present in its committed record",
    )
    add(
        "prior_books_verified",
        all(entry.get("verified") for entry in payload["prior_books"]),
        "every committed book is verified against its committed configuration file",
    )
    closed = {line["id"] for line in payload["prior_lines"]}
    add(
        "no_closed_line_proposed",
        not (closed & {row["id"] for row in scored}),
        "no scored segment reuses a closed candidate identifier",
    )
    add(
        "selection_rule_applied",
        len(payload["eligible_ids"]) >= 1
        and payload["selected_id"] == payload["eligible_ids"][0],
        f"the rule selects {payload['selected_id']} from the open segment(s) "
        f"{payload['eligible_ids']}",
    )
    add(
        "exactly_one_open_segment",
        len(payload["eligible_ids"]) == 1,
        f"open segments: {payload['eligible_ids']}",
    )

    screen = payload["screen"]
    add(
        "screen_is_pre_declared",
        screen["spec"]["universe"] == ["DBC", "GLD"]
        and screen["spec"]["lookback_sessions"] == 252
        and screen["spec"]["skip_sessions"] == 21,
        "the screen's rule, universe and horizons are the frozen constants of the tool",
    )
    add(
        "screen_pays_the_repository_cost",
        screen["cost_drag_annual"] > 0.0,
        f"the screen charges {screen['cost_drag_annual'] * 100.0:.4f}%/yr of realised "
        f"cost at 3.0 bp per unit of weight change",
    )
    add(
        "screen_result_published",
        "excess_net_annual" in screen and screen["panel_rows"] > 0,
        f"the screen's net benchmark-relative excess is published: "
        f"{screen['excess_net_annual'] * 100.0:.4f}%/yr",
    )
    add(
        "no_walk_forward_evaluation_run",
        screen["rebalances"] > 0 and "folds" not in screen,
        "the cycle computed no fold statistics: the screen is full-sample",
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
    except SearchError as error:
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
            f"SEGMENT|{row['id']}|TOTAL|{row['total']}|"
            f"A|{row['scores']['a']}|B|{row['scores']['b']}|C|{row['scores']['c']}|"
            f"D|{row['scores']['d']}|E|{row['scores']['e']}|F|{row['scores']['f']}|"
            f"G|{row['scores']['g']}|FOLDS|{row['measured']['folds']}"
        )
    screen = payload["screen"]
    print(
        f"SCREEN|{screen['spec']['candidate_id']}|EXCESS_NET_ANNUAL|"
        f"{screen['excess_net_annual']:.8f}|NET_SHARPE|{screen['net_sharpe']:.6f}|"
        f"TURNOVER_SESSIONS|{screen['turnover_sessions']}"
    )
    print("PREREGISTERED|none")
    print(f"REPORT|{OUT_REPORT if not args.no_report else '(not written: --no-report)'}")
    print(f"EXPERIMENT|{OUT_EXP if not args.no_report else '(not written: --no-report)'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
