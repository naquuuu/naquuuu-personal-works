#!/usr/bin/env python3
"""Check or repair the repo <-> relay-host persona mirror using hashes only.

Local side: the fenced persona block in internal-docs/relay/WHATSAPP_SOUL.md.
Remote side: ~/.hermes/SOUL.md on the relay host, normalized for line endings.
Only booleans and shortened SHA-256 digests are printed; persona text and host
state never enter agent context (AGENTS.md Model-Input Boundary).

Modes:
  --check (default): compare hashes, exit 1 on drift or an unreachable host.
  --apply: back up the host copy, write the repo block, then re-check.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def normalized(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.rstrip("\n") + "\n"


def repo_persona_block() -> str:
    text = (HERE.parent / "internal-docs/relay/WHATSAPP_SOUL.md").read_text(encoding="utf-8")
    match = re.search(r"(?ms)^```text\n(.*?)^```\s*$", text)
    if not match:
        raise ValueError("persona fence missing in WHATSAPP_SOUL.md")
    return match.group(1)


def digest(text: str) -> str:
    return hashlib.sha256(normalized(text).encode("utf-8")).hexdigest()


def ssh(target: str, script: str, timeout: int = 25) -> tuple[int, str]:
    payload = base64.b64encode(script.encode("utf-8")).decode("ascii")
    try:
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", target,
             f"printf %s {payload} | base64 -d | python3"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return result.returncode, result.stdout


REMOTE_HASH = '''
import hashlib, pathlib
p = pathlib.Path.home() / ".hermes/SOUL.md"
t = p.read_text(encoding="utf-8").replace("\\r\\n", "\\n").rstrip("\\n") + "\\n"
print("host_sha256=" + hashlib.sha256(t.encode("utf-8")).hexdigest())
'''

REMOTE_APPLY = '''
import datetime, hashlib, pathlib, shutil
p = pathlib.Path.home() / ".hermes/SOUL.md"
new = {encoded!r}
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
backup = p.with_name(p.name + ".bak-" + stamp)
shutil.copy2(p, backup)
p.write_text(new, encoding="utf-8")
t = p.read_text(encoding="utf-8").replace("\\r\\n", "\\n").rstrip("\\n") + "\\n"
print("host_sha256=" + hashlib.sha256(t.encode("utf-8")).hexdigest())
print("host_backup_stamp=" + stamp)
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--target", default=os.environ.get("NAQUUUU_RELAY_SSH_TARGET", "ubuntu@100.87.52.117"))
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@-]*", args.target):
        print("soul_mirror=invalid_target")
        return 2
    if not shutil.which("ssh"):
        print("soul_mirror=ssh_unavailable")
        return 2
    try:
        block = repo_persona_block()
    except (OSError, ValueError):
        print("soul_mirror=repo_persona_unavailable")
        return 2
    repo_digest = digest(block)
    print(f"soul_repo_sha256={repo_digest[:16]}")
    if args.apply:
        code, out = ssh(args.target, REMOTE_APPLY.format(encoded=block), timeout=40)
    else:
        code, out = ssh(args.target, REMOTE_HASH)
    host_digest = None
    for line in out.splitlines():
        if line.startswith("host_sha256="):
            host_digest = line.split("=", 1)[1].strip()
        if line.startswith("host_backup_stamp="):
            print("soul_mirror_backup_stamp=" + line.split("=", 1)[1].strip())
    if code != 0 or not host_digest:
        print("soul_mirror=host_unavailable")
        return 1
    print(f"soul_host_sha256={host_digest[:16]}")
    if host_digest == repo_digest:
        print("soul_mirror=match")
        return 0
    print("soul_mirror=drift")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
