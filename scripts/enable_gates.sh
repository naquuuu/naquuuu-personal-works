#!/bin/sh
# NAQUUUU gate arming + status (Linux hosts: VPS, home server).
#
# Usage:
#   sh scripts/enable_gates.sh            arm the gate, run it once, report
#   sh scripts/enable_gates.sh --check    report only; changes nothing
#   sh scripts/enable_gates.sh --help
#
# Arms `git config core.hooksPath .githooks` — the same line
# provision_home_server.sh sets for the home server; the VPS path had no step
# for it anywhere. Then verifies the gate can actually run, because a hook path
# that points at a missing script, a non-executable hook, or a host without
# Python arms nothing while looking armed.
#
# Services are observed, never touched: this script does not start, stop, or
# restart `opencode serve` or anything else. Safe to re-run (idempotent).
# No secrets in this file; the serve port is never printed.

set -u

CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    -h|--help)
      echo "usage: sh scripts/enable_gates.sh [--check]"
      exit 0
      ;;
    *)
      echo "enable-gates: unknown argument '$arg' (expected --check or --help)"
      exit 2
      ;;
  esac
done

if [ -n "${NAQUUUU_REPO:-}" ]; then
  REPO="$NAQUUUU_REPO"
  REPO_SOURCE="NAQUUUU_REPO"
elif [ -n "${NAQUUUU_WORKSPACE:-}" ]; then
  REPO="$NAQUUUU_WORKSPACE"
  REPO_SOURCE="NAQUUUU_WORKSPACE"
else
  REPO="$HOME/naquuuu"
  REPO_SOURCE="default \$HOME/naquuuu"
fi
GATE="scripts/verify_sanitization.py"
HOOKS_DIR=".githooks"

say() { printf '%s\n' "$1"; }

say "enable-gates: mode = $([ "$CHECK_ONLY" -eq 1 ] && echo 'check (read-only)' || echo 'arm')"
say "enable-gates: repo root = $REPO (source: $REPO_SOURCE)"

if [ ! -d "$REPO/.git" ]; then
  say "enable-gates: BLOCKED - no git repository at '$REPO'"
  say "enable-gates: fix: set NAQUUUU_REPO or NAQUUUU_WORKSPACE to the hub root, then re-run"
  exit 1
fi
cd "$REPO" || exit 1

rc=0

# 1. hooks path ---------------------------------------------------------
if [ "$CHECK_ONLY" -eq 1 ]; then
  current=$(git config --get core.hooksPath 2>/dev/null || true)
  if [ "$current" = "$HOOKS_DIR" ]; then
    say "hooks: core.hooksPath = $current (armed)"
  else
    say "hooks: core.hooksPath = ${current:-<unset>} (NOT armed; expected $HOOKS_DIR)"
    rc=1
  fi
else
  git config core.hooksPath "$HOOKS_DIR"
  say "hooks: core.hooksPath = $(git config --get core.hooksPath) (armed)"
fi

# 2. hook files must exist and be executable, or git silently skips them ---
if [ ! -d "$HOOKS_DIR" ]; then
  say "hooks: MISSING directory '$HOOKS_DIR'"
  rc=1
else
  for hook in pre-commit pre-push; do
    hook_path="$HOOKS_DIR/$hook"
    if [ ! -f "$hook_path" ]; then
      say "hooks: MISSING '$hook_path'"
      rc=1
    elif [ -x "$hook_path" ]; then
      say "hooks: $hook_path present and executable"
    elif [ "$CHECK_ONLY" -eq 1 ]; then
      say "hooks: $hook_path present but NOT executable (git would skip it)"
      rc=1
    else
      chmod +x "$hook_path"
      say "hooks: $hook_path present, chmod +x applied"
    fi
  done
fi

# 3. gate prerequisites: exactly which one is missing ------------------------
PY=""
if command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
fi

if [ -f "$GATE" ]; then
  say "gate: $GATE present"
else
  say "gate: MISSING $GATE (the hooks would skip the sanitization gate)"
  rc=1
fi
if [ -n "$PY" ]; then
  say "gate: interpreter $PY ($(command -v "$PY"))"
else
  say "gate: MISSING python3 (and python); the sanitization gate cannot run"
  rc=1
fi

# 4. run the gate once and report by exit code ------------------------------
if [ -f "$GATE" ] && [ -n "$PY" ]; then
  if "$PY" "$GATE"; then
    say "gate: PASS (exit 0)"
  else
    gate_rc=$?
    say "gate: FAIL (exit $gate_rc)"
    rc=1
  fi
else
  say "gate: NOT RUN (prerequisite missing)"
fi

# 5. opencode serve: observation only --------------------------------------
if command -v pgrep >/dev/null 2>&1; then
  if pgrep -f "opencode serve" >/dev/null 2>&1; then
    say "serve: an 'opencode serve' process exists (command line not printed)"
  else
    say "serve: no 'opencode serve' process found"
  fi
else
  say "serve: pgrep unavailable; process not checked"
fi
if [ -n "${NAQUUUU_OPENCODE_SERVE_PORT:-}" ]; then
  if command -v curl >/dev/null 2>&1; then
    if curl -s -o /dev/null --max-time 2 "http://127.0.0.1:${NAQUUUU_OPENCODE_SERVE_PORT}/"; then
      say "serve: loopback probe answered"
    else
      say "serve: loopback probe did not answer"
    fi
  else
    say "serve: curl unavailable; loopback probe skipped"
  fi
else
  say "serve: not probed (set NAQUUUU_OPENCODE_SERVE_PORT to probe; the value is never printed)"
fi

if [ "$rc" -eq 0 ]; then
  say "enable-gates: OK - gate armed and runnable"
else
  say "enable-gates: NOT ARMED OR NOT RUNNABLE - fix the lines marked MISSING / NOT armed, then re-run"
fi
exit "$rc"
