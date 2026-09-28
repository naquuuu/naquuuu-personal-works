#!/usr/bin/env bash
# NAQUUUU workspace auto-sync for Linux nodes (VPS, home server).
#
# Behaviour:
#   1. fetch + pull (rebase, autostash) so the node follows GitHub
#   2. if the tree is dirty: STAGE FIRST, then gate the staged snapshot, then
#      commit and push
#   3. on a read-only node (no push credentials) the push fails and is logged
#      as a tolerated, expected outcome (ADR-025); a real push error is logged
#      distinctly instead of being swallowed
#
# Order matters: the gate runs on the INDEX, not on the tracked file set. A
# file an agent just created is untracked, so a tracked-files gate would skip it
# and 'git add -A' would then publish it unaudited. Staging first means the gate
# sees exactly what the commit would contain. Consequence, on purpose: a gate
# failure now leaves the offending files STAGED, not unstaged. The message says
# how to unstage; nothing is auto-unstaged, because the staged index is the
# evidence of what was about to be published.
#
# The gate FAILS CLOSED. If scripts/verify_sanitization.py or a python3
# interpreter is missing, nothing is committed - auto-sync used to skip the
# gate silently and publish whatever an agent left behind (LESSONS.md item 4:
# an agent edit published an invalid model pin). The one deliberate escape
# hatch is NAQUUUU_ALLOW_UNGATED_SYNC=1, which logs a warning on every use.
#
# Installed to ~/.local/bin/naquuuu-autosync by scripts/provision_home_server.sh
# and driven by a systemd user timer (every ~5 min).

set -u

REPO="${NAQUUUU_REPO:-${NAQUUUU_WORKSPACE:-$HOME/naquuuu}}"
cd "$REPO" 2>/dev/null || { echo "auto-sync: no repo at $REPO (set NAQUUUU_REPO or NAQUUUU_WORKSPACE)"; exit 0; }

git fetch --quiet origin main 2>/dev/null || true

if [ -n "$(git status --porcelain)" ]; then
  # Stage BEFORE the gate so the audit covers new, previously untracked files.
  git add -A
  if [ "${NAQUUUU_ALLOW_UNGATED_SYNC:-0}" = "1" ]; then
    echo "auto-sync: WARNING - NAQUUUU_ALLOW_UNGATED_SYNC=1 is set; committing WITHOUT the sanitization gate"
  else
    if [ ! -f scripts/verify_sanitization.py ]; then
      echo "auto-sync: BLOCKED (gate script missing) - scripts/verify_sanitization.py is not in $REPO; refusing to commit ungated"
      echo "auto-sync: fix with 'git checkout -- scripts/verify_sanitization.py', or set NAQUUUU_ALLOW_UNGATED_SYNC=1 to override deliberately"
      echo "auto-sync: changes are STAGED (staging happens before the gate); inspect with 'git diff --cached', unstage with 'git restore --staged .' (or 'git reset')"
      exit 1
    fi
    if ! command -v python3 >/dev/null 2>&1; then
      echo "auto-sync: BLOCKED (no interpreter) - python3 is not installed, so the sanitization gate cannot run; refusing to commit ungated"
      echo "auto-sync: fix with 'apt-get install -y python3', or set NAQUUUU_ALLOW_UNGATED_SYNC=1 to override deliberately"
      echo "auto-sync: changes are STAGED (staging happens before the gate); inspect with 'git diff --cached', unstage with 'git restore --staged .' (or 'git reset')"
      exit 1
    fi
    if gate_out=$(python3 scripts/verify_sanitization.py --staged 2>&1); then
      gate_rc=0
    else
      gate_rc=$?
    fi
    if [ "$gate_rc" -ne 0 ]; then
      echo "auto-sync: sanitization gate FAILED (exit $gate_rc) - not committing"
      if [ -n "$gate_out" ]; then
        printf '%s\n' "$gate_out" | sed 's/^/auto-sync:   /'
      fi
      echo "auto-sync: re-run 'python3 scripts/verify_sanitization.py --staged' for the full report on the same snapshot"
      echo "auto-sync: the staged files are still STAGED (evidence of what was about to be published):"
      echo "auto-sync:   inspect with 'git diff --cached'"
      echo "auto-sync:   unstage with 'git restore --staged .' (or 'git reset' on older git)"
      exit 1
    fi
  fi
  git commit --quiet -m "chore(sync): $(hostname) $(date '+%Y-%m-%d %H:%M')" || true
fi

if ! git rebase --autostash --quiet origin/main; then
  git rebase --abort 2>/dev/null || true
  echo "auto-sync: rebase conflict - tree left for manual review"
  exit 1
fi

# Push outcome is reported, never discarded. A read-only node failing to push
# stays non-fatal (ADR-025); anything else is logged with git's own stderr.
if push_out=$(git push --quiet origin main 2>&1); then
  echo "auto-sync: push OK (origin/main)"
else
  push_rc=$?
  case "$push_out" in
    *"Permission denied"*|*"could not read Username"*|*"Authentication failed"*|*"403 Forbidden"*|*"write access"*|*" denied to "*)
      echo "auto-sync: push failed: not a writer (expected on a read-only node), exit $push_rc"
      ;;
    *)
      echo "auto-sync: push failed: real error, exit $push_rc"
      ;;
  esac
  if [ -n "$push_out" ]; then
    printf '%s\n' "$push_out" | sed 's/^/auto-sync:   /'
  fi
fi
exit 0
