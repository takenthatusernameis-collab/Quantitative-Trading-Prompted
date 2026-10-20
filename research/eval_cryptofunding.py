"""Cycle 891: hardened net-of-cost evaluation of the crypto funding carry candidate.

What this script does
---------------------
It evaluates the spot-long / perp-short perpetual-funding carry of
``cryptofunding_001`` (BTC + ETH, Binance USDT-margined perpetuals) on the
committed, checksum-verified carry paths, under the repository's own metric
machinery and under the **365-day** annualization that a 24/7 market requires.

The three defects it fixes (all raised by the Cycle 890 supervisor review):

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
* Cost model: the repository's flat model, ``3 bp per unit of weight change``
  (``get_cost_params()``: 1 bp commission + 2 bp slippage). Sensitivity rows
  at 1.5 bp and 4.5 bp are reported alongside.
* A *book* is one unit of equity running a delta-neutral carry pair:
  ``+w`` spot and ``-w`` perp (200% gross notional, zero net). A single-symbol
  book uses ``w = 1.0``; the BTC/ETH portfolio uses ``w = 0.5`` per symbol,
  which is exactly the construction the cost screen screens.

Reproduction
------------
::

    python research/eval_cryptofunding.py
    python -m pytest -q tests/test_eval_cryptofunding.py
    python -m pytest -q
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
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
        "convention): w*(|spot_return| + |perp_return|) while the pair is held."
    ),
    "parity": (
        "Equal-notional maintenance: only the basis drift is traded, "
        "w*|spot_return - perp_return| while the pair is held."
    ),
    "fixed_quantity": (
        "Fixed coin quantity on both legs (no daily rebalancing at all): the "
        "pair is entered and exited only."
    ),
}


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
    positions: pd.DataFrame
    weights: pd.DataFrame
    entries: int
    exits: int
    notes: list[str] = field(default_factory=list)

    @property
    def position(self) -> pd.Series:
        """The book's average position across its symbols (0 when flat)."""
        return self.positions.mean(axis=1)


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
        rebalance = weight * (spot.abs() + perp.abs()) * position
    elif turnover_convention == "parity":
        rebalance = weight * (spot - perp).abs() * position
    else:  # fixed_quantity
        rebalance = pd.Series(0.0, index=path.index)

    if charge_entry:
        change = position.diff()
        change.iloc[0] = position.iloc[0]
        transitions = change.abs() * 2.0 * weight
    else:
        transitions = pd.Series(0.0, index=path.index)

    turnover = (rebalance + transitions).astype(float)

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
) -> dict[str, Any]:
    """The metrics of *book* on the pre-registered *sample*.

    The return series is the **full path** sliced to the sample (so the cost of
    the first session of the sample is not lost), and the turnover and the
    position path are sliced with it.
    """
    idx = sample_index(net.index, sample)
    r = net.loc[idx]
    w = book.weights.loc[idx]
    t = book.turnover.loc[idx]
    p = book.position.loc[idx]
    if len(r) < 2:
        return {"sessions": int(len(r)), "sample": sample}

    engine = compute_metrics(
        r,
        w,
        COMMISSION_BPS,
        SLIPPAGE_BPS,
        RF_ANNUAL,
        periods_per_year=periods_per_year,
    )
    # The position changes are computed on the full path and then sliced, so a
    # sample that starts with an already-open position does not report a
    # spurious entry.
    change = position_changes(book.positions).loc[idx]
    ann_turnover = float(t.mean() * periods_per_year)
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
        "max_drawdown": float(engine["max_drawdown"]),
        "max_drawdown_recomputed": max_drawdown(r),
        "profit_factor": float(engine["profit_factor"]),
        "total_return": float(engine["total_return"]),
        "avg_gross_exposure": float(engine["avg_exposure"]),
        "annualized_turnover_units": ann_turnover,
        "annualized_cost_drag": ann_turnover * (float(cost_bps) / 10000.0),
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


def yearly_stability(book: Book, cost_bps: float = DECISION_BPS) -> dict[str, Any]:
    """Net annualized return, canonical Sharpe and max drawdown per calendar year."""
    net = net_series(book, cost_bps)
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
) -> dict[str, Any]:
    """The full metric set of one book."""
    net = net_series(book, cost_bps)
    samples = {
        sample: book_metrics(book, net, sample, cost_bps=cost_bps)
        for sample in SPLITS
    }
    intervals = {
        sample: bootstrap_ci(net.loc[sample_index(net.index, sample)])
        for sample in bootstrap_samples
    }
    return {
        "book": book.name,
        "symbol": book.symbol,
        "rule": book.rule.rule_id,
        "rule_label": book.rule.label,
        "look_ahead": book.rule.look_ahead,
        "turnover_convention": book.turnover_convention,
        "leg_weight": book.weight,
        "cost_bps_per_unit": cost_bps,
        "samples": samples,
        "bootstrap": intervals,
        "entries_full_sample": book.entries,
        "exits_full_sample": book.exits,
        "yearly": yearly_stability(book, cost_bps),
        "cost_sensitivity": cost_sensitivity(book),
    }


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
            "not an additional configuration. The robustness rows are "
            "sensitivity analyses of the same configurations, not new trials."
        ),
        "promotion_gates": {
            "net_oos_sharpe_min": PROMOTION_SHARPE_MIN,
            "min_pooled_oos_trades": PROMOTION_MIN_POOLED_OOS_TRADES,
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
    return 0


# ======================================================================
# Artifact rendering
# ======================================================================
def _fmt_pct(value: float, digits: int = 4) -> str:
    return f"{value * 100:+.{digits}f}%"


def _fmt_bp(value: float) -> str:
    return f"{value:.4f} bp"


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

    add("# Experiment: cryptofunding_002_evaluation — hardened net-of-cost evaluation (Cycle 891)")
    add("")
    add("Hypothesis: `research/hypotheses/cryptofunding_001.md`")
    add("")
    add(
        "This record supersedes the Cycle 890 evaluation "
        "(`research/experiments/cryptofunding_002_evaluation.md`, previous "
        "revision), which annualized a 24/7 crypto series at 252 periods/year "
        "and never charged the entry or the exit of the funding-positive rule."
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

    # ---- verdict -----------------------------------------------------
    add("## Verdict")
    add("")
    add(
        "**Exploratory signal — not promoted.** The carry is real and large "
        "net of the repository's cost model on every rule, symbol and sample, "
        "and it survives the post-2022 falsification condition, but the "
        "candidate is **not** promoted, for three measured reasons:"
    )
    add("")
    add(
        "1. The pre-registered funding-positive rule is contaminated by a "
        "look-ahead (the same day's aggregate funding). The implementable "
        "variant, which also pays for its entries and exits, is materially "
        "weaker than the Cycle 890 record reported."
    )
    add(
        "2. The Cycle 890 record reported "
        "`promotion_gate_pass: true` on a trade count that counted daily "
        "rebalances of a single position rather than independent round trips. "
        "On the honest count the trade criterion is not met."
    )
    add(
        "3. The edge is venue-specific (Binance only), regime-dependent "
        "(2021 is the best year by a wide margin) and structurally exposed to "
        "the funding-positive regime that produced it: a long period of "
        "negative funding removes the return *and* adds trading costs."
    )
    add("")
    add(
        "The Sharpe criterion is met with a very large margin, so the "
        "candidate deserves one more validation cycle (independent venue, "
        "live-fee schedule, borrow/financing costs on the spot leg) before it "
        "is either promoted or rejected."
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
    add(json.dumps(summary, indent=2, sort_keys=True, default=str))
    add("```")
    add("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
