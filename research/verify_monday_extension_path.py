"""Sandbox verification of the active extension path against the committed cache.

Prior corrective invocations only exercised the criterion-4 no-op path
(gate not released). This script verifies the *active* extension path
(end-to-end: real fetch_universe -> real run_simulation -> single state write)
using a pinned clock and a throwaway state, leaving the canonical state and
data/raw cache untouched.

The target session is chosen from the COMMITTED raw cache at run time, not
hard-coded: the tool reads the max date of the canonical SPY frame and pins
the clock to that session's 22:30 UTC (18:30 ET), so the session is complete
and its bar is guaranteed present. The throwaway state's last_run_date is set
to the prior trading session. This keeps the script correct across cache
extensions (Cycle 1034 pinned it to 2026-10-22, which the cache had since
receded past, so the script asserted a no-op and reported FAIL on a path it
could no longer exercise).

Cycle 1034: the default is now OFFLINE (force=False, cache-backed). The
previous default forced a live yfinance download (force=True), which held an
open TCP connection to the provider and was terminated by the 600 s idle
watchdog (exit 124) before the assertion phase ran. The canonical cache is
the authoritative, committed dataset; exercising the active path against it
is the deterministic, watchdog-safe equivalent. Pass --online to re-enable
the live download.

Cycle 1036: the committed-NAV reproduction check was nested under
``nav_after == nav_before`` (the no-op branch), so on a real one-session
advance -- where nav_after legitimately differs from nav_before -- the
strongest assertion in this script was skipped and RESULT: PASS was emitted
with no NAV verification at all. The check is now unconditional.
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
import pytest
import yaml

# Derive the repository root from this file's location rather than a
# hard-coded absolute path (Cycle 1256). A hard-coded worktree path breaks if
# the repository is ever checked out at a different path.
ROOT = Path(__file__).resolve().parent.parent
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

# 2. Derive the target session from the COMMITTED raw cache at run time.
#    The tool reads the max date of the canonical SPY frame and pins the
#    clock to that session's 22:30 UTC (18:30 ET), so the session is complete
#    and its bar is guaranteed present. The throwaway state's last_run_date is
#    set to the prior trading session. Deriving (not hard-coding) keeps the
#    script correct across cache extensions.
spy_frame = pd.read_parquet(ROOT / "data" / "raw" / "SPY.parquet")
target_date = pd.Timestamp(spy_frame.index.max()).strftime("%Y-%m-%d")
prior_dates = [d for d in spy_frame.index.unique() if pd.Timestamp(d).strftime("%Y-%m-%d") < target_date]
prior_date = pd.Timestamp(prior_dates[-1]).strftime("%Y-%m-%d")
fixed_now = datetime.strptime(target_date, "%Y-%m-%d").replace(
    hour=22, minute=30, tzinfo=UTC
)

# 3. Build a throwaway state whose last_run_date is the session BEFORE the
#    target, so the update is a real one-session advance rather than a replay
#    of hundreds of sessions.
with tempfile.TemporaryDirectory() as tmp:
    tmp_state = Path(tmp) / "state.yaml"
    canonical = PaperTradingState.from_yaml(STATE_PATH)
    committed_nav = next(r["nav"] for r in canonical.run_history if r["date"] == target_date)
    canonical.last_run_date = prior_date
    canonical.cumulative_dates = [d for d in canonical.cumulative_dates if d <= prior_date]
    canonical.cumulative_returns = canonical.cumulative_returns[: len(canonical.cumulative_dates)]
    canonical.cumulative_pnl = canonical.cumulative_pnl[: len(canonical.cumulative_dates)]
    canonical.run_history = [r for r in canonical.run_history if r["date"] <= prior_date]
    # Truncating the history leaves current_nav / peak_nav / max_drawdown
    # holding the COMMITTED (post-target) values, which would make nav_before
    # already include the target session's return and silently mask a write
    # that produces the wrong NAV (Cycle 1035). Recompute all three from the
    # truncated history so the extension is a genuine one-session advance and
    # nav_after can be checked bit-for-bit against the committed value.
    last_hist = canonical.run_history[-1]
    canonical.current_nav = float(last_hist["nav"])
    canonical.peak_nav = max(r["nav"] for r in canonical.run_history)
    canonical.max_drawdown = min(
        (r["nav"] - canonical.peak_nav) / canonical.peak_nav
        for r in canonical.run_history
    )
    canonical.to_yaml(tmp_state)

    state_before_hash = hashlib.sha256(tmp_state.read_bytes()).hexdigest()
    nav_before = canonical.current_nav

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
if result["target"] != target_date:
    print(f"FAIL: target != {target_date}"); ok = False
if result["sessions_extended"] != 1:
    print("FAIL: sessions_extended != 1"); ok = False
if result["state_writes"] != 1:
    print("FAIL: state_writes != 1"); ok = False
# The extension must reproduce the COMMITTED NAV for the target session
# bit-for-bit (mirrors test_real_extension_path.py). A write that produces
# a different NAV is a real-path defect, not a no-op.
#
# Cycle 1036: the committed-NAV reproduction check is unconditional; it runs
# on the real one-session advance path (not only the no-op branch), matching
# the assertion in test_real_extension_path.py.
if result["nav_after"] != pytest.approx(committed_nav, rel=1e-12):
    print(f"FAIL: nav_after {result['nav_after']} != committed {target_date} NAV {committed_nav}")
    ok = False
else:
    print(f"nav_after reproduces committed {target_date} NAV: {committed_nav}")
if written["last_run_date"] != target_date:
    print(f"FAIL: written last_run_date != {target_date}"); ok = False
if state_after_hash == state_before_hash:
    print("FAIL: state file unchanged after extension"); ok = False
if raw_hashes_before != raw_hashes_after:
    print("FAIL: canonical data/raw was modified"); ok = False
if hashlib.sha256(STATE_PATH.read_bytes()).hexdigest() != before_canonical:
    print("FAIL: canonical paper_trading_state.yaml was modified"); ok = False

print(f"target session: {target_date} (prior {prior_date}, pinned clock {fixed_now.isoformat()})")
print("canonical state hash unchanged:", hashlib.sha256(STATE_PATH.read_bytes()).hexdigest() == before_canonical)
print("canonical data/raw unchanged:", raw_hashes_before == raw_hashes_after)
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)