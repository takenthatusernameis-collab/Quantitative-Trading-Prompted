#!/usr/bin/env bash
set -Eeuo pipefail

persist_source=".github/scripts/kilo-persist-checkpoint.sh"
controller=".github/scripts/kilo-controller.sh"
repo_root="$PWD"
grep -Fq 'source .github/scripts/kilo-persist-checkpoint.sh' "$controller"
grep -Fq 'persist_current_checkpoint' "$controller"
grep -Fq 'git rebase --autostash "$remote_sha_before"' "$persist_source"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
export RUNNER_TEMP="$tmp/runner"
mkdir -p "$RUNNER_TEMP"
export GITHUB_RUN_ID="persistence-integration-test"
export GITHUB_RUN_ATTEMPT="1"

write_progress() { :; }
setup_remote() {
  local remote="$1" seed="$2"
  git init --quiet --bare --initial-branch=main "$remote"
  git init --quiet --initial-branch=main "$seed"
  git -C "$seed" config user.name "Kilo persistence integration test"
  git -C "$seed" config user.email "kilo-persistence-test@example.invalid"
  printf 'base version\n' > "$seed/shared.md"
  git -C "$seed" add shared.md
  git -C "$seed" commit --quiet -m "base"
  git -C "$seed" remote add origin "$remote"
  git -C "$seed" push --quiet --set-upstream origin main
}
configure_persistence_call() {
  DEFAULT_BRANCH="main"
  cutoff_epoch=$(( $(date +%s) + 90 ))
  cutoff=0
  project_progress=0
  persisted_checkpoints=0
  last_verified_checkpoint_sha="none"
  agent_index=1
  checkpoint_ready=1
  committed_this_iteration=1
  checkpoint_has_project_changes=1
}

# Case 1: a conflict-free local checkpoint must reach the remote and be verified.
success_remote="$tmp/success.git"
success_seed="$tmp/success-seed"
success_worker="$tmp/success-worker"
setup_remote "$success_remote" "$success_seed"
git clone --quiet "$success_remote" "$success_worker"
git -C "$success_worker" config user.name "Kilo persistence integration test"
git -C "$success_worker" config user.email "kilo-persistence-test@example.invalid"
printf 'verified worker version\n' > "$success_worker/shared.md"
git -C "$success_worker" commit --quiet -am "worker checkpoint without conflict"
expected_success_sha="$(git -C "$success_worker" rev-parse HEAD)"
(
  cd "$success_worker"
  source "$repo_root/$persist_source"
  configure_persistence_call
  persist_current_checkpoint
  [[ "$persisted" -eq 1 ]]
  [[ "$persisted_checkpoints" -eq 1 ]]
  [[ "$project_progress" -eq 1 ]]
  [[ "$last_verified_checkpoint_sha" == "$(git rev-parse --short HEAD)" ]]
  [[ "$(git ls-remote origin refs/heads/main | awk 'NR==1 {print $1}')" == "$expected_success_sha" ]]
)
echo "PASS: production persistence routine pushes and remotely verifies a clean checkpoint."

# Case 2: divergent edits must preserve both versions, abort safely, and stop repeating an identical conflict.
conflict_remote="$tmp/conflict.git"
conflict_seed="$tmp/conflict-seed"
conflict_worker="$tmp/conflict-worker"
competitor="$tmp/competitor"
setup_remote "$conflict_remote" "$conflict_seed"
git clone --quiet "$conflict_remote" "$conflict_worker"
git -C "$conflict_worker" config user.name "Kilo persistence integration test"
git -C "$conflict_worker" config user.email "kilo-persistence-test@example.invalid"
printf 'worker checkpoint version\n' > "$conflict_worker/shared.md"
git -C "$conflict_worker" commit --quiet -am "worker conflicting checkpoint"
expected_checkpoint_sha="$(git -C "$conflict_worker" rev-parse HEAD)"
git clone --quiet --branch main "$conflict_remote" "$competitor"
git -C "$competitor" config user.name "Kilo persistence integration test"
git -C "$competitor" config user.email "kilo-persistence-test@example.invalid"
printf 'remote concurrent version\n' > "$competitor/shared.md"
git -C "$competitor" commit --quiet -am "concurrent remote version"
git -C "$competitor" push --quiet origin main
expected_remote_sha="$(git -C "$competitor" rev-parse HEAD)"
(
  cd "$conflict_worker"
  source "$repo_root/$persist_source"
  configure_persistence_call
  persist_current_checkpoint
  [[ "$persisted" -eq 0 ]]
  [[ "$cutoff" -eq 1 ]]
  [[ "$project_progress" -eq 0 ]]
  [[ "$(git rev-parse HEAD)" == "$expected_checkpoint_sha" ]]
  recovery_ref="refs/heads/kilo-recovery/$expected_checkpoint_sha"
  [[ "$(git ls-remote origin "$recovery_ref" | awk 'NR==1 {print $1}')" == "$expected_checkpoint_sha" ]]
  [[ "$(git ls-remote origin refs/heads/main | awk 'NR==1 {print $1}')" == "$expected_remote_sha" ]]
  [[ "$(git show "$expected_checkpoint_sha:shared.md")" == "worker checkpoint version" ]]
  [[ "$(git show "$expected_remote_sha:shared.md")" == "remote concurrent version" ]]
  bundle_path="$(find "$RUNNER_TEMP/kilo-failure-logs" -type f -name "kilo-persistence-checkpoint-$expected_checkpoint_sha.bundle" -print -quit)"
  [[ -n "$bundle_path" ]]
  git bundle verify "$bundle_path" >/dev/null
  bundle_head="$(git bundle list-heads "$bundle_path" | awk 'NR==1 {print $1}')"
  [[ "$bundle_head" == "$expected_checkpoint_sha" ]]
)
echo "PASS: production routine preserves both commits, verifies a recovery copy, restores HEAD after abort, and stops after identical conflict."
