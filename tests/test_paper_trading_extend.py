import sys, os, tempfile, shutil
from pathlib import Path
import pandas as pd
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.extend_paper_trading_state import session_is_complete


def test_session_guard():
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/New_York")
    # completed: now next day
    now = datetime(2026,10,18,12,0,tzinfo=timezone.utc)
    assert session_is_complete("2026-10-17", now) is True
    # open session: same day before close+1
    now2 = datetime(2026,10,17,15,0,tzinfo=timezone.utc)  # 11am ET
    assert session_is_complete("2026-10-17", now2) is False
    # after close+1 same day
    now3 = datetime(2026,10,17,22,0,tzinfo=timezone.utc)  # 6pm ET
    assert session_is_complete("2026-10-17", now3) is True
