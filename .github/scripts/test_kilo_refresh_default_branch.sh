#!/usr/bin/env bash
set -Eeuo pipefail

root="$(git rev-parse --show-toplevel)"
refresh_script="$root/.github/scripts/kilo-refresh-default-branch.sh"
controller="$root/.github/scripts/kilo-controller.sh"
workflow="$root/.github/workflows/main.yml"

grep -Fq 'Refresh default-branch checkout after concurrency queue' "$workflow"
grep -Fq 'bash .github/scripts/kilo-refresh-default-branch.sh' "$workflow"
grep -Fq 'github.ref_name == github.event.repository.default_branch' "$workflow"
grep -Fq '.github/scripts/kilo-terminal-outcome.py' "$controller"
grep -Fq 'actual_cutoff_reached' "$controller"
grep -Fq 'terminal_stop_reason' "$controller"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
remote="$tmp/origin.git"
seed="$tmp/seed"
worker="$tmp/worker"

git init --quiet --bare --initial-branch=main "$remote"
git clone --quiet "$remote" "$seed"
git -C "$seed" config user.name "Kilo refresh test"
git -C "$seed" config user.email "kilo-refresh-test@example.invalid"
printf 'base version\n' > "$seed/README.md"
git -C "$seed" add README.md
git -C "$seed" commit --quiet -m "base"
git -C "$seed" push --quiet --set-upstream origin main

git clone --quiet "$remote" "$worker"
git -C "$worker" config user.name "Kilo refresh test"
git -C "$worker" config user.email "kilo-refresh-test@example.invalid"
printf 'new default branch state\n' > "$seed/NEXT_AGENT_TASK.md"
git -C "$seed" add NEXT_AGENT_TASK.md
git -C "$seed" commit --quiet -m "advance default branch while worker is queued"
git -C "$seed" push --quiet origin main
expected_sha="$(git -C "$seed" rev-parse HEAD)"

printf 'stale local edit\n' > "$worker/stale-worker-edit.txt"
(cd "$worker" && GITHUB_REF=refs/heads/main KILO_DEFAULT_BRANCH=main bash "$refresh_script")
actual_sha="$(git -C "$worker" rev-parse HEAD)"
[[ "$actual_sha" == "$expected_sha" ]] || {
  echo "::error::Stale checkout remains: local=$actual_sha remote=$expected_sha"
  exit 1
}
[[ ! -e "$worker/stale-worker-edit.txt" ]] || {
  echo "::error::Pre-worker stale edits survived the refresh."
  exit 1
}
grep -Fq 'new default branch state' "$worker/NEXT_AGENT_TASK.md"
echo "PASS: queued checkout advances to the verified latest remote default-branch commit before worker execution."
