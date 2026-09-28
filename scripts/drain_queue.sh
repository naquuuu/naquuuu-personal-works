#!/usr/bin/env bash
# NAQUUUU M2 queue drainer - runs ON the relay host (systemd user timer).
#
# Usage:
#   drain_queue.sh [--dry-run]
#   drain_queue.sh --prune
#
# Drains at most NAQUUUU_DRAIN_BATCH pending jobs per tick (default 1, FIFO).
# A flock (or an equivalent mkdir-based lock when flock is absent) guarantees
# only one drain runs at a time; if no lock can be taken the drain exits without
# running unlocked. When the worker is not ready the drain exits 0 and leaves
# the queue untouched. A successful job's output is archived under done/; a
# failed job gets its attempts counter incremented and moves to failed/ once it
# reaches NAQUUUU_MAX_ATTEMPTS (validated to be at least 1). Each outcome is
# appended to $QDIR/completed.log as "<epoch> <id> <done|failed> <path>".
#
# Each pending job file stores the owner-provided job body verbatim (Tier 2
# workspace text only; never secrets). `--prune` removes the oldest done/ and
# failed/ entries beyond NAQUUUU_QUEUE_KEEP (default 50) and never touches
# pending/.
#
# Worker SSH uses a dedicated key (NAQUUUU_WORKER_KEY, default
# ~/.ssh/id_ed25519_worker) with IdentitiesOnly=yes so the GitHub deploy key is
# never selected; a missing worker key file counts as "not ready" and the queue
# is left alone. The remote run is bounded by NAQUUUU_JOB_TIMEOUT (default
# 1800s) plus SSH keepalives; the readiness probe keeps the short
# NAQUUUU_WORKER_REACH_TIMEOUT.
#
# `--dry-run` lists what would run and touches neither the network nor opencode.

set -u

DRY=0
PRUNE=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --prune) PRUNE=1 ;;
  esac
done

REPO="${NAQUUUU_WORKSPACE:-${NAQUUUU_REPO:-$HOME/naquuuu}}"
WHOST="${NAQUUUU_WORKER_HOST:-mipad-linux}"
WUSER="${NAQUUUU_WORKER_USER:-ubuntu}"
WREPO="${NAQUUUU_WORKER_REPO:-${NAQUUUU_WORKSPACE:-${NAQUUUU_REPO:-$HOME/naquuuu}}}"
WKEY="${NAQUUUU_WORKER_KEY:-$HOME/.ssh/id_ed25519_worker}"
QDIR="${NAQUUUU_QUEUE_DIR:-$HOME/.naquuuu/queue}"
RTIMEOUT="${NAQUUUU_WORKER_REACH_TIMEOUT:-5}"
JOB_TIMEOUT="${NAQUUUU_JOB_TIMEOUT:-1800}"
MAXATT="${NAQUUUU_MAX_ATTEMPTS:-3}"
BATCH="${NAQUUUU_DRAIN_BATCH:-1}"
QKEEP="${NAQUUUU_QUEUE_KEEP:-50}"

case "$RTIMEOUT" in ''|*[!0-9]*) RTIMEOUT=5 ;; esac
case "$JOB_TIMEOUT" in ''|*[!0-9]*) JOB_TIMEOUT=1800 ;; esac
case "$MAXATT" in ''|*[!0-9]*) MAXATT=1 ;; esac
[ "$MAXATT" -ge 1 ] 2>/dev/null || MAXATT=1
case "$BATCH" in ''|*[!0-9]*|0) BATCH=1 ;; esac
case "$QKEEP" in ''|*[!0-9]*) QKEEP=50 ;; esac

PENDING="$QDIR/pending"
DONE="$QDIR/done"
FAILED="$QDIR/failed"
LOCK="$QDIR/drain.lock"
LOCKDIR="$QDIR/drain.lock.d"

SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout="$RTIMEOUT" -o StrictHostKeyChecking=accept-new)
SSH_KEY=(-i "$WKEY" -o IdentitiesOnly=yes)
RUN_SSH_OPTS=("${SSH_OPTS[@]}" "${SSH_KEY[@]}" -o ServerAliveInterval=30 -o ServerAliveCountMax=3)
TARGET="$WUSER@$WHOST"

diag() { printf 'drain_queue: %s\n' "$*" >&2; }

# Job ids are "<epoch>-<random>"; anything else must be derived from the file.
is_valid_id() {
  [[ "${1:-}" =~ ^[0-9]+-[0-9]+$ ]]
}

# Readiness probe: the worker key must exist, and the worker must have both the
# repo and the executor. Missing key/repo/script means "not ready" so the queue
# is left alone rather than falling back to another identity.
worker_ready() {
  if [ ! -f "$WKEY" ]; then
    diag "worker key $WKEY missing; treating worker as not ready"
    return 1
  fi
  local probe
  probe="$(printf 'test -d %q && test -f %q' "$WREPO" "$WREPO/scripts/worker_exec.sh")"
  ssh "${SSH_OPTS[@]}" "${SSH_KEY[@]}" "$TARGET" "$probe" >/dev/null 2>&1
}

# One line per outcome in $QDIR/completed.log: "<epoch> <id> <done|failed> <path>".
log_completed() {
  printf '%s %s %s %s\n' "$(date +%s)" "$1" "$2" "$3" >> "$QDIR/completed.log" 2>/dev/null || true
}

# Copy header lines then a blank line then the exact task body into $2. An empty
# or "-" agent is normalized to empty; an id that is not "<digits>-<digits>" is
# discarded so the caller derives it from the filename.
parse_job() {
  local file="$1" bodyfile="$2" line seen
  J_ID=""
  J_CREATED=""
  J_AGENT=""
  J_ATTEMPTS=0
  : > "$bodyfile"
  seen=0
  while IFS= read -r line || [ -n "$line" ]; do
    if [ "$seen" -eq 0 ]; then
      if [ -z "$line" ]; then
        seen=1
        continue
      fi
      case "$line" in
        "id: "*) J_ID="${line#id: }" ;;
        "created: "*) J_CREATED="${line#created: }" ;;
        "agent: "*) J_AGENT="${line#agent: }" ;;
        "attempts: "*) J_ATTEMPTS="${line#attempts: }" ;;
      esac
    else
      printf '%s\n' "$line" >> "$bodyfile"
    fi
  done < "$file"
  case "$J_ATTEMPTS" in ''|*[!0-9]*) J_ATTEMPTS=0 ;; esac
  [ "$J_AGENT" = "-" ] && J_AGENT=""
  is_valid_id "$J_ID" || J_ID=""
}

# Run the worker executor with the job body on $1, agent on $2, combined output
# on $3. The remote run is bounded by NAQUUUU_JOB_TIMEOUT; the ssh (and thus the
# remote) exit code is returned.
run_remote() {
  local bodyfile="$1" agent="$2" out="$3"
  local b64 b64_q wrepo_q agent_q script
  b64="$(base64 < "$bodyfile" | tr -d '\n')"
  b64_q="$(printf '%q' "$b64")"
  wrepo_q="$(printf '%q' "$WREPO")"
  agent_q="$(printf '%q' "$agent")"
  script=$(cat <<EOS
set -u
WREPO=$wrepo_q
B64=$b64_q
AGENT=$agent_q
cd "\$WREPO" || exit 1
TASK=\$(printf '%s' "\$B64" | base64 -d)
exec bash scripts/worker_exec.sh -- "\$TASK" "\$AGENT"
EOS
)
  printf '%s\n' "$script" | timeout "${JOB_TIMEOUT}s" ssh "${RUN_SSH_OPTS[@]}" "$TARGET" bash -s > "$out" 2>&1
}

# Increment attempts; move to failed/ once MAXATT is reached. Every failure is
# logged to completed.log (terminal failures archiving under failed/).
fail_job() {
  local job="$1" bodyfile="$2" out="$3"
  local id="${J_ID:-$(basename "$job" .job)}"
  is_valid_id "$id" || id="$(basename "$job" .job)"
  J_ATTEMPTS=$((J_ATTEMPTS + 1))
  if [ "$J_ATTEMPTS" -ge "$MAXATT" ]; then
    {
      printf 'id: %s\n' "$id"
      printf 'created: %s\n' "$J_CREATED"
      printf 'agent: %s\n' "$J_AGENT"
      printf 'attempts: %s\n' "$J_ATTEMPTS"
      printf '\n'
      cat "$bodyfile"
    } > "$FAILED/$id.job.tmp"
    chmod 600 "$FAILED/$id.job.tmp"
    mv "$FAILED/$id.job.tmp" "$FAILED/$id.job"
    [ -f "$out" ] && mv "$out" "$FAILED/$id.out"
    rm -f "$job"
    log_completed "$id" failed "$FAILED/$id.job"
    diag "job $id failed after $J_ATTEMPTS attempt(s); moved to failed/"
  else
    {
      printf 'id: %s\n' "$id"
      printf 'created: %s\n' "$J_CREATED"
      printf 'agent: %s\n' "$J_AGENT"
      printf 'attempts: %s\n' "$J_ATTEMPTS"
      printf '\n'
      cat "$bodyfile"
    } > "$job.tmp"
    chmod 600 "$job.tmp"
    mv "$job.tmp" "$job"
    rm -f "$out"
    log_completed "$id" failed "$job"
    diag "job $id failed (attempt $J_ATTEMPTS/$MAXATT); left pending"
  fi
}

process_job() {
  local job="$1" bodyfile out rc id
  bodyfile="$(mktemp "${TMPDIR:-/tmp}/naquuuu-job.XXXXXX")" || return 0
  out="$(mktemp "${TMPDIR:-/tmp}/naquuuu-out.XXXXXX")" || { rm -f "$bodyfile"; return 0; }
  parse_job "$job" "$bodyfile"
  id="${J_ID:-$(basename "$job" .job)}"
  is_valid_id "$id" || id="$(basename "$job" .job)"
  run_remote "$bodyfile" "$J_AGENT" "$out"
  rc=$?
  if [ "$rc" -eq 0 ]; then
    mv "$job" "$DONE/$id.job"
    mv "$out" "$DONE/$id.out"
    log_completed "$id" done "$DONE/$id.job"
    diag "job $id done"
  else
    fail_job "$job" "$bodyfile" "$out"
  fi
  rm -f "$bodyfile"
}

# Retention: remove the oldest done/ and failed/ job entries beyond QKEEP (and
# their matching .out), then cap completed.log to the newest QKEEP lines.
# pending/ is never touched.
prune_queue() {
  local list f total=0 base dir
  list="$(mktemp "${TMPDIR:-/tmp}/naquuuu-prune.XXXXXX")" || return 0
  {
    [ -d "$DONE" ] && find "$DONE" -maxdepth 1 -type f -name '*.job' -printf '%T@ %p\n' 2>/dev/null
    [ -d "$FAILED" ] && find "$FAILED" -maxdepth 1 -type f -name '*.job' -printf '%T@ %p\n' 2>/dev/null
  } | sort -nr | cut -d ' ' -f 2- > "$list"
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    total=$((total + 1))
    if [ "$total" -gt "$QKEEP" ]; then
      dir="$(dirname "$f")"
      base="$(basename "$f" .job)"
      rm -f "$f" "$dir/$base.out"
    fi
  done < "$list"
  rm -f "$list"
  if [ -f "$QDIR/completed.log" ]; then
    tail -n "$QKEEP" "$QDIR/completed.log" > "$QDIR/completed.log.tmp" 2>/dev/null \
      && mv "$QDIR/completed.log.tmp" "$QDIR/completed.log"
  fi
}

if [ "$DRY" -eq 0 ]; then
  mkdir -p "$PENDING" "$DONE" "$FAILED"
  chmod 700 "$QDIR" 2>/dev/null || true
  if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK"
    if ! flock -n 9; then
      exit 0
    fi
  else
    # No flock: use an equivalent mkdir-based lock. If it cannot be taken
    # because another drain holds it, exit 0; if it cannot be created at all,
    # fail closed (exit non-zero) rather than running unlocked.
    if mkdir "$LOCKDIR" 2>/dev/null; then
      printf '%s\n' "$$" > "$LOCKDIR/pid" 2>/dev/null || true
      trap 'rm -rf "$LOCKDIR" 2>/dev/null' EXIT INT TERM HUP
    elif [ -d "$LOCKDIR" ]; then
      oldpid="$(cat "$LOCKDIR/pid" 2>/dev/null || true)"
      case "$oldpid" in ''|*[!0-9]*) oldpid="" ;; esac
      if [ -n "$oldpid" ] && ! kill -0 "$oldpid" 2>/dev/null; then
        rm -rf "$LOCKDIR" 2>/dev/null
        if mkdir "$LOCKDIR" 2>/dev/null; then
          printf '%s\n' "$$" > "$LOCKDIR/pid" 2>/dev/null || true
          trap 'rm -rf "$LOCKDIR" 2>/dev/null' EXIT INT TERM HUP
        else
          diag "cannot acquire lock dir $LOCKDIR; refusing to run unlocked"
          exit 1
        fi
      else
        exit 0
      fi
    else
      diag "cannot create lock dir $LOCKDIR (no flock); refusing to run unlocked"
      exit 1
    fi
  fi
fi

if [ "$PRUNE" -eq 1 ]; then
  prune_queue
  exit 0
fi

JOBS=()
while IFS= read -r f; do
  JOBS+=("$f")
done < <(find "$PENDING" -maxdepth 1 -type f -name '*.job' 2>/dev/null | sort)

if [ "${#JOBS[@]}" -eq 0 ]; then
  exit 0
fi

if [ "$DRY" -eq 1 ]; then
  n=0
  for job in "${JOBS[@]}"; do
    [ "$n" -ge "$BATCH" ] && break
    n=$((n + 1))
    printf 'drain_queue (dry-run): would drain %s\n' "$job"
  done
  exit 0
fi

if ! worker_ready; then
  exit 0
fi

n=0
for job in "${JOBS[@]}"; do
  [ "$n" -ge "$BATCH" ] && break
  n=$((n + 1))
  process_job "$job"
done
exit 0
