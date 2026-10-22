"""Tests for the cryptofunding_001 evaluation (Cycle 944; corrected in Cycle 945)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import research.cryptofunding_001_evaluation as ev
import research.eval_cryptofunding as core


@pytest.fixture(scope="module")
def payload():
    return ev.build_payload()


@pytest.fixture(scope="module")
def headline_book():
    paths = {base: core.load_carry_path(base) for base in core.BASE_SYMBOLS}
    rule = next(r for r in core.RULES if r.rule_id == ev.HEADLINE_RULE)
    return core.portfolio_book(paths, rule)


def test_frozen_config_loads():
    config = ev.load_frozen_config()
    assert config["candidate_id"] == "cryptofunding_001"
    assert config["universe"] == ["BTCUSDT", "ETHUSDT"]


def test_evaluation_runs(payload):
    assert payload["data_unchanged"] is True
    assert payload["config_unchanged"] is True
    assert payload["artifacts_unchanged"] is True
    assert payload["overall"] == "PASS"


def test_frozen_cost_model_is_the_configured_one(payload):
    config = payload["config"]
    cost_model = payload["cost_model"]
    assert cost_model["kind"] == "flat"
    assert cost_model["flat_bps_per_unit"] == config["total_round_trip_bps"] == 5.0
    assert cost_model["capital_charge_annual"] == config["capital_charge_annual"] == 0.02


def test_headline_is_net_of_the_frozen_cost_model(payload, headline_book):
    """The published headline must be the frozen configuration's net return.

    The net series is rebuilt here from the book's primitives (gross return,
    turnover and the spot leg's notional), independently of the evaluator's
    own cost-model helper, and the annualized result must match the published
    headline. This is the regression guard for the Cycle 944 defect, in which
    the headline was computed with 0.02 bp/unit and no capital charge.
    """
    net = (
        headline_book.gross
        - headline_book.turnover * (5.0 / 10000.0)
        - headline_book.spot_notional * (0.02 / 365.0)
    )
    expected = core.annualized_return(net, 365)
    assert payload["portfolio_net_ann"] == pytest.approx(expected, abs=1e-12)
    assert payload["portfolio_net_ann"] < payload["portfolio_gross_ann"] - 0.01


def test_cycle944_published_numbers_are_reproduced(payload):
    """The superseded Cycle 944 figures stay verifiable from the same run."""
    published = payload["published_cycle944"]
    assert published["applied_cost_bps_per_unit"] == 0.02
    assert published["headline_net_ann"] == pytest.approx(0.137746, abs=5e-6)
    assert published["per_symbol_mean_oos_sharpe"]["always_on"] == pytest.approx(
        9.209, abs=5e-3
    )
    assert published["per_symbol_mean_oos_sharpe"]["funding_positive_sameday"] == pytest.approx(
        1.762, abs=5e-3
    )
    assert published["per_symbol_mean_oos_sharpe"]["funding_positive_lagged"] == pytest.approx(
        0.977, abs=5e-3
    )


def test_reconciliation_reproduces_the_prior_cycle_record(payload):
    """The prior cycles' published figures are reproduced under their own models."""
    always_on = payload["reconciliation"]["always_on"]
    assert always_on["cycle891_flat_3bp"]["full_ann"] == pytest.approx(0.127694, abs=5e-6)
    assert always_on["cycle891_flat_3bp"]["oos_sharpe"] == pytest.approx(11.144, abs=5e-3)
    assert always_on["cycle892_venue_taker_rf"]["full_ann"] == pytest.approx(0.092190, abs=5e-6)
    assert always_on["cycle892_venue_taker_rf"]["oos_sharpe"] == pytest.approx(1.516, abs=5e-3)
    lagged = payload["reconciliation"]["funding_positive_lagged"]
    assert lagged["cycle891_flat_3bp"]["full_ann"] == pytest.approx(0.105340, abs=5e-6)
    assert lagged["cycle891_flat_3bp"]["oos_sharpe"] == pytest.approx(1.128, abs=5e-3)
    assert lagged["cycle892_venue_taker_rf"]["full_ann"] == pytest.approx(0.019706, abs=5e-6)


def test_promotion_gate_fails_for_every_rule(payload):
    for rule_id, gate in payload["per_symbol_gate_results"].items():
        assert gate["promotion_gate_pass"] is False, rule_id
        assert gate["trade_count_criterion_pass"] is False, rule_id
    assert payload["per_symbol_gate_results"]["always_on"][
        "pooled_oos_position_round_trips"
    ] == 0
    for rule_id in ("funding_positive_sameday", "funding_positive_lagged"):
        assert payload["per_symbol_gate_results"][rule_id][
            "pooled_oos_position_round_trips"
        ] == 95


def test_committed_report_matches_the_generator(payload):
    assert ev.OUT_REPORT.read_text() == ev.render_report(payload)
    assert ev.OUT_EXP.read_text() == ev.render_experiment(payload)
