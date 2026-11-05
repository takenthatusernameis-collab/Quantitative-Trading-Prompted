"""Offline tests for the drift-flag persistence accounting.

No network, no data mutation: every test either uses synthetic series or reads
the committed paper-trading state read-only.
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.drift_persistence_report as report_tool
import src.simulation.paper_trading as pt
from src.evaluation.drift import (
    DEFAULT_MIN_PERIODS,
    DEFAULT_SHARPE_THRESHOLD,
    annualized_sharpe,
    rolling_sharpe_series,
    sharpe_persistence,
    subthreshold_calendar_window,
    subthreshold_streak,
)

STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"


def _independent_sharpe(returns) -> float:
    """Straight transcription of the live paper-trading formula."""
    vol = float(np.std(returns, ddof=1)) * np.sqrt(252)
    if vol <= 0.0:
        return 0.0
    return (float(np.mean(returns)) * 252) / vol


def _independent_streak(dates, returns, threshold=DEFAULT_SHARPE_THRESHOLD) -> int:
    """Trailing count of sub-threshold sessions, computed without the module."""
    values = []
    for i in range(len(returns)):
        if i + 1 < DEFAULT_MIN_PERIODS:
            values.append(None)
        else:
            values.append(_independent_sharpe(returns[max(0, i - 62) : i + 1]))
    streak = 0
    for value in reversed(values):
        if value is None or value >= threshold:
            break
        streak += 1
    return streak


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_annualized_sharpe_matches_live_formula():
    rng = np.random.default_rng(7)
    returns = rng.normal(0.0004, 0.008, size=200)
    assert annualized_sharpe(returns) == pytest.approx(_independent_sharpe(returns))


def test_annualized_sharpe_handles_degenerate_inputs():
    assert annualized_sharpe([]) == 0.0
    assert annualized_sharpe([0.01]) == 0.0
    assert annualized_sharpe([0.01, 0.01, 0.01]) == 0.0


def test_rolling_series_gates_on_min_periods():
    dates = [f"2026-01-{i:02d}" for i in range(1, 26)]
    returns = [0.001] * 25
    series = rolling_sharpe_series(dates, returns)
    assert len(series) == 25
    assert all(value is None for _d, value in series[: DEFAULT_MIN_PERIODS - 1])
    assert all(value is not None for _d, value in series[DEFAULT_MIN_PERIODS - 1 :])


def test_rolling_series_rejects_misaligned_inputs():
    with pytest.raises(ValueError):
        rolling_sharpe_series(["2026-01-01", "2026-01-02"], [0.001])


def test_rolling_series_last_value_matches_direct_computation():
    rng = np.random.default_rng(11)
    returns = list(rng.normal(0.0, 0.01, size=90))
    dates = [f"d{i:03d}" for i in range(90)]
    series = rolling_sharpe_series(dates, returns)
    assert series[-1][1] == pytest.approx(_independent_sharpe(returns[-63:]))


def test_subthreshold_streak_counts_trailing_subthreshold():
    series = [("a", 0.9), ("b", 0.4), ("c", 0.2), ("d", 0.1)]
    assert subthreshold_streak(series) == 3
    assert subthreshold_streak(series, threshold=0.15) == 1


def test_subthreshold_streak_resets_when_value_recovers():
    series = [("a", 0.2), ("b", 0.1), ("c", 0.8), ("d", 0.7)]
    assert subthreshold_streak(series) == 0
    assert subthreshold_streak([("a", 0.2), ("b", 0.1), ("c", 0.8), ("d", 0.4)]) == 1


def test_subthreshold_streak_stops_at_unavailable_value():
    # The scan stops at a session without a computed value.
    assert subthreshold_streak([("a", None), ("b", 0.1)]) == 1
    assert subthreshold_streak([("a", None), ("b", None)]) == 0


def test_sharpe_persistence_summary_fields():
    returns = [-0.002, 0.001] * 15
    dates = [f"d{i:03d}" for i in range(30)]
    summary = sharpe_persistence(dates, returns)
    assert summary["streak_days"] == _independent_streak(dates, returns)
    assert summary["streak_start_date"] == dates[DEFAULT_MIN_PERIODS - 1]
    assert summary["streak_end_date"] == dates[-1]
    assert summary["evaluated_sessions"] == 30 - DEFAULT_MIN_PERIODS + 1
    assert summary["last_sharpe"] == pytest.approx(_independent_sharpe(returns))


def test_calendar_window_counts_only_recent_sessions():
    dates = [f"2026-01-{i:02d}" for i in range(1, 29)]
    returns = [-0.002, 0.001] * 14
    series = rolling_sharpe_series(dates, returns)
    window = subthreshold_calendar_window(dates, series, calendar_days=7)
    assert window["window_end_date"] == dates[-1]
    assert window["sessions_in_window"] <= 7
    assert window["subthreshold_sessions"] <= window["sessions_in_window"]


# ---------------------------------------------------------------------------
# Live paper-trading integration
# ---------------------------------------------------------------------------


class _StubSimulation:
    def __init__(self, daily: pd.DataFrame):
        self.daily = daily


def _config(tmp_path):
    cfg = pt.PaperTradingConfig.from_paper_config_yaml(
        ROOT / "config" / "paper_trading_config.yaml"
    )
    cfg.output_dir = str(tmp_path / "out")
    cfg.report_path = str(tmp_path / "report.md")
    return cfg


def _stub_daily(latest_date: str, net_return: float, symbols) -> pd.DataFrame:
    index = pd.DatetimeIndex([pd.Timestamp(latest_date, tz="UTC")], name="Date")
    data = {
        "turnover": [0.01],
        "vol_scale": [1.0],
        "dd_scale": [1.0],
        "regime_exposure": [1.0],
        "net_return": [net_return],
        "exposure": [1.0],
        "n_positions": [1],
    }
    for symbol in symbols:
        data[f"weight_{symbol}"] = [1.0 / len(symbols)]
    return pd.DataFrame(data, index=index)


def test_drift_flag_records_persistence_days(tmp_path, monkeypatch):
    """The live update must record the consecutive sub-threshold session count."""
    history_dates = [f"2026-01-{i:02d}" for i in range(1, 31)]
    history_returns = [-0.002, 0.001] * 15
    state = pt.PaperTradingState(
        last_run_date=history_dates[-1],
        cumulative_returns=list(history_returns),
        cumulative_pnl=[0.0] * len(history_returns),
        cumulative_dates=list(history_dates),
        current_nav=100000.0,
        peak_nav=100000.0,
    )
    config = _config(tmp_path)
    latest_date = "2026-01-31"
    monkeypatch.setattr(
        pt,
        "run_simulation",
        lambda *a, **k: _StubSimulation(
            _stub_daily(latest_date, -0.001, config.universe)
        ),
    )

    new_state, _artifacts = pt.run_daily_paper_update(
        config, state, market_data=_stub_daily(latest_date, -0.001, config.universe)
    )

    flag = new_state.drift_flags.get("low_rolling_sharpe")
    assert flag is not None, "expected the low_rolling_sharpe flag to be raised"
    expected = _independent_streak(
        history_dates + [latest_date], list(history_returns) + [-0.001]
    )
    assert flag["persistence_days"] == expected
    assert flag["threshold"] == DEFAULT_SHARPE_THRESHOLD
    # The flag value itself is unchanged by the persistence accounting.
    assert flag["value"] == pytest.approx(
        _independent_sharpe((list(history_returns) + [-0.001])[-63:])
    )


# ---------------------------------------------------------------------------
# Committed state (read-only) and the reporting tool
# ---------------------------------------------------------------------------


def _load_state() -> dict:
    with open(STATE_PATH) as fh:
        return yaml.safe_load(fh)


def test_canonical_state_recomputes_stored_drift_flag():
    state = _load_state()
    dates = [str(d) for d in state["cumulative_dates"]]
    returns = [float(r) for r in state["cumulative_returns"]]
    assert len(dates) == len(returns)

    summary = sharpe_persistence(dates, returns)
    assert summary["streak_days"] == _independent_streak(dates, returns)

    stored = (state.get("drift_flags") or {}).get("low_rolling_sharpe")
    if stored is not None:
        assert summary["last_sharpe"] == pytest.approx(float(stored["value"]))


def test_report_tool_reproduces_canonical_state():
    report = report_tool.build_report(_load_state())
    state = _load_state()
    dates = [str(d) for d in state["cumulative_dates"]]
    returns = [float(r) for r in state["cumulative_returns"]]
    assert report["streak_days"] == _independent_streak(dates, returns)
    assert report["last_sharpe"] == pytest.approx(
        _independent_sharpe(returns[-63:])
    )
    stored = (state.get("drift_flags") or {}).get("low_rolling_sharpe")
    if stored is not None:
        assert report["stored_matches_recomputed"] is True


def test_report_tool_does_not_modify_state(tmp_path, monkeypatch, capsys):
    before = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()
    monkeypatch.setattr(
        sys, "argv", ["drift_persistence_report.py", "--json"]
    )
    assert report_tool.main() == 0
    out = capsys.readouterr().out
    assert '"streak_days"' in out
    assert hashlib.sha256(STATE_PATH.read_bytes()).hexdigest() == before


def test_report_tool_flags_state_inconsistency():
    with pytest.raises(ValueError):
        report_tool.build_report(
            {"cumulative_dates": ["2026-01-01"], "cumulative_returns": []}
        )


def test_build_report_includes_non_null_provenance_fields():
    state = _load_state()
    report = report_tool.build_report(state, state_path=STATE_PATH)
    prov = report.get("provenance") or {}
    assert prov.get("git_sha"), "git_sha must be non-null in the provenance block"
    assert prov.get("paper_trading_state_sha256"), (
        "paper_trading_state_sha256 must be non-null in the provenance block"
    )
    assert prov.get("config"), "config hash block must be non-null"


def test_provenance_state_sha_matches_file_hash():
    state = _load_state()
    report = report_tool.build_report(state, state_path=STATE_PATH)
    prov = report.get("provenance") or {}
    expected = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()
    assert prov.get("paper_trading_state_sha256") == expected


def test_main_prints_provenance_block(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["drift_persistence_report.py"])
    assert report_tool.main() == 0
    out = capsys.readouterr().out
    assert "provenance:" in out
    assert "git_sha:" in out
    assert "paper_trading_state_sha256:" in out


def test_main_json_includes_provenance(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["drift_persistence_report.py", "--json"])
    assert report_tool.main() == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    prov = payload.get("provenance") or {}
    assert prov.get("git_sha")
    assert prov.get("paper_trading_state_sha256")
    assert prov.get("config")


def test_update_rolling_report_preserves_git_sha_when_hashes_unchanged(tmp_path, monkeypatch):
    """Avoid self-referential churn: git_sha only updates when state/config hashes change."""
    state = _load_state()
    report = report_tool.build_report(state, state_path=STATE_PATH)
    prov = report["provenance"]
    report_path = tmp_path / "rolling.md"
    report_path.write_text(
        "# Report\n\n## Drift Persistence Provenance\n\n"
        f"- **git_sha:** deadbeefcafebabe\n"
        f"- **paper_trading_state_sha256:** {prov['paper_trading_state_sha256']}\n"
        f"- **paper_trading_config_sha256:** {prov['config']['paper_trading_config']}\n"
    )
    monkeypatch.setattr(report_tool, "_get_git_sha", lambda: "newhead0000000000000000000000000000000000")
    changed = report_tool.update_rolling_report(report, report_path=report_path)
    text = report_path.read_text()
    assert "deadbeefcafebabe" in text
    assert "newhead0000000000000000000000000000000000" not in text


def test_update_rolling_report_updates_git_sha_when_state_hash_changes(tmp_path, monkeypatch):
    """When state/config hashes change, git_sha should update to provenance value."""
    state = _load_state()
    report = report_tool.build_report(state, state_path=STATE_PATH)
    report = json.loads(json.dumps(report))  # deep copy
    report["provenance"]["git_sha"] = "newhead0000000000000000000000000000000000"
    report_path = tmp_path / "rolling.md"
    report_path.write_text(
        "# Report\n\n## Drift Persistence Provenance\n\n"
        "- **git_sha:** deadbeefcafebabe\n"
        "- **paper_trading_state_sha256:** differenthash\n"
        f"- **paper_trading_config_sha256:** {report['provenance']['config']['paper_trading_config']}\n"
    )
    report_tool.update_rolling_report(report, report_path=report_path)
    text = report_path.read_text()
    assert "newhead0000000000000000000000000000000000" in text
