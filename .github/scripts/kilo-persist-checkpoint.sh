#!/usr/bin/env bash
# Production checkpoint persistence routine, sourced by kilo-controller.sh and exercised directly by integration tests.
# Preserve a local recovery bundle for any checkpoint that cannot reach the default
# branch, including permission/rejection failures that never enter rebase-conflict
# handling. The optional remote recovery ref is created with a normal non-force push.
preserve_failed_checkpoint() {
  local checkpoint_sha recovery_dir recovery_bundle recovery_ref checkpoint_ref report
  local bundle_verified=0 recovery_ref_verified=0 recovery_remote_sha=""
  checkpoint_sha="$(git rev-parse HEAD 2>/dev/null)" || return 1
  recovery_dir="${RUNNER_TEMP:-/tmp}/kilo-failure-logs"
  mkdir -p "$recovery_dir" || return 1
  recovery_bundle="$recovery_dir/kilo-persistence-checkpoint-${checkpoint_sha}.bundle"
  recovery_ref="refs/heads/kilo-recovery/${checkpoint_sha}"
  checkpoint_ref="refs/kilo-recovery/checkpoint-failure-${checkpoint_sha}"
  report="$recovery_dir/kilo-persistence-failure-${GITHUB_RUN_ID:-manual}-${checkpoint_sha}.txt"
  {
    printf 'reason=checkpoint_not_persisted\n'
    printf 'checkpoint_sha=%s\n' "$checkpoint_sha"
    printf 'default_branch=%s\n' "${DEFAULT_BRANCH:-unknown}"
    printf 'recovery_ref=%s\n' "$recovery_ref"
  } > "$report" 2>/dev/null || true

  if [ -f "$recovery_bundle" ] && git bundle verify "$recovery_bundle" >> "$report" 2>&1; then
    bundle_verified=1
  else
    rm -f "$recovery_bundle"
    if git update-ref "$checkpoint_ref" "$checkpoint_sha" >> "$report" 2>&1; then
      if git bundle create "$recovery_bundle" "$checkpoint_ref" >> "$report" 2>&1 &&
         git bundle verify "$recovery_bundle" >> "$report" 2>&1; then
        bundle_verified=1
      fi
      git update-ref -d "$checkpoint_ref" >> "$report" 2>&1 || true
    fi
  fi

  if git push origin "${checkpoint_sha}:${recovery_ref}" >> "$report" 2>&1; then
    recovery_remote_sha="$(git ls-remote origin "$recovery_ref" 2>/dev/null | awk 'NR==1 {print $1}')"
    if [ -n "$recovery_remote_sha" ] && [ "$recovery_remote_sha" = "$checkpoint_sha" ]; then
      recovery_ref_verified=1
    fi
  fi

  {
    printf 'bundle_verified=%s\n' "$bundle_verified"
    printf 'recovery_ref_verified=%s\n' "$recovery_ref_verified"
    printf 'recovery_remote_sha=%s\n' "${recovery_remote_sha:-unverified}"
  } >> "$report" 2>/dev/null || true
  echo "::notice::Failed checkpoint recovery evidence: checkpoint=$checkpoint_sha bundle_verified=$bundle_verified recovery_ref_verified=$recovery_ref_verified report=$report"
  [ "$bundle_verified" -eq 1 ] || [ "$recovery_ref_verified" -eq 1 ]
}

persist_current_checkpoint() {
  # Deterministic repository-level persistence. A checkpoint is already committed
  # locally before entering this loop. When rebase fails, preserve that exact
  # commit in both a git bundle (uploaded as a run artifact) and a non-force-
  # pushed recovery ref before aborting; never blindly retry an identical
  # local-checkpoint/remote-head conflict.
  persisted=1
  if [ "$checkpoint_ready" -eq 1 ] && [ "$committed_this_iteration" -eq 1 ]; then
    persisted=0
    push_attempt=0
    rebase_conflicts=0
    last_conflict_signature=""
    delay=5
    while [ "$persisted" -ne 1 ]; do
      remaining=$((cutoff_epoch - $(date +%s)))
      if [ "$remaining" -le 0 ]; then
        cutoff=1
        echo "::warning::Safety cutoff reached before checkpoint persistence could be confirmed."
        break
      fi

      push_attempt=$((push_attempt + 1))
      write_progress "checkpoint-push" "remote reconciliation/persistence attempt=${push_attempt}"
      if ! git fetch origin "$DEFAULT_BRANCH"; then
        echo "::warning::Fetch failed on persistence attempt ${push_attempt}; retrying."
      else
        remote_sha_before="$(git rev-parse --verify "origin/$DEFAULT_BRANCH^{commit}" 2>/dev/null || true)"
        if [ -z "$remote_sha_before" ]; then
          echo "::warning::Fetched origin but could not resolve origin/$DEFAULT_BRANCH; retrying."
        elif git merge-base --is-ancestor "$remote_sha_before" HEAD; then
          if git push origin "HEAD:$DEFAULT_BRANCH"; then
            remote_sha="$(git ls-remote origin "refs/heads/$DEFAULT_BRANCH" 2>/dev/null | awk 'NR==1 {print $1}')"
            local_sha="$(git rev-parse HEAD)"
            if [ -n "$remote_sha" ] && [ "$remote_sha" = "$local_sha" ]; then
              persisted=1
              echo "Repository persistence verified at $remote_sha after $push_attempt attempt(s)."
              write_progress "checkpoint-verified" "remote head verified at ${remote_sha} after ${push_attempt} attempt(s)"
              break
            fi
            echo "::warning::Remote head did not match the local checkpoint after attempt $push_attempt; refetching."
          else
            echo "::warning::Push failed on persistence attempt $push_attempt; fetching and reconciling again."
          fi
        else
          checkpoint_sha_before="$(git rev-parse HEAD)"
          if git rebase --autostash "$remote_sha_before"; then
            # A successful rebase must be pushed in this same iteration. If
            # another writer advances main concurrently, the next loop fetches
            # and reconciles the new head.
            if git push origin "HEAD:$DEFAULT_BRANCH"; then
              remote_sha="$(git ls-remote origin "refs/heads/$DEFAULT_BRANCH" 2>/dev/null | awk 'NR==1 {print $1}')"
              local_sha="$(git rev-parse HEAD)"
              if [ -n "$remote_sha" ] && [ "$remote_sha" = "$local_sha" ]; then
                persisted=1
                echo "Repository persistence verified at $remote_sha after $push_attempt attempt(s)."
                write_progress "checkpoint-verified" "remote head verified at ${remote_sha} after ${push_attempt} attempt(s)"
                break
              fi
              echo "::warning::Remote head advanced after the rebased push on attempt $push_attempt; refetching."
            else
              echo "::warning::Push failed after successful rebase on persistence attempt $push_attempt; fetching and reconciling again."
            fi
          else
            rebase_conflicts=$((rebase_conflicts + 1))
            conflict_paths="$(git diff --name-only --diff-filter=U 2>/dev/null || true)"
            status_snapshot="$(git status --short --branch 2>&1 || true)"
            conflict_signature="${checkpoint_sha_before}:${remote_sha_before}"
            recovery_dir="${RUNNER_TEMP:-/tmp}/kilo-failure-logs"
            if ! mkdir -p "$recovery_dir"; then
              recovery_dir="/tmp/kilo-failure-logs"
              mkdir -p "$recovery_dir" 2>/dev/null || true
            fi
            recovery_report="$recovery_dir/kilo-persistence-recovery-${GITHUB_RUN_ID:-manual}-${agent_index:-0}-${push_attempt}.txt"
            recovery_bundle="$recovery_dir/kilo-persistence-checkpoint-${checkpoint_sha_before}.bundle"
            recovery_ref="refs/heads/kilo-recovery/${checkpoint_sha_before}"
            {
              printf 'reason=rebase_conflict\n'
              printf 'run_id=%s\n' "${GITHUB_RUN_ID:-unknown}"
              printf 'agent_index=%s\n' "${agent_index:-unknown}"
              printf 'persistence_attempt=%s\n' "$push_attempt"
              printf 'rebase_conflict_count=%s\n' "$rebase_conflicts"
              printf 'checkpoint_sha_before_rebase=%s\n' "$checkpoint_sha_before"
              printf 'remote_sha_before_rebase=%s\n' "$remote_sha_before"
              printf 'recovery_ref=%s\n' "$recovery_ref"
              printf 'conflicting_paths_begin\n%s\nconflicting_paths_end\n' "${conflict_paths:-<none reported by git diff --diff-filter=U>}"
              printf 'worktree_status_during_conflict_begin\n%s\nworktree_status_during_conflict_end\n' "${status_snapshot:-<status unavailable>}"
            } > "$recovery_report" 2>&1 || true

            bundle_verified=0
            checkpoint_ref="refs/kilo-recovery/checkpoint-${checkpoint_sha_before}"
            if git update-ref "$checkpoint_ref" "$checkpoint_sha_before" >> "$recovery_report" 2>&1; then
              if git bundle create "$recovery_bundle" "$checkpoint_ref" >> "$recovery_report" 2>&1 &&
                 git bundle verify "$recovery_bundle" >> "$recovery_report" 2>&1; then
                bundle_verified=1
              else
                printf 'bundle_verification=FAILED\n' >> "$recovery_report" 2>/dev/null || true
              fi
              git update-ref -d "$checkpoint_ref" >> "$recovery_report" 2>&1 || true
            else
              printf 'checkpoint_ref_creation=FAILED\n' >> "$recovery_report" 2>/dev/null || true
            fi

            recovery_ref_verified=0
            if git push origin "${checkpoint_sha_before}:${recovery_ref}" >> "$recovery_report" 2>&1; then
              recovery_remote_sha="$(git ls-remote origin "$recovery_ref" 2>/dev/null | awk 'NR==1 {print $1}')"
              if [ -n "$recovery_remote_sha" ] && [ "$recovery_remote_sha" = "$checkpoint_sha_before" ]; then
                recovery_ref_verified=1
              fi
            fi
            {
              printf 'bundle_verified=%s\n' "$bundle_verified"
              printf 'recovery_ref_verified=%s\n' "$recovery_ref_verified"
              printf 'recovery_remote_sha=%s\n' "${recovery_remote_sha:-unverified}"
            } >> "$recovery_report" 2>/dev/null || true

            abort_ok=0
            if git rebase --abort >> "$recovery_report" 2>&1; then
              abort_ok=1
            fi
            printf 'rebase_abort_succeeded=%s\n' "$abort_ok" >> "$recovery_report" 2>/dev/null || true
            echo "::warning::Rebase conflict on persistence attempt $push_attempt; checkpoint=$checkpoint_sha_before remote=$remote_sha_before bundle_verified=$bundle_verified recovery_ref_verified=$recovery_ref_verified. See the uploaded kilo-failure-transcripts artifact for conflict paths and recovery details."

            if [ "$abort_ok" -ne 1 ]; then
              echo "::error::Could not confirm rebase abort after preserving recovery evidence; stopping persistence attempts."
              cutoff=1
              break
            fi
            if [ "$bundle_verified" -ne 1 ] && [ "$recovery_ref_verified" -ne 1 ]; then
              echo "::error::Neither the checkpoint bundle nor recovery ref could be verified; stopping rather than risking repeated conflict retries."
              cutoff=1
              break
            fi
            if [ "$conflict_signature" = "$last_conflict_signature" ]; then
              printf 'repeated_identical_conflict=1\n' >> "$recovery_report" 2>/dev/null || true
              echo "::error::The same checkpoint conflicted with the same remote head again; recovery evidence is preserved and the loop is stopping for targeted resolution."
              cutoff=1
              break
            fi
            last_conflict_signature="$conflict_signature"
            if [ "$rebase_conflicts" -ge 3 ]; then
              echo "::error::Reached three rebase conflicts in this checkpoint persistence loop; recovery evidence is preserved and automatic retries are stopping."
              cutoff=1
              break
            fi
          fi
        fi
      fi

      remaining=$((cutoff_epoch - $(date +%s)))
      if [ "$cutoff" -eq 1 ] || [ "$remaining" -le 0 ]; then
        cutoff=1
        break
      fi
      if [ "$delay" -gt "$remaining" ]; then delay="$remaining"; fi
      if [ "$delay" -gt 0 ]; then sleep "$delay"; fi
      if [ "$delay" -lt 30 ]; then delay=$((delay * 2)); if [ "$delay" -gt 30 ]; then delay=30; fi; fi
    done
  fi
  if [ "$persisted" -ne 1 ]; then
    echo "::warning::Checkpoint persistence was not confirmed. No success claim is made; stopping edits and preserving diagnostics before the cutoff."
    if ! preserve_failed_checkpoint; then
      echo "::error::Could not verify either a local recovery bundle or remote recovery ref for the failed checkpoint."
    fi
    cutoff=1
  fi
  if [ "$persisted" -eq 1 ] && [ "$committed_this_iteration" -eq 1 ]; then
    persisted_checkpoints=$((persisted_checkpoints + 1))
    last_verified_checkpoint_sha="$(git rev-parse HEAD)"
  fi
  write_progress "checkpoint-result" "persisted=${persisted} committed=${committed_this_iteration} project_changes=${checkpoint_has_project_changes}"
  if [ "$persisted" -eq 1 ] && [ "$committed_this_iteration" -eq 1 ] && [ "$checkpoint_has_project_changes" -eq 1 ]; then
    project_progress=1
    echo "Meaningful repository progress checkpoint verified at $(git rev-parse HEAD)."
  fi
}
