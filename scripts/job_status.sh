#!/usr/bin/env bash
# NAQUUUU M2 queue status - read-only summary for the relay host.
#
# Usage:
#   job_status.sh [--prune]
#
# Prints the pending/done/failed counts, the tail of completed.log, and the
# newest done/*.out contents. Read-only unless --prune is supplied. Exits 0
# for status even when the queue directory does not exist. Output is ASCII-only so it is
# safe on any terminal.

set -u

QDIR="${NAQUUUU_QUEUE_DIR:-$HOME/.naquuuu/queue}"

if [ "${1:-}" = "--prune" ]; then
  REPO="${NAQUUUU_WORKSPACE:-${NAQUUUU_REPO:-$HOME/naquuuu}}"
  DRAIN="$REPO/scripts/drain_queue.sh"
  if [ ! -f "$DRAIN" ]; then
    echo "job_status: queue drainer unavailable; retention not run" >&2
    exit 1
  fi
  bash "$DRAIN" --prune || exit $?
elif [ "$#" -gt 0 ]; then
  echo "usage: job_status.sh [--prune]" >&2
  exit 2
fi

count_jobs() {
  local dir="$1"
  if [ -d "$dir" ]; then
    find "$dir" -maxdepth 1 -type f -name '*.job' 2>/dev/null | wc -l | tr -d ' '
  else
    printf '0'
  fi
}

# Strip anything outside printable ASCII (keeping tab/CR/LF) so the output is
# ASCII-only; each non-ASCII byte becomes '?'.
ascii_filter() {
  LC_ALL=C tr -c '\11\12\15\40-\176' '?' 2>/dev/null || cat
}

printf 'naquuuu queue: %s\n' "$QDIR"
printf 'pending: %s\n' "$(count_jobs "$QDIR/pending")"
printf 'done:    %s\n' "$(count_jobs "$QDIR/done")"
printf 'failed:  %s\n' "$(count_jobs "$QDIR/failed")"

printf '\n-- completed.log (tail) --\n'
if [ -f "$QDIR/completed.log" ]; then
  tail -n 10 "$QDIR/completed.log" 2>/dev/null | ascii_filter
else
  printf '(none)\n'
fi

printf '\n-- newest done output --\n'
newest=""
if [ -d "$QDIR/done" ]; then
  newest="$(find "$QDIR/done" -maxdepth 1 -type f -name '*.out' -printf '%T@ %p\n' 2>/dev/null \
    | sort -n | tail -n 1 | cut -d ' ' -f 2-)"
fi
if [ -n "$newest" ] && [ -f "$newest" ]; then
  printf 'file: %s\n' "$newest"
  ascii_filter < "$newest"
else
  printf '(none)\n'
fi

exit 0
