"""Tests for the paper-record vs committed raw-cache coverage audit.

The audit is read-only and must stay honest about the two failure modes that
matter for the research contract:

* a coverage gap must be *reported*, not silently absorbed (a stale raw cache
  must not look like full reproducibility);
* an internally inconsistent state (parallel arrays disagreeing, or a stored
  Sharpe that does not reproduce) must fail closed rather than print a
  reassuring summary.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research import paper_record_raw_coverage_audit as audit_mod

SYMBOLS = ["SPY", "QQQ"]
DATES = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-09-01", periods=30)]
RETURNS = [0.001 * ((i % 7) - 3) for i in range(len(DATES))]


def _write_raw(raw_dir: Path, symbols, dates, lag_symbol: str | None = None) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for sym in symbols:
        idx = dates[:-1] if sym == lag_symbol else dates
        df = pd.DataFrame(
            {"Close": np.linspace(100.0, 101.0, len(idx))},
            index=pd.to_datetime(idx, utc=True),
        )
        df.to_parquet(raw_dir / f"{sym}.parquet")


def _write_config(path: Path, symbols) -> None:
    path.write_text(yaml.safe_dump({"universe": list(symbols)}))


def _write_state(path: Path, dates, returns, stored_sharpe: float | None = None) -> None:
    last = dates[-1]
    state = {
        "cumulative_dates": list(dates),
        "cumulative_returns": list(returns),
        "cumulative_pnl": list(returns),
        "run_history": [{"date": d} for d in dates],
        "last_run_date": last,
        "rolling_sharpe_63d": stored_sharpe
        if stored_sharpe is not None
        else float(audit_mod.rolling_sharpe_at(np.asarray(returns, dtype=float))),
    }
    path.write_text(yaml.safe_dump(state))


def _fixture(tmp_path: Path, **kwargs):
    raw_dir = tmp_path / "raw"
    config = tmp_path / "config.yaml"
    state = tmp_path / "state.yaml"
    _write_raw(raw_dir, kwargs.get("symbols", SYMBOLS), kwargs.get("raw_dates", DATES),
               kwargs.get("lag_symbol"))
    _write_config(config, kwargs.get("symbols", SYMBOLS))
    _write_state(state, kwargs.get("dates", DATES), kwargs.get("returns", RETURNS),
                 kwargs.get("stored_sharpe"))
    return state, config, raw_dir


def test_coverage_end_is_minimum_across_universe(tmp_path):
    """One lagging symbol must lower coverage; it must not be averaged away."""
    state, config, raw_dir = _fixture(tmp_path, symbols=["SPY", "QQQ"], lag_symbol="QQQ")
    result = audit_mod.audit(state, config, raw_dir)
    assert result["coverage_end"] == DATES[-2]
    assert result["per_symbol_last_date"] == {"SPY": DATES[-1], "QQQ": DATES[-2]}
    assert result["n_unverified"] == 1
    assert result["unverified_sessions"] == [DATES[-1]]


def test_fully_covered_record_reports_zero_unverified(tmp_path):
    state, config, raw_dir = _fixture(tmp_path)
    result = audit_mod.audit(state, config, raw_dir)
    assert result["coverage_end"] == DATES[-1]
    assert result["n_covered"] == len(DATES)
    assert result["n_unverified"] == 0
    assert result["unverified_sessions"] == []


def test_split_coverage_is_inclusive_of_coverage_end():
    covered, unverified = audit_mod.split_coverage(DATES, DATES[2])
    assert covered == DATES[:3]
    assert unverified == DATES[3:]


def test_rolling_sharpe_reproduces_live_formula():
    returns = np.linspace(-0.01, 0.01, 40)
    expected = audit_mod.annualized_sharpe(returns[-63:])
    assert audit_mod.rolling_sharpe_at(returns) == pytest.approx(expected)


def test_rolling_sharpe_uses_last_63_sessions_only():
    rng = np.random.default_rng(0)
    returns = rng.normal(0.0, 0.01, 200)
    tail = audit_mod.rolling_sharpe_at(returns)
    explicit = audit_mod.annualized_sharpe(returns[-63:])
    assert tail == pytest.approx(explicit)
    assert tail != pytest.approx(audit_mod.annualized_sharpe(returns))


def test_covered_only_sharpe_uses_truncated_series(tmp_path):
    dates = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-09-01", periods=40)]
    returns = np.linspace(-0.01, 0.01, 40)
    state, config, raw_dir = _fixture(
        tmp_path,
        dates=dates,
        returns=[float(r) for r in returns],
        raw_dates=dates[:37],
    )
    result = audit_mod.audit(state, config, raw_dir)
    assert result["n_unverified"] == 3
    assert result["covered_only_rolling_sharpe_63d"] == pytest.approx(
        audit_mod.rolling_sharpe_at(returns[:37])
    )


def test_missing_symbol_fails_closed(tmp_path):
    state, config, raw_dir = _fixture(tmp_path)
    (raw_dir / "QQQ.parquet").unlink()
    with pytest.raises(FileNotFoundError):
        audit_mod.audit(state, config, raw_dir)


def test_parallel_array_mismatch_fails_closed(tmp_path):
    state, config, raw_dir = _fixture(tmp_path)
    payload = yaml.safe_load(state.read_text())
    payload["run_history"] = payload["run_history"][:-1]
    state.write_text(yaml.safe_dump(payload))
    with pytest.raises(ValueError, match="run_history"):
        audit_mod.audit(state, config, raw_dir)


def test_stored_sharpe_mismatch_returns_exit_1(tmp_path):
    state, config, raw_dir = _fixture(tmp_path, stored_sharpe=-9.0)
    assert audit_mod.main(
        ["--state", str(state), "--config", str(config), "--raw-dir", str(raw_dir),
         "--report", str(tmp_path / "report.md")]
    ) == 1


def test_main_writes_report_and_returns_0_for_gap(tmp_path):
    state, config, raw_dir = _fixture(tmp_path, lag_symbol="QQQ")
    report = tmp_path / "out" / "report.md"
    rc = audit_mod.main(
        ["--state", str(state), "--config", str(config), "--raw-dir", str(raw_dir),
         "--report", str(report)]
    )
    assert rc == 0
    text = report.read_text()
    assert DATES[-1] in text
    assert "not" in text and "re-derivable" in text


def test_missing_state_returns_exit_2(tmp_path):
    _, config, raw_dir = _fixture(tmp_path)
    rc = audit_mod.main(
        ["--state", str(tmp_path / "absent.yaml"), "--config", str(config),
         "--raw-dir", str(raw_dir), "--report", str(tmp_path / "r.md")]
    )
    assert rc == 2


def test_audit_is_read_only_on_committed_inputs():
    """The real committed state and cache must be byte-identical after the audit."""
    state = REPO / "data" / "processed" / "paper_trading_state.yaml"
    raw_files = sorted((REPO / "data" / "raw").glob("*.parquet"))
    assert state.exists() and raw_files

    def digest() -> str:
        h = hashlib.sha256()
        h.update(state.read_bytes())
        for p in raw_files:
            h.update(p.name.encode())
            h.update(p.read_bytes())
        return h.hexdigest()

    before = digest()
    result = audit_mod.audit(
        state, REPO / "config" / "simulation_candidate_001.yaml", REPO / "data" / "raw"
    )
    assert digest() == before
    assert result["n_sessions"] > 0
    assert result["reproduced_ok"] is True
