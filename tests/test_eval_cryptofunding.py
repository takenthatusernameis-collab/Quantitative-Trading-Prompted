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
