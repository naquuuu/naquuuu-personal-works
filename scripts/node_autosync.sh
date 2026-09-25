#!/usr/bin/env bash
# NAQUUUU workspace auto-sync for Linux nodes (VPS, home server).
#
# Behaviour:
#   1. fetch + pull (rebase, autostash) so the node follows GitHub
#   2. if the tree is dirty: run the sanitization gate, commit, push
#   3. on a read-only node (no push credentials) the push simply fails and is ignored
#
# Installed to ~/.local/bin/naquuuu-autosync by scripts/provision_home_server.sh
# and driven by a systemd user timer (every ~5 min).

set -u

REPO="${NAQUUUU_REPO:-$HOME/naquuuu}"
cd "$REPO" 2>/dev/null || { echo "auto-sync: no repo at $REPO"; exit 0; }

git fetch --quiet origin main 2>/dev/null || true

if [ -n "$(git status --porcelain)" ]; then
  if [ -f scripts/verify_sanitization.py ] && command -v python3 >/dev/null 2>&1; then
    if ! python3 scripts/verify_sanitization.py >/dev/null 2>&1; then
      echo "auto-sync: sanitization gate FAILED - not committing"
      exit 1
    fi
  fi
  git add -A
  git commit --quiet -m "chore(sync): $(hostname) $(date '+%Y-%m-%d %H:%M')" || true
fi

if ! git pull --rebase --autostash --quiet origin main; then
  git rebase --abort 2>/dev/null || true
  echo "auto-sync: pull/rebase conflict - tree left for manual review"
  exit 1
fi

git push --quiet origin main 2>/dev/null || true
