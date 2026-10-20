"""Offline tests for the hardened crypto funding carry evaluation (Cycle 891).

No network access and no writes to ``data/`` or ``config/``. The tests
exercise the pure helpers of ``research/eval_cryptofunding.py`` against the
committed, checksum-verified carry paths and pin the conventions that the
Cycle 890 evaluation got wrong:

* the 365-day annualization of a 24/7 market,
* the transition (entry/exit) turnover of the funding-positive rule,
* the absence of a look-ahead in the implementable funding-positive rule,
* the two metric scales (canonical vs backtest baseline) on one named series,
* the reconciliation with the cost screen's crypto row,
* the promotion gate on honest trade counts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import research.eval_cryptofunding as ev  # noqa: E402
from src.backtest.engine import compute_metrics  # noqa: E402
from src.evaluation.sharpe import sharpe_ratio  # noqa: E402
from src.evaluation.statistics import block_bootstrap_sharpe  # noqa: E402

ARTIFACT = REPO_ROOT / "research" / "experiments" / "cryptofunding_002_evaluation.md"

#: The Cycle 890 published numbers of the always-on rule (252-day
#: annualization, no transition cost). They are the regression guard: the
#: hardened evaluation must reproduce them when it is rendered at 252 and
#: without the position transitions.
CYCLE_890_ALWAYS_ON = {
    "BTCUSDT": {
        "ann_net_252": 0.07982111915517964,
        "sharpe_252": 6.867815988821421,
        "max_dd": -0.024283209961711516,
        "ann_turnover_252": 10.608759855503205,
    },
    "ETHUSDT": {
        "ann_net_252": 0.09334799790919646,
        "sharpe_252": 5.994283795069187,
        "max_dd": -0.019107832580336548,
        "ann_turnover_252": 14.48215064926316,
    },
}


@pytest.fixture(scope="module")
def paths() -> dict[str, pd.DataFrame]:
    return {base: ev.load_carry_path(base) for base in ev.BASE_SYMBOLS}


@pytest.fixture(scope="module")
def always_on_books(paths) -> dict[str, ev.Book]:
    return {
        base: ev.build_book(paths[base], ev.RULES[0], weight=1.0) for base in ev.BASE_SYMBOLS
    }


# ======================================================================
# Data invariants
# ======================================================================
@pytest.mark.parametrize("base", list(ev.BASE_SYMBOLS))
def test_carry_path_identity_holds(paths, base: str) -> None:
    """gross_carry must equal funding_cashflow + basis_convergence row by row."""
    assert ev.check_identity(paths[base]) == 0.0


@pytest.mark.parametrize("base", list(ev.BASE_SYMBOLS))
def test_committed_sample_covers_the_pre_registered_splits(paths, base: str) -> None:
    index = paths[base].index
    for name, (start, end) in ev.SPLITS.items():
        idx = ev.sample_index(index, name)
        assert len(idx) > 0, f"split {name} is empty"
        assert str(idx[0].date()) >= start
        assert str(idx[-1].date()) <= end


# ======================================================================
# Annualization
# ======================================================================
def test_annualization_is_365_for_a_24_7_market() -> None:
    assert ev.PERIODS_PER_YEAR == 365
    assert ev.SCREEN_PERIODS_PER_YEAR == 252


def test_annualized_turnover_uses_365_days(always_on_books) -> None:
    book = always_on_books["BTCUSDT"]
    net = ev.net_series(book, ev.DECISION_BPS)
    metrics = ev.book_metrics(book, net, "full")
    expected = float(book.turnover.mean() * 365)
    assert metrics["annualized_turnover_units"] == pytest.approx(expected)
    # The 252 rendering of the *drift-only* turnover is the Cycle 890 number
    # (the one-off entry cost is not part of the daily turnover rate).
    path = ev.load_carry_path("BTCUSDT")
    drift = path["spot_return"].abs() + path["perp_return"].abs()
    assert float(drift.mean() * 252) == pytest.approx(
        CYCLE_890_ALWAYS_ON["BTCUSDT"]["ann_turnover_252"], rel=1e-9
    )


@pytest.mark.parametrize("base", list(ev.BASE_SYMBOLS))
def test_always_on_reproduces_the_cycle_890_record_at_252(always_on_books, base: str) -> None:
    """Rendering the hardened book at 252 without transitions must reproduce Cycle 890."""
    book = always_on_books[base]
    gross = book.gross
    turnover = book.turnover - (2.0 * book.weight) * book.position.diff().abs().fillna(
        book.position.iloc[0]
    )
    net = gross - turnover * (ev.DECISION_BPS / 10000.0)
    published = CYCLE_890_ALWAYS_ON[base]
    assert ev.annualized_return(net, 252) == pytest.approx(
        published["ann_net_252"], rel=1e-9
    )
    assert ev.sharpe_ratio(net, periods_per_year=252) == pytest.approx(
        published["sharpe_252"], rel=1e-9
    )
    assert ev.max_drawdown(net) == pytest.approx(published["max_dd"], rel=1e-9)


def test_compute_metrics_periods_per_year_is_backward_compatible() -> None:
    """The new keyword must not change the repository's 252 default."""
    rng = np.random.default_rng(7)
    returns = pd.Series(rng.normal(0.0002, 0.01, 300))
    weights = pd.DataFrame({"A": 1.0}, index=returns.index)
    default = compute_metrics(returns, weights, 1e-4, 2e-4, 0.02)
    explicit = compute_metrics(returns, weights, 1e-4, 2e-4, 0.02, periods_per_year=252)
    assert default["annualized_return"] == pytest.approx(explicit["annualized_return"])
    assert default["annualized_volatility"] == pytest.approx(explicit["annualized_volatility"])
    assert default["annualized_turnover"] == pytest.approx(explicit["annualized_turnover"])
    crypto = compute_metrics(returns, weights, 1e-4, 2e-4, 0.02, periods_per_year=365)
    assert crypto["annualized_volatility"] == pytest.approx(
        default["annualized_volatility"] * np.sqrt(365 / 252)
    )


# ======================================================================
# Turnover accounting
# ======================================================================
def test_always_on_turnover_is_drift_only_and_has_one_entry(always_on_books) -> None:
    book = always_on_books["BTCUSDT"]
    path = ev.load_carry_path("BTCUSDT")
    drift = (path["spot_return"].abs() + path["perp_return"].abs()).to_numpy()
    # Every session after the opening trades only the notional drift...
    assert book.turnover.to_numpy()[1:] == pytest.approx(drift[1:])
    # ...and the opening session also pays for the two legs of the pair.
    assert book.turnover.iloc[0] == pytest.approx(drift[0] + 2.0 * book.weight)
    assert book.entries == 1
    assert book.exits == 0


def test_funding_positive_charges_one_unit_per_entry_and_per_exit(paths) -> None:
    """The masked rule must pay for opening and closing the pair."""
    book = ev.build_book(paths["BTCUSDT"], ev.RULES[2], weight=1.0)
    transitions = 2.0 * book.weight * ev.position_changes(book.positions).abs().sum(axis=1)
    without = ev.build_book(paths["BTCUSDT"], ev.RULES[2], weight=1.0, charge_entry=False)
    assert book.turnover.to_numpy() == pytest.approx(
        (without.turnover + transitions).to_numpy()
    )
    # Every transition is charged exactly one leg pair (2 * weight).
    assert transitions[transitions > 0].unique().tolist() == pytest.approx([2.0])
    assert book.entries > 50 and book.exits > 50


def test_funding_positive_rule_has_no_look_ahead(paths) -> None:
    """The implementable rule may only use funding settled before the day starts."""
    path = ev.load_carry_path("BTCUSDT")
    position = ev.position_series(path, ev.RULES[2])
    previous = path["funding_cashflow"].astype(float).shift(1)
    expected = (previous > 0).astype(float)
    expected.iloc[0] = 0.0
    assert position.to_numpy() == pytest.approx(expected.to_numpy())
    # The pre-registered same-day rule is contaminated and must differ.
    contaminated = ev.position_series(path, ev.RULES[1])
    assert not np.allclose(contaminated.to_numpy(), position.to_numpy())


# ======================================================================
# Metric conventions
# ======================================================================
def test_canonical_sharpe_is_mean_over_std_times_sqrt_365(always_on_books) -> None:
    book = always_on_books["BTCUSDT"]
    net = ev.net_series(book, ev.DECISION_BPS)
    metrics = ev.book_metrics(book, net, "full")
    expected = float(net.mean() / net.std(ddof=1) * np.sqrt(365))
    assert metrics["sharpe_canonical"] == pytest.approx(expected)


def test_both_metric_scales_use_the_same_daily_series(always_on_books) -> None:
    """The backtest-scale Sharpe/Sortino are the same series under the engine's convention.

    The engine subtracts the 2% risk-free rate from the *geometric*
    annualized return, so a rule that nets less than 2%/yr is negative on
    that scale while positive on the canonical scale. This test pins both
    formulas and therefore rules out a series mismatch.
    """
    book = always_on_books["BTCUSDT"]
    net = ev.net_series(book, ev.DECISION_BPS)
    for sample in ("full", "test_oos", "post2022"):
        idx = ev.sample_index(net.index, sample)
        r = net.loc[idx]
        metrics = ev.book_metrics(book, net, sample)
        ann_geo = ev.annualized_return(r, 365)
        ann_vol = float(r.std(ddof=1) * np.sqrt(365))
        assert metrics["ann_return_geometric"] == pytest.approx(ann_geo)
        assert metrics["ann_volatility"] == pytest.approx(ann_vol)
        assert metrics["sharpe_backtest_scale"] == pytest.approx(
            (ann_geo - ev.RF_ANNUAL) / ann_vol
        )
        assert metrics["sortino_backtest_scale"] == pytest.approx(
            (ann_geo - ev.RF_ANNUAL) / metrics["downside_deviation_annualized"]
        )
        # The canonical Sortino's sign follows the arithmetic mean.
        assert np.sign(metrics["sortino_canonical"]) == np.sign(
            metrics["ann_return_arithmetic"]
        )
        assert metrics["sortino_canonical"] == pytest.approx(
            ev.sortino_canonical(r, periods_per_year=365)
        )


def test_max_drawdown_comes_from_the_compounded_daily_series(always_on_books) -> None:
    book = always_on_books["BTCUSDT"]
    net = ev.net_series(book, ev.DECISION_BPS)
    metrics = ev.book_metrics(book, net, "full")
    cum = (1.0 + net).cumprod()
    expected = float((cum / cum.expanding().max() - 1.0).min())
    assert metrics["max_drawdown"] == pytest.approx(expected)
    assert metrics["max_drawdown_recomputed"] == pytest.approx(expected)


def test_bootstrap_distribution_matches_the_repository_helper(always_on_books) -> None:
    book = always_on_books["BTCUSDT"]
    net = ev.net_series(book, ev.DECISION_BPS)
    boot = ev.bootstrap_ci(net, n_samples=50, block_size=21, seed=11)
    reference = block_bootstrap_sharpe(
        net, n_samples=50, block_size=21, seed=11, periods_per_year=365
    )
    assert boot["sharpe_ci_95"][0] == pytest.approx(float(np.percentile(reference, 2.5)))
    assert boot["sharpe_ci_95"][1] == pytest.approx(float(np.percentile(reference, 97.5)))


def test_bootstrap_settings_match_the_pre_registration() -> None:
    assert ev.BOOTSTRAP_BLOCK_DAYS == 126
    assert ev.BOOTSTRAP_DRAWS == 2000
    assert ev.BOOTSTRAP_SEED == 20261019
    assert ev.SPLITS["train"] == ("2020-01-02", "2022-12-31")
    assert ev.SPLITS["val"] == ("2023-01-01", "2024-12-31")
    assert ev.SPLITS["test_oos"] == ("2025-01-01", "2026-09-30")
    assert ev.SPLITS["post2022"] == ("2023-01-01", "2026-09-30")


# ======================================================================
# Aggregation and reconciliation
# ======================================================================
def test_portfolio_is_the_equal_weight_of_the_two_symbol_books(paths) -> None:
    for rule in ev.RULES:
        portfolio = ev.portfolio_book(paths, rule)
        btc = ev.build_book(paths["BTCUSDT"], rule, weight=1.0)
        eth = ev.build_book(paths["ETHUSDT"], rule, weight=1.0)
        expected = 0.5 * (
            ev.net_series(btc, ev.DECISION_BPS) + ev.net_series(eth, ev.DECISION_BPS)
        )
        actual = ev.net_series(portfolio, ev.DECISION_BPS)
        assert actual.to_numpy() == pytest.approx(expected.to_numpy())
        assert portfolio.entries == btc.entries + eth.entries


def test_reconciliation_with_the_cost_screen(paths) -> None:
    """The screen's crypto row and this evaluation describe the same series."""
    recon = ev.screen_reconciliation(paths)
    assert recon["same_gross_series"] is True
    assert recon["same_turnover_series"] is True
    assert recon["screen_gross_annualized_signal"] == pytest.approx(0.090672, abs=1e-6)
    assert recon["screen_annual_turnover_units"] == pytest.approx(12.55, abs=0.005)
    assert recon["screen_cost_drag_3bp"] == pytest.approx(0.003764, abs=1e-6)
    assert recon["screen_break_even_cost_bps"] == pytest.approx(69.1853, abs=1e-3)
    # The crypto convention annualizes 365/252 times as much.
    assert recon["crypto_annual_turnover_units"] == pytest.approx(
        recon["screen_annual_turnover_units"] * 365 / 252, rel=1e-9
    )


def test_promotion_gate_is_not_passed_on_honest_trade_counts(paths) -> None:
    per_symbol = {}
    for rule in ev.RULES:
        books = {
            base: ev.evaluate_book(
                ev.build_book(paths[base], rule, weight=1.0), bootstrap_samples=()
            )
            for base in ev.BASE_SYMBOLS
        }
        gate = ev.promotion_gate(books)
        per_symbol[rule.rule_id] = gate
        assert gate["promotion_gate_pass"] is False
        assert gate["pooled_oos_position_round_trips"] < ev.PROMOTION_MIN_POOLED_OOS_TRADES
    # The always-on book opens its position before the out-of-sample window.
    assert per_symbol["always_on"]["pooled_oos_position_round_trips"] == 0
    assert per_symbol["always_on"]["pooled_oos_rebalance_days_repo_convention"] > 1000


# ======================================================================
# Cost models (Cycle 892)
# ======================================================================
def test_venue_fee_schedule_is_the_published_vip0_schedule() -> None:
    """The venue schedule must be the published VIP 0 numbers, not a guess."""
    assert ev.VENUE_SPOT_TAKER_BPS == 10.0
    assert ev.VENUE_SPOT_MAKER_BPS == 10.0
    assert ev.VENUE_PERP_TAKER_BPS == 5.0
    assert ev.VENUE_PERP_MAKER_BPS == 2.0
    assert ev.REPO_SLIPPAGE_BPS == 2.0
    # The headline model is the conservative end of both cost axes.
    headline = ev.COST_MODEL_BY_KEY[ev.HEADLINE_COST_MODEL]
    assert headline.kind == "venue"
    assert headline.spot_bps == ev.VENUE_SPOT_TAKER_BPS + ev.REPO_SLIPPAGE_BPS
    assert headline.perp_bps == ev.VENUE_PERP_TAKER_BPS + ev.REPO_SLIPPAGE_BPS
    assert headline.capital_rate_annual == ev.RF_ANNUAL


@pytest.mark.parametrize("convention", list(ev.TURNOVER_CONVENTIONS))
def test_leg_turnovers_sum_to_the_total_turnover(paths, convention: str) -> None:
    """The per-leg split must be a decomposition, not a second series."""
    for base in ev.BASE_SYMBOLS:
        book = ev.build_book(paths[base], ev.RULES[0], weight=1.0, turnover_convention=convention)
        assert book.turnover.to_numpy() == pytest.approx(
            (book.turnover_spot + book.turnover_perp).to_numpy()
        )
        assert (book.turnover_spot >= 0).all()
        assert (book.turnover_perp >= 0).all()


def test_drift_convention_trades_each_leg_its_own_drift(paths) -> None:
    """Under `drift` each leg trades the drift of its own price."""
    book = ev.build_book(paths["BTCUSDT"], ev.RULES[0], weight=1.0, turnover_convention="drift")
    path = ev.load_carry_path("BTCUSDT")
    assert book.turnover_spot.to_numpy()[1:] == pytest.approx(
        path["spot_return"].abs().to_numpy()[1:]
    )
    assert book.turnover_perp.to_numpy()[1:] == pytest.approx(
        path["perp_return"].abs().to_numpy()[1:]
    )


def test_transitions_are_charged_on_both_legs(paths) -> None:
    """An entry (long spot + short perp) trades both legs."""
    book = ev.build_book(paths["BTCUSDT"], ev.RULES[2], weight=1.0, turnover_convention="fixed_quantity")
    changes = ev.position_changes(book.positions).abs().sum(axis=1)
    assert book.turnover_spot.to_numpy() == pytest.approx(changes.to_numpy())
    assert book.turnover_perp.to_numpy() == pytest.approx(changes.to_numpy())


def test_flat_model_is_unchanged_by_the_per_leg_split(always_on_books) -> None:
    """The Cycle 891 flat-model numbers must not move."""
    for base, book in always_on_books.items():
        net = ev.net_series(book, ev.DECISION_BPS)
        assert net.to_numpy() == pytest.approx(
            (book.gross - book.turnover * (ev.DECISION_BPS / 10000.0)).to_numpy()
        )
        metrics = ev.book_metrics(book, net, "full")
        assert metrics["annualized_turnover_units"] == pytest.approx(
            float(book.turnover.mean() * 365)
        )
        assert metrics["annualized_cost_drag"] == pytest.approx(
            metrics["annualized_turnover_units"] * (ev.DECISION_BPS / 10000.0)
        )


def test_capital_charge_is_charged_on_the_spot_notional(paths) -> None:
    """The charge is the spot leg's notional times the annual rate, daily."""
    book = ev.build_book(paths["BTCUSDT"], ev.RULES[0], weight=1.0)
    rate = 0.05
    charge = ev.capital_charge_series(book, rate)
    expected = book.spot_notional * (rate / 365.0)
    assert charge.to_numpy() == pytest.approx(expected.to_numpy())
    # A zero rate is free capital, a negative rate is a rebate (the break-even
    # solver needs it to bracket the crossing).
    assert ev.capital_charge_series(book, 0.0).abs().sum() == 0.0
    assert (ev.capital_charge_series(book, -0.05) < 0).all()


def test_spot_notional_is_the_spot_leg_only(paths) -> None:
    """The perp leg is self-financing: it is not charged a capital cost."""
    book = ev.build_book(paths["BTCUSDT"], ev.RULES[0], weight=1.0)
    assert book.spot_notional.to_numpy() == pytest.approx(
        book.weights["BTCUSDT_spot"].to_numpy()
    )


def test_venue_model_charges_each_leg_at_its_own_rate(always_on_books) -> None:
    """The venue model's fee series is the per-leg fee, not a flat number."""
    book = always_on_books["BTCUSDT"]
    model = ev.COST_MODEL_BY_KEY["venue_taker"]
    fees = ev.fee_series(book, model)
    expected = (
        book.turnover_spot * (model.spot_bps / 10000.0)
        + book.turnover_perp * (model.perp_bps / 10000.0)
    )
    assert fees.to_numpy() == pytest.approx(expected.to_numpy())
    # The venue schedule is more expensive per unit than the flat model.
    flat = ev.fee_series(book, ev.COST_MODEL_BY_KEY["flat_3bp"])
    assert fees.mean() > flat.mean()


def test_capital_charge_rows_use_a_zero_risk_free_rate_in_the_engine_scale(
    always_on_books,
) -> None:
    """A charged capital cost must not be charged twice in the ratio."""
    book = always_on_books["BTCUSDT"]
    model = ev.COST_MODEL_BY_KEY["realistic_rf"]
    net = ev.net_series_model(book, model)
    metrics = ev.book_metrics(book, net, "full", cost_model=model)
    assert metrics["engine_risk_free_rate_annual"] == 0.0
    assert metrics["risk_free_rate_annual"] == ev.RF_ANNUAL
    # The canonical convention is a zero-risk-free-rate convention either way.
    assert metrics["sharpe_canonical"] == pytest.approx(
        float(net.mean() / net.std(ddof=1) * np.sqrt(365))
    )
    # A model without a capital charge keeps the engine's risk-free rate.
    no_capital = ev.COST_MODEL_BY_KEY["venue_taker_slippage"]
    metrics_no_capital = ev.book_metrics(
        book, ev.net_series_model(book, no_capital), "full", cost_model=no_capital
    )
    assert metrics_no_capital["engine_risk_free_rate_annual"] == ev.RF_ANNUAL


def test_cost_models_only_lower_the_return(always_on_books) -> None:
    """Every cost model must be at least as expensive as the flat model."""
    book = always_on_books["BTCUSDT"]
    base = ev.book_metrics(book, ev.net_series(book, ev.DECISION_BPS), "full")
    for model in ev.COST_MODELS:
        net = ev.net_series_model(book, model)
        metrics = ev.book_metrics(book, net, "full", cost_model=model)
        assert metrics["ann_return_arithmetic"] <= base["ann_return_arithmetic"] + 1e-12
        assert metrics["annualized_cost_drag"] >= base["annualized_cost_drag"] - 1e-12


def test_break_even_cost_per_unit_is_where_the_net_return_is_zero(paths) -> None:
    """The break-even flat cost must zero the net annualized return."""
    book = ev.portfolio_book(paths, ev.RULES[0])
    result = ev.break_even_flat_bps(book, "full")
    assert result["bracketed"] is True
    cost = result["solution_bps"]
    net = ev.net_series(book, cost)
    value = ev.annualized_return(net.loc[ev.sample_index(net.index, "full")], 365)
    assert value == pytest.approx(0.0, abs=1e-6)
    # A cheaper book is profitable, a more expensive one is not.
    assert ev.annualized_return(
        ev.net_series(book, cost - 5.0).loc[ev.sample_index(net.index, "full")], 365
    ) > 0.0
    assert ev.annualized_return(
        ev.net_series(book, cost + 5.0).loc[ev.sample_index(net.index, "full")], 365
    ) < 0.0


def test_break_even_capital_charge_is_where_the_net_return_is_zero(paths) -> None:
    """The break-even capital charge must zero the net annualized return."""
    from dataclasses import replace

    book = ev.portfolio_book(paths, ev.RULES[0])
    fee_model = ev.COST_MODEL_BY_KEY["venue_taker_slippage"]
    result = ev.break_even_capital_rate(book, fee_model, "full")
    assert result["bracketed"] is True
    rate = result["solution_annual_rate"]
    model = replace(fee_model, capital_rate_annual=rate)
    net = ev.net_series_model(book, model)
    value = ev.annualized_return(net.loc[ev.sample_index(net.index, "full")], 365)
    assert value == pytest.approx(0.0, abs=1e-6)
    # The always-on book holds the spot leg all the time, so the break-even
    # charge is the rate at which the capital cost eats the whole return.
    assert rate == pytest.approx(ev.RF_ANNUAL, abs=0.2)


def test_break_even_venue_multiple_is_where_the_net_return_is_zero(paths) -> None:
    """The break-even fee multiple must zero the net annualized return."""
    from dataclasses import replace

    book = ev.portfolio_book(paths, ev.RULES[0])
    model = ev.COST_MODEL_BY_KEY["realistic_rf"]
    result = ev.break_even_venue_multiplier(book, model, "full")
    assert result["bracketed"] is True
    multiplier = result["solution_multiplier"]
    scaled = replace(
        model, spot_bps=model.spot_bps * multiplier, perp_bps=model.perp_bps * multiplier
    )
    net = ev.net_series_model(book, scaled)
    value = ev.annualized_return(net.loc[ev.sample_index(net.index, "full")], 365)
    assert value == pytest.approx(0.0, abs=1e-6)
    assert multiplier > 1.0


def test_promotion_gate_is_not_passed_under_any_cost_model(paths) -> None:
    """The gate must fail under every cost model, and it is never relaxed."""
    for rule in ev.RULES:
        for model in ev.COST_MODELS:
            books = {
                base: ev.evaluate_book(
                    ev.build_book(paths[base], rule, weight=1.0),
                    bootstrap_samples=(),
                    cost_model=model,
                )
                for base in ev.BASE_SYMBOLS
            }
            gate = ev.promotion_gate(books)
            assert gate["promotion_gate_pass"] is False, (rule.rule_id, model.key)
            assert gate["pooled_oos_position_round_trips"] < ev.PROMOTION_MIN_POOLED_OOS_TRADES
            assert gate["sharpe_criterion_pass"] == (
                gate["net_oos_sharpe_canonical_365"] >= ev.PROMOTION_SHARPE_MIN
            )


def test_headline_convention_is_the_one_consistent_with_the_gross_path(paths) -> None:
    """The headline convention is documented and the others are cost-only bounds."""
    assert ev.HEADLINE_CONVENTION == "drift"
    bounds = ev.turnover_convention_bounds(paths)
    for rule_id, rows in bounds.items():
        for convention, row in rows.items():
            assert row["consistent_with_pre_registered_gross_path"] == (
                convention == ev.HEADLINE_CONVENTION
            )
        # The trading-frequency question is bounded: the cost-only corners are
        # cheaper than the headline, never more expensive.
        assert (
            rows["parity"]["annualized_fee_drag"]
            <= rows["drift"]["annualized_fee_drag"] + 1e-12
        )
        assert (
            rows["fixed_quantity"]["annualized_fee_drag"]
            <= rows["drift"]["annualized_fee_drag"] + 1e-12
        )


# ======================================================================
# Fixed coin quantity (Cycle 893)
# ======================================================================
def earning_days_mask(path, rule) -> pd.Series:
    """Days on which a fixed-coin book earns P&L: held and held the previous day.

    The entry day sizes ``q`` and earns nothing by convention; exit days are
    flat.
    """
    pos = ev.position_series(path, rule)
    return (pos == 1.0) & (pos.shift(1).fillna(0.0) == 1.0)


def test_fixed_coin_turnover_matches_claimed_trades(paths) -> None:
    """Fixed-coin turnover is entry/exit only: each leg trades ``weight`` per transition."""
    for base in ev.BASE_SYMBOLS:
        for rule in ev.RULES:
            book = ev.build_fixed_coin_book(paths[base], rule, weight=1.0)
            change = ev.position_changes(book.positions).squeeze(axis=1)
            # Entry/exit only: each leg trades ``weight`` per transition, nothing else.
            assert book.turnover_spot.to_numpy() == pytest.approx(
                (change.abs()).to_numpy()
            )
            assert book.turnover_perp.to_numpy() == pytest.approx(
                (change.abs()).to_numpy()
            )
            assert book.turnover.to_numpy() == pytest.approx(
                (2.0 * change.abs()).to_numpy()
            )
            assert book.entries == int((change > 0).to_numpy().sum())
            assert book.exits == int((change < 0).to_numpy().sum())
            assert (book.turnover[change == 0.0] == 0.0).all()


def test_fixed_coin_funding_equals_cashflow_times_notional_per_coin(paths) -> None:
    """Funding dollars over a holding stretch equal sum(funding_cashflow * q * P_{t-1})."""
    for base in ev.BASE_SYMBOLS:
        for rule in ev.RULES:
            book = ev.build_fixed_coin_book(paths[base], rule, weight=1.0)
            path = paths[base]
            spot = path["spot_close"].astype(float)
            perp = path["perp_close"].astype(float)
            funding = path["funding_cashflow"].astype(float)
            earning = earning_days_mask(path, rule)
            assert earning.any(), f"{base} {rule.rule_id} has no earning days"
            equity_prev = book.equity_path.shift(1).fillna(1.0)
            pnl = book.gross * equity_prev
            basis_level = book.coin_quantity * (spot - perp)
            price_pnl = basis_level - basis_level.shift(1)
            funding_dollars = pnl - price_pnl
            expected = book.coin_quantity * funding * perp.shift(1)
            np.testing.assert_allclose(
                funding_dollars[earning].to_numpy(),
                expected[earning].to_numpy(),
                rtol=1e-9,
                atol=1e-12,
            )


def test_fixed_coin_funding_scales_constant_notional_component(paths) -> None:
    """The fixed-coin funding component is the constant-notional funding-only
    return scaled by the notional fraction q * P_{t-1} / (weight * equity);
    identical when the notional is held at its target (fraction one)."""
    for base in ev.BASE_SYMBOLS:
        for rule in ev.RULES:
            fixed = ev.build_fixed_coin_book(paths[base], rule, weight=1.0)
            constant = ev.build_book(paths[base], rule, weight=1.0)
            path = paths[base]
            spot = path["spot_close"].astype(float)
            perp = path["perp_close"].astype(float)
            funding = path["funding_cashflow"].astype(float)
            earning = earning_days_mask(path, rule)
            equity_prev = fixed.equity_path.shift(1).fillna(1.0)
            pnl = fixed.gross * equity_prev
            q = fixed.coin_quantity
            basis_level = q * (spot - perp)
            price_pnl = basis_level - basis_level.shift(1)
            funding_ret = (pnl - price_pnl) / equity_prev
            cn_funding_ret = funding * constant.position  # weight * funding while held
            fraction = q * perp.shift(1) / equity_prev
            np.testing.assert_allclose(
                funding_ret[earning].to_numpy(),
                (cn_funding_ret * fraction)[earning].to_numpy(),
                rtol=1e-9,
                atol=1e-12,
            )


def test_fixed_coin_reproduces_constant_notional_funding_when_notional_constant() -> None:
    """With prices constant the notional stays at target and the fixed-coin
    funding component equals the constant-notional funding-only return (w * f)."""
    index = pd.date_range("2024-01-01", periods=6, freq="D", tz="UTC")
    path = pd.DataFrame(
        {
            "spot_close": 100.0,
            "perp_close": 100.0,
            "spot_return": 0.0,
            "perp_return": 0.0,
            "basis_convergence": 0.0,
            "gross_carry": 0.0001,
            "funding_cashflow": 0.0001,
        },
        index=index,
    )
    rule = ev.RULES[0]
    fixed = ev.build_fixed_coin_book(path, rule, weight=1.0)
    constant = ev.build_book(path, rule, weight=1.0)
    earning = earning_days_mask(path, rule)
    first = earning.idxmax()
    equity_prev = fixed.equity_path.shift(1).fillna(1.0)
    q = fixed.coin_quantity
    perp = path["perp_close"].astype(float)
    funding = path["funding_cashflow"].astype(float)
    # Notional held at the target weight on the first earning day.
    np.testing.assert_allclose(
        (q * perp.shift(1) / equity_prev).loc[first], 1.0, rtol=1e-12, atol=1e-15
    )
    # Funding component equals w * f = f there.
    pnl = fixed.gross * equity_prev
    basis_level = q * (path["spot_close"].astype(float) - perp)
    funding_ret = (pnl - (basis_level - basis_level.shift(1))) / equity_prev
    np.testing.assert_allclose(
        funding_ret.loc[first],
        funding.loc[first],
        rtol=1e-9,
        atol=1e-12,
    )
    # The constant-notional funding-only return is weight * funding = f.
    cn_funding = constant.gross * constant.position
    np.testing.assert_allclose(
        cn_funding[earning].to_numpy(), funding[earning].to_numpy(), rtol=1e-12, atol=1e-15
    )


def test_fixed_coin_promotion_gate_never_passes(paths) -> None:
    """The gate is re-evaluated for the fixed-coin construction and never passes."""
    model = ev.COST_MODEL_BY_KEY[ev.HEADLINE_COST_MODEL]
    for rule in ev.RULES:
        books = {
            base: ev.evaluate_book(
                ev.build_fixed_coin_book(paths[base], rule, weight=1.0),
                bootstrap_samples=(),
                cost_model=model,
            )
            for base in ev.BASE_SYMBOLS
        }
        gate = ev.promotion_gate(books)
        assert gate["promotion_gate_pass"] is False, (rule.rule_id,)
        assert gate["pooled_oos_position_round_trips"] < ev.PROMOTION_MIN_POOLED_OOS_TRADES


# ======================================================================
# The committed record
# ======================================================================
def test_committed_artifact_is_consistent_with_the_code() -> None:
    assert ARTIFACT.exists(), "missing committed evaluation record"
    text = ARTIFACT.read_text()
    assert "365" in text
    assert "promotion_gate_pass" in text
    start = text.index("```json") + len("```json")
    end = text.index("```", start)
    payload = json.loads(text[start:end])
    assert payload["meta"]["periods_per_year"] == 365
    assert payload["meta"]["trial_count"]
    for rule_id, gate in payload["promotion_gates"].items():
        assert gate["promotion_gate_pass"] is False, rule_id
    assert payload["reconciliation_with_cost_screen"]["same_gross_series"] is True
    assert payload["reconciliation_with_cost_screen"]["same_turnover_series"] is True


def test_committed_artifact_states_the_realistic_cost_model() -> None:
    """The record must state the headline model, its sources and the screen's premise."""
    text = ARTIFACT.read_text()
    assert "## Cost models (Cycle 892)" in text
    assert "### Break-evens" in text
    assert "Binance VIP 0" in text
    assert "2026-10-20" in text  # the fee schedule's access date
    assert "flat 3 bp/unit cost model" in text  # the screen's premise
    payload = json.loads(
        text[text.index("```json") + len("```json") : text.index("```", text.index("```json") + len("```json"))]
    )
    cost_meta = payload["meta"]["cost_models"]
    assert cost_meta["headline"] == "realistic_rf"
    assert cost_meta["headline_turnover_convention"] == "drift"
    assert cost_meta["venue_fee_schedule"]["spot_taker_bps"] == 10.0
    assert cost_meta["venue_fee_schedule"]["perp_taker_bps"] == 5.0
    # The gate is re-evaluated under every cost model and never passes.
    gates = payload["cost_model_evaluation"]["gates"]
    assert gates
    for rule_id, rows in gates.items():
        for model_key, gate in rows.items():
            assert gate["promotion_gate_pass"] is False, (rule_id, model_key)
