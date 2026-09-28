#!/usr/bin/env bash
# NAQUUUU M2 worker executor - runs ON the worker (e.g. mipad-linux).
#
# Usage:
#   worker_exec.sh [--dry-run] [--] <task> [agent]
#
# Behaviour:
#   1. cd into the workspace repo and best-effort `git pull --ff-only`
#   2. run opencode against the warm server (`--attach`) when possible
#   3. fall back to a plain `opencode run` when the attached run fails
#   4. commit and push are not expected and not credentialed on this replica
#      (this is not enforced in code; the worker simply has no push credential)
#
# stdout carries agent output; diagnostics go to stderr; the opencode exit
# code passes through. `--dry-run` prints the commands and exits 0.

set -u

DRY=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY=1
  shift
fi
if [ "${1:-}" = "--" ]; then
  shift
fi

TASK="${1:-}"
AGENT="${2:-}"

if [ -z "$TASK" ]; then
  echo "usage: worker_exec.sh [--dry-run] [--] <task> [agent]" >&2
  exit 2
fi

REPO="${NAQUUUU_WORKER_REPO:-${NAQUUUU_WORKSPACE:-${NAQUUUU_REPO:-$HOME/naquuuu}}}"
OPENCODE="${NAQUUUU_OPENCODE:-opencode}"
ATTACH="${OPENCODE_ATTACH:-http://127.0.0.1:4096}"

diag() { printf 'worker_exec: %s\n' "$*" >&2; }

if [ "$DRY" -eq 0 ] && [ ! -d "$REPO" ]; then
  diag "no repo at $REPO"
  exit 1
fi

# Build the opencode argument vector without eval so arbitrary task text
# (spaces, quotes, newlines, UTF-8) is passed through unchanged.
mk_cmd() {
  # $1 = attach | plain
  CMD=("$OPENCODE" run)
  if [ "$1" = "attach" ]; then
    CMD+=(--attach "$ATTACH")
  fi
  CMD+=(--dir "$REPO")
  if [ -n "$AGENT" ]; then
    CMD+=(--agent "$AGENT")
  fi
  CMD+=("$TASK")
}

if [ "$DRY" -eq 1 ]; then
  printf 'git -C %s pull --ff-only\n' "$REPO"
  mk_cmd attach
  printf 'worker_exec: %s\n' "$(printf '%q ' "${CMD[@]}")"
  mk_cmd plain
  printf 'worker_exec (fallback): %s\n' "$(printf '%q ' "${CMD[@]}")"
  exit 0
fi

cd "$REPO" || { diag "cannot cd to $REPO"; exit 1; }

if git rev-parse --git-dir >/dev/null 2>&1; then
  if ! git pull --ff-only --quiet; then
    diag "git pull --ff-only failed; continuing on the current tree"
  fi
else
  diag "not a git work tree at $REPO; skipping pull"
fi

mk_cmd attach
"${CMD[@]}"
rc=$?
if [ "$rc" -ne 0 ]; then
  diag "attached run exited $rc; retrying without --attach"
  mk_cmd plain
  "${CMD[@]}"
  rc=$?
fi
exit "$rc"
