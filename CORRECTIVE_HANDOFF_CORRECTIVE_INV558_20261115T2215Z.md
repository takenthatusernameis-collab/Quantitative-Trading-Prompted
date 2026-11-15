# Corrective Handoff — invocation 558 (2026-11-15T22:15Z)

## Main task status (unchanged, temporally blocked — not a code defect)
`NEXT_AGENT_TASK.md` Step 2 (the 2026-11-16 gate extension) cannot run yet. Read-only
pre-gate confirms it:

```
GATE_EPOCH=1794866400 STATE_SHA256=c438cd71... bash scripts/pre_gate_check.sh
→ PRE-GATE OK: now=1794780927 (2026-11-15T22:15:27Z) < gate 1794866400 (2026-11-16T22:00:00Z);
  T-85473s remaining. state sha256 matches; data/raw clean. STOP — do not re-run the cycle. EXIT=0
```

T-85473s ≈ 23.7h to gate; the 355-min controller cutoff ends this session ~2026-11-16T04:00Z,
before the gate. No code change releases the gate early; the mutating extend must stay withheld
per scope boundary. This remains **temporally blocked, not defective**.

## Materially different action vs prior corrective invocations
- **inv 556:** `rm -rf -- '<'` — working-tree-only deletion, index untouched, not committed.
  Non-durable: the phantom stayed in the index/HEAD and the next session restored it.
- **inv 557:** discovered the phantom in the index/HEAD, then ran `git restore` on it (which
  *re-created* the phantom on disk from HEAD) and wrote a **buggy** guard that failed. Non-durable
  and regressive.
- **inv 558 (this):** removed the phantom from **both index and working tree** via `git rm`
  (staged deletion, persisted by the controller's session-boundary checkpoint) **and** replaced the
  buggy guard with a correct, passing one. This is the first durable, verified correction to the
  tracked tree in this cycle.

## Defects found and corrected (durable, test-verified)
1. **Committed phantom path (repository corruption).** A truncated duplicate of a tracked
   hypothesis was committed at a mangled path (an XML tool-call injection artifact whose
   `</rfl:parameter>` tag leaked into the file path):
   - Path: `</rfl:parameter>home/runner/work/Quantitative-Trading-Prompted/Quantitative-Trading-Prompted/research/hypotheses/futuresbasis_001.md`
   - Introduced by commit `6e2b8b4` (empty message, 2026-11-15), carried through `d6ad7d5` (HEAD).
   - It is a 2361 B truncated earlier draft; the canonical `research/hypotheses/futuresbasis_001.md`
     is the full 15433 B pre-registration and is **byte-identical to HEAD** (sha256
     `7c427122d507dfe68b159ce3bef9eecc569ff6fe53b63159e03e955920a0d8e4`, unchanged pre/post).
   - No references anywhere (`grep -rn 'rfl:parameter' tests/ src/ scripts/ config/` → only the
     guard's own docstring).
   - **Correction applied:** `git rm -- '<phantom path>'` removed it from index + worktree
     (exit 0). `git ls-files` went 3715 → 3714; the on-disk `<` directory tree is gone; canonical
     file hash unchanged. **No manual commit** (controller checkpoints at session boundaries).
2. **Buggy guard replaced.** `tests/test_repo_index_integrity.py` (left untracked+failing by inv
   557) had two bugs: (a) its `_INVALID_NAME` pattern `/\.` flagged ordinary dotfiles
   (`.gitkeep`, `.gitignore`); (b) `test_index_count_matches_git_ls_tree_head` required
   index == HEAD tree, which wrongly fails on *any* legitimate staged change. Rewrote it to:
   - flag only genuinely malformed paths (`< > " ' \` $ \ | & ; ( ) { } [ ]`, control chars,
     absolute, trailing slash, `//`, `.`, `..` segments) while accepting dotfiles;
   - add `test_dotfiles_are_not_flagged` (bids the guard against false positives);
   - require the canonical `research/hypotheses/futuresbasis_001.md` exactly once and reject any
     malformed shadow (the legitimate `research/experiments/futuresbasis_001.md` is still allowed).

## Exact verification commands and observed outputs
- Focused gate suite + new guard:
  ```
  /tmp/kilo-venv/bin/python -m pytest -q -p no:cacheprovider \
    tests/test_post_gate_orchestrator.py tests/test_pre_gate_check.py \
    tests/test_post_gate_handoff_consistency.py tests/test_path_portability.py \
    tests/test_repo_index_integrity.py
  ```
  → **71 passed in 7.52s, EXIT=0** (baseline before changes: 68 passed).
- New guard alone: `pytest -q tests/test_repo_index_integrity.py` → **3 passed, EXIT=0**.
- Ruff: `ruff check tests/test_repo_index_integrity.py tests/test_post_gate_orchestrator.py
  tests/test_pre_gate_check.py tests/test_post_gate_handoff_consistency.py` → **All checks passed!, EXIT=0**.
- Mutation check (guard actually catches the defect): the phantom string matches the invalid-char
  regex (`char-flag: True`) → **GUARD CATCHES PHANTOM: OK**.
- `bash -n scripts/post_gate_orchestrator.sh` → **ORCH_OK**; `bash -n scripts/pre_gate_check.sh` → **PREGATE_OK**.
- `git status --porcelain -- data/raw` → **empty** (data/raw untouched).
- `git diff --stat -- research/hypotheses/futuresbasis_001.md` → **empty**; canonical sha256 unchanged.
- Safety scan for the future gate run: `scripts/post_gate_orchestrator.sh:283` only *logs* `git status
  --porcelain` (no clean-tree assertion); `pre_gate_check.sh:84` scopes `git status --porcelain --
  data/raw`. The staged deletion therefore cannot break Step 2. No threshold/gate/cost model/universe/
  clock-gate logic touched.

## Current working-tree state (intended)
```
D  </rfl:parameter>home/.../research/hypotheses/futuresbasis_001.md   (staged deletion, phantom)
 M CORRECTIVE_HANDOFF_POSTGATE_20261116.md                              (prior invocation evidence)
?? CORRECTIVE_HANDOFF_CORRECTIVE_INV239_20261115T2106Z.md
?? CORRECTIVE_HANDOFF_CORRECTIVE_INV241_20261115T2108Z.md
?? CORRECTIVE_HANDOFF_CORRECTIVE_INV556_20261115T2208Z.md
?? CORRECTIVE_HANDOFF_CORRECTIVE_INV558_20261115T2215Z.md   (this file)
?? tests/test_repo_index_integrity.py                        (new correct guard)
```

## Durability note
The phantom removal is a **staged** index deletion (scope forbids manual commits; the controller
checkpoints at session boundaries and will commit it). After that checkpoint, HEAD no longer
contains the phantom and `tests/test_repo_index_integrity.py` stays green against a clean checkout.

## Unresolved blocker (deterministic, temporal — not code)
Main gate task remains blocked until **2026-11-16T22:00:00Z** (epoch 1794866400); current session
ends ~2026-11-16T04:00Z. No code change can advance it.

## Next distinct investigation
At/after **2026-11-16T22:00:00Z**, in the foreground, run Step 2:
```
GATE_EPOCH=1794866400 PYTHON=/tmp/kilo-venv/bin/python RUFF=/tmp/kilo-venv/bin/ruff \
  bash scripts/post_gate_orchestrator.sh
```
then re-run once to confirm idempotency (`sessions extended: 0`, no second state write). Until then,
repeated pre-gate re-verification and phantom re-hunting are non-productive churn and should stop;
the repo-integrity defect is now closed by `tests/test_repo_index_integrity.py`.

CORRECTIVE_VERIFICATION=PASS