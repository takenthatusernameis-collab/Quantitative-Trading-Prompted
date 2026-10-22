"""Tests for Cycle 944 cryptofunding_001 evaluation."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import research.cryptofunding_001_evaluation as ev


def test_frozen_config_loads():
    config = ev.load_frozen_config()
    assert config["candidate_id"] == "cryptofunding_001"
    assert config["universe"] == ["BTCUSDT", "ETHUSDT"]


def test_evaluation_runs():
    payload = ev.build_payload()
    assert payload["data_unchanged"] is True
    assert payload["config_unchanged"] is True
