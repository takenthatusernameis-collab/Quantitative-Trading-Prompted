"""Regression tests for the read-only go/no-go evaluation tool.

Invariants covered:

* the tool runs standalone from the repository root (no ``PYTHONPATH`` help),
* running it never mutates the committed state or the raw cache,
* repeated evaluations of the same record reproduce the same PSR numbers,
  because the Probabilistic Sharpe Ratio bootstrap is seeded,
* the promotion-gate table in ``config/promotion_gates.yaml`` still carries the
  thresholds documented in the validation artifacts, and
* the code-level decision is gate-complete: a failing gate can never produce
  "GO", including when the PSR itself clears the GO threshold, and
* one Sharpe convention is used by the promotion gates, the drift flag and
  both sides of the PSR (Cycle 861).
"""

import hashlib
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluation import statistics as statistics_module  # noqa: E402
from src.evaluation.drift import sharpe_persistence  # noqa: E402
from src.evaluation.sharpe import (  # noqa: E402
    SHARPE_CONVENTION_FORMULA,
    SHARPE_CONVENTION_ID,
    backtest_sharpe_ratio,
    sharpe_ratio,
)
from src.evaluation.statistics import compute_psr  # noqa: E402
from src.simulation import evaluation as evaluation_module  # noqa: E402
from src.simulation.evaluation import (  # noqa: E402
    DEFAULT_PSR_SEED,
    GateEvaluation,
    GoNoGoConfig,
    classify_psr,
    evaluate_go_no_go,
    evaluate_promotion_gates,
    map_decision,
)
from src.simulation.paper_trading import (  # noqa: E402
    PaperTradingConfig,
    PaperTradingState,
)

SCRIPT = "research/go_no_go_evaluation.py"
STATE = ROOT / "data" / "processed" / "paper_trading_state.yaml"
RAW_DIR = ROOT / "data" / "raw"
GATES_YAML = ROOT / "config" / "promotion_gates.yaml"

# Thresholds documented in research/reports/paper_trading_validation_002.md
# (Go/No-Go Assessment) and research/reports/go_no_go_evaluation_002.md
# (PSR grey-zone boundaries). They are inputs: a change here is a change of the
# promotion policy and must be deliberate, not incidental.
DOCUMENTED_GATE_THRESHOLDS = {
    "track_record_length": 126.0,
    "full_period_sharpe": 0.9,
    "rolling_63d_sharpe": 0.9,
    "max_drawdown": -0.15,
    "rolling_63d_max_dd": -0.15,
    "regime_flips": 1.0,
    "psr": 0.95,
}
DOCUMENTED_PSR_GREY_ZONE = {"lower": 0.5, "upper": 0.95}


def _hashes() -> dict[str, str]:
    paths = [STATE, ROOT / "data" / "processed" / "paper_trading_state.yaml.backup"]
    paths += sorted(RAW_DIR.rglob("*.parquet"))
    out = {}
    for path in paths:
        out[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _run_script() -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run(
        [sys.executable, SCRIPT],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def test_script_runs_standalone_without_pythonpath():
    proc = _run_script()
    assert proc.returncode == 0, proc.stderr
    assert "side_effect_free: True" in proc.stdout
    assert "evaluation_deterministic: True" in proc.stdout
    assert "decision (evaluate_go_no_go):" in proc.stdout


def test_script_is_side_effect_free():
    before = _hashes()
    proc = _run_script()
    assert proc.returncode == 0, proc.stderr
    after = _hashes()
    assert before == after


def test_psr_is_deterministic_for_the_committed_state():
    state = PaperTradingState.from_yaml(STATE)
    config = PaperTradingConfig.from_paper_config_yaml(
        ROOT / "config" / "paper_trading_config.yaml"
    )
    go_no_go_config = GoNoGoConfig(
        min_days=config.go_no_go_min_days,
        target_sharpe=config.go_no_go_target_sharpe,
        max_dd_threshold=config.go_no_go_max_dd_threshold,
    )
    first = evaluate_go_no_go(state, config, go_no_go_config=go_no_go_config)
    second = evaluate_go_no_go(state, config, go_no_go_config=go_no_go_config)
    assert first.psr_normal == second.psr_normal
    assert first.psr_empirical == second.psr_empirical
    assert first.sharpe_se == second.sharpe_se
    assert first.sharpe_ci_lower == second.sharpe_ci_lower
    assert first.sharpe_ci_upper == second.sharpe_ci_upper
    assert first.decision == second.decision
    assert first.decision in {"GO", "NO-GO", "INCONCLUSIVE"}


def test_psr_seed_is_fixed_by_default():
    assert GoNoGoConfig().psr_seed == DEFAULT_PSR_SEED
    assert isinstance(DEFAULT_PSR_SEED, int)


# ----------------------------------------------------------------------
# Cycle 860: the promotion decision is gate-complete and conservative
# ----------------------------------------------------------------------


def _gates_doc() -> dict:
    with open(GATES_YAML, "r") as fh:
        return yaml.safe_load(fh)


def _paper_config() -> PaperTradingConfig:
    return PaperTradingConfig.from_paper_config_yaml(
        ROOT / "config" / "paper_trading_config.yaml"
    )


def _go_no_go_config(config: PaperTradingConfig) -> GoNoGoConfig:
    return GoNoGoConfig(
        min_days=config.go_no_go_min_days,
        target_sharpe=config.go_no_go_target_sharpe,
        max_dd_threshold=config.go_no_go_max_dd_threshold,
    )


def _synthetic_state(returns, regime_exposure=None) -> PaperTradingState:
    """Build a deterministic paper-trading state from a return series."""
    n = len(returns)
    start = date(2024, 1, 2)
    dates = [(start + timedelta(days=i)).isoformat() for i in range(n)]
    if regime_exposure is None:
        regime_exposure = [1.0] * (n // 2) + [0.0] * (n - n // 2)
    nav = 100000.0
    peak = nav
    run_history = []
    for i, (ret, exposure) in enumerate(zip(returns, regime_exposure)):
        nav *= 1.0 + float(ret)
        peak = max(peak, nav)
        run_history.append(
            {
                "date": dates[i],
                "net_return": float(ret),
                "turnover": 0.01,
                "vol_scale": 1.0,
                "dd_scale": 1.0,
                "regime_exposure": exposure,
                "nav": nav,
            }
        )
    return PaperTradingState(
        last_run_date=dates[-1],
        current_positions={},
        cumulative_returns=[float(r) for r in returns],
        cumulative_pnl=[],
        cumulative_dates=dates,
        peak_nav=peak,
        current_nav=nav,
        max_drawdown=nav / peak - 1.0,
        drift_flags={},
        run_history=run_history,
        previous_regime_exposure=regime_exposure[-1],
    )


def test_promotion_gate_table_matches_documented_gates():
    """AC1: the gate definition is the single source of truth and still carries
    the thresholds documented in the validation artifacts."""
    doc = _gates_doc()
    gates = {g["name"]: g for g in doc["gates"]}
    assert set(gates) == set(DOCUMENTED_GATE_THRESHOLDS)
    for name, threshold in DOCUMENTED_GATE_THRESHOLDS.items():
        gate = gates[name]
        assert float(gate["threshold"]) == threshold, name
        assert gate["comparison"] == "gte", name
        assert gate["source"], name
        assert gate["metric"], name
        assert gate.get("metric_definition"), name
    grey = doc["psr_grey_zone"]
    assert float(grey["lower"]) == DOCUMENTED_PSR_GREY_ZONE["lower"]
    assert float(grey["upper"]) == DOCUMENTED_PSR_GREY_ZONE["upper"]
    assert set(doc["decision_mapping"]) == {
        "insufficient_track_record",
        "all_gates_pass",
        "psr_grey_zone_and_only_psr_gate_fails",
        "any_other_gate_fails",
    }


def test_gate_evaluation_fails_closed_on_unknown_metric():
    """A typo in the gate table must not silently default the metric to 0."""
    doc = _gates_doc()
    gate_defs = [dict(g) for g in doc["gates"]]
    gate_defs[0] = {**gate_defs[0], "metric": "paper_days_typo"}
    try:
        evaluate_promotion_gates({"paper_days": 449}, gate_defs)
    except ValueError as exc:
        assert "unknown metric" in str(exc)
    else:
        raise AssertionError("unknown gate metric must raise ValueError")


def test_psr_above_go_threshold_with_failing_rolling_sharpe_cannot_yield_go():
    """AC4: a record whose PSR clears the GO threshold but whose rolling 63d
    Sharpe is below 0.9 must never be promoted.

    The synthetic series was re-specified in Cycle 861: the PSR now compares
    two numbers on the same (canonical) scale, so the previous series no
    longer cleared the PSR GO threshold and the premise of the test would
    have been void. The series keeps a strong first half and a weak trailing
    63-day window, so the rolling gate fails while the PSR gate passes.
    """
    rng = np.random.default_rng(20240101)
    n = 200
    early = 0.003 + rng.normal(0.0, 0.002, size=n - 63)
    trailing = np.array([0.005 if i % 2 == 0 else -0.005 for i in range(63)])
    returns = np.concatenate([early, trailing])

    config = _paper_config()
    result = evaluate_go_no_go(
        _synthetic_state(returns), config, go_no_go_config=_go_no_go_config(config)
    )

    gates = {g.name: g for g in result.gates}
    assert result.psr_normal > 0.95, "synthetic state must clear the PSR GO threshold"
    assert gates["psr"].passed is True
    assert gates["rolling_63d_sharpe"].value < 0.9
    assert gates["rolling_63d_sharpe"].passed is False
    # every other gate passes, so the decision is driven purely by the
    # rolling-Sharpe failure
    for name, gate in gates.items():
        if name != "rolling_63d_sharpe":
            assert gate.passed is True, name
    assert result.decision != "GO"
    assert result.decision == "NO-GO"
    assert "rolling_63d_sharpe" in result.failed_gates


def test_synthetic_state_passing_every_gate_yields_go():
    """AC4: the enforcement is not vacuous - a record that passes every gate
    is promoted."""
    rng = np.random.default_rng(7)
    returns = rng.normal(0.002, 0.003, size=250)

    config = _paper_config()
    result = evaluate_go_no_go(
        _synthetic_state(returns), config, go_no_go_config=_go_no_go_config(config)
    )

    assert all(g.passed for g in result.gates), [
        (g.name, g.value, g.threshold) for g in result.gates
    ]
    assert result.failed_gates == []
    assert result.decision == "GO"
    assert result.psr_zone == "above_go"


def test_decision_never_go_when_any_single_gate_fails():
    """AC2/AC3: for every gate in the table, failing that gate alone must
    never produce "GO"."""
    doc = _gates_doc()
    mapping = doc["decision_mapping"]
    grey_zone = doc["psr_grey_zone"]

    config = _paper_config()
    result = evaluate_go_no_go(
        PaperTradingState.from_yaml(STATE), config, go_no_go_config=_go_no_go_config(config)
    )
    assert result.gates, "the committed record must expose its gate table"

    for gate in result.gates:
        failing = [
            g if g.name != gate.name else GateEvaluation(**{**g.__dict__, "passed": False})
            for g in result.gates
        ]
        decision, rationale, _conditions = map_decision(
            failing, result.psr_normal, grey_zone, mapping
        )
        assert decision != "GO", f"failing '{gate.name}' must not yield GO"
        assert rationale

    # every gate passing yields GO
    all_passing = [GateEvaluation(**{**g.__dict__, "passed": True}) for g in result.gates]
    decision, _rationale, _conditions = map_decision(
        all_passing, 0.99, grey_zone, mapping
    )
    assert decision == "GO"


def test_insufficient_track_record_is_inconclusive_not_go():
    doc = _gates_doc()
    mapping = doc["decision_mapping"]
    grey_zone = doc["psr_grey_zone"]
    gate_defs = doc["gates"]
    metric_values = {
        "paper_days": 100.0,
        "paper_sharpe": 2.0,
        "rolling_sharpe_63d": 1.5,
        "paper_max_dd": -0.02,
        "rolling_max_dd_63d": -0.02,
        "regime_flips": 3.0,
        "psr_normal": 0.99,
    }
    gates = evaluate_promotion_gates(metric_values, gate_defs)
    decision, _rationale, _conditions = map_decision(
        gates, metric_values["psr_normal"], grey_zone, mapping
    )
    assert decision == "INCONCLUSIVE"


def test_only_psr_gate_failing_in_grey_zone_is_inconclusive_not_go():
    doc = _gates_doc()
    mapping = doc["decision_mapping"]
    grey_zone = doc["psr_grey_zone"]
    metric_values = {
        "paper_days": 449.0,
        "paper_sharpe": 1.64,
        "rolling_sharpe_63d": 1.20,
        "paper_max_dd": -0.05,
        "rolling_max_dd_63d": -0.04,
        "regime_flips": 6.0,
        "psr_normal": 0.70,
    }
    gates = evaluate_promotion_gates(metric_values, doc["gates"])
    assert [g.name for g in gates if not g.passed] == ["psr"]
    decision, _rationale, _conditions = map_decision(
        gates, metric_values["psr_normal"], grey_zone, mapping
    )
    assert decision == "INCONCLUSIVE"
    assert classify_psr(0.70, grey_zone) == "grey_zone"
    assert classify_psr(0.95, grey_zone) == "above_go"
    assert classify_psr(0.10, grey_zone) == "below_no_go"


def test_committed_record_is_not_promoted():
    """Regression guard for the false-promotion path: the committed record
    must not be labelled GO."""
    config = _paper_config()
    result = evaluate_go_no_go(
        PaperTradingState.from_yaml(STATE), config, go_no_go_config=_go_no_go_config(config)
    )
    assert result.decision != "GO"
    assert result.failed_gates
    assert result.gates


# ----------------------------------------------------------------------
# Cycle 861: one documented Sharpe convention
# ----------------------------------------------------------------------

# The rolling 63d Sharpe series for the last five sessions of the committed
# record (454 sessions, last_run_date 2026-10-23). Re-derived from
# src.evaluation.drift.sharpe_persistence on the committed state; the values
# quoted here are the ones the monitoring artifacts and the drift flag report
# (research/drift_persistence_report.py) must keep reproducing. The prior
# set ended at 2026-10-16/-0.2119 and was stale after the state advanced.
ARTIFACT_ROLLING_SERIES_TAIL = {
    "2026-10-19": -0.4489,
    "2026-10-20": -0.2483,
    "2026-10-21": 0.2184,
    "2026-10-22": -0.1429,
    "2026-10-23": -0.2549,
}


def _truncated_state(n_sessions: int) -> PaperTradingState:
    """The committed state truncated to its first *n_sessions* sessions."""
    state = PaperTradingState.from_yaml(STATE)
    state.cumulative_returns = list(state.cumulative_returns)[:n_sessions]
    state.cumulative_dates = list(state.cumulative_dates)[:n_sessions]
    state.cumulative_pnl = list(state.cumulative_pnl)[:n_sessions]
    state.run_history = list(state.run_history)[:n_sessions]
    return state


def test_documented_convention_matches_the_implementation():
    """AC1: the gate table declares the convention the code implements."""
    doc = _gates_doc()
    convention = doc["sharpe_convention"]
    assert convention["id"] == SHARPE_CONVENTION_ID
    assert convention["formula"] == SHARPE_CONVENTION_FORMULA
    assert float(convention["rf_annual"]) == 0.0
    assert int(convention["periods_per_year"]) == 252
    assert convention["implementation"] == "src.evaluation.sharpe.sharpe_ratio"
    # the backtest-baseline scale stays named and confined
    backtest_scale = convention["backtest_baseline_scale"]
    assert backtest_scale["id"] == "cagr_annualized_rf2"
    assert backtest_scale["implementation"] == "src.evaluation.sharpe.backtest_sharpe_ratio"


def test_gate_rolling_sharpe_equals_the_stored_drift_flag_value():
    """AC2: the promotion gate and the stored drift flag are the same
    measurement, so they must report the same number."""
    state = PaperTradingState.from_yaml(STATE)
    config = _paper_config()
    result = evaluate_go_no_go(
        state, config, go_no_go_config=_go_no_go_config(config)
    )
    gate = next(g for g in result.gates if g.name == "rolling_63d_sharpe")
    stored = float(state.drift_flags["low_rolling_sharpe"]["value"])
    assert gate.value == pytest.approx(stored, abs=1e-12)
    # Re-derived from the committed state at last_run_date 2026-10-23
    # (454 sessions); the previously hardcoded value -0.1429350026091491
    # was the rolling 63d Sharpe at 2026-10-22, stale after the state was
    # extended to 2026-10-23. The gate and the stored drift flag agree.
    assert gate.value == pytest.approx(-0.25492616117205563, abs=1e-12)
    # the gate value is on the canonical scale, not on the backtest scale
    assert gate.value != pytest.approx(
        backtest_sharpe_ratio(list(state.cumulative_returns)[-63:]), abs=1e-6
    )


def test_rolling_sharpe_series_reproduces_the_validation_artifact_values():
    """AC2: the gate's rolling Sharpe series reproduces the values quoted in
    the validation artifacts."""
    state = PaperTradingState.from_yaml(STATE)
    persistence = sharpe_persistence(
        state.cumulative_dates, state.cumulative_returns
    )
    tail = {
        date: round(value, 4)
        for date, value in persistence["series"][-5:]
        if value is not None
    }
    assert tail == ARTIFACT_ROLLING_SERIES_TAIL


def test_psr_numerator_uses_the_canonical_estimator():
    """AC3: the PSR numerator is the canonical Sharpe of the series."""
    returns = pd.Series(
        [0.004, -0.002, 0.006, 0.001, -0.003, 0.005, -0.001, 0.002, 0.003, -0.004]
    )
    psr = compute_psr(returns, sr_target=1.4178, n_bootstrap=50, block_size=3, seed=3)
    assert psr["sharpe_observed"] == pytest.approx(sharpe_ratio(returns), abs=1e-12)
    # the canonical scale and the backtest-baseline scale are different
    # measurements; the numerator must not silently use the latter
    assert psr["sharpe_observed"] != pytest.approx(
        backtest_sharpe_ratio(returns), abs=1e-3
    )


def test_psr_bootstrap_uses_the_canonical_estimator(monkeypatch):
    """AC3: every bootstrap resample is scored with the same estimator as
    the PSR numerator."""
    sample = np.array([0.004, -0.003, 0.006, -0.001, 0.002, 0.005, -0.004, 0.001])

    class _FixedResample:
        """Stand-in for MovingBlockBootstrap that yields one known resample."""

        def __init__(self, block_length, x, seed=None):
            self._x = x

        def bootstrap(self, n_samples):
            yield ((np.array(sample),), None)

    monkeypatch.setattr(
        statistics_module, "MovingBlockBootstrap", _FixedResample
    )
    values = statistics_module.block_bootstrap_sharpe(
        pd.Series(sample), n_samples=1, block_size=2, seed=11
    )
    assert list(values) == [pytest.approx(sharpe_ratio(sample), abs=1e-12)]


def test_evaluation_fails_closed_when_the_declared_convention_differs(
    tmp_path, monkeypatch
):
    """AC1: a gate table that declares a different convention must not be
    evaluated silently."""
    doc = _gates_doc()
    doc["sharpe_convention"]["id"] = "cagr_annualized_rf2"
    path = tmp_path / "promotion_gates.yaml"
    with open(path, "w") as fh:
        yaml.safe_dump(doc, fh)
    monkeypatch.setattr(evaluation_module, "_PROMOTION_GATES_PATH", path)

    config = _paper_config()
    with pytest.raises(ValueError, match="Sharpe convention"):
        evaluate_go_no_go(
            PaperTradingState.from_yaml(STATE),
            config,
            go_no_go_config=_go_no_go_config(config),
        )


def test_444_session_record_verdict_under_the_canonical_convention():
    """AC4: the convention change flips the 444-session rolling gate from
    FAIL (0.670178) to PASS (0.935578); the record then fails only the PSR
    gate, in the grey zone, so the decision is INCONCLUSIVE - never GO."""
    config = _paper_config()
    result = evaluate_go_no_go(
        _truncated_state(444), config, go_no_go_config=_go_no_go_config(config)
    )
    gates = {g.name: g for g in result.gates}
    assert gates["rolling_63d_sharpe"].value == pytest.approx(0.935578, abs=1e-6)
    assert gates["rolling_63d_sharpe"].passed is True
    assert result.failed_gates == ["psr"]
    assert result.psr_zone == "grey_zone"
    assert result.decision == "INCONCLUSIVE"
    assert result.decision != "GO"
