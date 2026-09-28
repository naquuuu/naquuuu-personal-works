#!/usr/bin/env bash
# Isolated queue tests: no worker, keys, models or live queue required.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT
export NAQUUUU_WORKSPACE="$ROOT"
export NAQUUUU_QUEUE_DIR="$TEST_ROOT/queue with spaces"
export NAQUUUU_WORKER_KEY="$TEST_ROOT/missing-key"
bash "$ROOT/scripts/dispatch_job.sh" 'Synthetic durable queue canary' >/dev/null
test "$(find "$NAQUUUU_QUEUE_DIR/pending" -name '*.job' | wc -l)" -eq 1
bash "$ROOT/scripts/drain_queue.sh"
test "$(find "$NAQUUUU_QUEUE_DIR/pending" -name '*.job' | wc -l)" -eq 1
for n in 1 2 3; do
  printf 'synthetic output %s\n' "$n" > "$NAQUUUU_QUEUE_DIR/done/1-$n.out"
  printf 'synthetic job\n' > "$NAQUUUU_QUEUE_DIR/done/1-$n.job"
  touch -t "20260101000$n" "$NAQUUUU_QUEUE_DIR/done/1-$n.job" "$NAQUUUU_QUEUE_DIR/done/1-$n.out"
done
NAQUUUU_QUEUE_KEEP=1 bash "$ROOT/scripts/job_status.sh" --prune > "$TEST_ROOT/status"
test -f "$NAQUUUU_QUEUE_DIR/done/1-3.job"
test ! -e "$NAQUUUU_QUEUE_DIR/done/1-1.job"
test ! -e "$NAQUUUU_QUEUE_DIR/done/1-2.out"
test "$(find "$NAQUUUU_QUEUE_DIR/pending" -name '*.job' | wc -l)" -eq 1
grep -q 'synthetic output 3' "$TEST_ROOT/status"
echo 'PASS: offline durability, newest retention, spaced paths, status prune, pending preservation'
