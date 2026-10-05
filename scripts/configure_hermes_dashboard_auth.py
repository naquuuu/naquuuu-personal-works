#!/usr/bin/env python3
"""Interactively configure Hermes dashboard Basic Auth without echoing secrets."""
from __future__ import annotations

import getpass
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
import tempfile
from datetime import datetime, timezone


def load_hash_helper():
    # Import the Hermes bootstrap before plugin code so the venv package paths resolve.
    import hermes_bootstrap  # noqa: F401

    from plugins.dashboard_auth.basic import hash_password

    return hash_password


def quote_env(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def update_env_file(path: Path, values: dict[str, str]) -> Path:
    if path.is_symlink():
        raise RuntimeError("Refusing to modify a symlinked Hermes .env file.")
    if not path.is_file():
        raise RuntimeError("Hermes .env file is missing; refusing to create an incomplete config.")

    original = path.read_text(encoding="utf-8")
    backup = path.with_name(
        f"{path.name}.bak-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    )
    backup_fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with path.open("rb") as source, os.fdopen(backup_fd, "wb") as destination:
            shutil.copyfileobj(source, destination)
            destination.flush()
            os.fsync(destination.fileno())
        os.chmod(backup, 0o600)
    except Exception:
        try:
            os.close(backup_fd)
        except OSError:
            pass
        try:
            backup.unlink()
        except OSError:
            pass
        raise

    keys = set(values)
    kept = []
    for line in original.splitlines():
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if not match or match.group(1) not in keys:
            kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()
    if kept:
        kept.append("")
    kept.extend(f"{key}={quote_env(value)}" for key, value in values.items())
    payload = "\n".join(kept) + "\n"

    fd, temp_name = tempfile.mkstemp(prefix=".hermes-env-", dir=path.parent)
    try:
        os.chmod(temp_name, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return backup


def main() -> int:
    print("Configure Hermes dashboard Basic Auth. Password input will not be displayed.")
    username = input("Dashboard username: ").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", username):
        print("Username must be 1-64 characters: letters, digits, dot, underscore, or hyphen.", file=sys.stderr)
        return 2

    password = getpass.getpass("Dashboard password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm dashboard password: ")
    if len(password) < 12:
        print("Password must be at least 12 characters.", file=sys.stderr)
        return 2
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 2

    try:
        hash_password = load_hash_helper()
        password_hash = hash_password(password)
        if not isinstance(password_hash, str) or len(password_hash) < 20:
            raise RuntimeError("Hermes password hash helper returned an unexpected result.")
        env_path = Path.home() / ".hermes" / ".env"
        backup = update_env_file(
            env_path,
            {
                "HERMES_DASHBOARD_BASIC_AUTH_USERNAME": username,
                "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH": password_hash,
                "HERMES_DASHBOARD_BASIC_AUTH_SECRET": secrets.token_hex(32),
            },
        )
    except Exception as exc:
        # Do not include exception text: import/config errors can contain sensitive paths or values.
        print(f"Dashboard auth configuration failed ({type(exc).__name__}).", file=sys.stderr)
        return 1
    finally:
        password = ""
        confirmation = ""

    print("Dashboard auth configured; .env and backup permissions are 0600.")
    print(f"Previous .env saved to {backup.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
