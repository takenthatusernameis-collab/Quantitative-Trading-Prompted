"""Tests for the same-session volatility correction (Cycle 926).

The cycle makes the same-session volatility estimate correctable behind a
**default-off, opt-in** switch and re-derives the incumbent's published record
on the corrected path in a **new** artifact.  These tests pin:

* the default path is **bit-identical** (max |diff| = 0.0) to a frozen copy of
  the pre-change implementation, in all three code paths;
* the switch is opt-in, defaults to off everywhere, and is not set by any
  config file;
* the anchor (published 48-fold walk-forward mean OOS Sharpe 0.947307 and the
  committed 450-session record) is reproduced and the run fails closed on a
  mismatch;
* the re-derivation is reported **side by side** and does not change the
  incumbent's verdict, its promotion decision or any committed artifact;
* `data/` and `config/` stay byte-identical and the published record and the
  committed paper-trading state are never overwritten.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.tsmomentum_same_session_vol_correction import (  # noqa: E402
    ARTEFACT_FOLD,
    COMMITTED_TRAILING_SHARPE,
    GATE_PSR,
    GATE_ROLLING_SHARPE,
    PSR_BLOCK_SIZE,
    PSR_N_BOOTSTRAP,
    PSR_SEED,
    PSR_TARGET,
    PUBLISHED_WF_MEAN,
    build_path,
    legacy_apply_overlay,
    legacy_combined_risk_overlay,
    legacy_target_weights,
    legacy_volatility_target_overlay,
    render_experiment,
    render_report,
    run_correction,
)
from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    fingerprint,
    load_close_from_cache,
)
from src.evaluation.risk import (  # noqa: E402
    combined_risk_overlay,
    realized_vol_scale,
    volatility_target_overlay,
)
from src.simulation.engine import SimulationConfig, _target_weights  # noqa: E402
from src.simulation.paper_trading import PaperTradingConfig  # noqa: E402

TOOL = "research/tsmomentum_same_session_vol_correction.py"
REPORT = REPO / "research" / "reports" / "tsmomentum_same_session_vol_correction_001.md"
EXPERIMENT = REPO / "research" / "experiments" / "tsmomentum_same_session_vol_correction_001.md"
PUBLISHED_RECORD = REPO / "research" / "experiments" / "tsmomentum_regime_filter_wf_001.md"
STATE_PATH = REPO / "data" / "processed" / "paper_trading_state.yaml"
SIM_CONFIG_PATH = REPO / "config" / "simulation_candidate_001.yaml"
PAPER_CONFIG_PATH = REPO / "config" / "paper_trading_config.yaml"

ALLOWED_RECOMMENDATIONS = (
    "adopt_everywhere",
    "adopt_only_for_new_live_paper_trading_records",
    "do_not_adopt",
)


def _run_tool(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, TOOL, *extra],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _committed_artifact_hashes() -> dict[str, str]:
    res = subprocess.run(
        ["git", "ls-files", "src", "config", "research/experiments", "research/reports"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    out: dict[str, str] = {}
    for rel in res.stdout.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        path = REPO / rel
        if path.is_file():
            out[rel] = _sha256(path)
    return out


@pytest.fixture(scope="module")
def close() -> pd.DataFrame:
    from research.run_cycle6 import SYMBOLS

    return load_close_from_cache(list(SYMBOLS), REPO / "data" / "raw")


@pytest.fixture(scope="module")
def payload() -> dict:
    """The full measurement, including the published-machinery anchor."""
    return run_correction()


@pytest.fixture(scope="module")
def cli() -> tuple[subprocess.CompletedProcess, dict[str, object]]:
    """One CLI run (no report) with the committed-artifact hashes around it."""
    before = _committed_artifact_hashes()
    state_before = _sha256(STATE_PATH)
    published_before = _sha256(PUBLISHED_RECORD)
    result = _run_tool("--no-report")
    after = _committed_artifact_hashes()
    return result, {
        "before": before,
        "after": after,
        "state_before": state_before,
        "state_after": _sha256(STATE_PATH),
        "published_before": published_before,
        "published_after": _sha256(PUBLISHED_RECORD),
    }


# ----------------------------------------------------------------------
# Tool contract
# ----------------------------------------------------------------------
def test_tool_runs_and_passes(cli):
    result, _ = cli
    assert result.returncode == 0, result.stderr
    assert "OVERALL: PASS" in result.stdout
    assert "recommendation: adopt_only_for_new_live_paper_trading_records" in result.stdout


def test_tool_output_is_deterministic():
    first = run_correction(published_machinery=False)
    second = run_correction(published_machinery=False)
    assert first["anchor"] == second["anchor"]
    assert first["record"] == second["record"]
    assert first["walk_forward"]["published"] == second["walk_forward"]["published"]
    assert first["walk_forward"]["corrected"] == second["walk_forward"]["corrected"]
    assert render_report(first) == render_report(second)


def test_tool_writes_report_and_experiment():
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert REPORT.is_file() and EXPERIMENT.is_file()
    report = REPORT.read_text(encoding="utf-8")
    assert "Same-session volatility estimate" in report
    assert "Side-by-side re-derivation" in report
    assert "Blast radius" in report
    experiment = EXPERIMENT.read_text(encoding="utf-8")
    assert "Objective" in experiment and "Verdict" in experiment and "Trial count" in experiment


def test_committed_records_are_exactly_what_the_tool_renders(payload):
    assert REPORT.read_text(encoding="utf-8") == render_report(payload)
    assert EXPERIMENT.read_text(encoding="utf-8") == render_experiment(payload)


# ----------------------------------------------------------------------
# The switch itself
# ----------------------------------------------------------------------
def test_switch_defaults_are_off_in_every_entry_point():
    assert SimulationConfig().lag_vol_estimate is False
    assert SimulationConfig.from_yaml(SIM_CONFIG_PATH).lag_vol_estimate is False
    assert PaperTradingConfig.from_paper_config_yaml(PAPER_CONFIG_PATH).lag_vol_estimate is False


def test_no_config_file_sets_the_switch():
    hits = [
        str(p.relative_to(REPO))
        for p in sorted((REPO / "config").rglob("*"))
        if p.is_file() and "_corrected" not in p.name and "lag_vol_estimate" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert hits == []


def test_corrected_config_is_specification_only_exception():
    hits = [
        str(p.relative_to(REPO))
        for p in sorted((REPO / "config").rglob("*"))
        if p.is_file() and "lag_vol_estimate" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert "config/simulation_candidate_001_corrected.yaml" in hits


def test_no_record_feeding_config_sets_the_switch():
    record_feeding = ["config/simulation_candidate_001.yaml", "config/paper_trading_config.yaml"]
    hits = [
        str(p.relative_to(REPO))
        for p in sorted((REPO / "config").rglob("*"))
        if p.is_file() and str(p.relative_to(REPO)) in record_feeding and "lag_vol_estimate" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert hits == []


def test_default_scale_is_the_committed_same_session_estimate():
    rng = np.random.default_rng(11)
    port_ret = pd.Series(rng.normal(0.0, 0.01, size=200))
    legacy = port_ret.rolling(63).std() * np.sqrt(252)
    legacy = legacy.replace(0, np.nan)
    legacy = (0.10 / legacy).clip(upper=1.0).fillna(0.0)
    default = realized_vol_scale(port_ret, 0.10, 63, False)
    assert float(np.max(np.abs(default.to_numpy() - legacy.to_numpy()))) == 0.0


def test_lagged_scale_is_the_default_scale_shifted_one_session():
    rng = np.random.default_rng(12)
    port_ret = pd.Series(rng.normal(0.0, 0.01, size=200))
    default = realized_vol_scale(port_ret, 0.10, 63, False)
    lagged = realized_vol_scale(port_ret, 0.10, 63, True)
    assert float(np.max(np.abs(lagged.to_numpy()[1:] - default.to_numpy()[:-1]))) == 0.0
    assert lagged.iloc[0] == 0.0  # no estimate before the first lagged window


def test_opt_in_changes_the_path(close):
    default = build_path(close, lag_vol_estimate=False)
    corrected = build_path(close, lag_vol_estimate=True)
    assert float(np.max(np.abs(corrected["net_ret"] - default["net_ret"]))) > 0.0
    assert float(np.max(np.abs(corrected["combined_weights"] - default["combined_weights"]))) > 0.0


# ----------------------------------------------------------------------
# Default-path bit-identity (the frozen pre-change implementations)
# ----------------------------------------------------------------------
def test_default_research_path_is_bit_identical(close):
    from research.run_cycle6 import _apply_overlay

    path = build_path(close, lag_vol_estimate=False)
    legacy_weights, legacy_net, _ = legacy_apply_overlay(
        path["daily_ret"], path["base_weights"], exposure_factor=path["exposure"]
    )
    new_weights, new_net, _ = _apply_overlay(
        path["daily_ret"], path["base_weights"], exposure_factor=path["exposure"]
    )
    assert float(np.max(np.abs(legacy_net - new_net))) == 0.0
    assert float(np.max(np.abs(legacy_weights - new_weights))) == 0.0


def test_default_simulation_path_is_bit_identical(close):
    path = build_path(close, lag_vol_estimate=False)
    config = SimulationConfig.from_yaml(SIM_CONFIG_PATH)
    new_targets = _target_weights(path["gated_weights"], path["asset_ret"], config)
    old_targets = legacy_target_weights(path["gated_weights"], path["asset_ret"], config)
    assert float(
        np.max(np.abs(new_targets["combined_weights"] - old_targets["combined_weights"]))
    ) == 0.0
    assert float(np.max(np.abs(new_targets["vol_scale"] - old_targets["vol_scale"]))) == 0.0


def test_default_risk_overlay_helpers_are_bit_identical(close):
    path = build_path(close, lag_vol_estimate=False)
    asset_returns = path["daily_ret"].sum(axis=1)
    new_vol, _ = volatility_target_overlay(asset_returns, path["gated_weights"])
    old_vol, _ = legacy_volatility_target_overlay(asset_returns, path["gated_weights"])
    assert float(np.max(np.abs(new_vol - old_vol))) == 0.0
    new_comb, _ = combined_risk_overlay(asset_returns, path["gated_weights"])
    old_comb, _ = legacy_combined_risk_overlay(asset_returns, path["gated_weights"])
    assert float(np.max(np.abs(new_comb - old_comb))) == 0.0


# ----------------------------------------------------------------------
# The anchor
# ----------------------------------------------------------------------
def test_anchor_reproduces_the_published_walk_forward(payload):
    anchor = payload["anchor"]
    assert anchor["reproduced_wf_mean"] == PUBLISHED_WF_MEAN
    assert anchor["n_folds"] == 48
    assert anchor["machinery_wf_mean"] == PUBLISHED_WF_MEAN


def test_anchor_reproduces_the_committed_record(payload):
    anchor = payload["anchor"]
    assert anchor["committed_sessions"] == 450
    assert anchor["record_max_abs_diff"] <= 1e-12


def test_all_internal_checks_pass(payload):
    failed = [c["name"] for c in payload["checks"] if not c["pass"]]
    assert failed == []
    assert payload["overall"] == "PASS"


# ----------------------------------------------------------------------
# The re-derivation
# ----------------------------------------------------------------------
def test_corrected_path_is_worse_on_every_record_statistic(payload):
    rec = payload["record"]
    assert rec["corrected"]["canonical_sharpe"] < rec["published"]["canonical_sharpe"]
    assert rec["corrected"]["trailing_63d_sharpe"] < rec["published"]["trailing_63d_sharpe"]
    assert rec["corrected"]["psr_normal"] < rec["published"]["psr_normal"]


def test_corrected_path_does_not_rescue_the_decision(payload):
    rec = payload["record"]
    assert rec["published"]["trailing_63d_sharpe"] == pytest.approx(
        COMMITTED_TRAILING_SHARPE, abs=1e-12
    )
    assert rec["corrected"]["rolling_gate_passes"] is False
    assert rec["corrected"]["psr_gate_passes"] is False
    assert rec["production_gates_published"]["decision"] == "NO-GO"
    assert rec["production_gates_corrected"]["decision"] == "NO-GO"
    assert rec["production_gates_corrected"]["failed_gates"] == [
        "rolling_63d_sharpe",
        "psr",
    ]


def test_the_higher_corrected_walk_forward_mean_is_an_artefact(payload):
    wf = payload["walk_forward"]
    assert wf["published"]["worst_fold_test_sharpe"] < -1.0
    assert wf["corrected"]["worst_fold_test_sharpe"] > -1.0
    # on the comparable statistic (each path excluding its own worst fold) the
    # corrected path is LOWER: the higher all-fold mean is the artefact
    # disappearing, not a better strategy
    assert (
        wf["corrected"]["mean_test_sharpe_excl_worst_fold"]
        < wf["published"]["mean_test_sharpe_excl_worst_fold"]
    )
    assert wf["published"]["artefact_fold"] == ARTEFACT_FOLD


def test_psr_uses_the_repository_settings(payload):
    settings = payload["record"]["psr_settings"]
    assert settings["target"] == PSR_TARGET == 1.4178
    assert settings["n_bootstrap"] == PSR_N_BOOTSTRAP == 1000
    assert settings["block_size"] == PSR_BLOCK_SIZE == 22
    assert settings["seed"] == PSR_SEED == 20240101
    assert payload["record"]["gate_threshold_rolling"] == GATE_ROLLING_SHARPE
    assert payload["record"]["gate_threshold_psr"] == GATE_PSR


def test_the_published_test_period_baseline_is_reproduced(payload):
    test_period = payload["record"]["test_period_2018_2026"]
    assert test_period["published"]["sharpe_ratio"] == pytest.approx(1.4178, abs=1e-3)
    assert int(test_period["published"]["trade_count"]) == 1196
    assert test_period["published"]["max_drawdown"] == pytest.approx(-0.0779, abs=1e-3)
    # the corrected path's own backtest reference is BELOW the fixed 1.4178, so
    # comparing a corrected live record against the unchanged reference stays
    # conservative
    assert test_period["corrected"]["sharpe_ratio"] < test_period["published"]["sharpe_ratio"]
    assert test_period["corrected"]["sharpe_ratio"] < PSR_TARGET


# ----------------------------------------------------------------------
# Blast radius and decision
# ----------------------------------------------------------------------
def test_blast_radius_inventory_is_measured(payload):
    code_paths = {entry["path"] for entry in payload["blast_radius"]["code_paths"]}
    assert "src/simulation/engine.py::_target_weights" in code_paths
    assert "src/evaluation/risk.py::combined_risk_overlay" in code_paths
    assert "research/run_cycle6.py::_apply_overlay" in code_paths
    artefacts = payload["blast_radius"]["committed_artifacts"]
    assert len(artefacts) == 4
    for item in artefacts:
        assert item["n_files"] > 0, item["marker"]
    assert any(
        "tsmomentum_regime_filter_wf_001.md" in rel
        for item in artefacts
        for rel in item["files"]
    )


def test_decision_recommendation_is_one_of_the_three_allowed_forms(payload):
    decision = payload["decision"]
    assert decision["recommendation"] in ALLOWED_RECOMMENDATIONS
    assert decision["reason"].strip()
    assert decision["re_derivation_plan"]


def test_the_incumbent_verdict_is_unchanged(payload):
    assert payload["incumbent_verdict"].startswith("Credible Candidate")
    assert "NO-GO" in payload["incumbent_verdict"]


# ----------------------------------------------------------------------
# Read-only guarantees
# ----------------------------------------------------------------------
def test_data_and_config_are_unchanged(payload):
    assert payload["read_only"]["data_unchanged"]
    assert payload["read_only"]["config_unchanged"]
    res = subprocess.run(
        ["git", "status", "--porcelain", "data/", "config/"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert res.stdout.strip() == ""


def test_the_published_record_and_the_state_are_not_overwritten(cli, payload):
    _, hashes = cli
    assert payload["read_only"]["committed_artifacts_unchanged"]
    changed = [k for k in hashes["before"] if hashes["before"][k] != hashes["after"].get(k)]
    assert changed == []
    assert hashes["state_before"] == hashes["state_after"]
    assert hashes["published_before"] == hashes["published_after"]


def test_the_fingerprints_of_data_and_config_do_not_move():
    before = fingerprint(REPO / "data")
    config_before = fingerprint(REPO / "config")
    run_correction(published_machinery=False)
    assert fingerprint(REPO / "data") == before
    assert fingerprint(REPO / "config") == config_before
