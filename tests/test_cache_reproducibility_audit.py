"""Tests for the state-vs-cache reproducibility audit.

Pure and read-only: synthetic states and synthetic cache frames only, so the
tests never touch the canonical state or the canonical raw cache.
"""
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.paper_trading_cache_reproducibility_audit as audit


def _write_cache(tmp_path: Path, frames: dict[str, list[str]]) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    for symbol, dates in frames.items():
        idx = pd.DatetimeIndex(
            [pd.Timestamp(d, tz="UTC") for d in dates], name="Date"
        )
        df = pd.DataFrame(
            {
                "Open": [100.0] * len(idx),
                "High": [101.0] * len(idx),
                "Low": [99.0] * len(idx),
                "Close": [100.5] * len(idx),
                "Volume": [1_000_000.0] * len(idx),
            },
            index=idx,
        )
        df.to_parquet(raw / f"{symbol}.parquet")
    return raw


def test_state_fully_reproducible_when_frontiers_match(tmp_path, monkeypatch):
    raw = _write_cache(
        tmp_path,
        {"SPY": ["2026-10-18", "2026-10-19"], "QQQ": ["2026-10-19"]},
    )
    monkeypatch.setattr(audit, "RAW_DIR", raw)
    state = {"cumulative_dates": ["2026-10-18", "2026-10-19"]}
    assert audit.build_audit(state, symbols=["SPY", "QQQ"])[
        "reproducible_from_committed_cache"
    ] is True
    assert audit.missing_sessions(state, symbols=["SPY", "QQQ"]) == []


def test_state_not_reproducible_when_ahead_of_cache(tmp_path, monkeypatch):
    raw = _write_cache(
        tmp_path,
        {"SPY": ["2026-10-19"], "QQQ": ["2026-10-19"]},
    )
    monkeypatch.setattr(audit, "RAW_DIR", raw)
    state = {
        "cumulative_dates": [
            "2026-10-18",
            "2026-10-19",
            "2026-10-20",
            "2026-11-04",
        ]
    }
    missing = audit.missing_sessions(state, symbols=["SPY", "QQQ"])
    assert missing == ["2026-10-20", "2026-11-04"]
    assert (
        audit.build_audit(state, symbols=["SPY", "QQQ"])[
            "reproducible_from_committed_cache"
        ]
        is False
    )


def test_cache_frontier_is_minimum_across_universe(tmp_path, monkeypatch):
    raw = _write_cache(
        tmp_path,
        {"SPY": ["2026-10-19"], "QQQ": ["2026-10-16"]},
    )
    monkeypatch.setattr(audit, "RAW_DIR", raw)
    # The simulation needs every symbol, so the binding frontier is the
    # shortest one (QQQ at 2026-10-16), not the longest (SPY at 2026-10-19).
    assert audit.cache_frontier(raw, symbols=["SPY", "QQQ"]) == "2026-10-16"


def test_cache_frontier_none_when_symbol_missing(tmp_path, monkeypatch):
    raw = _write_cache(tmp_path, {"SPY": ["2026-10-19"]})
    monkeypatch.setattr(audit, "RAW_DIR", raw)
    assert audit.cache_frontier(raw, symbols=["SPY", "QQQ"]) is None


def test_audit_main_strict_fails_when_not_reproducible(
    tmp_path, monkeypatch, capsys
):
    raw = _write_cache(tmp_path, {"SPY": ["2026-10-19"]})
    monkeypatch.setattr(audit, "RAW_DIR", raw)
    monkeypatch.setattr(audit, "STATE_PATH", tmp_path / "state.yaml")
    (tmp_path / "state.yaml").write_text(
        yaml.safe_dump({"cumulative_dates": ["2026-10-20"]})
    )
    monkeypatch.setattr(sys, "argv", ["audit.py", "--strict", "--symbols", "SPY"])
    assert audit.main() == 1
    out = capsys.readouterr().out
    assert "state frontier:          2026-10-20" in out
    assert "cache frontier:          2026-10-19" in out
    assert "BLOCKER" in out


def test_audit_main_strict_passes_when_reproducible(
    tmp_path, monkeypatch, capsys
):
    raw = _write_cache(tmp_path, {"SPY": ["2026-10-19"]})
    monkeypatch.setattr(audit, "RAW_DIR", raw)
    monkeypatch.setattr(audit, "STATE_PATH", tmp_path / "state.yaml")
    (tmp_path / "state.yaml").write_text(
        yaml.safe_dump({"cumulative_dates": ["2026-10-19"]})
    )
    monkeypatch.setattr(sys, "argv", ["audit.py", "--strict", "--symbols", "SPY"])
    assert audit.main() == 0
    out = capsys.readouterr().out
    assert "reproducible from committed cache: yes" in out