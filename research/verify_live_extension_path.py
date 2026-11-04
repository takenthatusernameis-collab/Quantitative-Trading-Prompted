"""Live-data pre-flight for the 2026-11-04 paper-trading extension.

The canonical clock gate (``extend_paper_trading_state.main``) correctly refuses
to select the 2026-11-04 session while it is still in progress (before 17:00 ET
close + settlement slack), so a real canonical extension cannot run until the
gate releases. This script is NOT a workaround for that gate: it drives the
exact same ``run_extension`` write path with the LIVE provider and a simulated
post-close clock, against a THROWAWAY copy of the state, so the end-to-end path
can be verified with real 2026-11-04 data before the gate releases.

Safety contract:
  * canonical ``data/processed/paper_trading_state.yaml`` is read-only here;
    the extension writes to a temp copy.
  * canonical ``data/raw`` is never written (the fetch uses a scratch dir).
  * on exit the temp state and scratch dir are removed.
"""
from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.extend_paper_trading_state as ext
from src.data.yfinance_fetcher import fetch_universe
from src.simulation.paper_trading import PaperTradingConfig, PaperTradingState

CONFIG_PATH = ROOT / "config" / "paper_trading_config.yaml"
STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"
RAW_DIR = ROOT / "data" / "raw"

# Simulated "now": 2026-11-04 22:00 UTC = 17:00 ET, i.e. the moment the clock
# gate releases and the 2026-11-04 session is complete. This is the gate's own
# completeness rule, applied to a fixed clock, so the path under test is the
# real extension branch, not the no-op branch.
NOW = datetime(2026, 11, 4, 22, 0, tzinfo=UTC)


def main() -> int:
    cfg = PaperTradingConfig.from_paper_config_yaml(CONFIG_PATH)
    with open(CONFIG_PATH) as f:
        raw_cfg = yaml.safe_load(f)
    close_hour = raw_cfg["data_refresh"]["market_close_hour"]
    tz = ZoneInfo(raw_cfg["data_refresh"]["timezone"])

    # 1. Canonical state must be untouched at the end.
    state_before = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()
    raw_before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(RAW_DIR.glob("*.parquet"))
    }

    tmp = Path(tempfile.mkdtemp(prefix="live-ext-verify-"))
    try:
        state_copy = tmp / "state.yaml"
        state_copy.write_text(STATE_PATH.read_text())
        out_dir = tmp / "paper_trading"
        out_dir.mkdir()
        report_path = tmp / "report.md"

        test_cfg = PaperTradingConfig(
            **{
                **cfg.__dict__,
                "output_dir": str(out_dir),
                "report_path": str(report_path),
                "state_path": str(state_copy),
            }
        )

        scratch = tempfile.mkdtemp(prefix="paper-extend-raw-")
        try:

            def fetch(end_date: str):
                raw = fetch_universe(
                    cfg.universe,
                    cfg.history_start,
                    end_date,
                    raw_dir=scratch,
                    force=True,
                    append_only=False,
                )
                return ext.complete_session_view(
                    raw, NOW, close_hour=close_hour, tz=tz
                )

            result = ext.run_extension(
                test_cfg,
                state_copy,
                NOW,
                fetch,
                close_hour=close_hour,
                tz=tz,
            )
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

        print("=== live extension path (simulated post-close clock) ===")
        print(f"target session:        {result['target']}")
        print(f"sessions extended:    {result['sessions_extended']}")
        print(f"state writes:         {result['state_writes']}")
        print(f"NAV before:            {result['nav_before']}")
        print(f"NAV after:             {result['nav_after']}")
        new_state = PaperTradingState.from_yaml(state_copy)
        print(f"last_run_date:         {new_state.last_run_date}")
        print(f"n run_history entries: {len(new_state.run_history)}")
        print(f"drift flags:           {new_state.drift_flags}")

        ok = True
        if result["target"] != "2026-11-04":
            print("FAIL: target != 2026-11-04"); ok = False
        if result["sessions_extended"] != 1:
            print("FAIL: sessions_extended != 1"); ok = False
        if result["state_writes"] != 1:
            print("FAIL: state_writes != 1"); ok = False
        if new_state.last_run_date != "2026-11-04":
            print("FAIL: last_run_date != 2026-11-04"); ok = False
        if not (isinstance(result["nav_after"], float) and result["nav_after"] > 0):
            print("FAIL: nav_after not positive"); ok = False

        # 2. Canonical state and raw cache must be byte-identical.
        state_after = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()
        raw_after = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(RAW_DIR.glob("*.parquet"))
        }
        if state_after != state_before:
            print("FAIL: canonical state mutated"); ok = False
        else:
            print("canonical state:      unchanged")
        if raw_after != raw_before:
            print("FAIL: canonical raw cache mutated"); ok = False
        else:
            print("canonical raw cache: unchanged")

        print("RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())