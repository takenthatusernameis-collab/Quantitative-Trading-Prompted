"""Regression guard for the committed post-gate durable handoff's evidence.

``scripts/post_gate_orchestrator.sh`` tests pin the *generation* logic (which
steps run, which Mode is derived, and that a malformed/empty state fingerprint
fails the cycle). What was NOT pinned is the committed record itself: nothing
stopped a handoff from carrying a ``- **State:**`` line that disagrees with the
real ``data/processed/paper_trading_state.yaml``, or a ``Mode``/``Gate state``/
``Cmds skipped`` that contradicts itself. That prose-only gap is exactly what let
successive sessions rewrite handoff-timestamp churn with no verifiable progress
(the recurring failure this cycle exists to prevent).

These tests read the committed ``CORRECTIVE_HANDOFF_POSTGATE_20261116.md`` and
``data/processed/paper_trading_state.yaml`` directly and assert the durable
record is internally consistent and anchored to the real state. They are
test-only: no production code, threshold, gate, cost model, universe, or
``data/raw`` is touched, and the checks fail closed if the canonical record is
absent (anti-vacuity) so the suite cannot silently pass by reading nothing.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
HANDOFF = REPO_ROOT / "CORRECTIVE_HANDOFF_POSTGATE_20261116.md"
STATE = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"

# Same gate the current cycle targets; kept here so the test states its own
# assumption rather than silently depending on wall-clock layout.
GATE_20261116 = datetime(2026, 11, 16, 22, 0, 0, tzinfo=UTC)
CANONICAL_GATE_EPOCH = int(GATE_20261116.timestamp())
CANONICAL_GATE_HUMAN = GATE_20261116.strftime("%Y-%m-%dT%H:%M:%SZ")

# nav allows an optional leading minus (nav=-?[0-9]+(?:\.[0-9]+)?): current_nav is
# a float and a paper account can legitimately fall below zero after losses. This
# mirrors the fingerprint guard in scripts/post_gate_orchestrator.sh:345
# (nav=-?[0-9]+\.?[0-9]*), which was loosened in inv-228 after a valid negative
# NAV was rejected as "malformed" and failed an otherwise-successful cycle. This
# guard was NOT loosened at the same time, so the two committed guards disagreed:
# the orchestrator would ACCEPT a negative-NAV handoff and then the very next
# gate cycle's consistency check would REJECT it, failing the acceptance
# verification of a handoff the orchestrator itself produced. A negative NAV must
# be accepted here too; a double minus or a non-numeric token must still fail.
_STATE_LINE = re.compile(
    r"(?P<sha>[0-9a-f]{64}) "
    r"last_run=(?P<last_run>\d{4}-\d{2}-\d{2}) "
    r"nav=(?P<nav>-?[0-9]+(?:\.[0-9]+)?) "
    r"runs=(?P<runs>[0-9]+)$"
)


def _handoff_lines() -> list[str]:
    """Return the committed handoff lines, failing closed if it is missing."""
    assert HANDOFF.exists(), (
        f"canonical handoff {HANDOFF} is absent; the gate cycle's durable record "
        "must be present in the repository for this consistency guard to run"
    )
    return HANDOFF.read_text().splitlines()


def _field(lines: list[str], key: str) -> str:
    """Extract the single ``- **{key}:** value`` field's value (without the label)."""
    matches = [ln for ln in lines if ln.startswith(f"- **{key}:**")]
    assert len(matches) == 1, f"expected exactly one '**{key}:**' line, got {len(matches)}"
    return matches[0][len(f"- **{key}:**") :].strip()


def test_state_line_present_and_matches_real_state_file() -> None:
    """The State line's sha256/last_run/nav/runs must match the real state file.

    This is the evidence anchor the acceptance criteria demand: a non-empty
    ``State:`` line whose hash is byte-identical to ``data/processed/paper_trading_state.yaml``
    and whose last_run/NAV/run-count agree with it. A handoff claiming an
    unrelated or empty fingerprint is the exact failure mode this prevents.
    """
    lines = _handoff_lines()
    raw_state = STATE.read_bytes()
    real_sha = hashlib.sha256(raw_state).hexdigest()
    state = yaml.safe_load(raw_state.decode("utf-8"))

    match = _STATE_LINE.match(_field(lines, "State"))
    assert match, (
        "the '- **State:**' line must be a non-empty, well-formed fingerprint "
        "'<sha> last_run=YYYY-MM-DD nav=<float> runs=<int>'; got: "
        f"{_field(lines, 'State')!r}"
    )
    assert match.group("sha") == real_sha, "State line sha256 does not match the real state file"
    assert match.group("last_run") == str(state["last_run_date"]), "State line last_run disagrees with the state file"
    assert float(match.group("nav")) == float(state["current_nav"]), "State line nav disagrees with the state file"
    assert int(match.group("runs")) == len(state.get("run_history") or []), "State line run count disagrees with the state file"


def test_mode_and_gate_state_agree() -> None:
    """Mode and Gate state must not contradict each other (or themselves).

    The recorded defect (corrective inv 182) was a handoff claiming
    ``Mode: full cycle (extend included)`` while its own ``Gate state`` line said
    ``NOT released ... mutating extend withheld``. Assert the two lines agree:
    a released gate implies full mode and no withheld extend; an unreleased gate
    implies a pre-gate/read-only mode and a withheld extend.
    """
    lines = _handoff_lines()
    mode = _field(lines, "Mode")
    gate_state = _field(lines, "Gate state")

    if gate_state.startswith("released"):
        assert "full cycle (extend included)" in mode, f"released gate but Mode is {mode!r}"
        assert "withheld" not in gate_state, gate_state
    elif gate_state.startswith("NOT released"):
        assert mode in (
            "pre-gate verification (extend withheld — gate not released)",
            "read-only verification",
        ), f"unreleased gate but Mode is {mode!r}"
        assert "mutating extend withheld" in gate_state, gate_state
    else:
        pytest.fail(f"unrecognized 'Gate state' value: {gate_state!r}")


def test_cmds_skipped_is_truthful_for_mode() -> None:
    """``Cmds skipped`` must list the withheld extend iff the gate is unreleased.

    A handoff that ran the mutating extend but listed it as skipped (or vice
    versa) misrepresents the cycle to the next session. Tie the skip list to the
    gate state: unreleased => the extend (cmd2) and its idempotent re-run (cmd4)
    are withheld; released => nothing is skipped.
    """
    lines = _handoff_lines()
    gate_state = _field(lines, "Gate state")
    skipped = _field(lines, "Cmds skipped")

    if gate_state.startswith("NOT released"):
        assert "2 extend (gate not released)" in skipped, skipped
        assert "4 idempotent re-extend (gate not released)" in skipped, skipped
    elif gate_state.startswith("released"):
        assert skipped == "none", f"released gate must skip nothing, got {skipped!r}"
    else:
        pytest.fail(f"unrecognized 'Gate state' value: {gate_state!r}")


def test_status_ok_for_pre_gate_verification() -> None:
    """Before the gate the handoff must be Status OK with the gate withheld.

    This is the current on-disk state (a pre-gate verification run). It pins the
    happy-path record so a future session cannot regress it into a FAILED or
    extend-included record while the clock gate is still un-released. It is
    guarded by the wall clock: once the gate is reached the canonical record is
    expected to become a full-cycle record and this assertion is skipped, not
    failed, so it does not block the real post-gate cycle.
    """
    if datetime.now(UTC) >= GATE_20261116:
        pytest.skip("gate released: the committed handoff is expected to be a full-cycle record")
    lines = _handoff_lines()
    assert _field(lines, "Status").startswith("OK"), _field(lines, "Status")
    assert _field(lines, "Mode") == "pre-gate verification (extend withheld — gate not released)"
    assert _field(lines, "Gate state").startswith("NOT released")


# Read-only verification steps the orchestrator always runs (cmds 1,3,5,6,7,8,9).
# Kept as an explicit tuple so the truthfulness guard fails closed if a step
# silently disappears from ``Cmds run`` rather than only checking the extend.
_VERIFY_TOKENS = (
    "1 date",
    "3 drift",
    "5 6-module pytest",
    "6 git status",
    "7 data-cost inventory + tests",
    "8 ruff",
    "9 state fingerprint",
)


def _assert_cmds_run_truthful(cmds_run: str, gate_state: str) -> None:
    """Assert ``Cmds run`` matches what the clock gate actually allows.

    The recorded defect class (corrective inv 182) is a durable record that
    contradicts itself: ``Mode``/``Gate state`` said the extend was withheld while
    ``Cmds run``/``Cmds skipped`` disagreed. The existing guards pin ``Cmds
    skipped`` but never ``Cmds run`` -- so a handoff could falsely claim
    ``2 extend``/``4 idempotent re-extend`` ran while its own ``Gate state`` said
    ``NOT released``. Assert the read-only steps are always recorded and the
    mutating extend appears iff the gate is released.
    """
    for token in _VERIFY_TOKENS:
        assert token in cmds_run, (
            f"'Cmds run' is missing the read-only verification step {token!r}: {cmds_run!r}"
        )
    if gate_state.startswith("NOT released"):
        assert "2 extend" not in cmds_run, (
            f"unreleased gate but 'Cmds run' claims the extend ran: {cmds_run!r}"
        )
        assert "4 idempotent" not in cmds_run, (
            f"unreleased gate but 'Cmds run' claims the re-extend ran: {cmds_run!r}"
        )
    elif gate_state.startswith("released"):
        assert "2 extend" in cmds_run, f"released gate but 'Cmds run' omits the extend: {cmds_run!r}"
        assert "4 idempotent" in cmds_run, (
            f"released gate but 'Cmds run' omits the re-extend: {cmds_run!r}"
        )
    else:
        pytest.fail(f"unrecognized 'Gate state' value: {gate_state!r}")


def test_gate_epoch_matches_canonical_gate() -> None:
    """The handoff must name the gate it was produced for, not a stale one.

    ``scripts/post_gate_orchestrator.sh`` writes ``Gate epoch: <epoch> (<human>)``
    derived from ``GATE_EPOCH``. A stale or malformed epoch would misattribute the
    record to the wrong gate (e.g. the 2026-11-12 default) and mislead the
    gate-active run. Pin both the integer epoch and the human timestamp.
    """
    raw = _field(_handoff_lines(), "Gate epoch")
    match = re.match(r"(?P<epoch>[0-9]+)\s+\((?P<human>[^)]+)\)$", raw)
    assert match, f"malformed 'Gate epoch' line: {raw!r}"
    assert int(match.group("epoch")) == CANONICAL_GATE_EPOCH, raw
    assert match.group("human") == CANONICAL_GATE_HUMAN, raw


def test_cmds_run_is_truthful_for_gate_state() -> None:
    """``Cmds run`` must record what actually ran for the current gate state."""
    lines = _handoff_lines()
    _assert_cmds_run_truthful(_field(lines, "Cmds run"), _field(lines, "Gate state"))


def test_false_extend_claim_is_rejected_when_gate_unreleased() -> None:
    """Anti-vacuity: a handoff claiming the extend ran before the gate must fail.

    This is the exact self-contradiction class of corrective inv 182: ``Gate
    state`` says the extend was withheld while ``Cmds run`` claims it ran. The
    guard must reject it so the committed consistency check cannot pass on a
    record that misrepresents the cycle.
    """
    false_claim = (
        "1 date, 2 extend, 3 drift, 4 idempotent re-extend, 5 6-module pytest, "
        "6 git status, 7 data-cost inventory + tests, 8 ruff, 9 state fingerprint"
    )
    with pytest.raises(AssertionError):
        _assert_cmds_run_truthful(false_claim, "NOT released — pre-gate verification run only")


def _make_handoff_with_nav(nav: str, tmp_path: Path) -> Path:
    """Build a throwaway handoff copy whose State line carries ``nav``."""
    text = HANDOFF.read_text()
    state_line = f"{'a' * 64} last_run=2026-11-13 nav={nav} runs=469"
    out = tmp_path / "probe_handoff.md"
    out.write_text(re.sub(r"- \*\*State:\*\*.*$", f"- **State:** {state_line}", text, flags=re.MULTILINE))
    return out


def test_negative_float_nav_handoff_is_consistent(tmp_path: Path) -> None:
    """A negative float NAV must pass the committed consistency guard.

    Mirrors test_negative_nav_fingerprint_is_not_malformed in the orchestrator
    suite: current_nav is a float and a paper account can legitimately fall
    below zero. The guard must accept it so a real post-gate cycle whose NAV has
    gone negative does not fail its own committed consistency check.
    """
    out = _make_handoff_with_nav("-1234.56", tmp_path)
    lines = out.read_text().splitlines()
    match = _STATE_LINE.match(_field(lines, "State"))
    assert match, f"negative float NAV rejected by the consistency guard: {_field(lines, 'State')!r}"
    assert match.group("nav") == "-1234.56"


def test_negative_integer_nav_handoff_is_consistent(tmp_path: Path) -> None:
    """A negative integer NAV must pass the committed consistency guard."""
    out = _make_handoff_with_nav("-500", tmp_path)
    lines = out.read_text().splitlines()
    match = _STATE_LINE.match(_field(lines, "State"))
    assert match, f"negative integer NAV rejected by the consistency guard: {_field(lines, 'State')!r}"
    assert match.group("nav") == "-500"


def test_double_minus_nav_handoff_is_rejected(tmp_path: Path) -> None:
    """Anti-vacuity: `--123.45` is not a valid number and must still fail."""
    out = _make_handoff_with_nav("--123.45", tmp_path)
    lines = out.read_text().splitlines()
    assert _STATE_LINE.match(_field(lines, "State")) is None, (
        f"double-minus NAV wrongly accepted: {_field(lines, 'State')!r}"
    )


def test_non_numeric_nav_handoff_is_rejected(tmp_path: Path) -> None:
    """The loosened nav pattern must not accept a non-numeric token."""
    out = _make_handoff_with_nav("-abc", tmp_path)
    lines = out.read_text().splitlines()
    assert _STATE_LINE.match(_field(lines, "State")) is None, (
        f"non-numeric NAV wrongly accepted: {_field(lines, 'State')!r}"
    )