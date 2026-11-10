"""Gate-time extension path test with a synthetic 2026-11-09 forward bar.

Materially different from inv339's verify_monday_extension_path.py: that
script exercises the extension against the COMMITTED cache's own max date
(2026-11-05), which is a backward replay. This script instead simulates the
exact gate-release scenario the 22:00 UTC 2026-11-09 run will face:

  * clock pinned at 22:00 UTC on the target session's own date (gate-release
    boundary for that session, resolved from the committed state)
  * canonical state last_run_date read from the committed state (advanced
    2026-11-06 -> 2026-11-09 in the post-gate run)
  * a synthetic forward bar appended to scratch copies of the committed
    raw cache, so the active write path is exercised against a FORWARD bar
    that the live fetch would return once the target session closes

The canonical state and data/raw are never modified: the synthetic frame is
built in-memory from scratch copies and the canonical state is backed up and
restored around the single write. The report and per-day artifact outputs are
also sandboxed (Cycle 1170): generate_paper_report writes config.output_dir and
config.report_path, and those default to the tracked data/ tree and
research/reports/, so a config copy with both fields redirected to a temp dir
is loaded for this run. Verified by comparing the tracked report's SHA256
before and after.

Exit 0 on PASS, 1 on FAIL.
"""
import hashlib
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

ROOT = Path("/home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted")
sys.path.insert(0, str(ROOT))

import research.extend_paper_trading_state as ext
from src.simulation.paper_trading import PaperTradingConfig, PaperTradingState

STATE_PATH = ROOT / "data" / "processed" / "paper_trading_state.yaml"
REPORT_PATH = ROOT / "research" / "reports" / "paper_trading_rolling.md"
TZ = ZoneInfo("America/New_York")
# Target date is derived from the committed state's next trading session, not
# hard-coded. The state advanced 2026-11-06 -> 2026-11-09 in the post-gate
# run, so a fixed 2026-11-09 target made this script FAIL even though the
# forward extension path itself was correct (Cycle 1186).
TARGET_DATE = None  # resolved from state.last_run_date at runtime
FIXED_NOW = datetime(2026, 11, 9, 22, 0, 0, tzinfo=UTC)


def build_synthetic_frame() -> pd.DataFrame:
    """Build a MultiIndex (field x symbol) frame from committed raw cache,
    with a synthetic 2026-11-09 bar appended."""
    frames = {}
    for p in sorted((ROOT / "data" / "raw").glob("*.parquet")):
        sym = Path(p).stem
        if sym == "^VIX":
            continue
        df = pd.read_parquet(p)
        frames[sym] = df
    parts = []
    for field in ("Open", "High", "Low", "Close", "Volume"):
        parts.append(
            pd.concat(
                {s: df[field] for s, df in frames.items()},
                axis=1,
                sort=False,
            )
        )
    synth = pd.concat(parts, axis=1, keys=("Open", "High", "Low", "Close", "Volume"))
    synth = synth.sort_index()
    # Append synthetic forward bar (up 0.5% from last close) for the resolved
    # target session, so the synthetic frame always exercises the extension
    # against the session the live run would target next.
    new_row = synth.iloc[-1:].copy()
    new_row.index = pd.DatetimeIndex([pd.Timestamp(TARGET_DATE + " 00:00:00+00:00")])
    new_row = new_row * 1.005
    return pd.concat([synth, new_row])


def sandboxed_config() -> PaperTradingConfig:
    """Load the paper config with output_dir/report_path redirected to a
    temp dir, so the write path under test never touches the tracked data/
    or research/reports/ trees."""
    cfg_path = ROOT / "config" / "paper_trading_config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f) or {}
    tmp = Path(tempfile.mkdtemp(prefix="paper-gate-sandbox-"))
    cfg["output_dir"] = str(tmp / "paper_trading")
    cfg["report_path"] = str(tmp / "report.md")
    cfg_path_local = tmp / "paper_trading_config.yaml"
    with open(cfg_path_local, "w") as f:
        yaml.safe_dump(cfg, f)
    return PaperTradingConfig.from_paper_config_yaml(cfg_path_local), tmp


def main() -> int:
    before_canonical = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()
    before_report = hashlib.sha256(REPORT_PATH.read_bytes()).hexdigest()
    state = PaperTradingState.from_yaml(STATE_PATH)
    print("state last_run_date:", state.last_run_date, "NAV:", state.current_nav)

    # Resolve the target forward session from the committed state so the
    # synthetic bar always targets the session the live run would extend
    # into next. The pinned clock is set to 22:00 UTC on the target session's
    # own date (gate-release boundary for that session).
    global TARGET_DATE, FIXED_NOW
    last = pd.Timestamp(state.last_run_date)
    target = ext.next_trading_session(last, tz=TZ)
    TARGET_DATE = target.strftime("%Y-%m-%d")
    FIXED_NOW = datetime(target.year, target.month, target.day, 22, 0, 0, tzinfo=UTC)
    print("target session:", TARGET_DATE)
    print("pinned clock:", FIXED_NOW.isoformat(), "ET:", FIXED_NOW.astimezone(TZ))

    synth = build_synthetic_frame()
    print("synthetic shape:", synth.shape, "max date:", synth.index.max())

    config, tmp = sandboxed_config()
    print("sandbox output_dir:", config.output_dir)
    print("sandbox report_path:", config.report_path)

    def synth_fetch(end_date: str) -> pd.DataFrame:
        return ext.complete_session_view(synth, FIXED_NOW, close_hour=16, tz=TZ)

    backup = Path(str(STATE_PATH) + ".gatebak")
    shutil.copy2(STATE_PATH, backup)
    ok = True
    try:
        result = ext.run_extension(
            config, STATE_PATH, FIXED_NOW, synth_fetch, close_hour=16, tz=TZ
        )
        print("RESULT:", result)
        print("target:", result["target"])
        print("sessions_extended:", result["sessions_extended"])
        print("state_writes:", result["state_writes"])
        print("nav_before:", result["nav_before"])
        print("nav_after:", result["nav_after"])
        new_state = PaperTradingState.from_yaml(STATE_PATH)
        print("new last_run_date:", new_state.last_run_date, "NAV:", new_state.current_nav)

        if result["target"] != TARGET_DATE:
            print(f"FAIL: target != {TARGET_DATE}"); ok = False
        if result["sessions_extended"] != 1:
            print("FAIL: sessions_extended != 1"); ok = False
        if result["state_writes"] != 1:
            print("FAIL: state_writes != 1"); ok = False
        if result["nav_after"] == result["nav_before"]:
            print("FAIL: NAV unchanged"); ok = False
        if new_state.last_run_date != TARGET_DATE:
            print(f"FAIL: written last_run_date != {TARGET_DATE}"); ok = False
    finally:
        shutil.copy2(backup, STATE_PATH)
        backup.unlink(missing_ok=True)
        shutil.rmtree(tmp, ignore_errors=True)

    after_canonical = hashlib.sha256(STATE_PATH.read_bytes()).hexdigest()
    after_report = hashlib.sha256(REPORT_PATH.read_bytes()).hexdigest()
    if after_canonical != before_canonical:
        print("FAIL: canonical state hash changed"); ok = False
    else:
        print("canonical state hash unchanged:", True)
    if after_report != before_report:
        print("FAIL: tracked report hash changed"); ok = False
    else:
        print("tracked report hash unchanged:", True)

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())