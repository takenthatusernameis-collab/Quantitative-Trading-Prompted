"""Hermetic tests for research/paper_trading_artifact_reconciliation_audit.py.

Each test builds a tiny synthetic record (state + the four per-session parquet
artifacts, written exactly the way ``src/simulation/paper_trading.py`` writes
them), then corrupts one artifact field and checks that the audit reports that
field and only that field. A final test runs the audit against the committed
record so a regression in the real data cannot pass unnoticed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from research import paper_trading_artifact_reconciliation_audit as audit_mod

UNIVERSE = ["SPY", "QQQ", "IWM"]
DATELINE = ["2026-01-02", "2026-01-05", "2026-01-06"]
NOTIONAL = 100000.0


def _record() -> dict:
    navs = [100400.0, 100100.0, 99800.0]
    weights = [
        {"SPY": 0.20, "QQQ": 0.10, "IWM": 0.00},
        {"SPY": 0.15, "QQQ": 0.10, "IWM": 0.05},
        {"SPY": 0.15, "QQQ": 0.05, "IWM": 0.05},
    ]
    vols = [0.80, 0.75, 0.70]
    regimes = [1.0, 1.0, 0.0]
    history = []
    for i, date in enumerate(DATELINE):
        prev_nav = NOTIONAL if i == 0 else navs[i - 1]
        prev_w = weights[i - 1] if i else None
        turnover = (
            0.0004
            if prev_w is None
            else float(
                sum(
                    abs(weights[i].get(s, 0.0) - prev_w.get(s, 0.0))
                    for s in set(weights[i]) | set(prev_w)
                )
            )
        )
        history.append(
            {
                "date": date,
                "nav": navs[i],
                "daily_return": (navs[i] - prev_nav) / prev_nav,
                "daily_pnl": navs[i] - prev_nav,
                "turnover": turnover,
                "vol_scale": vols[i],
                "dd_scale": 1.0,
                "regime_exposure": regimes[i],
                "n_positions": int(sum(1 for w in weights[i].values() if w > 0)),
            }
        )
    return {"run_history": history, "peak_nav": max(navs), "current_nav": navs[-1]}


def _write_artifacts(state: dict, paper_dir: Path) -> None:
    navs = [row["nav"] for row in state["run_history"]]
    running = np.minimum.accumulate(
        np.minimum(np.asarray(navs) / np.maximum.accumulate(navs) - 1.0, 0.0)
    )
    weights = [dict(zip(UNIVERSE, [0.2, 0.1, 0.0]))]
    weights = [
        {"SPY": 0.20, "QQQ": 0.10, "IWM": 0.00},
        {"SPY": 0.15, "QQQ": 0.10, "IWM": 0.05},
        {"SPY": 0.15, "QQQ": 0.05, "IWM": 0.05},
    ]
    paper_dir.mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(state["run_history"]):
        stamp = row["date"].replace("-", "")
        pd.DataFrame(
            [
                {
                    "date": row["date"],
                    "daily_return": row["daily_return"],
                    "daily_pnl": row["daily_pnl"],
                    "nav": row["nav"],
                }
            ]
        ).to_parquet(paper_dir / f"daily_pnl_{stamp}.parquet", index=False)
        pd.DataFrame(
            [
                {
                    "date": row["date"],
                    "vol_scale": row["vol_scale"],
                    "dd_scale": row["dd_scale"],
                    "drawdown": float(running[i]),
                    "exposure": row["vol_scale"] * row["regime_exposure"],
                }
            ]
        ).to_parquet(paper_dir / f"risk_state_{stamp}.parquet", index=False)
        pd.DataFrame(
            [
                {
                    "date": row["date"],
                    "spy_price": np.nan,
                    "regime_exposure": row["regime_exposure"],
                }
            ]
        ).to_parquet(paper_dir / f"regime_{stamp}.parquet", index=False)
        pd.DataFrame(
            [{"symbol": s, "weight": weights[i][s], "date": row["date"]} for s in UNIVERSE]
        ).to_parquet(paper_dir / f"positions_{stamp}.parquet", index=False)


@pytest.fixture()
def record(tmp_path: Path) -> dict:
    state = _record()
    paper_dir = tmp_path / "paper_trading"
    _write_artifacts(state, paper_dir)
    state_path = tmp_path / "paper_trading_state.yaml"
    state_path.write_text(yaml.safe_dump(state, sort_keys=False))
    config_path = tmp_path / "candidate.yaml"
    config_path.write_text(yaml.safe_dump({"universe": UNIVERSE}))
    return {
        "state": state,
        "paper_dir": paper_dir,
        "state_path": state_path,
        "config_path": config_path,
        "report": tmp_path / "report.md",
    }


def _run(record: dict) -> dict:
    return audit_mod.audit(record["state_path"], record["paper_dir"], record["config_path"])


def _fields(result: dict) -> set[str]:
    return {m["field"] for m in result["unattested"]}


def _mutate(record: dict, kind: str, stamp: str, **changes) -> None:
    path = record["paper_dir"] / f"{kind}_{stamp}.parquet"
    df = pd.read_parquet(path)
    for column, value in changes.items():
        df.loc[0, column] = value
    df.to_parquet(path, index=False)


def test_clean_synthetic_record_passes(record: dict) -> None:
    result = _run(record)
    assert result["ok"] is True
    assert result["n_sessions"] == 3
    assert result["n_mismatches"] == 0
    assert result["attested"] == []
    assert result["unattested"] == []


def test_daily_return_mismatch_detected(record: dict) -> None:
    _mutate(record, "daily_pnl", "20260105", daily_return=0.5)
    assert _fields(_run(record)) == {"daily_pnl.daily_return"}


def test_nav_mismatch_detected(record: dict) -> None:
    _mutate(record, "daily_pnl", "20260105", nav=1.0)
    fields = _fields(_run(record))
    assert "daily_pnl.nav" in fields
    assert "daily_pnl.pnl_identity" in fields


def test_pnl_identity_mismatch_detected(record: dict) -> None:
    state = record["state"]
    state["run_history"][1]["daily_pnl"] = 1.0
    state["run_history"][1]["daily_return"] = 1.0 / state["run_history"][0]["nav"]
    record["state_path"].write_text(yaml.safe_dump(state, sort_keys=False))
    _mutate(record, "daily_pnl", "20260105", daily_pnl=1.0, daily_return=1.0 / 100400.0)
    assert _fields(_run(record)) == {"daily_pnl.pnl_identity"}


def test_vol_scale_mismatch_detected(record: dict) -> None:
    _mutate(record, "risk_state", "20260106", vol_scale=9.9, exposure=9.9 * 0.0)
    assert _fields(_run(record)) == {"risk_state.vol_scale"}


def test_exposure_product_mismatch_detected(record: dict) -> None:
    _mutate(record, "risk_state", "20260105", exposure=0.5)
    assert _fields(_run(record)) == {"risk_state.exposure"}


def test_drawdown_mismatch_detected(record: dict) -> None:
    _mutate(record, "risk_state", "20260106", drawdown=-0.9)
    assert _fields(_run(record)) == {"drawdown"}


def test_regime_exposure_mismatch_detected(record: dict) -> None:
    _mutate(record, "regime", "20260106", regime_exposure=1.0)
    assert _fields(_run(record)) == {"regime.regime_exposure"}


def test_n_positions_mismatch_detected(record: dict) -> None:
    path = record["paper_dir"] / "positions_20260106.parquet"
    df = pd.read_parquet(path)
    df.loc[df["symbol"] == "IWM", "weight"] = 0.0
    df.to_parquet(path, index=False)
    fields = _fields(_run(record))
    assert "positions.n_positions" in fields
    assert "positions.turnover" in fields


def test_turnover_mismatch_detected(record: dict) -> None:
    path = record["paper_dir"] / "positions_20260105.parquet"
    df = pd.read_parquet(path)
    df.loc[df["symbol"] == "QQQ", "weight"] = 0.02
    df.to_parquet(path, index=False)
    fields = _fields(_run(record))
    assert "positions.turnover" in fields
    assert "positions.gross" not in fields


def test_gross_leverage_mismatch_detected(record: dict) -> None:
    path = record["paper_dir"] / "positions_20260105.parquet"
    df = pd.read_parquet(path)
    df.loc[df["symbol"] == "SPY", "weight"] = 1.5
    df.to_parquet(path, index=False)
    assert "positions.gross" in _fields(_run(record))


def test_universe_mismatch_detected(record: dict) -> None:
    path = record["paper_dir"] / "positions_20260105.parquet"
    df = pd.read_parquet(path)
    df.loc[df["symbol"] == "SPY", "symbol"] = "EFA"
    df.to_parquet(path, index=False)
    assert "positions.symbols" in _fields(_run(record))


def test_missing_artifact_detected(record: dict) -> None:
    (record["paper_dir"] / "risk_state_20260105.parquet").unlink()
    assert _fields(_run(record)) == {"risk_state.present"}


def test_duplicate_rows_detected(record: dict) -> None:
    path = record["paper_dir"] / "regime_20260105.parquet"
    df = pd.read_parquet(path)
    pd.concat([df, df], ignore_index=True).to_parquet(path, index=False)
    assert _fields(_run(record)) == {"regime.rows"}


def test_artifact_date_mismatch_detected(record: dict) -> None:
    _mutate(record, "daily_pnl", "20260106", date="2026-01-07")
    assert _fields(_run(record)) == {"daily_pnl.date"}


def test_attested_known_defect_passes(record: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        audit_mod.KNOWN_DEFECTS,
        ("2026-01-06", "drawdown"),
        {
            "artifact": "risk_state",
            "observed": -0.9,
            "expected": -0.002,
            "reason": "synthetic repair defect",
        },
    )
    _mutate(record, "risk_state", "20260106", drawdown=-0.9)
    result = _run(record)

    assert result["ok"] is True
    assert len(result["attested"]) == 1
    assert result["unattested"] == []


def test_attested_defect_with_changed_value_is_unattested(
    record: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(
        audit_mod.KNOWN_DEFECTS,
        ("2026-01-06", "drawdown"),
        {
            "artifact": "risk_state",
            "observed": -0.9,
            "expected": -0.002,
            "reason": "synthetic repair defect",
        },
    )
    _mutate(record, "risk_state", "20260106", drawdown=-0.8)
    result = _run(record)

    assert result["ok"] is False
    assert result["attested"] == []
    assert _fields(result) == {"drawdown"}


def test_attested_defect_does_not_cover_other_sessions(
    record: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(
        audit_mod.KNOWN_DEFECTS,
        ("2026-01-06", "drawdown"),
        {
            "artifact": "risk_state",
            "observed": -0.9,
            "expected": -0.002,
            "reason": "synthetic repair defect",
        },
    )
    _mutate(record, "risk_state", "20260105", drawdown=-0.9)
    result = _run(record)

    assert result["ok"] is False
    assert _fields(result) == {"drawdown"}


def test_main_fails_on_unattested_mismatch(record: dict) -> None:
    _mutate(record, "regime", "20260106", regime_exposure=1.0)
    exit_code = audit_mod.main(
        [
            "--state",
            str(record["state_path"]),
            "--paper-dir",
            str(record["paper_dir"]),
            "--candidate-config",
            str(record["config_path"]),
            "--report",
            str(record["report"]),
        ]
    )
    assert exit_code == 1
    assert "OVERALL: FAIL" in record["report"].read_text() or record["report"].exists()


def test_main_passes_and_writes_report(record: dict) -> None:
    exit_code = audit_mod.main(
        [
            "--state",
            str(record["state_path"]),
            "--paper-dir",
            str(record["paper_dir"]),
            "--candidate-config",
            str(record["config_path"]),
            "--report",
            str(record["report"]),
        ]
    )
    assert exit_code == 0
    text = record["report"].read_text()
    assert "mismatches unattested | `0`" in text
    assert "PASS" in text


def test_main_no_report_writes_nothing(record: dict) -> None:
    exit_code = audit_mod.main(
        [
            "--state",
            str(record["state_path"]),
            "--paper-dir",
            str(record["paper_dir"]),
            "--candidate-config",
            str(record["config_path"]),
            "--report",
            str(record["report"]),
            "--no-report",
        ]
    )
    assert exit_code == 0
    assert not record["report"].exists()


@pytest.mark.parametrize("missing", ["state_path", "paper_dir", "config_path"])
def test_missing_inputs_exit_2(record: dict, tmp_path: Path, missing: str) -> None:
    args = {
        "state_path": record["state_path"],
        "paper_dir": record["paper_dir"],
        "config_path": record["config_path"],
    }
    args[missing] = tmp_path / "does-not-exist"
    assert audit_mod.main(["--state", str(args["state_path"]), "--paper-dir", str(args["paper_dir"]), "--candidate-config", str(args["config_path"])]) == 2


def test_render_report_lists_known_defect(record: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        audit_mod.KNOWN_DEFECTS,
        ("2026-01-06", "drawdown"),
        {
            "artifact": "risk_state",
            "observed": -0.9,
            "expected": -0.002,
            "reason": "synthetic repair defect",
        },
    )
    _mutate(record, "risk_state", "20260106", drawdown=-0.9)
    text = audit_mod.render_report(_run(record))
    assert "`2026-01-06` `drawdown`" in text
    assert "synthetic repair defect" in text


def test_committed_record_reconciles() -> None:
    result = audit_mod.audit()
    assert result["ok"] is True
    assert result["n_sessions"] >= 472
    assert [(m["session"], m["field"]) for m in result["attested"]] == [("2026-11-02", "drawdown")]
    assert result["unattested"] == []
