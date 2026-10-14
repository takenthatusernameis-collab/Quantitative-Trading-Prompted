#!/usr/bin/env bash
set -Eeuo pipefail

controller=".github/scripts/kilo-controller.sh"
capture_line="$(grep -nF 'checkpoint_sha_before="$(git rev-parse HEAD)"' "$controller" | head -n 1 | cut -d: -f1)"
rebase_line="$(grep -nF 'git rebase --autostash "$remote_sha_before"' "$controller" | head -n 1 | cut -d: -f1)"
if [[ -z "$capture_line" || -z "$rebase_line" || "$capture_line" -ge "$rebase_line" ]]; then
  echo "::error::The original checkpoint SHA must be captured before starting rebase."
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

remote="$tmp/origin.git"
worker="$tmp/worker"
competitor="$tmp/competitor"
git init --quiet --bare --initial-branch=main "$remote"
git clone --quiet "$remote" "$worker"
git -C "$worker" config user.name "Kilo persistence test"
git -C "$worker" config user.email "kilo-persistence-test@example.invalid"

printf 'base version\n' > "$worker/shared.md"
git -C "$worker" add shared.md
git -C "$worker" commit --quiet -m "base"
git -C "$worker" push --quiet --set-upstream origin main

# The worker checkpoints a change that will conflict with a concurrent writer.
printf 'worker checkpoint version\n' > "$worker/shared.md"
git -C "$worker" commit --quiet -am "worker checkpoint"
checkpoint_expected="$(git -C "$worker" rev-parse HEAD)"

git clone --quiet --branch main "$remote" "$competitor"
git -C "$competitor" config user.name "Kilo persistence test"
git -C "$competitor" config user.email "kilo-persistence-test@example.invalid"
printf 'remote concurrent version\n' > "$competitor/shared.md"
git -C "$competitor" commit --quiet -am "concurrent remote change"
git -C "$competitor" push --quiet origin main

git -C "$worker" fetch --quiet origin main
remote_sha_before="$(git -C "$worker" rev-parse --verify 'origin/main^{commit}')"
checkpoint_sha_before="$(git -C "$worker" rev-parse HEAD)"
if [[ "$checkpoint_sha_before" != "$checkpoint_expected" ]]; then
  echo "::error::Test setup did not capture the original local checkpoint."
  exit 1
fi

if git -C "$worker" rebase --autostash "$remote_sha_before" > "$tmp/rebase.log" 2>&1; then
  echo "::error::The simulated conflicting rebase unexpectedly succeeded."
  exit 1
fi

# During a conflicted rebase, HEAD is the remote base, not the worker checkpoint.
head_during_conflict="$(git -C "$worker" rev-parse HEAD)"
if [[ "$head_during_conflict" != "$remote_sha_before" ]]; then
  cat "$tmp/rebase.log"
  echo "::error::Test did not reach the expected conflicted-rebase state."
  exit 1
fi

checkpoint_ref="refs/kilo-recovery/checkpoint-$checkpoint_sha_before"
recovery_ref="refs/heads/kilo-recovery/$checkpoint_sha_before"
bundle="$tmp/checkpoint.bundle"
git -C "$worker" update-ref "$checkpoint_ref" "$checkpoint_sha_before"
git -C "$worker" bundle create "$bundle" "$checkpoint_ref" > "$tmp/bundle-create.log"
git -C "$worker" bundle verify "$bundle" > "$tmp/bundle-verify.log"
git -C "$worker" update-ref -d "$checkpoint_ref"

git -C "$worker" push --quiet origin "$checkpoint_sha_before:$recovery_ref"
remote_recovery_sha="$(git -C "$worker" ls-remote origin "$recovery_ref" | awk 'NR == 1 { print $1 }')"
if [[ "$remote_recovery_sha" != "$checkpoint_expected" ]]; then
  echo "::error::The remote recovery ref does not point to the exact worker checkpoint."
  exit 1
fi

git -C "$worker" rebase --abort
head_after_abort="$(git -C "$worker" rev-parse HEAD)"
if [[ "$head_after_abort" != "$checkpoint_expected" ]]; then
  echo "::error::Aborting the rebase did not restore the original checkpoint."
  exit 1
fi

checkpoint_content="$(git -C "$worker" show "$remote_recovery_sha:shared.md")"
remote_content="$(git -C "$worker" show "$remote_sha_before:shared.md")"
if [[ "$checkpoint_content" != "worker checkpoint version" || "$remote_content" != "remote concurrent version" ]]; then
  echo "::error::The recovered checkpoint or concurrent remote commit has unexpected content."
  exit 1
fi

echo "PASS: recovery preserves and verifies the exact pre-rebase checkpoint, validates a Git bundle, confirms the remote recovery ref, and restores the worktree after rebase abort."
