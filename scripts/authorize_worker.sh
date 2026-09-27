#!/usr/bin/env bash
# NAQUUUU M2 worker trust helper - runs ON the worker, owner-invoked.
#
# Usage:
#   authorize_worker.sh <ssh-public-key>
#   authorize_worker.sh --key-file <path>
#   printf '%s\n' '<ssh-public-key>' | authorize_worker.sh
#
# Adds a relay public key to ~/.ssh/authorized_keys idempotently: a key whose
# body is already present is left alone. Creates ~/.ssh if missing and sets
# 700 on the directory and 600 on authorized_keys. Safe to re-run.
#
# No private keys, no secrets: the argument is a PUBLIC key.

set -u

KEY=""
case "${1:-}" in
  --key-file)
    FILE="${2:-}"
    if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
      echo "authorize_worker: --key-file needs an existing path" >&2
      exit 2
    fi
    KEY="$(cat "$FILE")"
    ;;
  --key-file=*)
    FILE="${1#--key-file=}"
    if [ ! -f "$FILE" ]; then
      echo "authorize_worker: --key-file needs an existing path" >&2
      exit 2
    fi
    KEY="$(cat "$FILE")"
    ;;
  -h|--help)
    echo "usage: authorize_worker.sh <ssh-public-key> | --key-file <path>" >&2
    exit 0
    ;;
  "")
    if [ ! -t 0 ]; then
      KEY="$(cat)"
    fi
    ;;
  *)
    KEY="$1"
    ;;
esac

KEY_LINE="$(printf '%s\n' "$KEY" | awk 'NF{print; exit}')"
if [ -z "$KEY_LINE" ]; then
  echo "usage: authorize_worker.sh <ssh-public-key> | --key-file <path>" >&2
  exit 2
fi

# The key body is the token right after the key type; this works even when the
# line carries authorized_keys options before the type.
BODY="$(printf '%s\n' "$KEY_LINE" | awk '{
  for (i = 1; i <= NF; i++) {
    if ($i ~ /^(ssh-|ecdsa-|sk-)/) { print $(i + 1); exit }
  }
}')"
if [ -z "$BODY" ]; then
  echo "authorize_worker: input does not look like an SSH public key" >&2
  exit 2
fi

SSH_DIR="$HOME/.ssh"
AUTH="$SSH_DIR/authorized_keys"

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
touch "$AUTH"
chmod 600 "$AUTH"

if awk -v b="$BODY" '{
  for (i = 1; i <= NF; i++) { if ($i == b) { found = 1 } }
} END { exit(found ? 0 : 1) }' "$AUTH"; then
  echo "authorize_worker: key already authorized (no change)"
else
  printf '%s\n' "$KEY_LINE" >> "$AUTH"
  chmod 600 "$AUTH"
  echo "authorize_worker: key added to $AUTH"
fi

exit 0
