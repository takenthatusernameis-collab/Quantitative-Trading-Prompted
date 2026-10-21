"""Tests for the pre-registered evaluation of ``riskparity_001`` (Cycle 930).

The tests cover the construction rules that the pre-registration fixes (the
lagged volatility estimate, the per-asset cap, the deterministic weight
path), the end-to-end reproduction of the published evaluation from the
committed cache, and the read-only guarantees.

Run with::

    python -m pytest -q tests/test_riskparity_001_evaluation.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.riskparity_001_eval import (  # noqa: E402
    BASELINE,
    CAPS,
    EVAL_START,
    GATE_POOLED_TRADES_MIN,
    GATE_POSITIVE_FOLD_MIN,
    GATE_WF_MEAN_MIN,
    LOOKBACKS,
    N_CONFIGS,
    OUT_EXP,
    OUT_REPORT,
    TRAIN_END,
    UNIVERSE,
    VAL_END,
    build_weights,
    capped_normalise,
    lagged_volatility,
    run_evaluation,
)

SCRIPT = REPO_ROOT / "research" / "riskparity_001_eval.py"


# ----------------------------------------------------------------------
# The construction rules the pre-registration fixes
# ----------------------------------------------------------------------


def test_capped_normalise_respects_the_cap_and_sums_to_one():
    raw = np.array([10.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    w, iterations, residual = capped_normalise(raw, 0.30)
    assert w.sum() == pytest.approx(1.0, abs=1e-12)
    assert w.max() <= 0.30 + 1e-12
    assert (w >= 0).all()
    assert iterations <= 5
    assert residual == pytest.approx(0.0, abs=1e-12)


def test_capped_normalise_is_deterministic():
    raw = np.array([3.0, 2.0, 1.0, 0.5, 0.2, 0.1, 0.05])
    first, _, _ = capped_normalise(raw, 0.25)
    second, _, _ = capped_normalise(raw, 0.25)
    assert np.array_equal(first, second)


def test_capped_normalise_rejects_degenerate_input():
    with pytest.raises(Exception):
        capped_normalise(np.zeros(3), 0.30)
    with pytest.raises(Exception):
        capped_normalise(np.array([1.0, np.nan, 1.0]), 0.30)


def test_lagged_volatility_has_no_same_session_feedback():
    """The estimate at t must not contain the return of session t."""
    index = pd.bdate_range("2020-01-01", periods=40, tz="UTC")
    base = pd.DataFrame(
        {"A": 100.0 * np.power(1.001, np.arange(40))}, index=index
    )
    vol_base = lagged_volatility(base, 10)

    shocked = base.copy()
    shocked.iloc[30, 0] *= 1.5  # a shock on session 30

    vol_shocked = lagged_volatility(shocked, 10)
    # The estimate at session 30 is unchanged ...
    assert vol_shocked["A"].iloc[30] == pytest.approx(vol_base["A"].iloc[30])
    # ... and the shock only enters one session later.
    assert vol_shocked["A"].iloc[31] != pytest.approx(vol_base["A"].iloc[31])
    # The first valid estimate needs L valid returns, and the shift delays it
    # by one further session (returns 0 is undefined, so the L-session window
    # is complete at index L and the lagged estimate lands at index L+1).
    assert np.isnan(vol_base["A"].iloc[10])
    assert not np.isnan(vol_base["A"].iloc[11])


def test_build_weights_forms_a_long_only_book_summing_to_one():
    index = pd.bdate_range("2015-01-01", periods=400, tz="UTC")
    close = pd.DataFrame(
        {
            "A": 100.0 * np.power(1.0005, np.arange(400)),
            "B": 100.0 * np.power(1.0001, np.arange(400)),
            "C": 100.0 * np.power(1.0002, np.arange(400)),
        },
        index=index,
    )
    weights, meta = build_weights(close, 21, 0.60)
    assert (weights >= -1e-12).all().all()
    row_sums = weights.sum(axis=1)
    invested = row_sums > 0
    assert invested.any()
    assert np.allclose(row_sums[invested], 1.0, atol=1e-9)
    assert weights.max().max() <= 0.60 + 1e-9
    assert meta["n_segments"] >= 10


# ----------------------------------------------------------------------
# The pre-registration is used unchanged
# ----------------------------------------------------------------------


def test_preregistered_constants_are_unchanged():
    assert UNIVERSE == ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
    assert EVAL_START == "2005-11-10"
    assert TRAIN_END == "2015-12-31"
    assert VAL_END == "2020-12-31"
    assert LOOKBACKS == (21, 63, 126)
    assert CAPS == (0.25, 0.30, 0.40)
    assert BASELINE == (63, 0.30)
    assert N_CONFIGS == 9
    assert GATE_WF_MEAN_MIN == 0.9
    assert GATE_POSITIVE_FOLD_MIN == 0.5
    assert GATE_POOLED_TRADES_MIN == 100


# ----------------------------------------------------------------------
# The end-to-end evaluation
# ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def payload():
    return run_evaluation()


def test_evaluation_passes_its_structural_checks(payload):
    assert payload["structural_pass"] is True
    names = {c["name"] for c in payload["checks"]}
    assert {
        "data_unchanged",
        "config_unchanged",
        "committed_artifacts_unchanged",
        "evaluation_window_is_point_in_time_complete",
        "baseline_weight_cap_respected",
        "trial_count_is_preregistered",
    } <= names
    assert all(c["pass"] for c in payload["checks"])


def test_exactly_the_preregistered_grid_is_evaluated(payload):
    assert len(payload["grid"]) == N_CONFIGS
    seen = {(row["lookback"], row["cap"]) for row in payload["grid"]}
    assert seen == {(L, c) for L in LOOKBACKS for c in CAPS}
    assert payload["dsr"]["n_configs"] == N_CONFIGS


def test_the_decision_follows_the_gates(payload):
    base = payload["baseline"]
    expected = (
        base["gates"]["wf_mean_oos_sharpe"]["value"] >= GATE_WF_MEAN_MIN
        and base["gates"]["positive_fold_rate"]["value"] >= GATE_POSITIVE_FOLD_MIN
        and base["gates"]["pooled_oos_trades"]["value"] > GATE_POOLED_TRADES_MIN
    )
    assert base["gates_passed"] is expected
    assert payload["decision"] == ("PROMOTE" if expected else "REJECT")


def test_the_evaluation_window_is_point_in_time_complete(payload):
    assert payload["first_complete_breadth_session"] <= EVAL_START


def test_the_benchmark_is_measured_on_the_same_folds(payload):
    bench = payload["benchmarks"]["one_over_n"]
    assert bench["n_folds"] == payload["n_folds"]
    excess = payload["benchmarks"]["excess_over_1n_wf_mean"]
    assert excess == pytest.approx(
        payload["baseline"]["wf_mean_test_sharpe"] - bench["wf_mean_test_sharpe"],
        abs=1e-12,
    )


def test_the_tool_is_reproducible_and_read_only():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--no-report"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "STRUCTURAL: PASS" in result.stdout
    assert "CHECK|data_unchanged|PASS" in result.stdout
    assert "CHECK|config_unchanged|PASS" in result.stdout
    assert "CHECK|committed_artifacts_unchanged|PASS" in result.stdout
    assert "TRIALS|9" in result.stdout
    assert re.search(r"^DECISION\|(PROMOTE|REJECT)$", result.stdout, re.M)


# ----------------------------------------------------------------------
# The published artefacts agree with the run
# ----------------------------------------------------------------------


def test_report_and_experiment_exist_and_state_the_decision(payload):
    for path in (OUT_REPORT, OUT_EXP):
        assert path.exists(), f"missing artefact: {path}"
        text = path.read_text(encoding="utf-8")
        assert payload["decision"] in text
        assert str(payload["cycle"]) in text


def test_the_report_carries_the_measured_gate_values(payload):
    text = OUT_REPORT.read_text(encoding="utf-8")
    base = payload["baseline"]
    assert f"{base['wf_mean_test_sharpe']:.6f}" in text
    assert str(base["total_test_trades"]) in text
    assert f"{payload['benchmarks']['corr_with_1n']:.6f}" in text
    assert "riskparity_001" in text


def test_the_experiment_record_carries_the_required_fields():
    text = OUT_EXP.read_text(encoding="utf-8")
    for field in (
        "Hypothesis reference",
        "Data used",
        "Point-in-time treatment",
        "Configuration",
        "Results",
        "Number of trials",
        "Reproduction commands",
    ):
        assert field in text, f"the experiment record is missing '{field}'"
