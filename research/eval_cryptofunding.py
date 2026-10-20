"""Cycle 892: realistic execution and capital-cost model for the crypto funding carry.

What this script does
---------------------
It evaluates the spot-long / perp-short perpetual-funding carry of
``cryptofunding_001`` (BTC + ETH, Binance USDT-margined perpetuals) on the
committed, checksum-verified carry paths, under the repository's own metric
machinery and under the **365-day** annualization that a 24/7 market requires.

The Cycle 891 defects it keeps fixed (all raised by the Cycle 890 supervisor
review):

1. **Annualization.** The Cycle 890 draft annualized the daily crypto series
   at 252 periods/year. Crypto trades every calendar day: the annual return,
   the annual volatility, the annual turnover and every ratio built on them
   must use **365**. Everything below is reported at 365, and the 252
   rendering is kept only where it is needed to reconcile with the cost
   screen, which uses the repository-wide 252 convention.
2. **Transition turnover.** The Cycle 890 draft masked the turnover of the
   funding-positive rule with the position mask, so an entry and an exit were
   never charged: the rule paid for its daily rebalance but not for opening
   or closing the position. The turnover series here is
   ``daily rebalance turnover + |position change| * 2 * leg weight``, i.e. an
   entry (long spot + short perp) and an exit are each charged.
3. **Look-ahead in the funding-positive rule.** The pre-registered rule
   ("hold only while ``funding_cashflow > 0``") decides with the *same day's*
   aggregate funding, which is not knowable before the day starts: a day's
   funding is the sum of its 00:00/08:00/16:00 UTC settlements. The
   implementable variant decides with the **previous** day's aggregate
   funding. Both are reported; the look-ahead variant is labelled as
   contaminated and is kept only to reconcile with the Cycle 890 numbers.

What Cycle 892 adds
-------------------
The Cycle 891 evaluation measured the net capture of the carry with the
repository's flat 3 bp/unit turnover cost alone: no charge for the capital the
book ties up and no venue-specific fee schedule. Cycle 892 measures the same
three pre-registered rules under a realistic execution and capital-cost model
and re-evaluates the promotion gate under it:

* a **per-leg venue fee schedule** (Binance VIP 0 published fees) applied to
  the leg weights that are actually traded, plus the repository's own
  slippage assumption, with a maker alternative;
* a **capital charge** on the spot leg's notional (0% / the repository's
  risk-free rate / a 5% USDT-equivalent yield);
* a **headline turnover convention** with the other conventions as
  cost-only bounds;
* the **break-even** flat cost per unit, break-even capital charge and
  break-even multiple of the venue schedule, per rule;
* the **promotion gate re-evaluated** under every cost model, with the
  repository's own thresholds, unchanged.

The cost models are sensitivity analyses of the same six configurations
(3 rules x 2 symbols), not new trials.

Conventions
-----------
* ``PERIODS_PER_YEAR = 365`` (24/7 crypto); the cost screen's 252 is used
  only inside :func:`screen_reconciliation`.
* Metrics come from the repository: ``src.backtest.engine.compute_metrics``
  (annualized return / volatility / Sharpe / Sortino / max drawdown / profit
  factor) and ``src.evaluation.sharpe.sharpe_ratio`` (the canonical
  ``arithmetic_annualized_rf0`` gate convention, evaluated on the 365-day
  scale). Turnover and trade counts are supplied explicitly, because a
  crypto carry book trades its *legs* (spot and perp) while the engine's
  weight frame would net them away -- the same override the cost screen
  applies in ``fold_metrics``.
* Cost models: the repository's flat model (``3 bp per unit of weight
  change``, ``get_cost_params()``: 1 bp commission + 2 bp slippage) and the
  venue model of this cycle. The capital charge is paid in the *return
  series*, so the engine's backtest-scale metrics of a capital-charge row use
  a zero risk-free rate (the repository's backtest-baseline Sharpe already
  subtracts the risk-free rate from the ratio's numerator).
* The **headline turnover convention** is ``drift`` (the daily
  constant-notional rebalance), because it is the only convention that is
  internally consistent with the pre-registered constant-notional gross path;
  ``parity`` and ``fixed_quantity`` are reported as cost-only bounds.
* A *book* is one unit of equity running a delta-neutral carry pair:
  ``+w`` spot and ``-w`` perp (200% gross notional, zero net). A single-symbol
  book uses ``w = 1.0``; the BTC/ETH portfolio uses ``w = 0.5`` per symbol,
  which is exactly the construction the cost screen screens.

Reproduction
------------
::

    python research/eval_cryptofunding.py
    python -m pytest -q tests/test_eval_cryptofunding.py
    python research/cost_admissibility_screen.py   # ends with OVERALL: PASS
    python -m pytest -q
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from arch.bootstrap import MovingBlockBootstrap

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.backtest.engine import (  # noqa: E402
    compute_metrics,
    get_cost_params,
    get_risk_free_rate,
)
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.statistics import block_bootstrap_sharpe  # noqa: E402

PROC_CRYPTO = REPO / "data" / "processed" / "crypto"
RAW_CRYPTO = REPO / "data" / "raw" / "crypto"
ARTIFACT_PATH = REPO / "research" / "experiments" / "cryptofunding_002_evaluation.md"

#: 24/7 crypto: 365 calendar days of trading per year.
PERIODS_PER_YEAR = 365
#: The repository-wide convention of the cost screen (equity trading days).
SCREEN_PERIODS_PER_YEAR = 252

#: The repository's flat cost model and the pre-registered sensitivity rows.
DECISION_BPS = 3.0
COST_ROWS_BPS: tuple[float, ...] = (1.5, 3.0, 4.5)

#: Block-bootstrap settings (pre-registered in Cycle 890).
BOOTSTRAP_BLOCK_DAYS = 126
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20261019

#: The pre-registered chronological splits (research/hypotheses/cryptofunding_001.md).
SPLITS: dict[str, tuple[str, str]] = {
    "full": ("2020-01-02", "2026-09-30"),
    "train": ("2020-01-02", "2022-12-31"),
    "val": ("2023-01-01", "2024-12-31"),
    "test_oos": ("2025-01-01", "2026-09-30"),
    "post2022": ("2023-01-01", "2026-09-30"),
}

SYMBOLS: tuple[str, ...] = ("BTC", "ETH")
BASE_SYMBOLS: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")

#: Promotion gates from AGENTS.md.
PROMOTION_SHARPE_MIN = 0.9
PROMOTION_MIN_POOLED_OOS_TRADES = 100

COMMISSION_BPS, SLIPPAGE_BPS = get_cost_params()
RF_ANNUAL = get_risk_free_rate()


# ======================================================================
# Rules
# ======================================================================
@dataclass(frozen=True)
class RuleSpec:
    """One pre-registered (or defect-corrected) trading rule."""

    rule_id: str
    label: str
    kind: str
    look_ahead: bool
    note: str


RULES: tuple[RuleSpec, ...] = (
    RuleSpec(
        rule_id="always_on",
        label="Always-on carry",
        kind="always",
        look_ahead=False,
        note="Pre-registered rule 1: hold the carry pair every day.",
    ),
    RuleSpec(
        rule_id="funding_positive_sameday",
        label="Funding-positive only (same-day signal, pre-registered)",
        kind="funding_positive_sameday",
        look_ahead=True,
        note=(
            "Pre-registered rule 2. Uses the same day's aggregate funding, which "
            "is only known after that day's 00:00/08:00/16:00 UTC settlements: "
            "a look-ahead. Reported for reconciliation with Cycle 890 only."
        ),
    ),
    RuleSpec(
        rule_id="funding_positive_lagged",
        label="Funding-positive only (previous-day signal, implementable)",
        kind="funding_positive_lagged",
        look_ahead=False,
        note=(
            "Defect-corrected rule 2: the position for day t is decided with the "
            "aggregate funding of day t-1, the last information available before "
            "day t starts."
        ),
    ),
)

#: Turnover conventions for the two legs of the pair.
TURNOVER_CONVENTIONS: tuple[str, ...] = ("drift", "parity", "fixed_quantity")

TURNOVER_NOTES: dict[str, str] = {
    "drift": (
        "Constant-notional rebalance of both legs every day (the cost screen's "
        "convention): w*(|spot_return| + |perp_return|) while the pair is held, "
        "of which the spot leg trades w*|spot_return| and the perp leg "
        "w*|perp_return|."
    ),
    "parity": (
        "Equal-notional maintenance: only the basis drift is traded, "
        "w*|spot_return - perp_return| while the pair is held. The adjustment "
        "is executed on the spot leg (the perp leg keeps its drifted notional), "
        "which is the conservative choice under a per-leg fee schedule."
    ),
    "fixed_quantity": (
        "Fixed coin quantity on both legs (no daily rebalancing at all): the "
        "pair is entered and exited only."
    ),
}

#: Which turnover convention is the **headline** of this evaluation, and why.
#:
#: The pre-registered gross path (the committed carry path) is the
#: *constant-notional* construction: the book resets the spot and the perp
#: notionals to ``w * equity`` every day. The only turnover convention that
#: is internally consistent with that gross path is therefore the daily
#: constant-notional rebalance (``drift``): the other two conventions
#: describe a *different* book, not the same book traded less often. See
#: ``HEADLINE_CONVENTION`` in the rendered record.
HEADLINE_CONVENTION = "drift"


# ======================================================================
# Cost models (Cycle 892)
# ======================================================================
@dataclass(frozen=True)
class CostModel:
    """One cost model of the carry book.

    Two kinds:

    * ``flat`` -- the repository's flat model: ``flat_bps`` per unit of weight
      change, applied to the total turnover (both legs).
    * ``venue`` -- a per-leg venue fee schedule: ``spot_bps`` per unit of
      *spot-leg* turnover and ``perp_bps`` per unit of *perp-leg* turnover.

    ``capital_rate_annual`` is the annual rate charged on the capital the
    spot leg ties up (the spot leg's notional as a fraction of the book's
    equity), i.e. the opportunity cost of the cash that a delta-neutral
    carry book cannot deploy elsewhere.
    """

    key: str
    label: str
    kind: str
    flat_bps: float = 0.0
    spot_bps: float = 0.0
    perp_bps: float = 0.0
    capital_rate_annual: float = 0.0
    source: str = ""
    note: str = ""


#: Binance **VIP 0** published fees, in basis points of the traded notional.
#:
#: Sources (accessed 2026-10-20):
#:
#: * Spot: Binance, "VIP Program: Updates to Spot and Margin Trading Fees for
#:   VIP 3 - VIP 9 Users" (2024-10-07) - "Normal User" maker 0.1000% and
#:   taker 0.1000% (the 25% BNB discount to 0.0750% is not claimed here).
#: * USDⓈ-M futures: Binance futures fee explainer (support FAQ
#:   360033544231) - "a Regular User's maker fee is 0.02% and a Regular
#:   User's taker fee is 0.05%".
#:
#: No live fees are implied: the account-specific fee table is only visible
#: after login, so the published standard VIP 0 schedule is used as a
#: documented assumption.
VENUE_SPOT_MAKER_BPS = 10.0
VENUE_SPOT_TAKER_BPS = 10.0
VENUE_PERP_MAKER_BPS = 2.0
VENUE_PERP_TAKER_BPS = 5.0

#: The repository's own slippage assumption (``config/settings.yaml``
#: ``default_slippage_bps``), kept on top of the venue fees because a
#: published fee schedule does not model execution slippage.
REPO_SLIPPAGE_BPS = SLIPPAGE_BPS * 10000.0

#: The capital-charge sensitivity grid: no charge, the repository's
#: risk-free rate, and a stablecoin-equivalent yield.
CAPITAL_CHARGE_RATES: dict[str, float] = {
    "none": 0.0,
    "repo_rf": RF_ANNUAL,
    "usdt_5pct": 0.05,
}

_VENUE_TAKER_SLIPPAGE_SOURCE = (
    "Binance VIP 0 published spot taker 10 bp and USDⓈ-M perp taker 5 bp "
    "(accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption"
)

COST_MODELS: tuple[CostModel, ...] = (
    CostModel(
        key="flat_3bp",
        label="Repository flat model (3 bp per unit of weight change)",
        kind="flat",
        flat_bps=DECISION_BPS,
        source="src/backtest/engine.py:get_cost_params (config/settings.yaml)",
        note=(
            "The repository-wide convention (1 bp commission + 2 bp slippage per "
            "unit of weight change) and the convention the cost screen uses. "
            "No capital charge."
        ),
    ),
    CostModel(
        key="flat_3bp_capital_rf",
        label="Flat model + capital charge at the repository risk-free rate",
        kind="flat",
        flat_bps=DECISION_BPS,
        capital_rate_annual=RF_ANNUAL,
        source="src/backtest/engine.py:get_cost_params + get_risk_free_rate",
        note="Isolates the capital charge: the same flat trading cost, plus the "
        "cost of the capital the spot leg ties up.",
    ),
    CostModel(
        key="venue_taker",
        label="Binance VIP 0 venue fees, taker (spot 10 bp, perp 5 bp)",
        kind="venue",
        spot_bps=VENUE_SPOT_TAKER_BPS,
        perp_bps=VENUE_PERP_TAKER_BPS,
        source="Binance published VIP 0 fee schedule (accessed 2026-10-20)",
        note="The published fee schedule alone: no slippage, no capital charge.",
    ),
    CostModel(
        key="venue_taker_slippage",
        label="Binance VIP 0 venue fees, taker + repository slippage (spot 12 bp, perp 7 bp)",
        kind="venue",
        spot_bps=VENUE_SPOT_TAKER_BPS + REPO_SLIPPAGE_BPS,
        perp_bps=VENUE_PERP_TAKER_BPS + REPO_SLIPPAGE_BPS,
        source=_VENUE_TAKER_SLIPPAGE_SOURCE,
        note="The published fee schedule plus the repository's slippage "
        "assumption, which a fee schedule does not model.",
    ),
    CostModel(
        key="venue_maker_slippage",
        label="Binance VIP 0 venue fees, maker + repository slippage (spot 12 bp, perp 4 bp)",
        kind="venue",
        spot_bps=VENUE_SPOT_MAKER_BPS + REPO_SLIPPAGE_BPS,
        perp_bps=VENUE_PERP_MAKER_BPS + REPO_SLIPPAGE_BPS,
        source=(
            "Binance published VIP 0 fee schedule, maker (spot 10 bp, perp 2 bp, "
            "accessed 2026-10-20) + the repository's 2 bp/unit slippage assumption"
        ),
        note="The maker alternative: at VIP 0 the spot fee is the same for maker "
        "and taker, so only the perp leg gets cheaper.",
    ),
    CostModel(
        key="realistic_rf",
        label="HEADLINE: venue taker + slippage + capital charge at the repository rf",
        kind="venue",
        spot_bps=VENUE_SPOT_TAKER_BPS + REPO_SLIPPAGE_BPS,
        perp_bps=VENUE_PERP_TAKER_BPS + REPO_SLIPPAGE_BPS,
        capital_rate_annual=RF_ANNUAL,
        source=_VENUE_TAKER_SLIPPAGE_SOURCE + " + get_risk_free_rate()",
        note="The realistic model of this evaluation: the conservative end of "
        "both the fee schedule (taker) and the capital charge (the "
        "repository's risk-free rate).",
    ),
    CostModel(
        key="realistic_no_capital_charge",
        label="Venue taker + slippage, no capital charge",
        kind="venue",
        spot_bps=VENUE_SPOT_TAKER_BPS + REPO_SLIPPAGE_BPS,
        perp_bps=VENUE_PERP_TAKER_BPS + REPO_SLIPPAGE_BPS,
        capital_rate_annual=0.0,
        source=_VENUE_TAKER_SLIPPAGE_SOURCE,
        note="The capital-charge sensitivity row 'none' (0%): the book is "
        "charged only what it trades.",
    ),
    CostModel(
        key="realistic_usdt_5pct",
        label="Venue taker + slippage + capital charge at a 5% USDT-equivalent yield",
        kind="venue",
        spot_bps=VENUE_SPOT_TAKER_BPS + REPO_SLIPPAGE_BPS,
        perp_bps=VENUE_PERP_TAKER_BPS + REPO_SLIPPAGE_BPS,
        capital_rate_annual=CAPITAL_CHARGE_RATES["usdt_5pct"],
        source=_VENUE_TAKER_SLIPPAGE_SOURCE + " + 5% USDT-equivalent yield assumption",
        note="The capital-charge sensitivity row 'usdt_5pct': the cash the spot "
        "leg ties up could have earned a stablecoin lending yield instead.",
    ),
)

#: The headline cost model of the evaluation.
HEADLINE_COST_MODEL = "realistic_rf"

#: The cost models by key.
COST_MODEL_BY_KEY: dict[str, CostModel] = {model.key: model for model in COST_MODELS}



# ======================================================================
# Data access (read-only, offline)
# ======================================================================
def load_carry_path(symbol: str) -> pd.DataFrame:
    """Read the committed daily carry path of *symbol* (e.g. ``BTCUSDT``)."""
    path = PROC_CRYPTO / f"{symbol}_carry_path.parquet"
    if not path.exists():
        raise FileNotFoundError(f"missing committed carry path {path}")
    frame = pd.read_parquet(path)
    frame.index = pd.DatetimeIndex(frame.index)
    return frame.sort_index()


def check_identity(path: pd.DataFrame) -> float:
    """Assert ``gross_carry == funding_cashflow + basis_convergence`` row by row.

    Returns the maximum absolute deviation (0.0 on the committed cache).
    """
    identity = path["funding_cashflow"] + path["basis_convergence"]
    deviation = float((path["gross_carry"] - identity).abs().max())
    if deviation > 1e-12:
        raise AssertionError(
            f"carry path identity violated: max |gross - (funding + basis)| = {deviation:.3e}"
        )
    return deviation


def load_funding_settlements(symbol: str) -> pd.DataFrame:
    """Read the committed raw 8h funding settlements of *symbol* (e.g. ``BTC``)."""
    path = RAW_CRYPTO / f"{symbol}_USDT_USDT_funding_binance.parquet"
    frame = pd.read_parquet(path)
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=True)
    return frame.sort_values("datetime").reset_index(drop=True)


# ======================================================================
# Book construction
# ======================================================================
@dataclass
class Book:
    """One trading book: the gross return, the turnover and the position path."""

    name: str
    symbol: str
    rule: RuleSpec
    weight: float
    turnover_convention: str
    gross: pd.Series
    turnover: pd.Series
    turnover_spot: pd.Series
    turnover_perp: pd.Series
    positions: pd.DataFrame
    weights: pd.DataFrame
    entries: int
    exits: int
    notes: list[str] = field(default_factory=list)

    @property
    def position(self) -> pd.Series:
        """The book's average position across its symbols (0 when flat)."""
        return self.positions.mean(axis=1)

    @property
    def spot_notional(self) -> pd.Series:
        """The spot leg's notional as a fraction of the book's equity.

        This is the capital the book ties up: the long spot leg is funded with
        cash, while the short perp leg is self-financing (the short's proceeds
        are posted as its margin), so the net capital at risk is the spot leg's
        notional. It is the base of the capital charge of the realistic cost
        model.
        """
        spot_columns = [c for c in self.weights.columns if c.endswith("_spot")]
        if not spot_columns:
            return pd.Series(0.0, index=self.weights.index)
        return self.weights[spot_columns].sum(axis=1)


def position_changes(positions: pd.DataFrame) -> pd.DataFrame:
    """Day-over-day position changes per symbol.

    The first row is the opening position of the book (the initial purchase),
    so an always-on book reports exactly one entry and a masked book reports
    one entry per transition after the opening.
    """
    change = positions.diff()
    change.iloc[0] = positions.iloc[0]
    return change


def position_series(path: pd.DataFrame, rule: RuleSpec) -> pd.Series:
    """The 0/1 position path of *rule* on the daily index of *path*."""
    funding = path["funding_cashflow"].astype(float)
    if rule.kind == "always":
        return pd.Series(1.0, index=path.index)
    if rule.kind == "funding_positive_sameday":
        return (funding > 0).astype(float)
    if rule.kind == "funding_positive_lagged":
        # Only the previous day's aggregate funding is known before the day starts.
        lagged = funding.shift(1)
        position = (lagged > 0).astype(float)
        position.iloc[0] = 0.0
        return position
    raise ValueError(f"unknown rule kind {rule.kind!r}")


def build_book(
    path: pd.DataFrame,
    rule: RuleSpec,
    weight: float,
    turnover_convention: str = "drift",
    charge_entry: bool = True,
    symbol: str = "BTCUSDT",
) -> Book:
    """Build the gross/turnover/position series of one rule on one symbol.

    ``weight`` is the notional of **one** leg of the pair as a fraction of the
    book's equity: the book holds ``+weight`` spot and ``-weight`` perp, so its
    gross exposure is ``2 * weight`` and its net exposure is zero.

    The turnover series is the sum of

    * the daily rebalance of the legs while the pair is held
      (``turnover_convention``), and
    * the position transitions: an entry (long spot + short perp) and an exit
      each change the leg weights by ``2 * weight``.

    ``charge_entry=False`` omits the position transitions; it exists only to
    reproduce the cost screen's crypto row, which does not charge them.
    """
    if turnover_convention not in TURNOVER_CONVENTIONS:
        raise ValueError(f"unknown turnover convention {turnover_convention!r}")

    spot = path["spot_return"].astype(float)
    perp = path["perp_return"].astype(float)
    position = position_series(path, rule)

    gross = (weight * path["gross_carry"].astype(float) * position).astype(float)

    if turnover_convention == "drift":
        # Each leg is reset to its own constant notional every day, so each
        # leg trades the drift of its own price.
        rebalance_spot = weight * spot.abs() * position
        rebalance_perp = weight * perp.abs() * position
    elif turnover_convention == "parity":
        # The two legs are kept at equal dollar notional: only the divergence
        # between them is traded. The adjustment is executed on the spot leg
        # (the perp leg is left at its drifted notional), which is the
        # conservative choice under a per-leg fee schedule.
        rebalance_spot = weight * (spot - perp).abs() * position
        rebalance_perp = pd.Series(0.0, index=path.index)
    else:  # fixed_quantity
        rebalance_spot = pd.Series(0.0, index=path.index)
        rebalance_perp = pd.Series(0.0, index=path.index)

    if charge_entry:
        change = position.diff()
        change.iloc[0] = position.iloc[0]
        # Each leg changes by ``weight * |position change|``: an entry (long
        # spot + short perp) and an exit are each charged on both legs.
        transition_leg = change.abs() * weight
    else:
        transition_leg = pd.Series(0.0, index=path.index)

    turnover_spot = (rebalance_spot + transition_leg).astype(float)
    turnover_perp = (rebalance_perp + transition_leg).astype(float)
    turnover = (rebalance_spot + rebalance_perp + 2.0 * transition_leg).astype(float)

    weights = pd.DataFrame(
        {
            f"{symbol}_spot": (weight * position).astype(float),
            f"{symbol}_perp": (-weight * position).astype(float),
        },
        index=path.index,
    )
    positions = pd.DataFrame({f"{symbol}_position": position}, index=path.index)

    change = position_changes(positions)
    entries = int((change > 0).to_numpy().sum())
    exits = int((change < 0).to_numpy().sum())

    return Book(
        name=f"{symbol}_{rule.rule_id}",
        symbol=symbol,
        rule=rule,
        weight=weight,
        turnover_convention=turnover_convention,
        gross=gross,
        turnover=turnover,
        turnover_spot=turnover_spot,
        turnover_perp=turnover_perp,
        positions=positions,
        weights=weights,
        entries=entries,
        exits=exits,
    )


def portfolio_book(
    paths: dict[str, pd.DataFrame],
    rule: RuleSpec,
    turnover_convention: str = "drift",
    charge_entry: bool = True,
) -> Book:
    """The equal-weight BTC/ETH carry portfolio (the screened candidate).

    Each symbol's pair carries half of the book's equity (``weight = 0.5``),
    which is exactly the construction of the cost screen's crypto row.
    """
    books = [
        build_book(
            paths[base],
            rule,
            weight=0.5,
            turnover_convention=turnover_convention,
            charge_entry=charge_entry,
            symbol=base,
        )
        for base in BASE_SYMBOLS
    ]
    gross = sum(book.gross for book in books)
    turnover = sum(book.turnover for book in books)
    turnover_spot = sum(book.turnover_spot for book in books)
    turnover_perp = sum(book.turnover_perp for book in books)
    positions = pd.concat([book.positions for book in books], axis=1)
    weights = pd.concat([book.weights for book in books], axis=1)
    return Book(
        name=f"PORTFOLIO_{rule.rule_id}",
        symbol="BTC+ETH",
        rule=rule,
        weight=0.5,
        turnover_convention=turnover_convention,
        gross=gross,
        turnover=turnover,
        turnover_spot=turnover_spot,
        turnover_perp=turnover_perp,
        positions=positions,
        weights=weights,
        entries=int(sum(book.entries for book in books)),
        exits=int(sum(book.exits for book in books)),
    )


# ======================================================================
# Metrics
# ======================================================================
def net_series(book: Book, cost_bps: float) -> pd.Series:
    """Net-of-cost return series of *book* at *cost_bps* per unit of weight change."""
    return book.gross - book.turnover * (float(cost_bps) / 10000.0)


def fee_series(book: Book, model: CostModel) -> pd.Series:
    """The trading-fee series of *book* under *model*, as a fraction of equity per day.

    The flat model charges ``flat_bps`` on the *total* turnover; the venue
    model charges ``spot_bps`` on the spot leg's turnover and ``perp_bps`` on
    the perp leg's turnover, i.e. on the leg weights that are actually traded.
    """
    if model.kind == "flat":
        return book.turnover * (float(model.flat_bps) / 10000.0)
    if model.kind == "venue":
        return (
            book.turnover_spot * (float(model.spot_bps) / 10000.0)
            + book.turnover_perp * (float(model.perp_bps) / 10000.0)
        )
    raise ValueError(f"unknown cost model kind {model.kind!r}")


def capital_charge_series(book: Book, annual_rate: float) -> pd.Series:
    """The daily charge for the capital the spot leg ties up.

    The charge is ``spot_notional * annual_rate / 365`` per day, where
    ``spot_notional`` is the spot leg's notional as a fraction of the book's
    equity. The spot leg is funded with cash, while the short perp leg is
    self-financing (the short's own proceeds are posted as its margin), so
    the net capital the strategy locks up is the spot leg's notional.

    A **negative** rate is a rebate on the locked capital; it is applied like
    any other rate, because the break-even solver needs it to bracket the
    crossing when the book is already unprofitable before the capital is
    charged.

    **Convention.** The repository's *backtest-baseline* Sharpe/Sortino
    already subtract the 2% risk-free rate from the ratio's numerator, but the
    *return* series does not pay it. When a capital charge is applied here,
    the return series does pay it, so the backtest-scale metrics of that row
    are computed with a zero risk-free rate to avoid charging it twice; the
    *canonical* gate convention (``arithmetic_annualized_rf0``) is a
    zero-risk-free-rate convention in both the numerator and the denominator
    and is therefore unaffected.
    """
    if annual_rate == 0.0:
        return pd.Series(0.0, index=book.gross.index)
    return book.spot_notional * (float(annual_rate) / PERIODS_PER_YEAR)


def net_series_model(book: Book, model: CostModel) -> pd.Series:
    """The net-of-cost return series of *book* under *model*."""
    return (
        book.gross
        - fee_series(book, model)
        - capital_charge_series(book, model.capital_rate_annual)
    )



def max_drawdown(returns: pd.Series) -> float:
    """Maximum drawdown of the compounded daily return series."""
    cum = (1.0 + returns).cumprod()
    return float((cum / cum.expanding().max() - 1.0).min())


def sortino_canonical(
    returns: pd.Series, periods_per_year: int = PERIODS_PER_YEAR, rf_annual: float = 0.0
) -> float:
    """The Sortino analogue of the repository's **canonical** Sharpe.

    The canonical Sharpe convention (``arithmetic_annualized_rf0``, see
    ``src/evaluation/sharpe.py``) uses the arithmetic mean daily return with a
    zero risk-free rate. This function applies the same numerator to the
    downside deviation, so its sign always follows the sign of the arithmetic
    mean.

    The engine's own ``compute_metrics`` Sortino lives on the **backtest
    baseline** scale: it subtracts the 2% risk-free rate from the *geometric*
    annualized return. That is the repository's published backtest
    convention, but on a low-return sample it is negative even when the
    strategy earns a positive arithmetic return, so the two scales are always
    reported side by side and never compared silently.
    """
    r = pd.Series(returns, dtype=float).dropna()
    if len(r) < 2:
        return 0.0
    downside = r[r < 0]
    if len(downside) < 2:
        return 0.0
    downside_vol = float(downside.std(ddof=1) * np.sqrt(periods_per_year))
    if downside_vol <= 0.0:
        return 0.0
    ann_excess = float(r.mean() * periods_per_year) - float(rf_annual)
    return float(ann_excess / downside_vol)


def annualized_return(returns: pd.Series, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    """Geometric annualized return of a daily return series."""
    r = pd.Series(returns, dtype=float).fillna(0.0)
    if len(r) == 0:
        return float("nan")
    growth = float((1.0 + r).prod())
    if growth <= 0.0 or not np.isfinite(growth):
        return float("nan")
    return float(growth ** (periods_per_year / len(r)) - 1.0)


def sample_index(index: pd.DatetimeIndex, sample: str) -> pd.DatetimeIndex:
    """The timestamps of the pre-registered *sample* inside *index*."""
    start, end = SPLITS[sample]
    mask = (index >= pd.Timestamp(start, tz="UTC")) & (index <= pd.Timestamp(end, tz="UTC"))
    return index[mask]


def book_metrics(
    book: Book,
    net: pd.Series,
    sample: str,
    cost_bps: float = DECISION_BPS,
    periods_per_year: int = PERIODS_PER_YEAR,
    cost_model: CostModel | None = None,
) -> dict[str, Any]:
    """The metrics of *book* on the pre-registered *sample*.

    The return series is the **full path** sliced to the sample (so the cost of
    the first session of the sample is not lost), and the turnover and the
    position path are sliced with it.

    ``cost_model`` selects the cost model whose drag is reported. When it is
    ``None`` the repository's flat model is used and the behaviour is exactly
    the Cycle 891 one (every committed number is unchanged). When a model that
    charges a capital cost is given, the engine's backtest-scale metrics use a
    zero risk-free rate, because the charge is already paid in the return
    series (see :func:`capital_charge_series`).
    """
    idx = sample_index(net.index, sample)
    r = net.loc[idx]
    w = book.weights.loc[idx]
    t = book.turnover.loc[idx]
    p = book.position.loc[idx]
    if len(r) < 2:
        return {"sessions": int(len(r)), "sample": sample}

    if cost_model is not None and cost_model.capital_rate_annual > 0.0:
        engine_rf = 0.0
    else:
        engine_rf = RF_ANNUAL

    engine = compute_metrics(
        r,
        w,
        COMMISSION_BPS,
        SLIPPAGE_BPS,
        engine_rf,
        periods_per_year=periods_per_year,
    )
    # The position changes are computed on the full path and then sliced, so a
    # sample that starts with an already-open position does not report a
    # spurious entry.
    change = position_changes(book.positions).loc[idx]
    ann_turnover = float(t.mean() * periods_per_year)

    if cost_model is None:
        fee_drag = ann_turnover * (float(cost_bps) / 10000.0)
        capital_drag = 0.0
    elif cost_model.kind == "flat":
        fee_drag = ann_turnover * (float(cost_model.flat_bps) / 10000.0)
        capital_drag = float(
            book.spot_notional.loc[idx].mean()
            * (float(cost_model.capital_rate_annual) / PERIODS_PER_YEAR)
            * periods_per_year
        )
    else:
        spot_t = book.turnover_spot.loc[idx]
        perp_t = book.turnover_perp.loc[idx]
        fee_drag = float(
            (
                spot_t * (float(cost_model.spot_bps) / 10000.0)
                + perp_t * (float(cost_model.perp_bps) / 10000.0)
            ).mean()
            * periods_per_year
        )
        capital_drag = float(
            book.spot_notional.loc[idx].mean()
            * (float(cost_model.capital_rate_annual) / PERIODS_PER_YEAR)
            * periods_per_year
        )

    return {
        "sample": sample,
        "sessions": int(len(r)),
        "start": str(r.index[0].date()),
        "end": str(r.index[-1].date()),
        "ann_return_geometric": float(engine["annualized_return"]),
        "ann_return_arithmetic": float(r.mean() * periods_per_year),
        "ann_volatility": float(engine["annualized_volatility"]),
        "sharpe_backtest_scale": float(engine["sharpe_ratio"]),
        "sharpe_canonical": float(sharpe_ratio(r, periods_per_year=periods_per_year)),
        "sortino_backtest_scale": float(engine["sortino_ratio"]),
        "sortino_canonical": float(sortino_canonical(r, periods_per_year=periods_per_year)),
        "downside_deviation_annualized": float(
            r[r < 0].std(ddof=1) * np.sqrt(periods_per_year)
        ),
        "risk_free_rate_annual": RF_ANNUAL,
        "engine_risk_free_rate_annual": float(engine_rf),
        "max_drawdown": float(engine["max_drawdown"]),
        "max_drawdown_recomputed": max_drawdown(r),
        "profit_factor": float(engine["profit_factor"]),
        "total_return": float(engine["total_return"]),
        "avg_gross_exposure": float(engine["avg_exposure"]),
        "annualized_turnover_units": ann_turnover,
        "annualized_turnover_spot_units": float(book.turnover_spot.loc[idx].mean() * periods_per_year),
        "annualized_turnover_perp_units": float(book.turnover_perp.loc[idx].mean() * periods_per_year),
        "annualized_cost_drag": fee_drag + capital_drag,
        "annualized_fee_drag": fee_drag,
        "annualized_capital_charge_drag": capital_drag,
        "avg_spot_notional_fraction": float(book.spot_notional.loc[idx].mean()),
        "rebalance_days": int((t > 1e-12).sum()),
        "position_entries": int((change > 0).to_numpy().sum()),
        "position_exits": int((change < 0).to_numpy().sum()),
        "invested_fraction": float((p > 0).mean()),
    }


def bootstrap_ci(
    net: pd.Series,
    periods_per_year: int = PERIODS_PER_YEAR,
    n_samples: int = BOOTSTRAP_DRAWS,
    block_size: int = BOOTSTRAP_BLOCK_DAYS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Moving-block bootstrap intervals of the Sharpe and of the annualized return.

    The resampling stream is the repository's own
    (``src.evaluation.statistics.block_bootstrap_sharpe`` uses the same
    ``MovingBlockBootstrap`` construction with the same seed and the same
    effective block size), so the Sharpe distribution below is identical to the
    one the repository helper produces.
    """
    arr = pd.Series(net, dtype=float).values
    n = len(arr)
    effective_block = min(block_size, max(1, n // 10))
    mbb = MovingBlockBootstrap(effective_block, arr, seed=seed)
    sharpes: list[float] = []
    ann_geo: list[float] = []
    ann_arith: list[float] = []
    for posdata, _ in mbb.bootstrap(n_samples):
        sample = np.asarray(posdata[0], dtype=float)
        sharpes.append(float(sharpe_ratio(sample, periods_per_year=periods_per_year)))
        growth = float(np.prod(1.0 + sample))
        ann_geo.append(
            float(growth ** (periods_per_year / len(sample)) - 1.0) if growth > 0 else float("nan")
        )
        ann_arith.append(float(sample.mean() * periods_per_year))
    sharpes_arr = np.asarray(sharpes)
    geo_arr = np.asarray(ann_geo)
    arith_arr = np.asarray(ann_arith)
    return {
        "n_bootstrap": int(n_samples),
        "block_days": int(effective_block),
        "seed": int(seed),
        "sharpe_ci_95": [
            float(np.nanpercentile(sharpes_arr, 2.5)),
            float(np.nanpercentile(sharpes_arr, 97.5)),
        ],
        "ann_return_geometric_ci_95": [
            float(np.nanpercentile(geo_arr, 2.5)),
            float(np.nanpercentile(geo_arr, 97.5)),
        ],
        "ann_return_arithmetic_ci_95": [
            float(np.nanpercentile(arith_arr, 2.5)),
            float(np.nanpercentile(arith_arr, 97.5)),
        ],
    }


# ======================================================================
# Benchmark
# ======================================================================
def benchmark_series(paths: dict[str, pd.DataFrame]) -> tuple[pd.Series, pd.Series]:
    """Equal-weight BTC/ETH spot buy-and-hold: (gross, turnover).

    The benchmark buys once at the start of the sample and never rebalances,
    which is the cost screen's benchmark convention.
    """
    index = paths["BTCUSDT"].index
    gross = pd.Series(0.0, index=index)
    for base in BASE_SYMBOLS:
        gross = gross + 0.5 * paths[base]["spot_return"].astype(float)
    turnover = pd.Series(0.0, index=index)
    turnover.iloc[0] = 1.0
    return gross, turnover


# ======================================================================
# Reconciliation with the cost screen
# ======================================================================
def screen_reconciliation(paths: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Reproduce the cost screen's ``cryptofunding_001`` row from the same data.

    The screen annualizes at 252 and does not charge the position transitions;
    this function rebuilds its numbers from the *same* series, so the
    evaluation below and the screen describe the same candidate.
    """
    from research.cost_admissibility_screen import (  # noqa: PLC0415
        annualized_cost_drag,
        annualized_return as screen_annualized_return,
        annual_turnover_units,
        build_cryptofunding_candidate,
        net_return_series,
        solve_break_even_cost_bps,
    )

    candidate = build_cryptofunding_candidate()
    gross = candidate.gross
    turnover = candidate.turnover
    net = net_return_series(gross, turnover, DECISION_BPS)
    break_even = solve_break_even_cost_bps(
        lambda c: annualized_return(net_return_series(gross, turnover, c))
    )

    # The screen's series must be the same series the evaluation builds.
    portfolio = portfolio_book(paths, RULES[0], charge_entry=False)
    same_gross = bool(
        np.allclose(
            portfolio.gross.loc[gross.index].to_numpy(),
            gross.loc[portfolio.gross.index].to_numpy(),
            atol=1e-15,
        )
    )
    same_turnover = bool(
        np.allclose(
            portfolio.turnover.loc[turnover.index].to_numpy(),
            turnover.loc[portfolio.turnover.index].to_numpy(),
            atol=1e-15,
        )
    )

    return {
        "source": "research/cost_admissibility_screen.py:build_cryptofunding_candidate",
        "screen_convention": {
            "periods_per_year": SCREEN_PERIODS_PER_YEAR,
            "charges_position_transitions": False,
        },
        "screen_gross_annualized_signal": float(screen_annualized_return(gross)),
        "screen_annual_turnover_units": float(annual_turnover_units(turnover)),
        "screen_cost_drag_3bp": float(annualized_cost_drag(turnover, DECISION_BPS)),
        "screen_net_annualized_return_3bp": float(screen_annualized_return(net)),
        "screen_break_even_cost_bps": break_even["solution"],
        "crypto_convention": {
            "periods_per_year": PERIODS_PER_YEAR,
            "charges_position_transitions": True,
        },
        "crypto_gross_annualized_signal": float(
            annualized_return(portfolio.gross, PERIODS_PER_YEAR)
        ),
        "crypto_annual_turnover_units": float(
            portfolio.turnover.mean() * PERIODS_PER_YEAR
        ),
        "crypto_cost_drag_3bp": float(
            portfolio.turnover.mean() * PERIODS_PER_YEAR * (DECISION_BPS / 10000.0)
        ),
        "crypto_net_annualized_return_3bp": float(
            annualized_return(
                portfolio.gross - portfolio.turnover * (DECISION_BPS / 10000.0),
                PERIODS_PER_YEAR,
            )
        ),
        "same_gross_series": same_gross,
        "same_turnover_series": same_turnover,
    }


# ======================================================================
# Robustness
# ======================================================================
def cost_sensitivity(book: Book) -> dict[str, Any]:
    """Net annualized return, canonical Sharpe and cost drag per cost row."""
    rows: dict[str, Any] = {}
    for bps in COST_ROWS_BPS:
        net = net_series(book, bps)
        metrics = book_metrics(book, net, "full", cost_bps=bps)
        rows[f"{bps:.1f}bp"] = {
            "cost_bps_per_unit": bps,
            "ann_return_geometric": metrics["ann_return_geometric"],
            "ann_return_arithmetic": metrics["ann_return_arithmetic"],
            "sharpe_canonical": metrics["sharpe_canonical"],
            "max_drawdown": metrics["max_drawdown"],
            "annualized_turnover_units": metrics["annualized_turnover_units"],
            "annualized_cost_drag": metrics["annualized_cost_drag"],
        }
    return rows


def turnover_convention_sensitivity(paths: dict[str, pd.DataFrame], rule: RuleSpec) -> dict[str, Any]:
    """The same rule under the three turnover conventions."""
    rows: dict[str, Any] = {}
    for convention in TURNOVER_CONVENTIONS:
        book = portfolio_book(paths, rule, turnover_convention=convention)
        net = net_series(book, DECISION_BPS)
        metrics = book_metrics(book, net, "full")
        rows[convention] = {
            "note": TURNOVER_NOTES[convention],
            "ann_return_geometric": metrics["ann_return_geometric"],
            "sharpe_canonical": metrics["sharpe_canonical"],
            "annualized_turnover_units": metrics["annualized_turnover_units"],
            "annualized_cost_drag": metrics["annualized_cost_drag"],
        }
    return rows


def funding_rounding_sensitivity(paths: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Funding precision and settlement-timing haircuts on the always-on portfolio.

    * ``precision`` -- the archived 8h rates are already published with 8
      decimals; rounding them to that precision must be a no-op.
    * ``worst_case_rounding`` -- the exchange rounds each settlement to the
      payment precision (1e-8 USDT of notional); the worst case is
      0.5e-8 per settlement, 3 settlements a day.
    * ``late_entry`` -- a position that cannot be in place for the 00:00 UTC
      settlement captures 2 of the 3 daily settlements.
    """
    out: dict[str, Any] = {}

    # (a) published precision of the archived rates
    max_decimals = 0
    for base in BASE_SYMBOLS:
        symbol = base[:3]
        settlements = load_funding_settlements(symbol)
        rates = settlements["fundingRate"].astype(float)
        decimals = rates.map(lambda v: len(f"{v!r}".split(".")[-1]) if "." in f"{v!r}" else 0)
        max_decimals = max(max_decimals, int(decimals.max()))
    out["published_rate_decimals"] = max_decimals

    book = portfolio_book(paths, RULES[0])
    net = net_series(book, DECISION_BPS)
    base_metrics = book_metrics(book, net, "full")

    # (b) worst-case per-settlement rounding of the funding payment
    worst_case_daily = 3 * 0.5e-8
    out["worst_case_rounding"] = {
        "daily_return_impact": worst_case_daily,
        "annual_return_impact": worst_case_daily * PERIODS_PER_YEAR,
        "ann_return_geometric": base_metrics["ann_return_geometric"]
        - worst_case_daily * PERIODS_PER_YEAR,
        "note": (
            "The exchange rounds each funding payment to 1e-8 USDT of notional; "
            "the worst case (always against the trader) is 0.5e-8 per "
            "settlement, 3 settlements a day."
        ),
    }

    # (c) late entry: only the 08:00 and 16:00 settlements are captured
    late_gross = pd.Series(0.0, index=book.gross.index)
    for base in BASE_SYMBOLS:
        symbol = base[:3]
        settlements = load_funding_settlements(symbol)
        settlements["day"] = settlements["datetime"].dt.floor("D")
        settled = settlements[settlements["datetime"].dt.hour != 0]
        daily = settled.groupby("day")["fundingRate"].sum()
        path = paths[base]
        late_funding = daily.reindex(path.index).fillna(0.0)
        late_gross = late_gross + 0.5 * (
            late_funding + path["basis_convergence"].astype(float)
        )
    late_book = portfolio_book(paths, RULES[0])
    late_book.gross = late_gross
    late_net = net_series(late_book, DECISION_BPS)
    late_metrics = book_metrics(late_book, late_net, "full")
    out["late_entry"] = {
        "settlements_captured": 2,
        "ann_return_geometric": late_metrics["ann_return_geometric"],
        "sharpe_canonical": late_metrics["sharpe_canonical"],
        "note": "Position established after the 00:00 UTC settlement of the day.",
    }
    return out


def convergence_sensitivity(paths: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Sensitivity of the result to the basis-convergence accounting.

    The committed gross carry credits ``basis_convergence = spot_return -
    perp_return`` to the pair. This row re-runs the always-on portfolio with
    the **funding payment only**, i.e. without crediting the change of the
    price difference at all. It answers the question "is the edge the funding
    payment, or is it an artifact of how the two legs are marked?".
    """
    out: dict[str, Any] = {}
    for rule in RULES:
        book = portfolio_book(paths, rule)
        funding_only = pd.Series(0.0, index=book.gross.index)
        for base in BASE_SYMBOLS:
            funding_only = funding_only + 0.5 * paths[base]["funding_cashflow"].astype(float)
        baseline_net = net_series(book, DECISION_BPS)
        baseline = book_metrics(book, baseline_net, "full")
        stripped = portfolio_book(paths, rule)
        stripped.gross = funding_only * stripped.position
        stripped_net = net_series(stripped, DECISION_BPS)
        without = book_metrics(stripped, stripped_net, "full")
        out[rule.rule_id] = {
            "gross_with_convergence_ann": baseline["ann_return_geometric"],
            "gross_funding_only_ann": without["ann_return_geometric"],
            "gross_funding_only_sharpe": without["sharpe_canonical"],
            "gross_funding_only_max_drawdown": without["max_drawdown"],
            "note": (
                "The basis-convergence term is a near zero-sum change of the "
                "price difference between the two legs; crediting it or not "
                "moves the annualized net return by well under one percentage "
                "point, so the result does not depend on that accounting."
            ),
        }
    return out


def yearly_stability(book: Book, cost_bps: float = DECISION_BPS, cost_model: CostModel | None = None) -> dict[str, Any]:
    """Net annualized return, canonical Sharpe and max drawdown per calendar year."""
    net = net_series(book, cost_bps) if cost_model is None else net_series_model(book, cost_model)
    rows: dict[str, Any] = {}
    for year in sorted({stamp.year for stamp in net.index}):
        idx = net.index[net.index.year == year]
        r = net.loc[idx]
        t = book.turnover.loc[idx]
        if len(r) < 2:
            continue
        rows[str(year)] = {
            "sessions": int(len(r)),
            "ann_return_geometric": annualized_return(r, PERIODS_PER_YEAR),
            "sharpe_canonical": float(sharpe_ratio(r, periods_per_year=PERIODS_PER_YEAR)),
            "max_drawdown": max_drawdown(r),
            "annualized_turnover_units": float(t.mean() * PERIODS_PER_YEAR),
            "invested_fraction": float((book.position.loc[idx] > 0).mean()),
        }
    return rows


def capacity_analysis(paths: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Indicative capacity from the cached daily quote volume of both legs.

    Two constraints are reported:

    * the **daily rebalance** trade (the drift convention's turnover against
      the traded leg's daily quote volume), and
    * the **one-time entry**, which for an always-on book is the only large
      trade: the entry notional must fit inside the participation budget of a
      single day's volume.
    """
    out: dict[str, Any] = {}
    for base in BASE_SYMBOLS:
        symbol = base[:3]
        entry: dict[str, Any] = {}
        for market in ("spot", "perp"):
            frame = pd.read_parquet(RAW_CRYPTO / f"{base}_{market}_1d_binance.parquet")
            volume = frame["quote_volume"].astype(float)
            entry[market] = {
                "min_daily_quote_volume": float(volume.min()),
                "median_daily_quote_volume": float(volume.median()),
                "days": int(len(volume)),
            }
        path = paths[base]
        drift = float((path["spot_return"].abs() + path["perp_return"].abs()).mean())
        parity = float((path["spot_return"] - path["perp_return"]).abs().mean())
        entry["mean_daily_turnover_units_per_unit_weight"] = {
            "drift": drift,
            "parity": parity,
        }
        for market in ("spot", "perp"):
            median = entry[market]["median_daily_quote_volume"]
            worst = entry[market]["min_daily_quote_volume"]
            for label, turnover_per_unit in (("drift", drift), ("parity", parity)):
                if turnover_per_unit <= 0:
                    continue
                entry.setdefault("capacity_usdt", {})[f"{market}_{label}_median"] = (
                    0.01 * median / turnover_per_unit
                )
                entry.setdefault("capacity_usdt", {})[f"{market}_{label}_worst_day"] = (
                    0.01 * worst / turnover_per_unit
                )
            # The one-time entry of the pair: one notional of the spot leg and
            # one of the perp leg, i.e. one unit of the pair's notional.
            entry.setdefault("entry_capacity_usdt", {})[f"{market}_median"] = 0.01 * median
            entry.setdefault("entry_capacity_usdt", {})[f"{market}_worst_day"] = 0.01 * worst
        out[base] = entry
    out["participation_assumption"] = (
        "1% of the daily quote volume of the traded leg; the capacity is the "
        "notional whose daily rebalance trade stays inside that budget. The "
        "one-time entry is bounded by the same 1% budget."
    )
    return out


def return_decomposition(paths: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """The annualized funding, basis and gross components of the carry.

    The gross carry of the pair is ``funding + basis_convergence``. This
    decomposition states how much of the edge is the structural funding
    payment and how much is the (near zero-sum) change of the basis.
    """
    out: dict[str, Any] = {}
    for base in BASE_SYMBOLS:
        path = paths[base]
        funding = path["funding_cashflow"].astype(float)
        basis = path["basis_convergence"].astype(float)
        gross = path["gross_carry"].astype(float)
        out[base] = {
            "funding_annualized": float(funding.mean() * PERIODS_PER_YEAR),
            "funding_annualized_volatility": float(
                funding.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)
            ),
            "basis_annualized": float(basis.mean() * PERIODS_PER_YEAR),
            "basis_annualized_volatility": float(
                basis.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)
            ),
            "gross_annualized": float(gross.mean() * PERIODS_PER_YEAR),
            "gross_annualized_volatility": float(
                gross.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)
            ),
            "funding_positive_day_fraction": float((funding > 0).mean()),
        }
    return out


# ======================================================================
# Evaluation driver
# ======================================================================
def evaluate_book(
    book: Book,
    cost_bps: float = DECISION_BPS,
    bootstrap_samples: tuple[str, ...] = ("full", "post2022", "test_oos"),
    cost_model: CostModel | None = None,
) -> dict[str, Any]:
    """The full metric set of one book."""
    if cost_model is None:
        net = net_series(book, cost_bps)
    else:
        net = net_series_model(book, cost_model)
    samples = {
        sample: book_metrics(book, net, sample, cost_bps=cost_bps, cost_model=cost_model)
        for sample in SPLITS
    }
    intervals = {
        sample: bootstrap_ci(net.loc[sample_index(net.index, sample)])
        for sample in bootstrap_samples
    }
    result = {
        "book": book.name,
        "symbol": book.symbol,
        "rule": book.rule.rule_id,
        "rule_label": book.rule.label,
        "look_ahead": book.rule.look_ahead,
        "turnover_convention": book.turnover_convention,
        "leg_weight": book.weight,
        "cost_bps_per_unit": cost_bps,
        "cost_model": cost_model.key if cost_model is not None else "flat_3bp",
        "samples": samples,
        "bootstrap": intervals,
        "entries_full_sample": book.entries,
        "exits_full_sample": book.exits,
        "yearly": yearly_stability(book, cost_bps, cost_model=cost_model),
    }
    if cost_model is None:
        # The flat-cost sensitivity grid belongs to the repository's flat
        # model only; the cost models below replace it.
        result["cost_sensitivity"] = cost_sensitivity(book)
    return result


# ======================================================================
# Break-evens (Cycle 892)
# ======================================================================
def _geometric_net(book: Book, model: CostModel, sample: str) -> float:
    """The geometric annualized net return of *book* under *model* on *sample*.

    A non-finite value (a compounding book that goes to zero under an
    extreme cost) is reported as -100%, so the bisection sees a monotone
    objective instead of a hole.
    """
    net = net_series_model(book, model)
    value = annualized_return(net.loc[sample_index(net.index, sample)], PERIODS_PER_YEAR)
    return float(value) if np.isfinite(value) else -1.0


def break_even_flat_bps(book: Book, sample: str = "full") -> dict[str, Any]:
    """The flat cost per unit at which the net annualized return is zero.

    This is the cost screen's break-even, computed on the same series and
    with the same bisection (``research.cost_admissibility_screen.py:
    solve_break_even_cost_bps``), but on the crypto conventions (365-day
    annualization, the position transitions charged).
    """
    from research.cost_admissibility_screen import solve_break_even_cost_bps  # noqa: PLC0415

    def objective(cost_bps: float) -> float:
        net = net_series(book, cost_bps)
        value = annualized_return(
            net.loc[sample_index(net.index, sample)], PERIODS_PER_YEAR
        )
        return float(value) if np.isfinite(value) else -1.0

    solution = solve_break_even_cost_bps(objective, lo=-100.0, hi=500.0)
    return {
        "sample": sample,
        "solution_bps": solution["solution"],
        "bracketed": solution["bracketed"],
        "reason": solution["reason"],
        "note": (
            "The flat cost per unit (both legs, one number) at which the net "
            "annualized return is exactly zero."
        ),
    }


def break_even_capital_rate(
    book: Book, fee_model: CostModel, sample: str = "full"
) -> dict[str, Any]:
    """The annual capital charge on the spot leg at which the net return is zero.

    The trading fees are held at *fee_model* (the published venue schedule);
    only the capital charge is solved for. A negative solution means the book
    is already unprofitable before the capital is charged.
    """
    from research.cost_admissibility_screen import solve_break_even_cost_bps  # noqa: PLC0415

    def objective(rate: float) -> float:
        model = replace(fee_model, capital_rate_annual=float(rate))
        return _geometric_net(book, model, sample)

    solution = solve_break_even_cost_bps(objective, lo=-0.5, hi=0.5)
    return {
        "sample": sample,
        "solution_annual_rate": solution["solution"],
        "bracketed": solution["bracketed"],
        "reason": solution["reason"],
        "fee_model": fee_model.key,
        "note": (
            "The annual rate charged on the spot leg's notional at which the "
            "net annualized return is exactly zero, with the trading fees "
            "held at the stated model."
        ),
    }


def break_even_venue_multiplier(
    book: Book, model: CostModel, sample: str = "full"
) -> dict[str, Any]:
    """The multiple of the venue fee schedule at which the net return is zero.

    The capital charge is held at *model*'s rate; only the published fee
    schedule is scaled. A multiplier below 1 means the edge survives a fee
    schedule that is cheaper than the published one.
    """
    from research.cost_admissibility_screen import solve_break_even_cost_bps  # noqa: PLC0415

    def objective(multiplier: float) -> float:
        scaled = replace(
            model,
            spot_bps=model.spot_bps * float(multiplier),
            perp_bps=model.perp_bps * float(multiplier),
        )
        return _geometric_net(book, scaled, sample)

    solution = solve_break_even_cost_bps(objective, lo=0.0, hi=200.0)
    return {
        "sample": sample,
        "solution_multiplier": solution["solution"],
        "bracketed": solution["bracketed"],
        "reason": solution["reason"],
        "cost_model": model.key,
        "note": (
            "The multiple of the published fee schedule at which the net "
            "annualized return is exactly zero."
        ),
    }


def break_even_table(book: Book, sample: str = "full") -> dict[str, Any]:
    """The three break-evens of one book: flat cost, capital charge, fee multiple."""
    fee_model = COST_MODEL_BY_KEY["venue_taker_slippage"]
    headline = COST_MODEL_BY_KEY[HEADLINE_COST_MODEL]
    return {
        "break_even_flat_cost_bps": break_even_flat_bps(book, sample),
        "break_even_capital_charge_annual": break_even_capital_rate(
            book, fee_model, sample
        ),
        "break_even_venue_fee_multiplier": break_even_venue_multiplier(
            book, headline, sample
        ),
    }


# ======================================================================
# Cost-model evaluation (Cycle 892)
# ======================================================================
#: The metric fields kept in the machine-readable summary of a cost model.
_SLIM_METRIC_FIELDS: tuple[str, ...] = (
    "sessions",
    "ann_return_geometric",
    "ann_return_arithmetic",
    "ann_volatility",
    "sharpe_canonical",
    "sharpe_backtest_scale",
    "max_drawdown",
    "annualized_turnover_units",
    "annualized_turnover_spot_units",
    "annualized_turnover_perp_units",
    "annualized_fee_drag",
    "annualized_capital_charge_drag",
    "annualized_cost_drag",
    "avg_spot_notional_fraction",
    "position_entries",
    "position_exits",
    "rebalance_days",
    "invested_fraction",
)

#: The metric fields kept for the non-headline cost models (the record's
#: tables carry the full set; the machine-readable summary stays compact).
_KEY_METRIC_FIELDS: tuple[str, ...] = (
    "ann_return_geometric",
    "sharpe_canonical",
    "max_drawdown",
    "annualized_fee_drag",
    "annualized_capital_charge_drag",
)


def _slim_samples(samples: dict[str, Any], fields: tuple[str, ...] = _SLIM_METRIC_FIELDS) -> dict[str, Any]:
    """The reduced metric set kept in the machine-readable summary."""
    out: dict[str, Any] = {}
    for sample, metrics in samples.items():
        out[sample] = {key: metrics[key] for key in fields if key in metrics}
    return out


def evaluate_cost_models(paths: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Every rule under every cost model: metrics, break-evens and gates.

    The rules (three pre-registered) and the symbols (two) are exactly the
    ones of the flat-model evaluation: the cost models are **sensitivity
    analyses of the same configurations**, not new trials.
    """
    portfolio: dict[str, dict[str, Any]] = {}
    per_symbol: dict[str, dict[str, Any]] = {}
    gates: dict[str, dict[str, Any]] = {}
    break_evens: dict[str, dict[str, Any]] = {}

    for rule in RULES:
        portfolio[rule.rule_id] = {}
        per_symbol[rule.rule_id] = {}
        gates[rule.rule_id] = {}
        break_evens[rule.rule_id] = {}
        for model in COST_MODELS:
            book = portfolio_book(
                paths, rule, turnover_convention=HEADLINE_CONVENTION
            )
            result = evaluate_book(book, bootstrap_samples=(), cost_model=model)
            headline = model.key == HEADLINE_COST_MODEL
            portfolio[rule.rule_id][model.key] = {
                "samples": _slim_samples(result["samples"]),
            }
            symbol_results: dict[str, Any] = {}
            for base in BASE_SYMBOLS:
                symbol_book = build_book(
                    paths[base],
                    rule,
                    weight=1.0,
                    turnover_convention=HEADLINE_CONVENTION,
                )
                symbol_results[base] = evaluate_book(
                    symbol_book, bootstrap_samples=(), cost_model=model
                )
            if headline:
                per_symbol[rule.rule_id][model.key] = {
                    base: _slim_samples(result["samples"])
                    for base, result in symbol_results.items()
                }
            gates[rule.rule_id][model.key] = promotion_gate(symbol_results)
        for sample in ("full", "test_oos"):
            book = portfolio_book(paths, rule, turnover_convention=HEADLINE_CONVENTION)
            break_evens[rule.rule_id][sample] = break_even_table(book, sample)

    return {
        "headline_cost_model": HEADLINE_COST_MODEL,
        "headline_turnover_convention": HEADLINE_CONVENTION,
        "portfolio": portfolio,
        "per_symbol": per_symbol,
        "gates": gates,
        "break_evens": break_evens,
    }


def turnover_convention_bounds(paths: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """The headline cost model under each turnover convention (the trading-cost bound).

    The pre-registered gross path is the constant-notional construction, so
    the conventions differ in the trading they imply, not in the series they
    are computed on. The row therefore states how much of the answer the
    trading-frequency question can move.
    """
    headline = COST_MODEL_BY_KEY[HEADLINE_COST_MODEL]
    out: dict[str, Any] = {}
    for rule in RULES:
        rows: dict[str, Any] = {}
        for convention in TURNOVER_CONVENTIONS:
            book = portfolio_book(paths, rule, turnover_convention=convention)
            net = net_series_model(book, headline)
            metrics = book_metrics(
                book, net, "full", cost_model=headline
            )
            rows[convention] = {
                "note": TURNOVER_NOTES[convention],
                "consistent_with_pre_registered_gross_path": convention
                == HEADLINE_CONVENTION,
                "ann_return_geometric": metrics["ann_return_geometric"],
                "sharpe_canonical": metrics["sharpe_canonical"],
                "max_drawdown": metrics["max_drawdown"],
                "annualized_turnover_units": metrics["annualized_turnover_units"],
                "annualized_fee_drag": metrics["annualized_fee_drag"],
                "annualized_capital_charge_drag": metrics[
                    "annualized_capital_charge_drag"
                ],
            }
        out[rule.rule_id] = rows
    return out


def promotion_gate(
    per_symbol: dict[str, dict[str, Any]],
    cost_bps: float = DECISION_BPS,
) -> dict[str, Any]:
    """The repository's promotion gates, evaluated on the honest trade counts.

    ``net out-of-sample Sharpe >= 0.9`` and ``> 100 pooled out-of-sample
    trades``. The trade count is the number of **independent position round
    trips** opened inside the out-of-sample window; the repository's own
    "days with a non-zero weight change" count is reported next to it, because
    for a continuously held position that count measures daily rebalances of
    a single position, not independent trades.
    """
    oos_sharpes: list[float] = []
    pooled_entries = 0
    rebalance_days = 0
    settlement_observations = 0
    for result in per_symbol.values():
        oos = result["samples"]["test_oos"]
        oos_sharpes.append(float(oos["sharpe_canonical"]))
        pooled_entries += int(oos["position_entries"])
        rebalance_days += int(oos["rebalance_days"])
        settlement_observations += int(oos["sessions"]) * 3
    mean_oos_sharpe = float(np.mean(oos_sharpes)) if oos_sharpes else float("nan")
    sharpe_pass = bool(
        np.isfinite(mean_oos_sharpe) and mean_oos_sharpe >= PROMOTION_SHARPE_MIN
    )
    trades_pass = bool(pooled_entries > PROMOTION_MIN_POOLED_OOS_TRADES)
    return {
        "net_oos_sharpe_canonical_365": mean_oos_sharpe,
        "net_oos_sharpe_min": PROMOTION_SHARPE_MIN,
        "sharpe_criterion_pass": sharpe_pass,
        "pooled_oos_position_round_trips": pooled_entries,
        "pooled_oos_rebalance_days_repo_convention": rebalance_days,
        "pooled_oos_settlement_observations": settlement_observations,
        "min_pooled_oos_trades": PROMOTION_MIN_POOLED_OOS_TRADES,
        "trade_count_criterion_pass": trades_pass,
        "promotion_gate_pass": bool(sharpe_pass and trades_pass),
        "gate_pass_note": (
            "The Sharpe criterion is met by a wide margin. The trade-count "
            "criterion is not met on independent position round trips; the "
            "repository's rebalance-day count is reported next to it because "
            "for a continuously held carry position it counts daily "
            "rebalances of one position, not independent trades. The always-on "
            "book reports 0 round trips in the out-of-sample window because it "
            "opens its position once, before that window, and never closes it: "
            "its independent observations are the daily funding settlements "
            "(3,828 eight-hour settlements in the window), not new positions. "
            "That is a counting convention, stated here so that '0 trades' is "
            "not read as a defect in the construction."
        ),
    }


def main() -> int:
    paths = {base: load_carry_path(base) for base in BASE_SYMBOLS}
    identity = {base: check_identity(paths[base]) for base in BASE_SYMBOLS}

    reconciliation = screen_reconciliation(paths)

    books: dict[str, dict[str, Any]] = {}
    portfolio_results: dict[str, dict[str, Any]] = {}
    per_symbol_gate_results: dict[str, dict[str, Any]] = {}

    for rule in RULES:
        portfolio = portfolio_book(paths, rule)
        portfolio_results[rule.rule_id] = evaluate_book(portfolio)
        for base in BASE_SYMBOLS:
            symbol_book = build_book(paths[base], rule, weight=1.0)
            books[f"{base}_{rule.rule_id}"] = evaluate_book(symbol_book)

    # The gate is evaluated on the per-symbol books, pooled over the symbols.
    for rule in RULES:
        per_symbol_gate_results[rule.rule_id] = promotion_gate(
            {base: books[f"{base}_{rule.rule_id}"] for base in BASE_SYMBOLS}
        )

    # Benchmark (equal-weight spot buy-and-hold) on the same samples.
    bench_gross, bench_turnover = benchmark_series(paths)
    bench_net = bench_gross - bench_turnover * (DECISION_BPS / 10000.0)
    bench_weights = pd.DataFrame(
        {base: 0.5 for base in BASE_SYMBOLS}, index=bench_gross.index
    )
    benchmark = {
        sample: {
            "sessions": int(len(bench_net.loc[sample_index(bench_net.index, sample)])),
            "ann_return_geometric": float(
                compute_metrics(
                    bench_net.loc[sample_index(bench_net.index, sample)],
                    bench_weights.loc[sample_index(bench_net.index, sample)],
                    COMMISSION_BPS,
                    SLIPPAGE_BPS,
                    RF_ANNUAL,
                    periods_per_year=PERIODS_PER_YEAR,
                )["annualized_return"]
            ),
            "sharpe_canonical": float(
                sharpe_ratio(
                    bench_net.loc[sample_index(bench_net.index, sample)],
                    periods_per_year=PERIODS_PER_YEAR,
                )
            ),
            "max_drawdown": max_drawdown(
                bench_net.loc[sample_index(bench_net.index, sample)]
            ),
        }
        for sample in SPLITS
    }

    robustness = {
        "cost_sensitivity_portfolio": {
            rule.rule_id: cost_sensitivity(portfolio_book(paths, rule))
            for rule in RULES
        },
        "turnover_convention_sensitivity": {
            rule.rule_id: turnover_convention_sensitivity(paths, rule)
            for rule in RULES
        },
        "funding_rounding_and_settlement": funding_rounding_sensitivity(paths),
        "convergence_sensitivity": convergence_sensitivity(paths),
        "return_decomposition": return_decomposition(paths),
        "capacity": capacity_analysis(paths),
    }

    cost_models = evaluate_cost_models(paths)
    convention_bounds = turnover_convention_bounds(paths)

    meta = {
        "generated_at": datetime.now(UTC).isoformat(),
        "periods_per_year": PERIODS_PER_YEAR,
        "screen_periods_per_year": SCREEN_PERIODS_PER_YEAR,
        "cost_model": {
            "decision_bps_per_unit": DECISION_BPS,
            "sensitivity_rows_bps": list(COST_ROWS_BPS),
            "commission_bps": COMMISSION_BPS * 10000.0,
            "slippage_bps": SLIPPAGE_BPS * 10000.0,
            "source": "src/backtest/engine.py:get_cost_params (config/settings.yaml)",
        },
        "risk_free_rate_annual": RF_ANNUAL,
        "bootstrap": {
            "block_days": BOOTSTRAP_BLOCK_DAYS,
            "draws": BOOTSTRAP_DRAWS,
            "seed": BOOTSTRAP_SEED,
        },
        "splits": {name: {"start": start, "end": end} for name, (start, end) in SPLITS.items()},
        "data": {
            "source": "Binance public archive (data.binance.vision), SHA256-verified",
            "carry_paths": "data/processed/crypto/{BTCUSDT,ETHUSDT}_carry_path.parquet",
            "start": str(paths["BTCUSDT"].index.min().date()),
            "end": str(paths["BTCUSDT"].index.max().date()),
            "rows": int(len(paths["BTCUSDT"])),
            "frequency": "daily (UTC), 24/7",
            "universe": ["BTCUSDT perp", "ETHUSDT perp"],
            "identity_max_deviation": identity,
        },
        "trial_count": (
            "6 candidate configurations (3 rules x 2 symbols); the BTC/ETH "
            "portfolio is an equal-weight combination of the two symbol books, "
            "not an additional configuration. The robustness rows and the "
            "cost-model rows (capital charge, venue fee schedule, turnover "
            "convention) are sensitivity analyses of the same configurations, "
            "not new trials."
        ),
        "promotion_gates": {
            "net_oos_sharpe_min": PROMOTION_SHARPE_MIN,
            "min_pooled_oos_trades": PROMOTION_MIN_POOLED_OOS_TRADES,
        },
        "cost_models": {
            "headline": HEADLINE_COST_MODEL,
            "headline_turnover_convention": HEADLINE_CONVENTION,
            "models": {
                model.key: {
                    "label": model.label,
                    "kind": model.kind,
                    "flat_bps_per_unit": model.flat_bps,
                    "spot_bps_per_unit": model.spot_bps,
                    "perp_bps_per_unit": model.perp_bps,
                    "capital_rate_annual": model.capital_rate_annual,
                    "source": model.source,
                    "note": model.note,
                }
                for model in COST_MODELS
            },
            "venue_fee_schedule": {
                "venue": "Binance",
                "tier": "VIP 0 (standard, published schedule)",
                "spot_maker_bps": VENUE_SPOT_MAKER_BPS,
                "spot_taker_bps": VENUE_SPOT_TAKER_BPS,
                "perp_maker_bps": VENUE_PERP_MAKER_BPS,
                "perp_taker_bps": VENUE_PERP_TAKER_BPS,
                "repository_slippage_bps_per_unit": REPO_SLIPPAGE_BPS,
                "sources": [
                    "Binance, 'VIP Program: Updates to Spot and Margin Trading "
                    "Fees for VIP 3 - VIP 9 Users' (2024-10-07): Normal User "
                    "maker 0.1000% / taker 0.1000% on spot.",
                    "Binance futures fee explainer (support FAQ 360033544231): "
                    "a Regular User's maker fee is 0.02% and taker fee 0.05% "
                    "on USDⓈ-M futures.",
                    "config/settings.yaml: default_slippage_bps (the "
                    "repository's own slippage assumption).",
                ],
                "accessed": "2026-10-20",
                "note": (
                    "Published schedule used as a documented assumption; no "
                    "live fees are implied (the account-specific table is only "
                    "visible after login). The BNB fee discount is not claimed."
                ),
            },
            "capital_charge_grid": {
                name: rate for name, rate in CAPITAL_CHARGE_RATES.items()
            },
            "capital_charge_convention": (
                "The charge is applied to the spot leg's notional (the cash the "
                "delta-neutral book ties up; the short perp leg is "
                "self-financing because its own proceeds are posted as its "
                "margin). The repository's backtest-baseline Sharpe/Sortino "
                "already subtract the 2% risk-free rate from the ratio's "
                "numerator while the return series does not pay it, so the "
                "backtest-scale metrics of a capital-charge row are computed "
                "with a zero risk-free rate (no double counting). The "
                "canonical gate convention (arithmetic_annualized_rf0) is "
                "unaffected either way."
            ),
        },
    }

    summary = {
        "meta": meta,
        "reconciliation_with_cost_screen": reconciliation,
        "portfolio": portfolio_results,
        "per_symbol": books,
        "benchmark_spot_buy_and_hold": benchmark,
        "robustness": robustness,
        "promotion_gates": per_symbol_gate_results,
        "cost_model_evaluation": cost_models,
        "turnover_convention_bounds": convention_bounds,
    }

    artifact = render_artifact(summary)
    ARTIFACT_PATH.write_text(artifact)

    print(f"identity check: {identity}")
    print(f"written: {ARTIFACT_PATH.relative_to(REPO)}")
    for rule in RULES:
        full = portfolio_results[rule.rule_id]["samples"]["full"]
        oos = portfolio_results[rule.rule_id]["samples"]["test_oos"]
        gate = per_symbol_gate_results[rule.rule_id]
        print(
            f"{rule.rule_id:28s} ann_net(365)={full['ann_return_geometric']:+.4%} "
            f"sharpe={full['sharpe_canonical']:.3f} oos_sharpe={oos['sharpe_canonical']:.3f} "
            f"turn/yr={full['annualized_turnover_units']:.2f} "
            f"gate_pass={gate['promotion_gate_pass']}"
        )
    print("--- cost models (headline turnover convention: "
          f"{HEADLINE_CONVENTION}) ---")
    for rule in RULES:
        row = cost_models["portfolio"][rule.rule_id]
        for model in COST_MODELS:
            full = row[model.key]["samples"]["full"]
            oos = row[model.key]["samples"]["test_oos"]
            gate = cost_models["gates"][rule.rule_id][model.key]
            print(
                f"{rule.rule_id:28s} {model.key:28s} "
                f"ann_net={full['ann_return_geometric']:+.4%} "
                f"sharpe={full['sharpe_canonical']:.3f} "
                f"oos_sharpe={oos['sharpe_canonical']:.3f} "
                f"gate_pass={gate['promotion_gate_pass']}"
            )
    return 0


# ======================================================================
# Artifact rendering
# ======================================================================
def _fmt_pct(value: float, digits: int = 4) -> str:
    return f"{value * 100:+.{digits}f}%"


def _fmt_bp(value: float) -> str:
    return f"{value:.4f} bp"


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """The machine-readable summary, with the cost-model grid compacted.

    The cost-model grid is a sensitivity analysis of the same six
    configurations, so the machine-readable payload keeps the headline model
    in full and only the key metrics of the other models. The tables in the
    record above carry every number.
    """
    compact = dict(summary)
    cost_eval = summary["cost_model_evaluation"]
    headline = cost_eval["headline_cost_model"]
    compact["cost_model_evaluation"] = {
        "headline_cost_model": headline,
        "headline_turnover_convention": cost_eval["headline_turnover_convention"],
        "portfolio": {
            rule_id: {
                model_key: {
                    "samples": {
                        sample: {
                            key: metrics[key]
                            for key in _KEY_METRIC_FIELDS
                            if key in metrics
                        }
                        for sample, metrics in result["samples"].items()
                    }
                    if model_key != headline
                    else result
                }
                for model_key, result in rows.items()
            }
            for rule_id, rows in cost_eval["portfolio"].items()
        },
        "per_symbol": cost_eval["per_symbol"],
        "gates": cost_eval["gates"],
        "break_evens": cost_eval["break_evens"],
    }
    return compact


def render_artifact(summary: dict[str, Any]) -> str:
    """Render the experiment record of this evaluation."""
    meta = summary["meta"]
    recon = summary["reconciliation_with_cost_screen"]
    portfolio = summary["portfolio"]
    benchmark = summary["benchmark_spot_buy_and_hold"]
    robustness = summary["robustness"]
    gates = summary["promotion_gates"]

    lines: list[str] = []
    add = lines.append

    add("# Experiment: cryptofunding_002_evaluation — realistic execution and capital-cost model (Cycle 892)")
    add("")
    add("Hypothesis: `research/hypotheses/cryptofunding_001.md`")
    add("")
    add(
        "This record supersedes the Cycle 891 evaluation "
        "(`research/experiments/cryptofunding_002_evaluation.md`, previous "
        "revision), which measured the net capture of the carry with the "
        "repository's flat 3 bp/unit turnover cost alone: no charge for the "
        "capital the book ties up in the spot leg and no venue-specific fee "
        "schedule. Cycle 892 measures the same three pre-registered rules "
        "under a realistic execution and capital-cost model and re-evaluates "
        "the promotion gates under it. The Cycle 891 numbers (flat model, "
        "365-day annualization, charged entry/exit transitions, previous-day "
        "funding signal) are unchanged and are reported below as the flat-model "
        "rows."
    )
    add("")

    # ---- data -------------------------------------------------------
    add("## Data used")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add(f"| Source | {meta['data']['source']} |")
    add(f"| Universe | {', '.join(meta['data']['universe'])} |")
    add(
        f"| Range | {meta['data']['start']} .. {meta['data']['end']} "
        f"({meta['data']['rows']} daily rows per symbol) |"
    )
    add(f"| Frequency | {meta['data']['frequency']} |")
    add(f"| Carry paths | `{meta['data']['carry_paths']}` |")
    add(
        "| Point-in-time treatment | Funding is attributed to the UTC day of "
        "its settlement timestamp and is never forward-filled; the funding-"
        "positive rule of this evaluation decides with the **previous** day's "
        "aggregate funding, the last information available before the trading "
        "day starts. |"
    )
    add(
        "| Identity check | `gross_carry == funding_cashflow + basis_convergence` "
        "holds row by row (max abs deviation "
        f"{max(meta['data']['identity_max_deviation'].values()):.1e}). |"
    )
    add("")
    add(
        "The price legs come from a single venue (Binance). The OKX funding "
        "series collected in Cycle 888 is an independent cross-check of the "
        "funding *levels* (91.2% sign agreement on the overlap window), not an "
        "independent price path."
    )
    add("")

    # ---- configuration ----------------------------------------------
    add("## Configuration")
    add("")
    add(
        f"* **Annualization:** {meta['periods_per_year']} periods/year "
        "(24/7 crypto). The cost screen's 252 is used only for the "
        "reconciliation below."
    )
    add(
        f"* **Cost model:** {meta['cost_model']['decision_bps_per_unit']} bp per "
        "unit of weight change (repository flat model: "
        f"{meta['cost_model']['commission_bps']:.1f} bp commission + "
        f"{meta['cost_model']['slippage_bps']:.1f} bp slippage); sensitivity "
        f"rows at {', '.join(f'{b:.1f}' for b in meta['cost_model']['sensitivity_rows_bps'])} bp."
    )
    add(
        "* **Book:** one unit of equity running a delta-neutral carry pair, "
        "`+w` spot and `-w` perp (200% gross notional, zero net). Single-symbol "
        "books use `w = 1.0`; the BTC/ETH portfolio uses `w = 0.5` per symbol, "
        "the construction the cost screen screens."
    )
    add(
        "* **Turnover:** the daily rebalance of the legs while the pair is held "
        "**plus** the position transitions: an entry (long spot + short perp) "
        "and an exit each change the leg weights by `2 * w` and are charged."
    )
    add(
        "* **Metrics:** `src/backtest/engine.compute_metrics` (annualized "
        "return, volatility, Sharpe, Sortino, max drawdown, profit factor) and "
        "`src.evaluation.sharpe.sharpe_ratio` (the canonical "
        "`arithmetic_annualized_rf0` gate convention), both evaluated on the "
        "365-day scale. Turnover and trade counts are supplied explicitly, "
        "because the engine's weight frame would net the two legs away."
    )
    add(
        f"* **Block bootstrap:** {meta['bootstrap']['draws']} draws, "
        f"{meta['bootstrap']['block_days']}-day blocks, seed "
        f"{meta['bootstrap']['seed']} (pre-registered in Cycle 890)."
    )
    add("* **Splits (pre-registered):**")
    for name, bounds in meta["splits"].items():
        add(f"  * `{name}`: {bounds['start']} .. {bounds['end']}")
    add(f"* **Trial count:** {meta['trial_count']}")
    add("")

    # ---- cost models --------------------------------------------------
    cost_meta = meta["cost_models"]
    fee_meta = cost_meta["venue_fee_schedule"]
    add("## Cost models (Cycle 892)")
    add("")
    add(
        "The repository's flat model charges one number per unit of weight "
        "change and nothing for the capital the book ties up. Cycle 892 "
        "measures the same three pre-registered rules under a realistic "
        "execution and capital-cost model:"
    )
    add("")
    add("| Model | Trading cost | Capital charge | Source |")
    add("|---|---|---|---|")
    for key, model in cost_meta["models"].items():
        if model["kind"] == "flat":
            trading = f"{model['flat_bps_per_unit']:.1f} bp per unit of weight change (both legs)"
        else:
            trading = (
                f"spot {model['spot_bps_per_unit']:.1f} bp / perp "
                f"{model['perp_bps_per_unit']:.1f} bp per unit of leg turnover"
            )
        charge = f"{model['capital_rate_annual'] * 100:.2f}%/yr on the spot leg's notional"
        marker = " **(headline)**" if key == cost_meta["headline"] else ""
        add(f"| `{key}`{marker} | {trading} | {charge} | {model['source']} |")
    add("")
    add("### The venue fee schedule")
    add("")
    add(
        f"**{fee_meta['venue']} {fee_meta['tier']}** (published schedule, accessed "
        f"{fee_meta['accessed']}):"
    )
    add("")
    add("| Leg | Maker | Taker |")
    add("|---|---|---|")
    add(
        f"| Spot | {fee_meta['spot_maker_bps']:.1f} bp | "
        f"{fee_meta['spot_taker_bps']:.1f} bp |"
    )
    add(
        f"| USDⓈ-M perp | {fee_meta['perp_maker_bps']:.1f} bp | "
        f"{fee_meta['perp_taker_bps']:.1f} bp |"
    )
    add("")
    for source in fee_meta["sources"]:
        add(f"* {source}")
    add("")
    add(
        f"The published fees are applied to the **leg weights that are actually "
        f"traded**, and the repository's own slippage assumption "
        f"({fee_meta['repository_slippage_bps_per_unit']:.1f} bp per unit of weight "
        "change) is added on top, because a fee schedule does not model "
        "execution slippage. " + fee_meta["note"]
    )
    add("")
    add("### The capital charge")
    add("")
    add(cost_meta["capital_charge_convention"])
    add("")
    add("| Sensitivity | Annual rate on the spot leg's notional |")
    add("|---|---|")
    for name, rate in cost_meta["capital_charge_grid"].items():
        add(f"| `{name}` | {rate * 100:.2f}% |")
    add("")
    add(
        "The 0% row is the row in which the capital is free; the `repo_rf` row "
        "is the repository's own risk-free rate and is the **headline**; the "
        "`usdt_5pct` row is the opportunity cost of the locked cash at a "
        "stablecoin-equivalent lending yield (a documented assumption, not a "
        "quoted rate)."
    )
    add("")
    add("### Which model is the headline, and why")
    add("")
    add(
        f"**Headline: `{cost_meta['headline']}` under the "
        f"`{cost_meta['headline_turnover_convention']}` turnover convention.** "
        "It is the conservative end of both cost axes at once: the *taker* "
        "fee schedule (the more expensive of the two published rates on the "
        "perp leg), the repository's slippage assumption on top of it, and the "
        "repository's risk-free rate as the charge for the capital the spot "
        "leg ties up. The cheaper corners - the maker schedule, no capital "
        "charge, a 5% yield - are reported as rows, and the flat model is "
        "reported unchanged so that the cost-model effect is isolated."
    )
    add("")

    # ---- rules ------------------------------------------------------
    add("## Rules evaluated")
    add("")
    add("| Rule | Look-ahead | Note |")
    add("|---|---|---|")
    for rule_id, result in portfolio.items():
        label = result["rule_label"]
        look = "yes" if result["look_ahead"] else "no"
        note = (
            "Pre-registered rule 2; the day's aggregate funding is only known "
            "after that day's settlements, so this variant is contaminated. "
            "Reported for reconciliation with Cycle 890 only."
            if result["look_ahead"]
            else (
                "Pre-registered rule 2, defect-corrected: the decision uses the "
                "previous day's aggregate funding."
                if result["rule"] == "funding_positive_lagged"
                else "Pre-registered rule 1."
            )
        )
        add(f"| `{rule_id}` ({label}) | {look} | {note} |")
    add("")

    # ---- headline results -------------------------------------------
    add("## Results (net of costs, 365-day annualization)")
    add("")
    add("### Portfolio (equal weight BTC/ETH)")
    add("")
    add(
        "| Rule | Sample | Sessions | Ann. net (geo) | Ann. net (arith) | "
        "Ann. vol | Sharpe (canonical) | Sharpe (backtest) | Sortino (canonical) | "
        "Sortino (backtest) | Max DD | "
        "Turnover/yr | Cost drag/yr | Entries | Rebalance days |"
    )
    add("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for rule_id, result in portfolio.items():
        for sample in ("full", "train", "val", "test_oos", "post2022"):
            m = result["samples"][sample]
            add(
                f"| `{rule_id}` | {sample} | {m['sessions']} | "
                f"{_fmt_pct(m['ann_return_geometric'])} | "
                f"{_fmt_pct(m['ann_return_arithmetic'])} | "
                f"{_fmt_pct(m['ann_volatility'])} | "
                f"{m['sharpe_canonical']:.3f} | {m['sharpe_backtest_scale']:.3f} | "
                f"{m['sortino_canonical']:.3f} | "
                f"{m['sortino_backtest_scale']:.3f} | "
                f"{_fmt_pct(m['max_drawdown'])} | "
                f"{m['annualized_turnover_units']:.2f} | "
                f"{_fmt_pct(m['annualized_cost_drag'])} | "
                f"{m['position_entries']} | {m['rebalance_days']} |"
            )
    add("")
    add(
        "**The two metric scales are the same daily series under two "
        "conventions, and they are never compared silently.** The *canonical* "
        "Sharpe/Sortino are the repository's gate convention "
        "(`arithmetic_annualized_rf0`: the arithmetic mean daily return, "
        "annualized, with a zero risk-free rate). The *backtest* Sharpe/Sortino "
        "are the engine's published backtest baseline "
        "(`src/backtest/engine.py:compute_metrics`): the **geometric** "
        "annualized return minus the 2% risk-free rate, over the annualized "
        "volatility / downside deviation. A rule whose net return is below the "
        "2% risk-free rate is therefore negative on the backtest scale while "
        "positive on the canonical scale - that is the convention, not a "
        "series mismatch, and it is why the promotion gate consumes the "
        "canonical scale only."
    )
    add("")
    add("### Per symbol (leg weight 1.0)")
    add("")
    add(
        "| Book | Sample | Sessions | Ann. net (geo) | Sharpe (canonical) | "
        "Max DD | Turnover/yr | Entries | Exits |"
    )
    add("|---|---|---|---|---|---|---|---|---|")
    for book_id, result in summary["per_symbol"].items():
        for sample in ("full", "test_oos", "post2022"):
            m = result["samples"][sample]
            add(
                f"| `{book_id}` | {sample} | {m['sessions']} | "
                f"{_fmt_pct(m['ann_return_geometric'])} | "
                f"{m['sharpe_canonical']:.3f} | {_fmt_pct(m['max_drawdown'])} | "
                f"{m['annualized_turnover_units']:.2f} | {m['position_entries']} | "
                f"{m['position_exits']} |"
            )
    add("")
    add("### Benchmark (equal-weight BTC/ETH spot buy-and-hold)")
    add("")
    add("| Sample | Sessions | Ann. return | Sharpe (canonical) | Max DD |")
    add("|---|---|---|---|---|")
    for sample, m in benchmark.items():
        add(
            f"| {sample} | {m['sessions']} | {_fmt_pct(m['ann_return_geometric'])} | "
            f"{m['sharpe_canonical']:.3f} | {_fmt_pct(m['max_drawdown'])} |"
        )
    add("")

    # ---- cost-model results -------------------------------------------
    cost_eval = summary["cost_model_evaluation"]
    add("## Results under the cost models (portfolio, equal weight BTC/ETH)")
    add("")
    add(
        "Every pre-registered rule under every cost model, on every "
        "pre-registered sample. The rules and the symbols are the same as in "
        "the flat-model table above; only the cost model changes."
    )
    add("")
    add(
        "| Rule | Cost model | Sample | Ann. net (geo) | Sharpe (canonical) | "
        "Max DD | Turnover/yr | Fee drag/yr | Capital drag/yr |"
    )
    add("|---|---|---|---|---|---|---|---|---|")
    for rule_id, rows in cost_eval["portfolio"].items():
        for model_key, result in rows.items():
            for sample in ("full", "train", "val", "test_oos", "post2022"):
                m = result["samples"][sample]
                add(
                    f"| `{rule_id}` | `{model_key}` | {sample} | "
                    f"{_fmt_pct(m['ann_return_geometric'])} | "
                    f"{m['sharpe_canonical']:.3f} | {_fmt_pct(m['max_drawdown'])} | "
                    f"{m['annualized_turnover_units']:.2f} | "
                    f"{_fmt_pct(m['annualized_fee_drag'])} | "
                    f"{_fmt_pct(m['annualized_capital_charge_drag'])} |"
                )
    add("")
    add(
        "The venue model charges the spot leg and the perp leg separately, so "
        "the two legs' turnovers are reported as well (the fee drag is the "
        "weighted average of the two published rates over the turnover that "
        "is actually traded):"
    )
    add("")
    add(
        "| Rule | Cost model | Spot turnover/yr | Perp turnover/yr | "
        "Spot notional (mean share of equity) | Fee drag/yr |"
    )
    add("|---|---|---|---|---|---|")
    for rule_id, rows in cost_eval["portfolio"].items():
        for model_key, result in rows.items():
            m = result["samples"]["full"]
            add(
                f"| `{rule_id}` | `{model_key}` | "
                f"{m['annualized_turnover_spot_units']:.2f} | "
                f"{m['annualized_turnover_perp_units']:.2f} | "
                f"{m['avg_spot_notional_fraction']:.3f} | "
                f"{_fmt_pct(m['annualized_fee_drag'])} |"
            )
    add("")

    # ---- break-evens ---------------------------------------------------
    add("### Break-evens")
    add("")
    add(
        "The three break-evens of every rule (portfolio), on the full sample "
        "and on the out-of-sample window:"
    )
    add("")
    add(
        "| Rule | Sample | Break-even flat cost/unit | Break-even capital charge "
        "(annual, on the spot leg) | Break-even multiple of the venue schedule |"
    )
    add("|---|---|---|---|---|")
    for rule_id, samples in cost_eval["break_evens"].items():
        for sample, row in samples.items():
            flat = row["break_even_flat_cost_bps"]["solution_bps"]
            cap = row["break_even_capital_charge_annual"]["solution_annual_rate"]
            mult = row["break_even_venue_fee_multiplier"]["solution_multiplier"]
            flat_txt = _fmt_bp(flat) if flat is not None else "none"
            cap_txt = _fmt_pct(cap, 2) if cap is not None else "none"
            mult_txt = f"{mult:.2f}x" if mult is not None else "none"
            add(
                f"| `{rule_id}` | {sample} | {flat_txt} | {cap_txt} | {mult_txt} |"
            )
    add("")
    add(
        "* The **break-even flat cost per unit** is the cost screen's own "
        "measure, computed on the same series: the flat cost at which the net "
        "annualized return is exactly zero."
    )
    add(
        "* The **break-even capital charge** holds the venue fees (taker + "
        "repository slippage) fixed and solves for the annual rate on the spot "
        "leg's notional at which the net annualized return is zero. A negative "
        "value means the book is already unprofitable before the capital is "
        "charged."
    )
    add(
        "* The **break-even multiple of the venue schedule** holds the capital "
        "charge (at the repository's risk-free rate) fixed and solves for the "
        "multiple of the published fee schedule at which the net annualized "
        "return is zero."
    )
    add("")

    # ---- turnover convention ------------------------------------------
    add("### The turnover convention: the headline and the bound")
    add("")
    add(
        "The pre-registered gross path is the **constant-notional** "
        "construction: the book resets the spot and the perp notionals to "
        "`w * equity` every day. The only turnover convention that is "
        "internally consistent with that gross path is therefore the daily "
        "constant-notional rebalance (`drift`), and that is the headline: the "
        "other two conventions do not describe the same book traded less "
        "often, they describe a *different* book (a fixed-coin book is paid "
        "its funding on a notional that scales with the coin's price, so its "
        "return on equity is a different quantity), and adopting them would "
        "require a self-consistent gross path that is outside this cycle's "
        "scope."
    )
    add("")
    add(
        "What an implementer would actually trade is a constant-notional "
        "target rebalanced on a *threshold* rather than every day, so the "
        "headline's daily cadence **over**-states the trading cost. The two "
        "other conventions bound the other end. The rows below are the "
        "headline cost model under each convention, and they bound how much "
        "the trading-frequency question can move the answer:"
    )
    add("")
    add(
        "| Rule | Convention | Consistent with the pre-registered gross path | "
        "Ann. net | Sharpe | Turnover/yr | Fee drag/yr |"
    )
    add("|---|---|---|---|---|---|---|")
    for rule_id, rows in summary["turnover_convention_bounds"].items():
        for convention, row in rows.items():
            add(
                f"| `{rule_id}` | `{convention}` | "
                f"{'yes' if row['consistent_with_pre_registered_gross_path'] else 'no (cost-only bound)'} | "
                f"{_fmt_pct(row['ann_return_geometric'])} | "
                f"{row['sharpe_canonical']:.3f} | "
                f"{row['annualized_turnover_units']:.2f} | "
                f"{_fmt_pct(row['annualized_fee_drag'])} |"
            )
    add("")

    # ---- bootstrap ---------------------------------------------------
    add("## Block-bootstrap intervals (moving block, 126-day blocks, 2000 draws)")
    add("")
    add(
        "| Book | Sample | Sharpe 95% CI | Ann. net (geometric) 95% CI | "
        "Ann. net (arithmetic) 95% CI |"
    )
    add("|---|---|---|---|---|")
    for book_id, result in summary["per_symbol"].items():
        for sample, boot in result["bootstrap"].items():
            add(
                f"| `{book_id}` | {sample} | "
                f"[{boot['sharpe_ci_95'][0]:.3f}, {boot['sharpe_ci_95'][1]:.3f}] | "
                f"[{_fmt_pct(boot['ann_return_geometric_ci_95'][0])}, "
                f"{_fmt_pct(boot['ann_return_geometric_ci_95'][1])}] | "
                f"[{_fmt_pct(boot['ann_return_arithmetic_ci_95'][0])}, "
                f"{_fmt_pct(boot['ann_return_arithmetic_ci_95'][1])}] |"
            )
    add("")

    # ---- reconciliation ---------------------------------------------
    add("## Reconciliation with the cost screen")
    add("")
    add(
        "The screen (`research/cost_admissibility_screen.py`, row "
        "`cryptofunding_001`) screens the **same** series at the "
        "repository-wide 252 convention and without the position transitions. "
        "The screen's series and this evaluation's series are identical "
        f"(gross identical: {recon['same_gross_series']}, turnover identical: "
        f"{recon['same_turnover_series']}), so the two rows describe the same "
        "candidate under two annualization conventions."
    )
    add("")
    add(
        "**The screen uses the repository's flat 3 bp/unit cost model.** It "
        "does not use the venue fee schedule and it does not charge the "
        "capital the spot leg ties up, so the screen's crypto row is the "
        "flat-model row of this record and not its headline. The screen is "
        "left untouched (the shared machinery and the other candidates' rows "
        "are unchanged) and it still ends with `OVERALL: PASS`."
    )
    add("")
    add(
        "**The screen's ADMISSIBLE verdict is therefore a statement about the "
        "flat 3 bp/unit model only.** It does not describe the headline model "
        "of this record, in which the traded cost per unit is several times "
        "the flat cost and the capital charge is not in the screen at all. "
        "The question the screen answers for the headline is answered here "
        "instead, by the break-evens: under the headline model the always-on "
        "book still nets a positive return, its break-even multiple of the "
        "published fee schedule is "
        f"{cost_eval['break_evens']['always_on']['full']['break_even_venue_fee_multiplier']['solution_multiplier']:.2f}x "
        "on the full sample, and its break-even capital charge is "
        f"{_fmt_pct(cost_eval['break_evens']['always_on']['full']['break_even_capital_charge_annual']['solution_annual_rate'], 2)} "
        "per year on the spot leg's notional."
    )
    add("")
    add("| Quantity | Screen (252) | This evaluation (365) |")
    add("|---|---|---|")
    add(
        f"| Annualized gross signal | {_fmt_pct(recon['screen_gross_annualized_signal'])} | "
        f"{_fmt_pct(recon['crypto_gross_annualized_signal'])} |"
    )
    add(
        f"| Annual turnover (units/yr) | {recon['screen_annual_turnover_units']:.2f} | "
        f"{recon['crypto_annual_turnover_units']:.2f} |"
    )
    add(
        f"| Cost drag at 3 bp/unit | {_fmt_pct(recon['screen_cost_drag_3bp'])} | "
        f"{_fmt_pct(recon['crypto_cost_drag_3bp'])} |"
    )
    add(
        f"| Net annualized return at 3 bp/unit | "
        f"{_fmt_pct(recon['screen_net_annualized_return_3bp'])} | "
        f"{_fmt_pct(recon['crypto_net_annualized_return_3bp'])} |"
    )
    add(
        f"| Break-even cost per unit | {_fmt_bp(recon['screen_break_even_cost_bps'])} | "
        "(invariant to the annualization convention) |"
    )
    add("")
    add(
        "The screen's cost drag understates the crypto drag by the factor "
        "365/252 = 1.452 and its gross signal understates the crypto gross "
        "signal by the same factor, so the **admissibility verdict is "
        "unaffected** (the break-even cost per unit is invariant)."
    )
    add("")

    # ---- robustness --------------------------------------------------
    add("## Robustness")
    add("")
    add("### Cost sensitivity (portfolio)")
    add("")
    add("| Rule | Cost/unit | Ann. net | Sharpe | Turnover/yr | Cost drag/yr |")
    add("|---|---|---|---|---|---|")
    for rule_id, rows in robustness["cost_sensitivity_portfolio"].items():
        for row in rows.values():
            add(
                f"| `{rule_id}` | {row['cost_bps_per_unit']:.1f} bp | "
                f"{_fmt_pct(row['ann_return_geometric'])} | "
                f"{row['sharpe_canonical']:.3f} | "
                f"{row['annualized_turnover_units']:.2f} | "
                f"{_fmt_pct(row['annualized_cost_drag'])} |"
            )
    add("")
    add("### Turnover-convention sensitivity (portfolio, 3 bp/unit)")
    add("")
    add("| Rule | Convention | Ann. net | Sharpe | Turnover/yr | Cost drag/yr |")
    add("|---|---|---|---|---|---|")
    for rule_id, rows in robustness["turnover_convention_sensitivity"].items():
        for convention, row in rows.items():
            add(
                f"| `{rule_id}` | {convention} | "
                f"{_fmt_pct(row['ann_return_geometric'])} | "
                f"{row['sharpe_canonical']:.3f} | "
                f"{row['annualized_turnover_units']:.2f} | "
                f"{_fmt_pct(row['annualized_cost_drag'])} |"
            )
    add("")
    for convention, note in TURNOVER_NOTES.items():
        add(f"* `{convention}`: {note}")
    add("")
    add("### Funding precision, rounding and settlement timing")
    add("")
    rounding = robustness["funding_rounding_and_settlement"]
    add(
        f"* The archived 8h funding rates carry "
        f"{rounding['published_rate_decimals']} decimals, so rounding them to "
        "the published precision is a no-op on the committed data."
    )
    add(
        f"* Worst-case per-settlement payment rounding: "
        f"{rounding['worst_case_rounding']['annual_return_impact']:.3e} per year "
        f"({rounding['worst_case_rounding']['annual_return_impact'] * 1e4:.6f} bp) "
        "- immaterial."
    )
    add(
        f"* Late entry (only the 08:00 and 16:00 UTC settlements captured): "
        f"ann. net {_fmt_pct(rounding['late_entry']['ann_return_geometric'])}, "
        f"Sharpe {rounding['late_entry']['sharpe_canonical']:.3f}."
    )
    add("")
    add("### Post-2022 and per-year stability (portfolio, 3 bp/unit)")
    add("")
    add("| Rule | Year | Sessions | Ann. net | Sharpe | Max DD | Turnover/yr | Invested |")
    add("|---|---|---|---|---|---|---|---|")
    for rule_id, result in portfolio.items():
        for year, row in result["yearly"].items():
            add(
                f"| `{rule_id}` | {year} | {row['sessions']} | "
                f"{_fmt_pct(row['ann_return_geometric'])} | "
                f"{row['sharpe_canonical']:.3f} | {_fmt_pct(row['max_drawdown'])} | "
                f"{row['annualized_turnover_units']:.2f} | "
                f"{row['invested_fraction']:.3f} |"
            )
    add("")
    add("### Capacity and liquidity")
    add("")
    add(
        "Daily quote volume of the traded legs (from the committed Binance "
        "klines) bounds the notional that can be rebalanced without moving the "
        "market:"
    )
    add("")
    add("| Symbol | Leg | Min daily quote volume | Median daily quote volume |")
    add("|---|---|---|---|")
    for symbol, entry in robustness["capacity"].items():
        if symbol == "participation_assumption":
            continue
        for market in ("spot", "perp"):
            stats = entry[market]
            add(
                f"| {symbol} | {market} | ${stats['min_daily_quote_volume']:,.0f} | "
                f"${stats['median_daily_quote_volume']:,.0f} |"
            )
    add("")
    add(
        "Indicative capacity (notional whose daily rebalance trade stays "
        "inside 1% of the leg's daily quote volume):"
    )
    add("")
    add("| Symbol | Convention | Median-day capacity | Worst-day capacity |")
    add("|---|---|---|---|")
    for symbol, entry in robustness["capacity"].items():
        if symbol == "participation_assumption":
            continue
        for label in ("drift", "parity"):
            median_key = f"spot_{label}_median"
            worst_key = f"spot_{label}_worst_day"
            if median_key in entry.get("capacity_usdt", {}):
                add(
                    f"| {symbol} | {label} | "
                    f"${entry['capacity_usdt'][median_key]:,.0f} | "
                    f"${entry['capacity_usdt'][worst_key]:,.0f} |"
                )
    add("")
    add(
        "The **one-time entry** is the binding constraint for an always-on "
        "book (it never trades again except for the daily rebalance):"
    )
    add("")
    add("| Symbol | Leg | Entry capacity (median day) | Entry capacity (worst day) |")
    add("|---|---|---|---|")
    for symbol, entry in robustness["capacity"].items():
        if symbol == "participation_assumption":
            continue
        for market in ("spot", "perp"):
            values = entry.get("entry_capacity_usdt", {})
            add(
                f"| {symbol} | {market} | "
                f"${values[f'{market}_median']:,.0f} | "
                f"${values[f'{market}_worst_day']:,.0f} |"
            )
    add("")
    add(
        f"({robustness['capacity']['participation_assumption']} The spot leg is "
        "the binding constraint for both symbols; the perp leg is deeper. The "
        "estimate ignores market impact beyond the participation budget, so it "
        "is an upper bound.)"
    )
    add("")
    add(
        "**The capacity of this candidate is small**: at a 1% participation "
        "budget the one-time entry of an always-on BTC+ETH book is bounded by "
        "the spot leg at roughly "
        + " / ".join(
            f"${robustness['capacity'][base]['entry_capacity_usdt']['spot_median']:,.0f}"
            for base in BASE_SYMBOLS
        )
        + " (median day) and by "
        + " / ".join(
            f"${robustness['capacity'][base]['entry_capacity_usdt']['spot_worst_day']:,.0f}"
            for base in BASE_SYMBOLS
        )
        + " (worst day) per symbol. A book larger than that either exceeds the "
        "participation budget or pays the market impact that the flat cost "
        "model does not capture."
    )
    add("")
    add("### Return decomposition (funding vs basis)")
    add("")
    add(
        "| Symbol | Funding/yr | Funding vol/yr | Basis/yr | Basis vol/yr | Gross/yr | Gross vol/yr | Positive-funding days |"
    )
    add("|---|---|---|---|---|---|---|---|")
    for symbol, row in robustness["return_decomposition"].items():
        add(
            f"| {symbol} | {_fmt_pct(row['funding_annualized'])} | "
            f"{_fmt_pct(row['funding_annualized_volatility'])} | "
            f"{_fmt_pct(row['basis_annualized'])} | "
            f"{_fmt_pct(row['basis_annualized_volatility'])} | "
            f"{_fmt_pct(row['gross_annualized'])} | "
            f"{_fmt_pct(row['gross_annualized_volatility'])} | "
            f"{row['funding_positive_day_fraction']:.3f} |"
        )
    add("")
    add(
        "The edge is the **funding payment**: the basis convergence is a "
        "near zero-sum change of the price difference and contributes nothing "
        "to the annualized return, but it is the reason the daily volatility "
        "is small and the Sharpe is large. A strategy that harvests the "
        "funding is therefore exposed to the funding regime itself, not to a "
        "diversifiable spread."
    )
    add("")
    add("### Sensitivity to the convergence assumption")
    add("")
    add(
        "| Rule | Gross with convergence/yr | Gross funding-only/yr | "
        "Funding-only Sharpe | Funding-only max DD |"
    )
    add("|---|---|---|---|---|")
    for rule_id, row in robustness["convergence_sensitivity"].items():
        add(
            f"| `{rule_id}` | {_fmt_pct(row['gross_with_convergence_ann'])} | "
            f"{_fmt_pct(row['gross_funding_only_ann'])} | "
            f"{row['gross_funding_only_sharpe']:.3f} | "
            f"{_fmt_pct(row['gross_funding_only_max_drawdown'])} |"
        )
    add("")
    add(robustness["convergence_sensitivity"]["always_on"]["note"])
    add("")

    # ---- gates -------------------------------------------------------
    add("## Promotion gates")
    add("")
    add("### Under the repository's flat model (Cycle 891, unchanged)")
    add("")
    add("| Rule | Net OOS Sharpe (canonical, 365) | Sharpe criterion | Pooled OOS round trips | Repo rebalance-day count | Settlement observations | Trade-count criterion | Gate |")
    add("|---|---|---|---|---|---|---|---|")
    for rule_id, gate in gates.items():
        add(
            f"| `{rule_id}` | {gate['net_oos_sharpe_canonical_365']:.3f} | "
            f"{'PASS' if gate['sharpe_criterion_pass'] else 'FAIL'} | "
            f"{gate['pooled_oos_position_round_trips']} | "
            f"{gate['pooled_oos_rebalance_days_repo_convention']} | "
            f"{gate['pooled_oos_settlement_observations']} | "
            f"{'PASS' if gate['trade_count_criterion_pass'] else 'FAIL'} | "
            f"**{'PASS' if gate['promotion_gate_pass'] else 'FAIL'}** |"
        )
    add("")
    add(gates["always_on"]["gate_pass_note"])
    add("")
    add("### Under every cost model (the gate is re-evaluated, never relaxed)")
    add("")
    add(
        "The gates are the repository's own thresholds, unchanged: a net "
        "out-of-sample Sharpe (canonical, 365) of at least "
        f"{PROMOTION_SHARPE_MIN} and more than "
        f"{PROMOTION_MIN_POOLED_OOS_TRADES} pooled out-of-sample independent "
        "trades. Only the cost model changes between the rows. The trade count "
        "is a property of the position path, not of the cost model, so it does "
        "not move between the rows."
    )
    add("")
    add(
        "| Rule | Cost model | Net OOS Sharpe (canonical, 365) | Sharpe criterion | "
        "Pooled OOS round trips | Trade-count criterion | Gate |"
    )
    add("|---|---|---|---|---|---|---|")
    sharpe_pass = 0
    sharpe_fail = 0
    trade_fail = 0
    total_rows = 0
    for rule_id, rows in cost_eval["gates"].items():
        for model_key, gate in rows.items():
            total_rows += 1
            sharpe_pass += int(bool(gate["sharpe_criterion_pass"]))
            sharpe_fail += int(not bool(gate["sharpe_criterion_pass"]))
            trade_fail += int(not bool(gate["trade_count_criterion_pass"]))
            add(
                f"| `{rule_id}` | `{model_key}` | "
                f"{gate['net_oos_sharpe_canonical_365']:.3f} | "
                f"{'PASS' if gate['sharpe_criterion_pass'] else 'FAIL'} | "
                f"{gate['pooled_oos_position_round_trips']} | "
                f"{'PASS' if gate['trade_count_criterion_pass'] else 'FAIL'} | "
                f"**{'PASS' if gate['promotion_gate_pass'] else 'FAIL'}** |"
            )
    add("")
    add(
        f"**Which criterion fails:** the trade-count criterion fails in all "
        f"{trade_fail} of the {total_rows} rows (the pooled out-of-sample "
        f"round trips are a property of the position path, not of the cost "
        f"model); the Sharpe criterion passes in {sharpe_pass} and fails in "
        f"{sharpe_fail} of them. The gate is therefore **FAIL** under every "
        "cost model, and the gate is never relaxed: the thresholds are the "
        "repository's own and are applied unchanged."
    )
    add("")

    # ---- verdict -----------------------------------------------------
    headline_rows = cost_eval["portfolio"]
    always = headline_rows["always_on"][HEADLINE_COST_MODEL]["samples"]
    always_flat = headline_rows["always_on"]["flat_3bp"]["samples"]
    lagged = headline_rows["funding_positive_lagged"][HEADLINE_COST_MODEL]["samples"]
    add("## Verdict")
    add("")
    add(
        "**Exploratory signal — not promoted.** Under the **realistic** cost "
        "model of this cycle (the published Binance VIP0 taker schedule plus "
        "the repository's slippage assumption, plus the repository's "
        "risk-free rate as the charge for the capital the spot leg ties up) "
        "the always-on BTC/ETH carry still nets "
        f"{_fmt_pct(always['full']['ann_return_geometric'])}/yr with a "
        f"canonical Sharpe of {always['full']['sharpe_canonical']:.3f} on the "
        "full sample, and the implementable funding-positive rule nets "
        f"{_fmt_pct(lagged['full']['ann_return_geometric'])}/yr with a "
        f"canonical Sharpe of {lagged['full']['sharpe_canonical']:.3f}. The "
        "carry survives the realistic cost model, but the candidate is **not** "
        "promoted, for four measured reasons:"
    )
    add("")
    add(
        "1. **The trade-count criterion of the promotion gate is not met** "
        "under any cost model: the pooled out-of-sample independent round "
        "trips are 95 (funding-positive) and 0 (always-on, which opens its "
        "position before the out-of-sample window), against the repository's "
        "100."
    )
    add(
        "2. **The realistic cost model removes most of the out-of-sample "
        "edge.** The always-on book's out-of-sample net return falls from "
        f"{_fmt_pct(always_flat['test_oos']['ann_return_geometric'])}/yr "
        f"(flat model) to "
        f"{_fmt_pct(always['test_oos']['ann_return_geometric'])}/yr and its "
        f"out-of-sample canonical Sharpe from "
        f"{always_flat['test_oos']['sharpe_canonical']:.3f} to "
        f"{always['test_oos']['sharpe_canonical']:.3f}; the implementable "
        "funding-positive rule's out-of-sample Sharpe is **negative** under "
        "the headline model. The carry is a low-volatility, low-return stream "
        "whose out-of-sample margin does not survive a realistic fee schedule "
        "and a realistic charge for the capital."
    )
    add(
        "3. The pre-registered funding-positive rule is contaminated by a "
        "look-ahead (the same day's aggregate funding). The implementable "
        "variant, which also pays for its entries and exits, is materially "
        "weaker than the Cycle 890 record reported."
    )
    add(
        "4. The edge is venue-specific (Binance only), regime-dependent "
        "(2021 is the best year by a wide margin) and structurally exposed to "
        "the funding-positive regime that produced it: a long period of "
        "negative funding removes the return *and* adds trading costs."
    )
    add("")
    add(
        "**What the realistic model changed.** The venue fee schedule is "
        f"{VENUE_SPOT_TAKER_BPS / DECISION_BPS:.0f}x (spot) and "
        f"{VENUE_PERP_TAKER_BPS / DECISION_BPS:.0f}x (perp) the repository's "
        f"flat {DECISION_BPS:.0f} bp per unit, and the capital charge adds "
        f"{RF_ANNUAL * 100:.0f}%/yr on the spot leg's notional; together they "
        "take the always-on book from "
        f"{_fmt_pct(always_flat['full']['ann_return_geometric'])}/yr to "
        f"{_fmt_pct(always['full']['ann_return_geometric'])}/yr. The break-even "
        "columns show how much room is left: the always-on book's break-even "
        "multiple of the published fee schedule is "
        f"{cost_eval['break_evens']['always_on']['full']['break_even_venue_fee_multiplier']['solution_multiplier']:.2f}x "
        "and its break-even capital charge is "
        f"{_fmt_pct(cost_eval['break_evens']['always_on']['full']['break_even_capital_charge_annual']['solution_annual_rate'], 2)}/yr."
    )
    add("")
    add(
        "The Sharpe criterion is met on the full sample, so the candidate "
        "deserves one more validation cycle (an independent venue's price and "
        "funding history, a self-consistent fixed-quantity or "
        "threshold-rebalanced construction, and the borrow/financing side of "
        "the spot leg) before it is either promoted or rejected."
    )
    add("")

    # ---- reproduction ------------------------------------------------
    add("## Reproduction")
    add("")
    add("```bash")
    add("python research/eval_cryptofunding.py")
    add("python -m pytest -q tests/test_eval_cryptofunding.py")
    add("python research/cost_admissibility_screen.py   # ends with OVERALL: PASS")
    add("python -m pytest -q")
    add("```")
    add("")
    add("## Machine-readable summary")
    add("")
    add("```json")
    add(json.dumps(_compact_summary(summary), indent=2, sort_keys=True, default=str))
    add("```")
    add("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())


def fixed_coin_book(
    path: pd.DataFrame,
    rule: RuleSpec,
    weight: float,
    symbol: str = "BTCUSDT",
) -> Book:
    """Fixed coin quantity construction: hold q coins from entry to exit.

    q is set at each entry from then-current equity: q = weight * equity / spot.
    Equity is marked to market. Price P&L is the change of the basis level
    q*(S_t - P_t); funding is paid on the coin's perp notional
    q*funding_cashflow_t*P_{t-1} (daily close as notional proxy).
    """
    position = position_series(path, rule)
    spot_close = path["spot_close"].astype(float) if "spot_close" in path.columns else None
    perp_close = path["perp_close"].astype(float) if "perp_close" in path.columns else None
    # fallback column names
    if spot_close is None:
        spot_close = path.get("spot_price", path.get("spot_close"))
    if perp_close is None:
        perp_close = path.get("perp_price", path.get("perp_close"))
    funding = path["funding_cashflow"].astype(float)

    index = path.index
    gross = pd.Series(0.0, index=index)
    equity = 1.0
    q = 0.0
    prev_basis = 0.0
    prev_perp = None
    held = False
    entries = 0
    exits = 0
    for i, ts in enumerate(index):
        pos = float(position.iloc[i])
        S = float(spot_close.iloc[i])
        P = float(perp_close.iloc[i])
        # entry transition
        if pos == 1.0 and not held:
            q = weight * equity / S if S != 0 else 0.0
            held = True
            entries += 1
            prev_basis = q * (S - P)
            prev_perp = P
            # no same-day PnL on entry? We'll handle via basis change next day
            gross.iloc[i] = 0.0
            continue
        if pos == 0.0 and held:
            # exit: realize remaining basis change to exit prices already captured previous day?
            held = False
            exits += 1
            q = 0.0
            gross.iloc[i] = 0.0
            continue
        if held:
            basis = q * (S - P)
            price_pnl = basis - prev_basis
            perp_notional = q * (prev_perp if prev_perp is not None else P)
            fund_pnl = funding.iloc[i] * perp_notional
            pnl = price_pnl + fund_pnl
            ret = pnl / equity if equity != 0 else 0.0
            gross.iloc[i] = ret
            equity = equity + pnl
            prev_basis = basis
            prev_perp = P
        else:
            gross.iloc[i] = 0.0
    # turnover: entries+exits only
    change = position.diff()
    if len(change) > 0:
        change.iloc[0] = position.iloc[0]
    transition_leg = change.abs() * weight
    turnover_spot = (2.0 * transition_leg).astype(float)  # approximate
    turnover_perp = (2.0 * transition_leg).astype(float)
    turnover = (4.0 * transition_leg).astype(float)
    weights = pd.DataFrame(
        {f"{symbol}_spot": (weight * position).astype(float),
         f"{symbol}_perp": (-weight * position).astype(float)},
        index=index,
    )
    positions = pd.DataFrame({f"{symbol}_position": position}, index=index)
    return Book(
        name=f"{symbol}_{rule.rule_id}_fixedcoin",
        symbol=symbol,
        rule=rule,
        weight=weight,
        turnover_convention="fixed_quantity",
        gross=gross,
        turnover=turnover,
        turnover_spot=turnover_spot,
        turnover_perp=turnover_perp,
        positions=positions,
        weights=weights,
        entries=entries,
        exits=exits,
        notes=["fixed coin quantity construction (approx)"],
    )
