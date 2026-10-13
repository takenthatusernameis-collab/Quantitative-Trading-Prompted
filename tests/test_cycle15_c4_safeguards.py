from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research import run_cycle15_c4_corrected as runner  # noqa: E402


def test_missing_cache_fails_before_any_parquet_read(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)

    def forbidden_read(*args, **kwargs):
        pytest.fail("cache preflight attempted to read after required cache files were missing")

    monkeypatch.setattr(runner.pd, "read_parquet", forbidden_read)
    with pytest.raises(RuntimeError, match="blocked before fetch"):
        runner._require_cached_inputs()


def test_walkforward_schema_matches_canonical_metric_engine():
    walkforward = (ROOT / "src/evaluation/walkforward.py").read_text(encoding="utf-8")
    eval_utils = (ROOT / "src/evaluation/utils.py").read_text(encoding="utf-8")
    engine = (ROOT / "src/backtest/engine.py").read_text(encoding="utf-8")

    mappings = {
        "train_sharpe": "sharpe_ratio",
        "train_ann_return": "annualized_return",
        "test_sharpe": "sharpe_ratio",
        "test_ann_return": "annualized_return",
        "test_max_dd": "max_drawdown",
        "test_turnover": "annualized_turnover",
        "test_trades": "trade_count",
    }
    for output_column, metric in mappings.items():
        assert f'"{output_column}"' in walkforward
        assert f'.get("{metric}"' in walkforward
        assert f'"{metric}"' in engine
    assert "def period_metrics(" in eval_utils
    assert "return compute_metrics(" in eval_utils


def test_nonfinite_fold_metric_fails_closed():
    splits = runner.generate_walkforward_splits(
        runner.START_DATE, runner.END_DATE,
        runner.WF_TRAIN_YEARS, runner.WF_TEST_MONTHS, runner.WF_STEP_MONTHS,
        runner.WF_PURGE_DAYS, runner.WF_EMBARGO_DAYS,
    )
    wf_df = pd.DataFrame({
        "fold": list(range(1, 37)),
        "train_start": [sp["train_start"] for sp in splits],
        "train_end": [sp["train_end"] for sp in splits],
        "test_start": [sp["test_start"] for sp in splits],
        "test_end": [sp["test_end"] for sp in splits],
        "train_sharpe": np.zeros(36),
        "train_ann_return": np.zeros(36),
        "test_sharpe": np.zeros(36),
        "test_ann_return": np.zeros(36),
        "test_max_dd": np.zeros(36),
        "test_turnover": np.zeros(36),
        "test_trades": np.zeros(36),
        "test_sortino": np.zeros(36),
    })
    wf_df.loc[6, "test_sharpe"] = np.nan
    with pytest.raises(RuntimeError, match=r"test_sharpe.*non-finite in fold\(s\): \[7\]"):
        runner._validate_generated_outputs(
            pd.DataFrame(),
            {},
            {"wf_df": wf_df, "summary": {"n_folds": 36}},
            splits,
            "",
        )


def _write_valid_artifact_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "SIM_PARQUET", tmp_path / "simulation.parquet")
    monkeypatch.setattr(runner, "TRADES_PARQUET", tmp_path / "trades.parquet")
    monkeypatch.setattr(runner, "WEIGHTS_PARQUET", tmp_path / "weights.parquet")

    index = pd.date_range(
        runner.EXPECTED_CLOSE_START, runner.EXPECTED_CLOSE_END,
        periods=runner.EXPECTED_CLOSE_ROWS, tz="UTC",
    )
    close = pd.DataFrame(1.0, index=index, columns=runner.UNIVERSE)
    weights = pd.DataFrame(0.0, index=index, columns=runner.UNIVERSE)
    daily_columns = [
        "net_return", "gross_return", "cost", "turnover",
        "exposure", "n_long", "drawdown",
        *(f"weight_{symbol}" for symbol in runner.UNIVERSE),
    ]
    daily = pd.DataFrame(0.0, index=index, columns=daily_columns)
    daily["n_long"] = 0
    trade_columns = [
        "trade_id", "date", "symbol", "side",
        "weight_before", "weight_after", "weight_change", "price", "cost",
    ]
    trades = pd.DataFrame(columns=trade_columns)
    weights.to_parquet(runner.WEIGHTS_PARQUET)
    daily.to_parquet(runner.SIM_PARQUET)
    trades.to_parquet(runner.TRADES_PARQUET)

    splits = runner.generate_walkforward_splits(
        runner.START_DATE, runner.END_DATE,
        runner.WF_TRAIN_YEARS, runner.WF_TEST_MONTHS, runner.WF_STEP_MONTHS,
        runner.WF_PURGE_DAYS, runner.WF_EMBARGO_DAYS,
    )
    wf_df = pd.DataFrame({
        "fold": list(range(1, 37)),
        "train_start": [sp["train_start"] for sp in splits],
        "train_end": [sp["train_end"] for sp in splits],
        "test_start": [sp["test_start"] for sp in splits],
        "test_end": [sp["test_end"] for sp in splits],
        "train_sharpe": np.zeros(36),
        "train_ann_return": np.zeros(36),
        "test_sharpe": np.zeros(36),
        "test_ann_return": np.zeros(36),
        "test_max_dd": np.zeros(36),
        "test_turnover": np.zeros(36),
        "test_trades": np.zeros(36),
        "test_sortino": np.zeros(36),
    })
    report = "\n".join([
        "sectorrotation_baseline_wf_001",
        "config/sectorrotation_candidate_001.yaml",
        runner._config_hash(),
        "1998-12-22",
        "36 Folds",
        "XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY",
        runner._git_hash(),
    ])
    return close, {
        "weights": weights,
        "daily": daily,
        "trades_df": trades,
    }, {"wf_df": wf_df, "summary": {"n_folds": 36}}, splits, report


def test_persisted_artifacts_round_trip_and_tampering_is_rejected(tmp_path, monkeypatch):
    close, baseline, wf, splits, report = _write_valid_artifact_fixture(tmp_path, monkeypatch)
    runner._validate_generated_outputs(close, baseline, wf, splits, report)

    altered = pd.read_parquet(runner.SIM_PARQUET)
    altered.loc[altered.index[10], "net_return"] = 0.01
    altered.to_parquet(runner.SIM_PARQUET)
    with pytest.raises(RuntimeError, match="differs from in-memory results"):
        runner._validate_generated_outputs(close, baseline, wf, splits, report)
