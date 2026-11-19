"""Tests for the provider-price attestation written by the extension path.

The extension downloads market data into a scratch directory that is discarded
on exit, so a session advanced beyond the committed raw cache cannot be
re-derived from any committed price file. The attestation
(``provider_digest_YYYYMMDD.json``) is the only durable record of those inputs,
which makes two properties load-bearing and worth pinning down:

* the digest must describe *exactly* the slice handed to the update (target
  session, prices, canonical sha256), otherwise it attests the wrong inputs;
* the digest write must never block or roll back a valid state extension, and
  must never be written by a no-op or dry-run.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import research.extend_paper_trading_state as ext
import research.paper_record_raw_coverage_audit as audit_mod

TZ = ZoneInfo("America/New_York")
SYMBOLS = ["SPY", "QQQ"]
DATES = ["2026-10-15", "2026-10-16", "2026-10-19"]


def _frame(closes: dict[str, list[float]] | None = None, dates=DATES) -> pd.DataFrame:
    """Universe frame with sorted MultiIndex columns and per-symbol Close values."""
    closes = closes or {"SPY": [100.0, 101.0, 102.0], "QQQ": [300.0, 303.0, 306.0]}
    index = pd.DatetimeIndex([pd.Timestamp(d, tz="UTC") for d in dates], name="Date")
    fields = ["Open", "High", "Low", "Close", "Volume"]
    cols = pd.MultiIndex.from_product([fields, SYMBOLS])
    data = {}
    for field, sym in cols:
        if field == "Close":
            data[(field, sym)] = closes[sym]
        elif field == "Volume":
            data[(field, sym)] = [1_000_000.0] * len(index)
        else:
            data[(field, sym)] = [float(v) for v in closes[sym]]
    return pd.DataFrame(data, index=index, columns=cols)


# ---------------------------------------------------------------------------
# Canonical serialization
# ---------------------------------------------------------------------------


def test_canonical_bytes_ignore_column_order():
    frame = _frame()
    shuffled = frame.loc[:, sorted(frame.columns, key=str, reverse=True)]
    assert ext.canonical_slice_bytes(frame) == ext.canonical_slice_bytes(shuffled)


def test_canonical_bytes_ignore_row_order():
    frame = _frame()
    assert ext.canonical_slice_bytes(frame) == ext.canonical_slice_bytes(
        frame.iloc[::-1]
    )


def test_canonical_bytes_change_when_a_close_changes():
    before = ext.canonical_slice_bytes(_frame())
    after = ext.canonical_slice_bytes(
        _frame({"SPY": [100.0, 101.0, 102.5], "QQQ": [300.0, 303.0, 306.0]})
    )
    assert before != after


def test_canonical_bytes_preserve_full_float_precision():
    a = ext.canonical_slice_bytes(
        _frame({"SPY": [100.0, 101.0, 102.00000000000001], "QQQ": [300.0, 303.0, 306.0]})
    )
    b = ext.canonical_slice_bytes(
        _frame({"SPY": [100.0, 101.0, 102.0], "QQQ": [300.0, 303.0, 306.0]})
    )
    assert a != b


# ---------------------------------------------------------------------------
# build_provider_digest
# ---------------------------------------------------------------------------


def test_digest_describes_the_slice_through_the_target():
    frame = _frame()
    payload = ext.build_provider_digest(frame, "2026-10-16", SYMBOLS)

    slice_ = frame.loc[:"2026-10-16"]
    assert payload["schema_version"] == ext.DIGEST_SCHEMA_VERSION
    assert payload["session"] == "2026-10-16"
    assert payload["previous_session"] == "2026-10-15"
    assert payload["universe"] == SYMBOLS
    assert payload["prices"]["SPY"] == {"previous_close": 100.0, "close": 101.0}
    assert payload["prices"]["QQQ"] == {"previous_close": 300.0, "close": 303.0}
    assert payload["slice"]["rows"] == 2
    assert payload["slice"]["columns"] == len(frame.columns)
    assert payload["slice"]["first_session"] == "2026-10-15"
    assert payload["slice"]["sha256"] == hashlib.sha256(
        ext.canonical_slice_bytes(slice_)
    ).hexdigest()
    # the digest must not attest data beyond the session it extended to
    assert payload["slice"]["sha256"] != hashlib.sha256(
        ext.canonical_slice_bytes(frame)
    ).hexdigest()


def test_digest_has_no_previous_session_on_a_single_row_slice():
    frame = _frame(dates=["2026-10-15"], closes={"SPY": [100.0], "QQQ": [300.0]})
    payload = ext.build_provider_digest(frame, "2026-10-15", SYMBOLS)
    assert payload["previous_session"] is None
    assert payload["prices"]["SPY"] == {"previous_close": None, "close": 100.0}


def test_digest_records_none_for_non_finite_close():
    frame = _frame({"SPY": [100.0, 101.0, float("nan")], "QQQ": [300.0, 303.0, 306.0]})
    payload = ext.build_provider_digest(frame, "2026-10-19", SYMBOLS)
    assert payload["prices"]["SPY"]["close"] is None


def test_digest_rejects_a_slice_that_does_not_reach_the_target():
    frame = _frame()
    with pytest.raises(ValueError, match="expected target session"):
        ext.build_provider_digest(frame, "2026-10-20", SYMBOLS)


def test_digest_rejects_an_empty_slice():
    frame = _frame()
    with pytest.raises(ValueError, match="empty"):
        ext.build_provider_digest(frame, "2026-10-14", SYMBOLS)


def test_digest_rejects_a_missing_close_column():
    frame = _frame().drop(columns=[("Close", "QQQ")])
    with pytest.raises(ValueError, match="no Close column"):
        ext.build_provider_digest(frame, "2026-10-19", SYMBOLS)


# ---------------------------------------------------------------------------
# write_provider_digest
# ---------------------------------------------------------------------------


def test_digest_write_is_deterministic_and_named_by_session(tmp_path):
    payload = ext.build_provider_digest(_frame(), "2026-10-16", SYMBOLS)
    first = ext.write_provider_digest(payload, tmp_path / "paper")
    second = ext.write_provider_digest(payload, tmp_path / "paper")
    assert first.name == "provider_digest_20261016.json"
    assert first == second
    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text())["session"] == "2026-10-16"


# ---------------------------------------------------------------------------
# Audit-side validation
# ---------------------------------------------------------------------------


def _payload(**overrides) -> dict:
    payload = ext.build_provider_digest(_frame(), "2026-10-19", SYMBOLS)
    payload.update(overrides)
    return payload


def test_valid_digest_has_no_issues():
    assert audit_mod.digest_issues(_payload(), "2026-10-19", SYMBOLS) == []


@pytest.mark.parametrize(
    ("payload", "needle"),
    [
        (None, "not a JSON object"),
        (_payload(schema_version=2), "schema_version"),
        (_payload(session="2026-10-16"), "session"),
        (_payload(universe=["SPY"]), "universe"),
        (_payload(previous_session="2026-10-19"), "previous_session"),
        (_payload(slice=None), "slice block missing"),
        (_payload(prices=None), "prices block missing"),
    ],
)
def test_digest_issues_reject_structural_corruption(payload, needle):
    issues = audit_mod.digest_issues(payload, "2026-10-19", SYMBOLS)
    assert any(needle in issue for issue in issues)


def test_digest_issues_reject_a_bad_hash():
    payload = _payload()
    payload["slice"] = {**payload["slice"], "sha256": "not-a-hash"}
    assert any("slice.sha256" in i for i in audit_mod.digest_issues(payload, "2026-10-19", SYMBOLS))

    payload["slice"] = {**payload["slice"], "sha256": "A" * 64}
    assert any("slice.sha256" in i for i in audit_mod.digest_issues(payload, "2026-10-19", SYMBOLS))


def test_digest_issues_reject_a_non_positive_close():
    payload = _payload()
    payload["prices"]["QQQ"]["close"] = 0.0
    assert any("QQQ" in i for i in audit_mod.digest_issues(payload, "2026-10-19", SYMBOLS))


def test_digest_issues_reject_symbols_outside_the_universe():
    payload = _payload()
    payload["prices"]["TLT"] = {"previous_close": 100.0, "close": 101.0}
    assert any("outside the universe" in i for i in audit_mod.digest_issues(payload, "2026-10-19", SYMBOLS))


# ---------------------------------------------------------------------------
# attest_unverified / audit integration
# ---------------------------------------------------------------------------


UNVERIFIED = ["2026-10-19"]


def test_attest_marks_a_valid_digest_as_attested(tmp_path):
    payload = ext.build_provider_digest(_frame(), "2026-10-19", SYMBOLS)
    ext.write_provider_digest(payload, tmp_path)
    attested, problems = audit_mod.attest_unverified(UNVERIFIED, tmp_path, SYMBOLS)
    assert attested == UNVERIFIED
    assert problems == {}


def test_attest_ignores_a_missing_digest(tmp_path):
    attested, problems = audit_mod.attest_unverified(UNVERIFIED, tmp_path, SYMBOLS)
    assert attested == []
    assert problems == {}


def test_attest_reports_malformed_and_unreadable_digests(tmp_path):
    path = audit_mod.digest_path(tmp_path, "2026-10-19")
    path.write_text("{ not json")
    attested, problems = audit_mod.attest_unverified(UNVERIFIED, tmp_path, SYMBOLS)
    assert attested == []
    assert "unreadable JSON" in problems[path.name][0]

    path.write_text(json.dumps(_payload(session="2026-10-16")))
    attested, problems = audit_mod.attest_unverified(UNVERIFIED, tmp_path, SYMBOLS)
    assert attested == []
    assert any("session" in i for i in problems[path.name])


def _audit_fixture(tmp_path: Path, digest: dict | None = None):
    dates = list(pd.bdate_range("2026-09-01", periods=20).strftime("%Y-%m-%d"))
    returns = [0.001 * ((i % 5) - 2) for i in range(len(dates))]
    raw = tmp_path / "raw"
    raw.mkdir()
    for sym in SYMBOLS:
        pd.DataFrame(
            {"Close": np.linspace(100.0, 101.0, len(dates) - 1)},
            index=pd.to_datetime(dates[:-1], utc=True),
        ).to_parquet(raw / f"{sym}.parquet")
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({"universe": SYMBOLS}))
    state = tmp_path / "state.yaml"
    state.write_text(
        yaml.safe_dump(
            {
                "cumulative_dates": dates,
                "cumulative_returns": returns,
                "cumulative_pnl": returns,
                "run_history": [{"date": d} for d in dates],
                "last_run_date": dates[-1],
                "rolling_sharpe_63d": float(
                    audit_mod.rolling_sharpe_at(np.asarray(returns))
                ),
            }
        )
    )
    paper = tmp_path / "paper_trading"
    paper.mkdir()
    if digest is not None:
        audit_mod.digest_path(paper, dates[-1]).write_text(json.dumps(digest))
    return state, config, raw, paper, dates


def test_audit_counts_a_valid_digest_as_attested(tmp_path):
    dates = list(pd.bdate_range("2026-09-01", periods=20).strftime("%Y-%m-%d"))
    payload = {
        "schema_version": audit_mod.DIGEST_SCHEMA_VERSION,
        "session": dates[-1],
        "previous_session": dates[-2],
        "universe": SYMBOLS,
        "prices": {
            sym: {"previous_close": 100.0, "close": 101.0} for sym in SYMBOLS
        },
        "slice": {
            "rows": 20,
            "columns": 2,
            "first_session": dates[0],
            "sha256": "0" * 64,
        },
    }
    state, config, raw, paper, _ = _audit_fixture(tmp_path, digest=payload)
    result = audit_mod.audit(state, config, raw, paper_dir=paper)
    assert result["n_unverified"] == 1
    assert result["n_attested"] == 1
    assert result["attested_sessions"] == [dates[-1]]


def test_audit_fails_closed_on_a_malformed_digest(tmp_path):
    bad = {"schema_version": 1, "session": "1999-01-01"}
    state, config, raw, paper, _ = _audit_fixture(tmp_path, digest=bad)
    with pytest.raises(ValueError, match="malformed provider digest"):
        audit_mod.audit(state, config, raw, paper_dir=paper)


# ---------------------------------------------------------------------------
# Extension path: digest written after the single state write, never fatal
# ---------------------------------------------------------------------------


def _extension_state(tmp_path: Path) -> Path:
    path = tmp_path / "state.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "last_run_date": "2026-10-16",
                "current_positions": {"SPY": 0.5},
                "cumulative_returns": [0.001],
                "cumulative_pnl": [100.0],
                "cumulative_dates": ["2026-10-16"],
                "peak_nav": 100000.0,
                "current_nav": 100000.0,
                "max_drawdown": 0.0,
                "drift_flags": {},
                "run_history": [{"date": "2026-10-16", "nav": 100000.0}],
                "previous_regime_exposure": 1.0,
            }
        )
    )
    return path


def _extension_config(tmp_path: Path):
    cfg = ext.PaperTradingConfig.from_paper_config_yaml(
        ROOT / "config" / "paper_trading_config.yaml"
    )
    cfg.report_path = str(tmp_path / "report.md")
    cfg.output_dir = str(tmp_path / "paper_trading")
    # the digest covers exactly the configured universe
    cfg.universe = list(SYMBOLS)
    return cfg


def _stub_extend(monkeypatch):
    def fake_update(config, state, market_data=None):
        latest = pd.Timestamp(market_data.index.max()).strftime("%Y-%m-%d")
        state.last_run_date = latest
        state.cumulative_dates.append(latest)
        state.cumulative_returns.append(0.001)
        state.cumulative_pnl.append(100.0)
        state.current_nav = state.current_nav * 1.001
        state.run_history.append({"date": latest, "nav": state.current_nav})
        return state, {}

    monkeypatch.setattr(ext, "run_daily_paper_update", fake_update)
    monkeypatch.setattr(ext, "generate_paper_report", lambda state, config: "")


def _stub_fetch(frame: pd.DataFrame):
    def fetch(end_date: str) -> pd.DataFrame:
        return frame.loc[frame.index < pd.Timestamp(end_date, tz="UTC")]

    return fetch


def _repo_digest_names() -> set[str]:
    paper = ROOT / "data" / "processed" / "paper_trading"
    return {p.name for p in paper.glob("provider_digest_*.json")}


def test_extension_writes_digest_for_the_extended_session(tmp_path, monkeypatch):
    state_path = _extension_state(tmp_path)
    frame = _frame()
    _stub_extend(monkeypatch)
    now = datetime(2026, 10, 19, 22, 30, tzinfo=UTC)
    repo_before = _repo_digest_names()

    result = ext.run_extension(
        _extension_config(tmp_path),
        state_path,
        now,
        _stub_fetch(frame),
        close_hour=16,
        tz=TZ,
    )

    assert result["sessions_extended"] == 1
    assert result["state_writes"] == 1
    assert result["digest_error"] is None
    digest_file = Path(result["provider_digest"])
    assert digest_file.parent == tmp_path / "paper_trading"
    payload = json.loads(digest_file.read_text())
    assert payload["session"] == "2026-10-19"
    assert payload["prices"]["SPY"]["close"] == 102.0
    assert payload["prices"]["QQQ"]["close"] == 306.0
    # the digest must describe the same slice the update consumed
    assert payload["slice"]["rows"] == len(frame)
    # and the committed data tree must stay clean
    assert _repo_digest_names() == repo_before


def test_digest_failure_never_blocks_the_state_write(tmp_path, monkeypatch):
    state_path = _extension_state(tmp_path)
    frame = _frame()
    _stub_extend(monkeypatch)
    now = datetime(2026, 10, 19, 22, 30, tzinfo=UTC)

    def broken(frame_, target, symbols):
        raise RuntimeError("digest exploded")

    monkeypatch.setattr(ext, "build_provider_digest", broken)
    result = ext.run_extension(
        _extension_config(tmp_path),
        state_path,
        now,
        _stub_fetch(frame),
        close_hour=16,
        tz=TZ,
    )

    assert result["sessions_extended"] == 1
    assert result["state_writes"] == 1
    assert yaml.safe_load(state_path.read_text())["last_run_date"] == "2026-10-19"
    assert result["provider_digest"] is None
    assert "digest exploded" in result["digest_error"]


def test_no_digest_without_a_write(tmp_path, monkeypatch):
    state_path = _extension_state(tmp_path)
    frame = _frame()
    _stub_extend(monkeypatch)
    now = datetime(2026, 10, 19, 22, 30, tzinfo=UTC)

    dry = ext.run_extension(
        _extension_config(tmp_path),
        state_path,
        now,
        _stub_fetch(frame),
        dry_run=True,
        close_hour=16,
        tz=TZ,
    )
    assert dry["sessions_extended"] == 1
    assert dry["state_writes"] == 0
    assert "provider_digest" not in dry

    ext.run_extension(
        _extension_config(tmp_path),
        state_path,
        now,
        _stub_fetch(frame),
        close_hour=16,
        tz=TZ,
    )
    # second invocation: session already processed, nothing to attest
    again = ext.run_extension(
        _extension_config(tmp_path),
        state_path,
        now,
        _stub_fetch(frame),
        close_hour=16,
        tz=TZ,
    )
    assert again["sessions_extended"] == 0
    assert "provider_digest" not in again
    assert sorted(p.name for p in (tmp_path / "paper_trading").glob("*.json")) == [
        "provider_digest_20261019.json"
    ]
