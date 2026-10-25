"""Sandbox verification of the Monday extension path with the REAL provider.

Prior corrective invocations only exercised the criterion-4 no-op path
(gate not released). This script verifies the *active* extension path
(end-to-end: real fetch_universe -> real run_simulation -> single state write)
using a pinned clock and a throwaway state, leaving the canonical state and
data/raw cache untouched.

Target: last_run_date 2026-10-21, pinned clock 2026-10-22 18:30 ET.
The 2026-10-22 session is complete at that time and present in the canonical
raw cache, so no network call is needed for a deterministic result.

Cycle 1034: the default is now OFFLINE (force=False, cache-backed). The
previous default forced a live yfinance download (force=True), which held an
open TCP connection to the provider and was terminated by the 600 s idle
watchdog (exit 124) before the assertion phase ran. The canonical cache is
the authoritative, committed dataset; exercising the active path against it
is the deterministic, watchdog-safe equivalent. Pass --online to re-enable
the live download.
"""
import argparse
import hashlib
import shutil
import sys
import tempfile
from datetime import UTC, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

ROOT = Path("/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted")
sys.path.insert(0, str(ROOT))

import research.extend_paper_trading_state as ext
from src.simulation import paper_trading as pt
from src.simulation.paper_trading import PaperTradingState

TZ = ZoneInfo("America/New_York")
STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"
CANONICAL_HASH = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()

parser = argparse.ArgumentParser()
parser.add_argument("--online", action="store_true",
                    help="force a live yfinance download (force=True); "
                         "default is cache-backed offline (force=False)")
ARGS = parser.parse_args()
FORCE = ARGS.online

# 1. Snapshot canonical state hash (must not change).
before_canonical = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()

# 2. Build a throwaway state whose last_run_date is 2026-10-21 (cache has 10-22).
with tempfile.TemporaryDirectory() as tmp:
    tmp_state = Path(tmp) / "state.yaml"
    canonical = PaperTradingState.from_yaml(STATE_PATH)
    canonical.last_run_date = "2026-10-21"
    # Truncate history to match the new last_run_date so the update is a real
    # one-session advance rather than a replay of hundreds of sessions.
    canonical.cumulative_dates = [d for d in canonical.cumulative_dates if d <= "2026-10-21"]
    canonical.cumulative_returns = canonical.cumulative_returns[: len(canonical.cumulative_dates)]
    canonical.cumulative_pnl = canonical.cumulative_pnl[: len(canonical.cumulative_dates)]
    canonical.run_history = [r for r in canonical.run_history if r["date"] <= "2026-10-21"]
    canonical.to_yaml(tmp_state)

    state_before_hash = hashlib.sha256(tmp_state.read_bytes()).hexdigest()
    nav_before = canonical.current_nav

    # 3. Pin the clock to 2026-10-22 18:30 ET -> the 10-22 session is complete.
    fixed_now = datetime(2026, 10, 22, 22, 30, tzinfo=UTC)

    class _StubClock:
        timezone = timezone

        @staticmethod
        def now(tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    # Patch both modules that consult datetime.now().
    ext.datetime = _StubClock
    pt.datetime = _StubClock

    config = ext.PaperTradingConfig.from_paper_config_yaml(
        ROOT / "config" / "paper_trading_config.yaml"
    )
    config.report_path = str(Path(tmp) / "report.md")
    config.output_dir = str(Path(tmp) / "paper_trading")

    # 4. Real fetch_universe into a scratch dir (canonical data/raw untouched).
    raw_hashes_before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "data" / "raw").glob("*.parquet"))
    }

    def real_fetch(end_date: str) -> pd.DataFrame:
        # Seed the scratch dir with byte-identical copies of the canonical
        # cache so fetch_universe(force=False) resolves from the offline
        # cache instead of opening a live yfinance connection. The canonical
        # data/raw is never written by this tool (Cycle 854).
        scratch = tempfile.mkdtemp(prefix="verify-raw-")
        canonical_raw = ROOT / "data" / "raw"
        for parquet in sorted(canonical_raw.glob("*.parquet")):
            shutil.copy2(parquet, Path(scratch) / parquet.name)
        raw = ext.fetch_universe(
            config.universe,
            config.history_start,
            end_date,
            raw_dir=scratch,
            force=FORCE,
        )
        shutil.rmtree(scratch, ignore_errors=True)
        return ext.complete_session_view(raw, fixed_now, close_hour=16, tz=TZ)

    # 5. Run the real extension path.
    result = ext.run_extension(
        config,
        tmp_state,
        fixed_now,
        real_fetch,
        close_hour=16,
        tz=TZ,
    )

    print("target:", result["target"])
    print("sessions_extended:", result["sessions_extended"])
    print("state_writes:", result["state_writes"])
    print("nav_before:", result["nav_before"])
    print("nav_after:", result["nav_after"])

    state_after_hash = hashlib.sha256(tmp_state.read_bytes()).hexdigest()
    written = yaml.safe_load(tmp_state.read_text())

    raw_hashes_after = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "data" / "raw").glob("*.parquet"))
    }

# 6. Assertions.
ok = True
if result["target"] != "2026-10-22":
    print("FAIL: target != 2026-10-22"); ok = False
if result["sessions_extended"] != 1:
    print("FAIL: sessions_extended != 1"); ok = False
if result["state_writes"] != 1:
    print("FAIL: state_writes != 1"); ok = False
if result["nav_after"] == result["nav_before"]:
    print("FAIL: NAV unchanged"); ok = False
if written["last_run_date"] != "2026-10-22":
    print("FAIL: written last_run_date != 2026-10-22"); ok = False
if state_after_hash == state_before_hash:
    print("FAIL: state file unchanged after extension"); ok = False
if raw_hashes_before != raw_hashes_after:
    print("FAIL: canonical data/raw was modified"); ok = False
if hashlib.sha256(STATE_PATH.read_bytes()).hexdigest() != before_canonical:
    print("FAIL: canonical paper_trading_state.yaml was modified"); ok = False

print("canonical state hash unchanged:", hashlib.sha256(STATE_PATH.read_bytes()).hexdigest() == before_canonical)
print("canonical data/raw unchanged:", raw_hashes_before == raw_hashes_after)
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)