"""Regression guard for the committed post-gate durable handoff's evidence.

``scripts/post_gate_orchestrator.sh`` tests pin the *generation* logic (which
steps run, which Mode is derived, and that a malformed/empty state fingerprint
fails the cycle). What was NOT pinned is the committed record itself: nothing
stopped a handoff from carrying a ``- **State:**`` line that disagrees with the
real ``data/processed/paper_trading_state.yaml``, or a ``Mode``/``Gate state``/
``Cmds skipped`` that contradicts itself. That prose-only gap is exactly what let
successive sessions rewrite handoff-timestamp churn with no verifiable progress
(the recurring failure this cycle exists to prevent).

These tests read the most recent committed post-gate durable handoff
(``CORRECTIVE_HANDOFF_POSTGATE_<YYYYMMDD>.md`` with the greatest gate date) and
``data/processed/paper_trading_state.yaml`` directly and assert the durable
record is internally consistent and anchored to the real state. They are
test-only: no production code, threshold, gate, cost model, universe, or
``data/raw`` is touched, and the checks fail closed if the canonical record is
absent (anti-vacuity) so the suite cannot silently pass by reading nothing.

Forward-compatibility (this guard's own correction): the suite previously
hard-pinned ``CORRECTIVE_HANDOFF_POSTGATE_20261116.md`` and asserted its
``State:`` line equalled the *live* state file. That is only true while the
state is still the one that handoff recorded (470 / 2026-11-16). The imminent
2026-11-17T22:00:00Z cycle appends a session (state -> 471 / 2026-11-17, new
sha256) and writes ``CORRECTIVE_HANDOFF_POSTGATE_20261117.md``; the pinned
20261116 record's ``State:`` line would then disagree with the live state and
``test_state_line_present_and_matches_real_state_file`` would FAIL on the very
cycle it exists to guard. The record to verify is therefore selected
dynamically as the newest gate handoff, and the canonical gate epoch is derived
from that handoff's own filename date (22:00 UTC), so the guard tracks the
current cycle without a wall-clock-pinned constant or a hard-coded past date.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE = REPO_ROOT / "data" / "processed" / "paper_trading_state.yaml"

# Gate handoffs are written as CORRECTIVE_HANDOFF_POSTGATE_<YYYYMMDD>.md where
# the date is the gate's UTC date. A pre-gate backup file
# (..._20261113_pregate_backup.md) does NOT match this anchored pattern, so it is
# correctly excluded from selection.
_POSTGATE_RE = re.compile(r"^CORRECTIVE_HANDOFF_POSTGATE_(\d{8})\.md$")


def _select_handoff() -> Path:
    """Return the newest committed post-gate handoff (greatest gate date).

    The "current" durable record is the one for the most recent gate cycle that
    has run. Selecting by the greatest ``YYYYMMDD`` in the filename makes the
    guard forward-compatible: before the 2026-11-17 cycle it selects
    ``..._20261116.md`` (whose State line matches the live 470 / 2026-11-16
    state); after that cycle it selects ``..._20261117.md`` (matching the new
    471 / 2026-11-17 state) instead of failing against the stale pinned record.

    Fails closed (anti-vacuity) if no gate handoff is present, so the suite
    cannot silently pass by validating nothing.
    """
    candidates: list[tuple[int, Path]] = []
    for path in REPO_ROOT.glob("CORRECTIVE_HANDOFF_POSTGATE_*.md"):
        match = _POSTGATE_RE.match(path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    assert candidates, (
        "no CORRECTIVE_HANDOFF_POSTGATE_<YYYYMMDD>.md record is present; the "
        "gate cycle's durable record must be committed for this guard to run"
    )
    return max(candidates, key=lambda item: item[0])[1]


def _handoff_gate_dt(path: Path) -> datetime:
    """Derive the gate's UTC datetime (22:00 on the filename date) from ``path``."""
    match = _POSTGATE_RE.match(path.name)
    assert match, f"handoff name is not a gate record: {path.name!r}"
    return datetime.strptime(match.group(1), "%Y%m%d").replace(hour=22, tzinfo=UTC)


HANDOFF = _select_handoff()
HANDOFF_GATE = _handoff_gate_dt(HANDOFF)
CANONICAL_GATE_EPOCH = int(HANDOFF_GATE.timestamp())
CANONICAL_GATE_HUMAN = HANDOFF_GATE.strftime("%Y-%m-%dT%H:%M:%SZ")

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


def _is_pre_gate_record(lines: list[str]) -> bool:
    """True iff ``lines`` describe a pre-gate (extend-withheld) verification run.

    The gate-state line is the authoritative record of which side of the clock
    gate produced the handoff (see ``scripts/post_gate_orchestrator.sh``: a
    pre-gate run writes ``Gate state: NOT released ...``). This helper lets the
    happy-path test decide from the *committed record* -- not the wall clock --
    whether the record it is validating is a pre-gate one.
    """
    return _field(lines, "Gate state").startswith("NOT released")


def _assert_pre_gate_record_ok(lines: list[str]) -> None:
    """Assert a pre-gate verification handoff is Status OK and honestly withheld.

    A pre-gate record must report ``Status: OK`` (verification passed) AND, if it
    claims the gate is unreleased, must label its Mode as the pre-gate
    (extend-withheld) verification mode. This is the happy-path contract the
    wall-clock-anchored version only checked opportunistically.
    """
    assert _field(lines, "Status").startswith("OK"), _field(lines, "Status")
    assert _field(lines, "Mode") == "pre-gate verification (extend withheld — gate not released)"


def test_status_ok_for_pre_gate_verification() -> None:
    """A committed pre-gate handoff must be Status OK with the extend withheld.

    This guard is **record-anchored**, not wall-clock-anchored. It inspects the
    newest committed gate handoff and, *iff that record itself is a pre-gate
    verification run* (``Gate state: NOT released``), asserts the happy-path
    contract (Status OK + pre-gate Mode). Otherwise -- i.e. the newest record is
    already a full-cycle / released record -- there is no pre-gate record to
    pin, so the assertion is skipped rather than vacuously passing.

    The previous version skipped on the *wall clock* (``now >= handoff_gate +
    1 day``). That was both wrong and vacuous in the current window: the newest
    committed handoff is the released 2026-11-16 full-cycle record, so the old
    test ran while the gate clock was still in the future but never exercised its
    own pre-gate branch, and its docstring falsely claimed "this is the current
    on-disk state (a pre-gate verification run)". Anchoring on the committed
    record makes the skip meaningful and keeps the test non-vacuous whenever a
    real pre-gate record exists (see the synthetic regression tests below).
    """
    lines = _handoff_lines()
    if not _is_pre_gate_record(lines):
        pytest.skip("newest committed handoff is not a pre-gate record; no pre-gate record to pin")
    _assert_pre_gate_record_ok(lines)


def test_pre_gate_record_happy_path_is_enforced() -> None:
    """Anti-vacuity: a NOT-released record must satisfy the pre-gate contract.

    Builds a synthetic pre-gate record (``Gate state: NOT released``) and shows
    the happy-path assertion passes for a correct one and rejects a FAILED /
    extend-included one. This proves the guard is not vacuous: it actually
    constrains pre-gate records rather than trivially passing on any input.
    """
    good = [
        "- **Status:** OK — all verification steps passed",
        "- **Mode:** pre-gate verification (extend withheld — gate not released)",
        "- **Gate state:** NOT released — pre-gate verification run only (T-100s remaining; mutating extend withheld)",
    ]
    assert _is_pre_gate_record(good)
    _assert_pre_gate_record_ok(good)  # correct record passes

    bad_status = [
        "- **Status:** FAILED — a verification step failed",
        "- **Mode:** pre-gate verification (extend withheld — gate not released)",
        "- **Gate state:** NOT released — pre-gate verification run only (T-100s remaining; mutating extend withheld)",
    ]
    with pytest.raises(AssertionError):
        _assert_pre_gate_record_ok(bad_status)

    wrong_mode = [
        "- **Status:** OK — all verification steps passed",
        "- **Mode:** full cycle (extend included)",
        "- **Gate state:** NOT released — pre-gate verification run only (T-100s remaining; mutating extend withheld)",
    ]
    with pytest.raises(AssertionError):
        _assert_pre_gate_record_ok(wrong_mode)


def test_released_record_is_not_treated_as_pre_gate() -> None:
    """Anti-vacuity: a released/full-cycle record must NOT match the pre-gate branch.

    Guards against the inverse defect: a released record (like the newest
    2026-11-16 handoff) must be classified as *not* pre-gate so the happy-path
    test skips it instead of wrongly asserting pre-gate semantics on it.
    """
    released = [
        "- **Status:** OK — all verification steps passed",
        "- **Mode:** full cycle (extend included)",
        "- **Gate state:** released (gate epoch reached)",
    ]
    assert not _is_pre_gate_record(released)


# Read-only verification steps the orchestrator always runs (cmds 1,3,5,6,7,8,
# 8b, 8c, 8d, 9). Kept as an explicit tuple so the truthfulness guard fails
# closed if a step silently disappears from ``Cmds run`` rather than only
# checking the extend.
#
# Cycle 1272: the cmd8b/8c/8d family (drift invariant, coverage audit, artifact
# reconciliation) was wired into the orchestrator after this tuple was written,
# and the three new ``mark_run`` labels were never added here. A handoff that
# silently dropped those steps therefore still passed the committed consistency
# guard -- the exact false-evidence class this file exists to prevent (a record
# that reads "Status: OK" while omitting three verification steps). The tokens
# below match the literal labels in scripts/post_gate_orchestrator.sh
# (``mark_run "8b drift invariant"``, ``"8c coverage audit"``,
# ``"8d artifact reconciliation"``) so a rename on either side fails the guard.
_VERIFY_TOKENS = (
    "1 date",
    "3 drift",
    "5 6-module pytest",
    "6 git status",
    "7 data-cost inventory + tests",
    "8 ruff",
    "8b drift invariant",
    "8c coverage audit",
    "8d artifact reconciliation",
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


def test_select_handoff_picks_newest_gate_record(tmp_path: Path) -> None:
    """The guard must verify the NEWEST gate handoff, not a stale pinned one.

    Regression for this guard's own forward-compatibility defect: it previously
    hard-pinned ``CORRECTIVE_HANDOFF_POSTGATE_20261116.md`` and asserted that
    record's ``State:`` line equalled the live state. After the 2026-11-17 cycle
    appends a session and writes ``..._20261117.md`` the pinned 20261116 record's
    State line no longer matches the live state, so the whole suite would fail on
    the very cycle it guards. Selection must follow the greatest gate date.
    """
    (tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261112.md").write_text("old")
    (tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261116.md").write_text("mid")
    (tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261117.md").write_text("new")
    # A pre-gate backup must NOT be selected even though it shares the prefix.
    (tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261117_pregate_backup.md").write_text("bak")
    # An unrelated handoff (different family) must not be selected.
    (tmp_path / "CORRECTIVE_HANDOFF_GATECLOCK_20261117T0527Z.md").write_text("x")

    import importlib

    module = importlib.import_module("tests.test_post_gate_handoff_consistency")
    original_root = module.REPO_ROOT
    try:
        module.REPO_ROOT = tmp_path
        selected = module._select_handoff()
        gate = module._handoff_gate_dt(selected)
    finally:
        module.REPO_ROOT = original_root

    assert selected.name == "CORRECTIVE_HANDOFF_POSTGATE_20261117.md"
    assert gate == datetime(2026, 11, 17, 22, 0, 0, tzinfo=UTC)


def test_select_handoff_fails_closed_without_any_gate_record(tmp_path: Path) -> None:
    """Anti-vacuity: with no gate handoff present the guard must fail, not pass."""
    (tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261117_pregate_backup.md").write_text("bak")

    import importlib

    module = importlib.import_module("tests.test_post_gate_handoff_consistency")
    original_root = module.REPO_ROOT
    try:
        module.REPO_ROOT = tmp_path
        with pytest.raises(AssertionError):
            module._select_handoff()
    finally:
        module.REPO_ROOT = original_root


def test_handoff_gate_dt_derives_2200_utc(tmp_path: Path) -> None:
    """The canonical gate datetime is 22:00 UTC on the filename date."""
    import importlib

    module = importlib.import_module("tests.test_post_gate_handoff_consistency")
    gate = module._handoff_gate_dt(tmp_path / "CORRECTIVE_HANDOFF_POSTGATE_20261117.md")
    assert gate == datetime(2026, 11, 17, 22, 0, 0, tzinfo=UTC)
    assert int(gate.timestamp()) == 1794952800
    assert gate.strftime("%Y-%m-%dT%H:%M:%SZ") == "2026-11-17T22:00:00Z"


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


def test_false_extend_claim_is_rejected_when_gate_released() -> None:
    """Anti-vacuity: a released handoff that omits the mutating extend must fail.

    Complement to the pre-gate case above: a handoff whose ``Gate state`` says
    released but whose ``Cmds run`` drops ``2 extend`` / ``4 idempotent
    re-extend`` misrepresents a full cycle as a read-only one. Reject it.
    """
    false_claim = (
        "1 date, 3 drift, 5 6-module pytest, 6 git status, "
        "7 data-cost inventory + tests, 8 ruff, 9 state fingerprint"
    )
    with pytest.raises(AssertionError):
        _assert_cmds_run_truthful(false_claim, "released (gate epoch reached)")


def test_read_only_steps_8bcd_must_be_recorded_when_gate_released() -> None:
    """The cmd8b/8c/8d verification steps must appear in ``Cmds run``.

    Regression guard for the Cycle-1272 gap: those three steps were wired into
    the orchestrator (mark_run "8b drift invariant", "8c coverage audit",
    "8d artifact reconciliation") after ``_VERIFY_TOKENS`` was written and were
    never added to it, so a handoff that silently dropped them passed the
    committed consistency guard while still reading "Status: OK". A released
    handoff that omits any of the three must now fail.
    """
    released = (
        "1 date, 2 extend, 3 drift, 4 idempotent re-extend, 5 6-module pytest, "
        "6 git status, 7 data-cost inventory + tests, 8 ruff, "
        "8b drift invariant, 8c coverage audit, 8d artifact reconciliation, "
        "9 state fingerprint"
    )
    _assert_cmds_run_truthful(released, "released (gate epoch reached)")

    dropped = released.replace("8b drift invariant, ", "")
    with pytest.raises(AssertionError):
        _assert_cmds_run_truthful(dropped, "released (gate epoch reached)")
    dropped = released.replace("8c coverage audit, ", "")
    with pytest.raises(AssertionError):
        _assert_cmds_run_truthful(dropped, "released (gate epoch reached)")
    dropped = released.replace("8d artifact reconciliation, ", "")
    with pytest.raises(AssertionError):
        _assert_cmds_run_truthful(dropped, "released (gate epoch reached)")


def test_read_only_steps_8bcd_must_be_recorded_when_gate_unreleased() -> None:
    """The cmd8b/8c/8d steps run in every mode, including pre-gate.

    They are read-only (they never write state or artifacts), so a pre-gate
    handoff must still list them -- a pre-gate run that silently dropped them
    would be a record that omits verification steps while claiming the extend
    was withheld.
    """
    pre_gate = (
        "1 date, 3 drift, 5 6-module pytest, 6 git status, "
        "7 data-cost inventory + tests, 8 ruff, "
        "8b drift invariant, 8c coverage audit, 8d artifact reconciliation, "
        "9 state fingerprint"
    )
    _assert_cmds_run_truthful(pre_gate, "NOT released — pre-gate verification run only")

    dropped = pre_gate.replace("8b drift invariant, ", "")
    with pytest.raises(AssertionError):
        _assert_cmds_run_truthful(dropped, "NOT released — pre-gate verification run only")


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