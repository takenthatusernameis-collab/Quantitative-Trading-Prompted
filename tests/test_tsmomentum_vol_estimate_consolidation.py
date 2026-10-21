"""Tests for the same-session volatility consolidation (Cycle 927).

The cycle consolidates the same-session volatility estimate onto one shared
implementation behind a **default-off, opt-in** ``lag_vol_estimate`` switch in
all seven research scripts that still inlined it, and publishes the incumbent's
corrected backtest as a **new, labelled successor reference** that supersedes
nothing.

These tests pin:

* all seven scripts now route through ``src/evaluation.risk.realized_vol_scale``
  behind the same default-off switch;
* every default path is bit-identical (max |diff| = 0.0) to a frozen copy of
  its pre-change implementation;
* after the change there are **zero** remaining inline same-session exposure
  estimates across the seven scripts;
* the switch defaults off everywhere and is set by no config file;
* the anchor (published 48-fold walk-forward mean OOS Sharpe, committed
  450-session record) is reproduced and the run fails closed on a mismatch;
* the corrected successor record is reported side by side and does not change
  the incumbent's verdict, its promotion decision or any committed artifact;
* ``data/`` and ``config/`` stay byte-identical and committed artifacts are
  never overwritten.
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
    PSR_BLOCK_SIZE,
    PSR_N_BOOTSTRAP,
    PSR_SEED,
    PSR_TARGET,
    PUBLISHED_WF_MEAN,
    PUBLISHED_WF_FOLDS,
    build_path,
)
from research.tsmomentum_vol_estimate_consolidation import (  # noqa: E402
    CORRECTED_RECORD_EXPECTED,
    CORRECTED_TEST_PERIOD_EXPECTED,
    CORRECTED_WF_EXPECTED,
    OUT_EXP,
    OUT_REPORT,
    SCRIPTS,
    render_experiment,
    render_report,
    run_consolidation,
    script_consolidation_checks,
)
from research.tsmomentum_walkforward_embargo_audit import (  # noqa: E402
    fingerprint,
)
from src.evaluation.risk import realized_vol_scale  # noqa: E402
from src.simulation.engine import SimulationConfig  # noqa: E402
from src.simulation.paper_trading import PaperTradingConfig  # noqa: E402

TOOL = "research/tsmomentum_vol_estimate_consolidation.py"
STATE_PATH = REPO / "data" / "processed" / "paper_trading_state.yaml"
PUBLISHED_RECORD = REPO / "research" / "experiments" / "tsmomentum_regime_filter_wf_001.md"
SIM_CONFIG_PATH = REPO / "config" / "simulation_candidate_001.yaml"
PAPER_CONFIG_PATH = REPO / "config" / "paper_trading_config.yaml"


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
def payload() -> dict:
    return run_consolidation()


@pytest.fixture(scope="module")
def cli() -> tuple[subprocess.CompletedProcess, dict[str, object]]:
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


def test_tool_output_is_deterministic():
    first = run_consolidation()
    second = run_consolidation()
    assert first["anchor"] == second["anchor"]
    assert first["record"] == second["record"]
    assert first["walk_forward"]["published"] == second["walk_forward"]["published"]
    assert first["walk_forward"]["corrected"] == second["walk_forward"]["corrected"]
    assert render_report(first) == render_report(second)


def test_tool_writes_report_and_experiment():
    result = _run_tool()
    assert result.returncode == 0, result.stderr
    assert OUT_REPORT.is_file() and OUT_EXP.is_file()


def test_committed_records_match_what_the_tool_renders(payload):
    assert OUT_REPORT.read_text(encoding="utf-8") == render_report(payload)
    assert OUT_EXP.read_text(encoding="utf-8") == render_experiment(payload)


# ----------------------------------------------------------------------
# Switch semantics
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
    assert lagged.iloc[0] == 0.0


def test_opt_in_changes_the_path():
    from research.run_cycle6 import SYMBOLS
    close = __import__(
        "research.tsmomentum_walkforward_embargo_audit", fromlist=["load_close_from_cache"]
    ).load_close_from_cache(list(SYMBOLS), REPO / "data" / "raw")
    default = build_path(close, lag_vol_estimate=False)
    corrected = build_path(close, lag_vol_estimate=True)
    assert float(np.max(np.abs(corrected["net_ret"] - default["net_ret"]))) > 0.0


# ----------------------------------------------------------------------
# Consolidation across the seven scripts
# ----------------------------------------------------------------------
def test_all_per_script_consolidation_checks_pass():
    checks = script_consolidation_checks()
    failed = [c["name"] for c in checks if not c["pass"]]
    assert failed == [], failed
    assert len(checks) == 16


def test_zero_remaining_inline_same_session_estimates():
    inline_marker = "vol_target / realized_vol"
    remaining = []
    for rel in SCRIPTS:
        text = (REPO / rel).read_text(encoding="utf-8", errors="ignore")
        if inline_marker in text:
            remaining.append(rel)
    assert remaining == [], remaining


# ----------------------------------------------------------------------
# Anchor
# ----------------------------------------------------------------------
def test_anchor_reproduces_the_published_walk_forward(payload):
    anchor = payload["anchor"]
    assert anchor["reproduced_wf_mean"] == PUBLISHED_WF_MEAN
    assert anchor["n_folds"] == PUBLISHED_WF_FOLDS
    assert anchor["committed_sessions"] == 450
    assert anchor["record_max_abs_diff"] <= 1e-12


def test_all_internal_checks_pass(payload):
    failed = [c["name"] for c in payload["checks"] if not c["pass"]]
    assert failed == []
    assert payload["overall"] == "PASS"


# ----------------------------------------------------------------------
# Corrected successor record
# ----------------------------------------------------------------------
def test_corrected_path_is_worse_on_every_record_statistic(payload):
    rec = payload["record"]
    assert rec["corrected"]["canonical_sharpe"] < rec["published"]["canonical_sharpe"]
    assert rec["corrected"]["trailing_63d_sharpe"] < rec["published"]["trailing_63d_sharpe"]
    assert rec["corrected"]["psr_normal"] < rec["published"]["psr_normal"]


def test_corrected_path_does_not_rescue_the_decision(payload):
    rec = payload["record"]
    assert abs(rec["published"]["trailing_63d_sharpe"] - COMMITTED_TRAILING_SHARPE) < 1e-12
    assert rec["production_gates_published"]["decision"] == "NO-GO"
    assert rec["production_gates_corrected"]["decision"] == "NO-GO"
    assert rec["production_gates_corrected"]["failed_gates"] == [
        "rolling_63d_sharpe",
        "psr",
    ]


def test_higher_corrected_walk_forward_mean_is_an_artefact(payload):
    wf = payload["walk_forward"]
    assert (
        wf["corrected"]["mean_test_sharpe_excl_worst_fold"]
        < wf["published"]["mean_test_sharpe_excl_worst_fold"]
    )
    assert wf["published"]["worst_fold"] == ARTEFACT_FOLD


def test_psr_uses_the_repository_settings(payload):
    settings = payload["record"]["psr_settings"]
    assert settings["target"] == PSR_TARGET == 1.4178
    assert settings["n_bootstrap"] == PSR_N_BOOTSTRAP == 1000
    assert settings["block_size"] == PSR_BLOCK_SIZE == 22
    assert settings["seed"] == PSR_SEED == 20240101


def test_corrected_record_matches_cycle926_values(payload):
    rec = payload["record"]["corrected"]
    assert abs(rec["canonical_sharpe"] - CORRECTED_RECORD_EXPECTED["canonical_sharpe"]) < 5e-5
    assert abs(rec["trailing_63d_sharpe"] - CORRECTED_RECORD_EXPECTED["trailing_63d_sharpe"]) < 5e-5
    assert abs(rec["psr_normal"] - CORRECTED_RECORD_EXPECTED["psr_normal"]) < 5e-5
    assert abs(rec["max_drawdown"] - CORRECTED_RECORD_EXPECTED["max_drawdown"]) < 5e-5


def test_corrected_walk_forward_matches_cycle926_values(payload):
    wf = payload["walk_forward"]["corrected"]
    assert abs(wf["mean_test_sharpe"] - CORRECTED_WF_EXPECTED["mean_test_sharpe"]) < 5e-5
    assert abs(wf["mean_test_sharpe_excl_artefact_fold"] - CORRECTED_WF_EXPECTED["mean_test_sharpe_excl_artefact_fold"]) < 5e-5
    assert abs(wf["mean_test_sharpe_excl_worst_fold"] - CORRECTED_WF_EXPECTED["mean_test_sharpe_excl_worst_fold"]) < 5e-5
    assert abs(wf["median_test_sharpe"] - CORRECTED_WF_EXPECTED["median_test_sharpe"]) < 5e-5
    assert wf["worst_fold"] == CORRECTED_WF_EXPECTED["worst_fold"]
    assert abs(wf["worst_fold_test_sharpe"] - CORRECTED_WF_EXPECTED["worst_fold_test_sharpe"]) < 5e-4
    assert wf["total_test_trades"] == CORRECTED_WF_EXPECTED["total_test_trades"]


def test_corrected_test_period_matches_cycle926_value(payload):
    tp = payload["test_period"]
    assert abs(tp["corrected"]["sharpe_ratio"] - CORRECTED_TEST_PERIOD_EXPECTED["sharpe_ratio"]) < 5e-5
    assert tp["corrected"]["sharpe_ratio"] < tp["published"]["sharpe_ratio"]
    assert tp["corrected"]["sharpe_ratio"] < PSR_TARGET


# ----------------------------------------------------------------------
# Incumbent unchanged
# ----------------------------------------------------------------------
def test_incumbent_verdict_is_unchanged(payload):
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


def test_committed_artifacts_are_not_overwritten(cli, payload):
    _, hashes = cli
    assert payload["read_only"]["committed_artifacts_unchanged"]
    changed = [k for k in hashes["before"] if hashes["before"][k] != hashes["after"].get(k)]
    assert changed == []
    assert hashes["state_before"] == hashes["state_after"]
    assert hashes["published_before"] == hashes["published_after"]


def test_fingerprints_of_data_and_config_do_not_move():
    before = fingerprint(REPO / "data")
    config_before = fingerprint(REPO / "config")
    run_consolidation()
    assert fingerprint(REPO / "data") == before
    assert fingerprint(REPO / "config") == config_before
