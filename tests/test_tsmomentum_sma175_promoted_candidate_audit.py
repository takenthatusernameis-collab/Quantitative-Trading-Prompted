"""Tests for the SMA-175 promoted candidate (Cycle 917, hardened Cycle 918).

Cycle 917 promoted the SMA-175 variant of ``tsmomentum_spytrend_001`` as a
*separate tracked candidate* (``tsmomentum_sma175_promoted_001``) while leaving
the incumbent baseline (SPY SMA window 200 in ``research/run_cycle6.py``)
unchanged. The original audit test asserted only that the two doc files exist,
so a later edit that (a) dropped the "NOT the incumbent baseline" disclaimer,
(b) flipped the incumbent to SMA-175, or (c) silently upgraded the candidate to
"promotable" would have left the suite green. These tests pin the safety
invariants that make the Cycle-915 "NOT PROMOTED" decision durable.

The critical property is the *separation* between "tracked candidate" and
"incumbent baseline": promoting SMA-175 into ``run_cycle6.py`` would break the
committed-artifact / anchor-reproduction guarantees of the incumbent-phase-
stability audits (see ``research/reports/tsmomentum_sma175_decision_001.md``),
so the incumbent must stay at SMA-200 and the candidate must remain non-
promotable until a future cycle regenerates those anchors.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXP = REPO / "research" / "experiments" / "tsmomentum_sma175_promoted_candidate_001.md"
REPORT = REPO / "research" / "reports" / "tsmomentum_sma175_promoted_candidate_001.md"
DECISION = REPO / "research" / "reports" / "tsmomentum_sma175_decision_001.md"
PROMOTION_EVAL = (
    REPO / "research" / "experiments" / "tsmomentum_sma175_promotion_gate_eval_001.md"
)
RUN_CYCLE6 = REPO / "research" / "run_cycle6.py"


def test_promoted_candidate_files_exist():
    assert EXP.exists()
    assert REPORT.exists()


def test_candidate_is_not_the_incumbent_baseline():
    """The promoted candidate must be documented as a separate track.

    Dropping this disclaimer would let a reader mistake the candidate for the
    production baseline, which the Cycle-915 decision explicitly forbids.
    """
    report = REPORT.read_text()
    assert "NOT the incumbent baseline" in report
    assert "Incumbent (SMA-200) baseline in run_cycle6.py unchanged" in report

    experiment = EXP.read_text()
    assert "NOT incumbent baseline" in experiment
    assert "Incumbent baseline unchanged" in experiment


def test_incumbent_baseline_stays_sma_200():
    """``run_cycle6.py`` must keep SPY_SMA_WINDOW = 200 (the incumbent).

    The SMA-175 variant lives only in the separate candidate track. If this
    ever flips to 175 the incumbent baseline has been promoted without the
    committed-artifact regeneration plan the decision record requires, and the
    anchor-reproduction guarantees break.
    """
    source = RUN_CYCLE6.read_text()
    match = re.search(r"^SPY_SMA_WINDOW\s*=\s*(\d+)", source, re.MULTILINE)
    assert match is not None, "SPY_SMA_WINDOW assignment not found in run_cycle6.py"
    assert int(match.group(1)) == 200


def test_candidate_is_not_promotable():
    """The candidate must remain non-promotable until a future cycle.

    Cycle 920's promotion-gate eval found the SMA-175 candidate fails the
    ``rolling_63d_sharpe`` and ``psr`` gates (candidate_promotable = False,
    Decision = NO-GO). The decision record and the eval experiment must both
    keep saying so; a silent upgrade to "promotable" would contradict the gate
    evaluation.
    """
    decision = DECISION.read_text()
    assert "NOT PROMOTED" in decision

    experiment = PROMOTION_EVAL.read_text()
    assert "candidate_promotable (every promotion gate passes): False" in experiment
    assert "Decision: NO-GO" in experiment
    assert "rolling_63d_sharpe" in experiment
    assert "psr" in experiment


def test_promoted_candidate_records_phase_stability():
    """The candidate's phase-stability evidence must remain recorded.

    Phase A (odd folds) and Phase B (even folds) both pass gate-1, which is the
    property that distinguishes SMA-175 from the phase-unstable SMA-200
    incumbent. Pinning the headline numbers guards against a doc regression
    that would erase the justification for tracking the candidate at all.
    """
    report = REPORT.read_text()
    assert "1.539964" in report  # WF mean OOS Sharpe
    assert "1.539145" in report  # phase A mean
    assert "1.540784" in report  # phase B mean
    assert "NOT the incumbent baseline" in report