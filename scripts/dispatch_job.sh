#!/usr/bin/env bash
# NAQUUUU M2 dispatcher - runs ON the relay host.
#
# Usage:
#   dispatch_job.sh [--local] [--agent NAME] [--dry-run] [--] <task>
#   dispatch_job.sh [--local] [--agent NAME] [--dry-run]        # task on stdin
#
# Light work (--local) runs opencode on the relay host synchronously (RELAY_PLAN
# section 1). Heavy work (the default) runs scripts/worker_exec.sh on the worker
# over SSH when the worker is reachable; when it is not, the job is written to
# the durable queue and "QUEUED <id>" is printed on stdout. A reachable worker
# whose remote run fails non-zero is also queued, never dropped.
#
# Worker SSH uses a dedicated key (NAQUUUU_WORKER_KEY, default
# ~/.ssh/id_ed25519_worker) with IdentitiesOnly=yes so the GitHub deploy key is
# never selected; a missing worker key file counts as "not ready" and the job
# queues rather than silently falling back to another identity. The remote run
# is bounded by NAQUUUU_JOB_TIMEOUT (default 1800s) plus SSH keepalives; the
# readiness probe keeps the short NAQUUUU_WORKER_REACH_TIMEOUT.
#
# The task text crosses the SSH boundary base64-encoded, so arbitrary content
# (spaces, quotes, newlines, UTF-8) survives. Job bodies are stored verbatim
# (Tier 2 workspace text only) and are owner-provided. No secrets: no private
# keys, and only public keys ever reach a remote host.

set -u

LOCAL=0
DRY=0
AGENT=""

usage() {
  echo "usage: dispatch_job.sh [--local] [--agent NAME] [--dry-run] [--] <task>" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --local) LOCAL=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --agent) AGENT="${2:-}"; shift; [ $# -gt 0 ] && shift ;;
    --agent=*) AGENT="${1#--agent=}"; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    *) break ;;
  esac
done

TASK="$*"
if [ -z "$TASK" ] && [ ! -t 0 ]; then
  TASK="$(cat)"
fi
if [ -z "$TASK" ]; then
  usage
  exit 2
fi

REPO="${NAQUUUU_REPO:-$HOME/naquuuu}"
OPENCODE="${NAQUUUU_OPENCODE:-opencode}"
WHOST="${NAQUUUU_WORKER_HOST:-mipad-linux}"
WUSER="${NAQUUUU_WORKER_USER:-ubuntu}"
WREPO="${NAQUUUU_WORKER_REPO:-${NAQUUUU_REPO:-$HOME/naquuuu}}"
WKEY="${NAQUUUU_WORKER_KEY:-$HOME/.ssh/id_ed25519_worker}"
QDIR="${NAQUUUU_QUEUE_DIR:-$HOME/.naquuuu/queue}"
RTIMEOUT="${NAQUUUU_WORKER_REACH_TIMEOUT:-5}"
JOB_TIMEOUT="${NAQUUUU_JOB_TIMEOUT:-1800}"

case "$RTIMEOUT" in ''|*[!0-9]*) RTIMEOUT=5 ;; esac
case "$JOB_TIMEOUT" in ''|*[!0-9]*) JOB_TIMEOUT=1800 ;; esac

SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout="$RTIMEOUT" -o StrictHostKeyChecking=accept-new)
SSH_KEY=(-i "$WKEY" -o IdentitiesOnly=yes)
RUN_SSH_OPTS=("${SSH_OPTS[@]}" "${SSH_KEY[@]}" -o ServerAliveInterval=30 -o ServerAliveCountMax=3)
TARGET="$WUSER@$WHOST"

diag() { printf 'dispatch_job: %s\n' "$*" >&2; }

# Job ids are "<epoch>-<random>"; anything else must be derived from the file.
is_valid_id() {
  [[ "${1:-}" =~ ^[0-9]+-[0-9]+$ ]]
}

# Non-interactive readiness probe. Reachable means the worker key exists AND the
# key works AND the worker has both the repo and the executor; a missing key,
# repo, or script is "not ready" so the job queues instead of failing or
# falling back to another identity.
worker_ready() {
  if [ ! -f "$WKEY" ]; then
    diag "worker key $WKEY missing; treating worker as not ready"
    return 1
  fi
  local probe
  probe="$(printf 'test -d %q && test -f %q' "$WREPO" "$WREPO/scripts/worker_exec.sh")"
  ssh "${SSH_OPTS[@]}" "${SSH_KEY[@]}" "$TARGET" "$probe" >/dev/null 2>&1
}

# Run worker_exec.sh on the worker. The task is base64-encoded locally and
# decoded on the worker; the repo path and agent are %q-quoted so the generated
# script embeds them safely. The remote run is bounded by NAQUUUU_JOB_TIMEOUT.
run_on_worker() {
  local task="$1" agent="${2:-}"
  local b64 b64_q wrepo_q agent_q script
  b64="$(printf '%s' "$task" | base64 | tr -d '\n')"
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
  printf '%s\n' "$script" | timeout "${JOB_TIMEOUT}s" ssh "${RUN_SSH_OPTS[@]}" "$TARGET" bash -s
}

# Persist a job under $QDIR/pending and print "QUEUED <id>". The body is stored
# verbatim, atomically (write <file>.tmp then mv into place). An empty agent is
# stored empty (never "-") so a job with no agent runs without --agent.
enqueue_job() {
  local task="$1" agent="${2:-}"
  local pending="$QDIR/pending" epoch rand id f tmp
  mkdir -p "$pending" "$QDIR/done" "$QDIR/failed"
  chmod 700 "$QDIR"
  epoch="$(date +%s)"
  rand="$RANDOM"
  id="$epoch-$rand"
  is_valid_id "$id" || id="$epoch-0"
  f="$pending/$id.job"
  while [ -e "$f" ] || [ -e "$f.tmp" ]; do
    rand="$RANDOM"
    id="$epoch-$rand"
    is_valid_id "$id" || id="$epoch-0"
    f="$pending/$id.job"
  done
  tmp="$f.tmp"
  {
    printf 'id: %s\n' "$id"
    printf 'created: %s\n' "$epoch"
    printf 'agent: %s\n' "$agent"
    printf 'attempts: 0\n'
    printf '\n'
    printf '%s\n' "$task"
  } > "$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$f"
  printf 'QUEUED %s\n' "$id"
}

run_local() {
  local -a cmd=("$OPENCODE" run --dir "$REPO")
  if [ -n "$AGENT" ]; then
    cmd+=(--agent "$AGENT")
  fi
  cmd+=("$TASK")
  if [ "$DRY" -eq 1 ]; then
    printf 'dispatch_job (local): %s\n' "$(printf '%q ' "${cmd[@]}")"
    return 0
  fi
  "${cmd[@]}"
}

if [ "$DRY" -eq 1 ]; then
  if [ "$LOCAL" -eq 1 ]; then
    run_local
    exit 0
  fi
  printf 'reach check: ssh %s %s %s\n' "${SSH_OPTS[*]} ${SSH_KEY[*]}" "$TARGET" "<probe>"
  b64="$(printf '%s' "$TASK" | base64 | tr -d '\n')"
  printf 'dispatch (worker): timeout %ss ssh %s %s bash -s  <task base64: %s>\n' \
    "$JOB_TIMEOUT" "${RUN_SSH_OPTS[*]}" "$TARGET" "$b64"
  exit 0
fi

if [ "$LOCAL" -eq 1 ]; then
  run_local
  exit $?
fi

if worker_ready; then
  if run_on_worker "$TASK" "$AGENT"; then
    exit 0
  else
    rc=$?
    diag "remote run exited $rc; queueing the job instead of dropping it"
    enqueue_job "$TASK" "$AGENT"
    exit 0
  fi
fi

enqueue_job "$TASK" "$AGENT"
exit 0
