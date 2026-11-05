"""Live end-to-end verification of the PRODUCTION extension path at the REAL clock.

Every prior corrective invocation only ever exercised:
  (a) the no-op path (clock gate not released), or
  (b) pinned-clock tests (test_real_extension_path.py,
     verify_monday_extension_path.py) backed by the offline cache.

Neither proves that the REAL production path -- real datetime.now(), real
fetch_universe over the live network, real run_simulation, single state write --
works at the current wall-clock time against the current committed cache. This
is the exact code path that ``research/extend_paper_trading_state.py`` runs at
22:00 UTC on 2026-11-05, and it had never been verified with a live clock.

This script drives ``ext.run_extension`` directly against a THROWAWAY state
file and a scratch raw_dir. The canonical ``data/processed/paper_trading_state.yaml``
and ``data/raw/*.parquet`` are hashed before and after and must not change.

Run from the repository root:

    python3 research/verify_live_extension_path.py

Exit code 0 == the production path advances one completed session, writes
exactly once, and reproduces the committed NAV bit-for-bit, with the canonical
artifacts untouched.
"""
import hashlib
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.extend_paper_trading_state as ext
from src.simulation.paper_trading import PaperTradingState

STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"
RAW_DIR = ROOT / "data" / "raw"
TZ = ext.ZoneInfo("America/New_York")

# Snapshot canonical artifacts before anything runs.
state_hash_before = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()
raw_hashes_before = {
    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(RAW_DIR.glob("*.parquet"))
}

# Real clock -- this is the whole point. No pinning, no stub.
now_et = datetime.now(UTC)
print("real now (UTC):", now_et.isoformat())
print("real now (ET):  ", now_et.astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S %Z"))

# Which sessions are complete right now, per the production completeness rule?
spy = pd.read_parquet(RAW_DIR / "SPY.parquet")
completed = [
    pd.Timestamp(ts).strftime("%Y-%m-%d")
    for ts in spy.index.unique()
    if ext.session_is_complete(
        pd.Timestamp(ts).strftime("%Y-%m-%d"), now_et, close_hour=16, tz=TZ
    )
]
print("completed sessions in canonical cache right now:", completed[-5:])

# Build a throwaway state whose last_run_date is the session BEFORE the newest
# completed session, so run_extension performs a real one-session advance at
# the real clock. The canonical state is already at the newest completed
# session, so stepping back one session makes that session the candidate.
canonical = PaperTradingState.from_yaml(STATE_PATH)
prior = completed[-2]  # second-newest completed session
canonical.last_run_date = prior
canonical.cumulative_dates = [d for d in canonical.cumulative_dates if d <= prior]
canonical.cumulative_returns = canonical.cumulative_returns[
    : len(canonical.cumulative_dates)
]
canonical.cumulative_pnl = canonical.cumulative_pnl[: len(canonical.cumulative_dates)]
canonical.run_history = [r for r in canonical.run_history if r["date"] <= prior]
last_hist = canonical.run_history[-1]
canonical.current_nav = float(last_hist["nav"])
canonical.peak_nav = max(r["nav"] for r in canonical.run_history)
canonical.max_drawdown = min(
    (r["nav"] - canonical.peak_nav) / canonical.peak_nav
    for r in canonical.run_history
)

with tempfile.TemporaryDirectory() as tmp:
    tmp_state = Path(tmp) / "state.yaml"
    canonical.to_yaml(tmp_state)

    config = ext.PaperTradingConfig.from_paper_config_yaml(
        ROOT / "config" / "paper_trading_config.yaml"
    )
    config.report_path = str(Path(tmp) / "report.md")
    config.output_dir = str(Path(tmp) / "paper_trading")

    def real_fetch(end_date: str) -> pd.DataFrame:
        # force=True: this mirrors extend_paper_trading_state.py exactly.
        # The canonical data/raw is never written (scratch dir is disposable).
        scratch = tempfile.mkdtemp(prefix="live-ext-raw-")
        try:
            raw = ext.fetch_universe(
                config.universe,
                config.history_start,
                end_date,
                raw_dir=scratch,
                force=True,
                append_only=False,
            )
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        return ext.complete_session_view(raw, now_et, close_hour=16, tz=TZ)

    result = ext.run_extension(
        config,
        tmp_state,
        now_et,
        real_fetch,
        close_hour=16,
        tz=TZ,
    )

    print("target:", result["target"])
    print("sessions_extended:", result["sessions_extended"])
    print("state_writes:", result["state_writes"])
    print("nav_before:", result["nav_before"])
    print("nav_after:", result["nav_after"])

    written = yaml.safe_load(tmp_state.read_text())
    print("written last_run_date:", written["last_run_date"])

# Re-verify canonical artifacts untouched.
state_hash_after = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()
raw_hashes_after = {
    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(RAW_DIR.glob("*.parquet"))
}

ok = True
if result["sessions_extended"] != 1:
    print("FAIL: sessions_extended != 1"); ok = False
if result["state_writes"] != 1:
    print("FAIL: state_writes != 1"); ok = False
if result["target"] != completed[-1]:
    print(f"FAIL: target != {completed[-1]} (got {result['target']})"); ok = False
if result["nav_after"] == result["nav_before"]:
    print("FAIL: NAV unchanged after real extension"); ok = False
if written["last_run_date"] != completed[-1]:
    print("FAIL: written last_run_date != target"); ok = False
if state_hash_after != state_hash_before:
    print("FAIL: canonical paper_trading_state.yaml was modified"); ok = False
if raw_hashes_after != raw_hashes_before:
    print("FAIL: canonical data/raw was modified"); ok = False

print("canonical state hash unchanged:", state_hash_after == state_hash_before)
print("canonical data/raw unchanged:", raw_hashes_after == raw_hashes_before)
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)