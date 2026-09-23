#!/usr/bin/env python3
r"""
Host Readiness Check (host_check.py)

Usage:
  python scripts/host_check.py

Read-only readiness probe for the Hermes gateway and WhatsApp bridge lifecycle
on this host (pulled forward from Phase 4 per ADR-013). The script only reads
state: it never mutates Hermes, and it never prints `.env` values or the
WhatsApp allowlist (key names and present/missing markers only).

Checks (one PASS / WARN / FAIL line each):
  a. Hub git tree clean (WARN when dirty).
  b. Hermes install present at %LOCALAPPDATA%\hermes (or ~/.hermes); WARN when
     absent because Phase 2 may be stopped.
  c. Gateway status via `hermes gateway status`; falls back to logs/__gateway.lock
     with a WARN when the hermes binary cannot be found.
  d. Bridge singleton: the first integer in whatsapp/session/bridge.pid must map
     to a live process (FAIL on unparsable pid file or a stale pid).
  e. Bridge mode drift: the last `listening on port 3000 (mode: X)` line in
     whatsapp/bridge.log must match WHATSAPP_MODE in .env (FAIL on mismatch).
  f. Effective config presence: WHATSAPP_ENABLED / WHATSAPP_MODE /
     WHATSAPP_ALLOWED_USERS are present and non-empty in .env.

Exit codes: 0 = no FAIL, 1 = one or more FAIL. A WARN never fails the run.
"""

import os
import re
import sys
import shutil
import subprocess
import argparse

# Windows console UTF-8 fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

CONFIG_KEYS = ("WHATSAPP_ENABLED", "WHATSAPP_MODE", "WHATSAPP_ALLOWED_USERS")

BRIDGE_MODE_RE = re.compile(
    r"listening on port\s+3000\s*\(mode:\s*([^)]+?)\s*\)", re.IGNORECASE
)


def hermes_home():
    """Resolve the native Hermes install root for this host."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local"
        )
        return os.path.join(base, "hermes")
    return os.path.join(os.path.expanduser("~"), ".hermes")


def find_hermes_bin(home):
    """Locate the hermes executable: install bin dir first, then PATH."""
    for candidate in (
        os.path.join(home, "bin", "hermes.exe"),
        os.path.join(home, "bin", "hermes"),
    ):
        if os.path.isfile(candidate):
            return candidate
    return shutil.which("hermes")


def pid_alive(pid):
    """Return True when a live process owns pid. Never signals the process.

    On Windows, OpenProcess is used instead of os.kill(pid, 0): the os.kill
    docs still describe TerminateProcess semantics for arbitrary sig, so the
    strictly read-only probe is the Win32 query API.
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel32.GetExitCodeProcess.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int

        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def read_env(home):
    """Parse <home>/.env into a dict of key -> value (values never printed).

    Returns None when the file is missing or unreadable.
    """
    path = os.path.join(home, ".env")
    values = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.lstrip("\ufeff").strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if key.startswith("export "):
                    key = key[len("export "):].strip()
                if key:
                    values[key] = value.strip().strip('"').strip("'")
    except OSError:
        return None
    return values


def check_hub_tree(hub_root):
    try:
        result = subprocess.run(
            ["git", "-C", hub_root, "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except Exception as exc:
        return WARN, f"could not run git status ({exc.__class__.__name__})"
    if result.returncode != 0:
        return WARN, "git status failed (hub root is not a git repository?)"
    changed = [line for line in result.stdout.splitlines() if line.strip()]
    if changed:
        return WARN, f"dirty ({len(changed)} changed path(s))"
    return PASS, "clean"


def check_hermes_install(home):
    if os.path.isdir(home):
        return PASS, f"present at {home}"
    return WARN, f"not found at {home} (Phase 2 may be stopped)"


def check_gateway(home):
    exe = find_hermes_bin(home)
    if exe:
        try:
            result = subprocess.run(
                [exe, "gateway", "status"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except Exception as exc:
            return WARN, f"`hermes gateway status` could not run ({exc.__class__.__name__})"
        output = f"{result.stdout}\n{result.stderr}".lower()
        if "not running" in output:
            return WARN, "gateway status reports: not running"
        if "running" in output:
            return PASS, "gateway status reports: running"
        return WARN, f"gateway status output unrecognized (exit {result.returncode})"
    lock = os.path.join(home, "logs", "__gateway.lock")
    if os.path.isfile(lock):
        return WARN, "hermes binary not found; logs/__gateway.lock present (may be stale)"
    return WARN, "hermes binary not found; no __gateway.lock, status unverified"


def check_bridge_pid(home):
    pid_file = os.path.join(home, "whatsapp", "session", "bridge.pid")
    if not os.path.isfile(pid_file):
        return WARN, "whatsapp/session/bridge.pid absent (bridge not started?)"
    try:
        with open(pid_file, "r", encoding="utf-8", errors="replace") as fh:
            first_line = fh.readline()
    except OSError as exc:
        return WARN, f"bridge.pid unreadable ({exc.__class__.__name__})"
    match = re.search(r"\d+", first_line)
    if not match:
        return FAIL, "bridge.pid has no valid PID on its first line"
    pid = int(match.group(0))
    if pid <= 0:
        return FAIL, "bridge.pid contains a non-positive PID"
    if pid_alive(pid):
        return PASS, f"bridge process alive (pid {pid})"
    return FAIL, f"stale bridge.pid: pid {pid} is not running"


def check_bridge_mode(home, env):
    if env is None:
        return WARN, "mode drift unverified: .env missing"
    env_mode = env.get("WHATSAPP_MODE", "").strip()
    log_path = os.path.join(home, "whatsapp", "bridge.log")
    last_mode = None
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                match = BRIDGE_MODE_RE.search(line)
                if match:
                    last_mode = match.group(1).strip()
    except OSError:
        return WARN, "mode drift unverified: whatsapp/bridge.log missing"
    if not last_mode:
        return WARN, "mode drift unverified: no 'listening on port 3000' line in bridge.log"
    if not env_mode:
        return WARN, "mode drift unverified: WHATSAPP_MODE missing or empty in .env"
    if last_mode.casefold() == env_mode.casefold():
        return PASS, "bridge effective mode matches WHATSAPP_MODE"
    return FAIL, (
        f"bridge mode drift: bridge.log last started as '{last_mode}' "
        "but .env WHATSAPP_MODE differs"
    )


def check_config_presence(env):
    if env is None:
        return WARN, "unverified: .env missing (cannot confirm effective config)"
    report = " ".join(
        f"{key}={'present' if env.get(key) else 'missing'}" for key in CONFIG_KEYS
    )
    if all(env.get(key) for key in CONFIG_KEYS):
        return PASS, report
    return FAIL, report


def run_checks():
    hub_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    home = hermes_home()
    env = read_env(home)

    checks = [
        ("(a) hub tree", check_hub_tree(hub_root)),
        ("(b) hermes install", check_hermes_install(home)),
        ("(c) gateway singleton", check_gateway(home)),
        ("(d) bridge singleton", check_bridge_pid(home)),
        ("(e) bridge mode drift", check_bridge_mode(home, env)),
        ("(f) effective config", check_config_presence(env)),
    ]

    print("=" * 78)
    print("  NAQUUUU HOST READINESS CHECK - Hermes gateway + WhatsApp bridge")
    print("=" * 78)
    print(f"  hub root:    {hub_root}")
    print(f"  hermes home: {home}")
    print("-" * 78)
    for label, (status, message) in checks:
        print(f"{status}  {label}: {message}")
    print("-" * 78)

    passed = sum(1 for _, (status, _) in checks if status == PASS)
    warned = sum(1 for _, (status, _) in checks if status == WARN)
    failed = sum(1 for _, (status, _) in checks if status == FAIL)
    print(f"SUMMARY: {passed} PASS, {warned} WARN, {failed} FAIL")
    if failed:
        print("RESULT: NOT READY")
        return 1
    print("RESULT: READY" + (" (with warnings)" if warned else ""))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read-only readiness check for the Hermes gateway and WhatsApp bridge lifecycle"
    )
    parser.parse_args()

    try:
        sys.exit(run_checks())
    except Exception as exc:
        print(f"FAIL  host check aborted: {exc.__class__.__name__}")
        sys.exit(1)
