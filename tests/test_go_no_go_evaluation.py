"""Regression tests for the read-only go/no-go evaluation tool.

Invariants covered:

* the tool runs standalone from the repository root (no ``PYTHONPATH`` help),
* running it never mutates the committed state or the raw cache,
* repeated evaluations of the same state reproduce the same PSR numbers,
  because the Probabilistic Sharpe Ratio bootstrap is seeded.
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.simulation.evaluation import (  # noqa: E402
    DEFAULT_PSR_SEED,
    GoNoGoConfig,
    evaluate_go_no_go,
)
from src.simulation.paper_trading import (  # noqa: E402
    PaperTradingConfig,
    PaperTradingState,
)

SCRIPT = "research/go_no_go_evaluation.py"
STATE = ROOT / "data" / "processed" / "paper_trading_state.yaml"
RAW_DIR = ROOT / "data" / "raw"


def _hashes() -> dict[str, str]:
    paths = [STATE, ROOT / "data" / "processed" / "paper_trading_state.yaml.backup"]
    paths += sorted(RAW_DIR.rglob("*.parquet"))
    out = {}
    for path in paths:
        out[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _run_script() -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run(
        [sys.executable, SCRIPT],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def test_script_runs_standalone_without_pythonpath():
    proc = _run_script()
    assert proc.returncode == 0, proc.stderr
    assert "side_effect_free: True" in proc.stdout
    assert "evaluation_deterministic: True" in proc.stdout
    assert "decision (evaluate_go_no_go):" in proc.stdout


def test_script_is_side_effect_free():
    before = _hashes()
    proc = _run_script()
    assert proc.returncode == 0, proc.stderr
    after = _hashes()
    assert before == after


def test_psr_is_deterministic_for_the_committed_state():
    state = PaperTradingState.from_yaml(STATE)
    config = PaperTradingConfig.from_paper_config_yaml(
        ROOT / "config" / "paper_trading_config.yaml"
    )
    go_no_go_config = GoNoGoConfig(
        min_days=config.go_no_go_min_days,
        target_sharpe=config.go_no_go_target_sharpe,
        max_dd_threshold=config.go_no_go_max_dd_threshold,
    )
    first = evaluate_go_no_go(state, config, go_no_go_config=go_no_go_config)
    second = evaluate_go_no_go(state, config, go_no_go_config=go_no_go_config)
    assert first.psr_normal == second.psr_normal
    assert first.psr_empirical == second.psr_empirical
    assert first.sharpe_se == second.sharpe_se
    assert first.sharpe_ci_lower == second.sharpe_ci_lower
    assert first.sharpe_ci_upper == second.sharpe_ci_upper
    assert first.decision == second.decision
    assert first.decision in {"GO", "NO-GO", "INCONCLUSIVE"}


def test_psr_seed_is_fixed_by_default():
    assert GoNoGoConfig().psr_seed == DEFAULT_PSR_SEED
    assert isinstance(DEFAULT_PSR_SEED, int)
