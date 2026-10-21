"""Cycle 935 erratum 001: the published Cycle-934/935 records are immutable.

The erratum (`research/experiments/reversal_001_evaluation_erratum_001.md`)
corrects two figures and one imprecise sentence in the **published** records.
It replaces an in-place regeneration: the tools and the records they produced
are left byte-identical to the Cycle-935 commit, and the correction is carried
by the erratum instead.

The tests pin that arrangement:

* the erratum exists and states the published figure and the measured figure
  side by side;
* the published tools and records are byte-identical to the Cycle-935 commit
  (skipped when the git history is not available);
* the measured figures in the erratum still agree with the frozen evaluator's
  own payload, and the verdict is unchanged.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.reversal_001_evaluation import build_payload  # noqa: E402

ERRATUM = (
    REPO_ROOT / "research" / "experiments" / "reversal_001_evaluation_erratum_001.md"
)
CYCLE_COMMIT = "1612851"
PUBLISHED_ARTIFACTS = [
    "research/reversal_001_evaluation.py",
    "research/candidate_shortlist_934.py",
    "research/experiments/reversal_001_evaluation.md",
    "research/reports/reversal_001_evaluation.md",
    "research/experiments/candidate_shortlist_934.md",
    "research/reports/candidate_shortlist_934.md",
]


@pytest.fixture(scope="module")
def payload() -> dict:
    return build_payload()


def _git_show(path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{CYCLE_COMMIT}:{path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def test_the_erratum_exists_and_states_both_figures():
    assert ERRATUM.exists(), "the erratum must exist"
    text = ERRATUM.read_text()
    for published, measured in (
        ("3.5%", "4.2843%"),  # the cost hurdle in the Cycle-934 record
        ("0.383187", "0.752318"),  # the fold-Sharpe dispersion in the README
        ("0.020047", "0.042843"),  # the pre-registered and recomputed hurdles
        ("29", "62.8"),  # the capture/hurdle ratios
    ):
        assert published in text, published
        assert measured in text, measured


def test_the_published_artifacts_are_byte_identical_to_the_cycle_commit():
    for path in PUBLISHED_ARTIFACTS:
        committed = _git_show(path)
        if committed is None:
            pytest.skip(f"git history for {CYCLE_COMMIT} is not available")
        assert (REPO_ROOT / path).read_bytes() == committed, (
            f"{path} was edited in place after commit {CYCLE_COMMIT}; "
            "the correction belongs in the erratum, not in the published record"
        )


def test_the_measured_figures_still_agree_with_the_frozen_evaluator(payload):
    assert payload["corrected_hurdle"] == pytest.approx(0.042843, abs=1e-6)
    assert payload["config"]["capture_fraction_min"] == pytest.approx(0.020047)
    assert payload["capture"]["median"] == pytest.approx(-1.259560, abs=1e-6)
    assert payload["evaluation"]["wf_std_oos_sharpe"] == pytest.approx(
        0.752318, abs=1e-6
    )
    assert payload["evaluation"]["realized_turnover_per_year"] == pytest.approx(
        100.766355, abs=1e-6
    )
    assert payload["evaluation"]["realized_cost_drag_per_year"] == pytest.approx(
        0.03022991, abs=1e-8
    )
    ratio_corrected = abs(
        payload["capture"]["median"] / payload["corrected_hurdle"]
    )
    ratio_preregistered = abs(
        payload["capture"]["median"] / payload["config"]["capture_fraction_min"]
    )
    assert ratio_corrected == pytest.approx(29.4, abs=0.05)
    assert ratio_preregistered == pytest.approx(62.8, abs=0.05)


def test_the_verdict_is_unchanged_by_the_erratum(payload):
    assert payload["verdict"]["fired"] == ["i", "iii", "iv", "vi"]
    assert payload["verdict"]["falsified"] is True
    assert payload["verdict"]["label"].startswith("Rejected/Failed")


def test_the_readme_states_the_measured_figures():
    text = (REPO_ROOT / "README.md").read_text()
    assert "0.752318" in text, "the README must state the measured dispersion"
    assert "std 0.383187" not in text, "the stale dispersion must be gone"
    assert "4.2843%" in text, "the README must state the corrected hurdle"
    assert "reversal_001_evaluation_erratum_001.md" in text, (
        "the README must point at the erratum"
    )
