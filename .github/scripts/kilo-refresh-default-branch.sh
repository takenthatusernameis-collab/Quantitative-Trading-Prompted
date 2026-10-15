#!/usr/bin/env bash
set -Eeuo pipefail

branch="${KILO_DEFAULT_BRANCH:-}"
if [[ -z "$branch" ]] || ! git check-ref-format "refs/heads/$branch"; then
  echo "::error::KILO_DEFAULT_BRANCH must identify a valid branch."
  exit 1
fi
expected_ref="refs/heads/$branch"
if [[ "${GITHUB_REF:-}" != "$expected_ref" ]]; then
  echo "::error::Refusing to refresh: workflow ref '${GITHUB_REF:-unset}' is not the configured default branch '$expected_ref'."
  exit 1
fi

remote_ref="refs/remotes/origin/$branch"
if ! git fetch --no-tags origin "+$expected_ref:$remote_ref"; then
  echo "::error::Unable to fetch the current default branch after the concurrency queue."
  exit 1
fi
remote_sha="$(git rev-parse --verify "$remote_ref^{commit}")" || {
  echo "::error::Fetched remote default-branch ref is not a commit."
  exit 1
}

# This step runs immediately after checkout, before any agent or controller edits.
git reset --hard "$remote_sha"
git clean -fd
local_sha="$(git rev-parse HEAD)"
if [[ "$local_sha" != "$remote_sha" ]]; then
  echo "::error::Checkout refresh failed verification: local=$local_sha remote=$remote_sha"
  exit 1
fi
echo "Verified fresh default-branch checkout after queue: $local_sha"
