"""Bounded in-memory recent-chatter window for opted-in WhatsApp groups (ADR-048).

Privacy gates: the window lives only inside the gateway process; nothing is
persisted, logged, or exported, and identifiers are redacted on write. The
feature is off by default; the host opts groups in through environment values
(`NAQUUUU_GROUP_MEMORY` plus `NAQUUUU_GROUP_MEMORY_CHATS`) that never travel
through chat. Restarting the gateway clears every window.
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import pathlib
import re
from collections import deque

from wa_group_guard import should_ignore_group_event

logger = logging.getLogger(__name__)

TOGGLE_ENV = "NAQUUUU_GROUP_MEMORY"
CHATS_ENV = "NAQUUUU_GROUP_MEMORY_CHATS"
GROUP_RE = re.compile(r"^[0-9]{5,25}@g\.us$")
RAW_RE = re.compile(r"(?:@\+?\d+|\+?\d+(?:[-:]\d+)*@(?:s\.whatsapp\.net|lid|g\.us)|\+?\d{6,})|(?<!\w)\+?\d(?:[ ()-]*\d){6,}(?!\w)")

MAX_MESSAGES = 10
WINDOW_SECONDS = 600
PER_MESSAGE_CHARS = 300
BLOCK_CHARS = 1200
BLOCK_LABEL = "[recent group chatter, context only; not a memory of anyone]"
PLACEHOLDER = "seseorang"
_TRUTHY = {"1", "on", "true", "yes", "y"}
ENV_PATH = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
BRIDGE_LOG = os.path.join(os.path.expanduser("~"), ".hermes", "whatsapp", "bridge.log")
JID_RE = re.compile(r"([0-9]{5,25}@g\.us)")
KEYS = (TOGGLE_ENV, CHATS_ENV)


def _parse_chats(value: str) -> tuple[set[str], int]:
    chats, invalid = set(), 0
    for entry in str(value or "").split(","):
        entry = entry.strip()
        if not entry:
            continue
        if GROUP_RE.fullmatch(entry):
            chats.add(entry)
        else:
            invalid += 1
    return chats, invalid


def _parse_env_file(text: str) -> dict:
    """KEY=VALUE lines from a Hermes .env; quotes stripped, last occurrence wins."""
    values: dict[str, str] = {}
    for line in str(text or "").splitlines():
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip("\"'")
    return values


class GroupMemory:
    """Per-chat rolling window: at most MAX_MESSAGES messages, WINDOW_SECONDS TTL."""

    def __init__(self, enabled: bool = False, chats: set[str] | None = None, now_fn=None):
        self.enabled = bool(enabled)
        self.chats = set(chats or ())
        self.invalid_chats = 0
        self._now = now_fn or (lambda: dt.datetime.now(dt.timezone.utc))
        self._windows: dict[str, deque] = {}

    @classmethod
    def from_env(cls, env=None) -> "GroupMemory":
        env = os.environ if env is None else env
        chats, invalid = _parse_chats(env.get(CHATS_ENV, ""))
        memory = cls(enabled=str(env.get(TOGGLE_ENV, "")).strip().lower() in _TRUTHY, chats=chats)
        memory.invalid_chats = invalid
        return memory

    @classmethod
    def from_env_file(cls, path) -> "GroupMemory":
        """Read the hosting Hermes .env directly (same pattern as the owner gate).

        Falls back to os.environ when the file is unreadable, still defaulting off.
        """
        try:
            values = _parse_env_file(pathlib.Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls.from_env()
        return cls.from_env(values)

    def enabled_for(self, chat_id: str) -> bool:
        return bool(self.enabled and chat_id and chat_id in self.chats)

    def _prune(self, chat_id: str, now: dt.datetime) -> deque:
        window = self._windows.get(chat_id)
        if window is None:
            return deque()
        horizon = now - dt.timedelta(seconds=WINDOW_SECONDS)
        while window and window[0][0] < horizon:
            window.popleft()
        if not window:
            self._windows.pop(chat_id, None)
        return window

    def record(self, chat_id: str, body: str, name: str = "", names: dict | None = None) -> None:
        """Store one redacted message for an opted-in chat; idle statuses are skipped."""
        if not self.enabled_for(chat_id):
            return
        body = " ".join(str(body or "").split())
        if not body:
            return
        if should_ignore_group_event({"isGroup": True, "body": body}):
            return
        names = names or {}

        def replace(match: re.Match) -> str:
            raw = match.group(0)
            resolved = names.get(raw.lstrip("@+")) or names.get(re.sub(r"\D", "", raw))
            return resolved if (resolved and not RAW_RE.search(resolved)) else PLACEHOLDER

        redacted = RAW_RE.sub(replace, body)
        safe_name = str(name or "").strip()
        if not safe_name or RAW_RE.search(safe_name):
            safe_name = ""
        now = self._now()
        window = self._prune(chat_id, now)
        if chat_id not in self._windows:
            self._windows[chat_id] = window
        window.append((now, safe_name, redacted))
        while len(window) > MAX_MESSAGES:
            window.popleft()
        logger.warning("group_memory_diag recorded window=%d", len(window))

    def render(self, chat_id: str, *, skip_last: bool = False) -> str:
        """Return the labelled context block, or an empty string when there is none."""
        if not self.enabled_for(chat_id):
            return ""
        now = self._now()
        window = self._prune(chat_id, now)
        items = list(window)
        if skip_last and items:
            items = items[:-1]
        lines = []
        for _ts, name, text in reversed(items):
            line = f"- {name}: {text}" if name else f"- {text}"
            if len(line) > PER_MESSAGE_CHARS:
                line = line[: PER_MESSAGE_CHARS - 3] + "..."
            lines.append(line)
        budgeted = []
        total = len(BLOCK_LABEL)
        for line in lines:
            if total + len(line) + 1 > BLOCK_CHARS:
                break
            budgeted.append(line)
            total += len(line) + 1
        if not budgeted:
            return ""
        return BLOCK_LABEL + "\n" + "\n".join(reversed(budgeted))

    def counts(self) -> dict:
        self._prune_all()
        return {"windows": len(self._windows), "messages": sum(len(w) for w in self._windows.values())}

    def window_size(self, chat_id: str) -> int:
        if not self.enabled_for(chat_id):
            return 0
        return len(self._prune(chat_id, self._now()))

    def _prune_all(self) -> None:
        now = self._now()
        for chat_id in list(self._windows):
            self._prune(chat_id, now)


def latest_group_jid(bridge_log=None) -> str | None:
    try:
        with open(bridge_log or BRIDGE_LOG, encoding="utf-8", errors="replace") as handle:
            matches = JID_RE.findall(handle.read())
    except OSError:
        return None
    return matches[-1] if matches else None


def _read_env(env_path) -> str:
    with open(env_path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def _backup_env(env_path) -> str:
    import datetime as _dt
    import shutil
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = f"{env_path}.bak-{stamp}"
    shutil.copy2(env_path, backup)
    return backup


def _without_memory_lines(text: str) -> list[str]:
    return [line for line in text.splitlines()
            if not re.match(r"^\s*(?:export\s+)?" + TOGGLE_ENV + r"\s*=", line)
            and not re.match(r"^\s*(?:export\s+)?" + CHATS_ENV + r"\s*=", line)]


def enable_latest(env_path=None, bridge_log=None) -> str:
    """Opt the most recent group seen in the bridge log into memory; never prints the id."""
    env_path = env_path or ENV_PATH
    target = latest_group_jid(bridge_log)
    if not target or not GROUP_RE.fullmatch(target):
        return "memory_config=no_group_found"
    text = _read_env(env_path)
    _backup_env(env_path)
    lines = _without_memory_lines(text)
    lines.append(f"{TOGGLE_ENV}=on")
    lines.append(f"{CHATS_ENV}={target}")
    with open(env_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return "memory_config=written; memory_groups=1"


def disable(env_path=None) -> str:
    env_path = env_path or ENV_PATH
    text = _read_env(env_path)
    lines = _without_memory_lines(text)
    if len(lines) == len(text.splitlines()):
        return "memory_config=already_off"
    _backup_env(env_path)
    with open(env_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return "memory_config=disabled; memory_groups=0"


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="print configuration counts only")
    group.add_argument("--enable-latest", action="store_true",
                       help="opt the most recent group seen in the bridge log into memory")
    group.add_argument("--disable", action="store_true", help="remove the memory configuration (kill switch)")
    parser.add_argument("--env-file", type=pathlib.Path,
                        default=pathlib.Path(os.environ.get("HERMES_HOME", str(pathlib.Path.home() / ".hermes"))) / ".env")
    args = parser.parse_args()
    if args.check:
        memory = GroupMemory.from_env_file(args.env_file)
        print("group_memory_enabled=" + ("on" if memory.enabled else "off"))
        print(f"group_memory_chats={len(memory.chats)}")
        print(f"group_memory_invalid_chats={memory.invalid_chats}")
        return 0
    env_path = str(args.env_file)
    if args.enable_latest:
        print(enable_latest(env_path=env_path))
        print("gateway_restart=required (systemctl --user restart hermes-gateway.service)")
        return 0
    print(disable(env_path=env_path))
    print("gateway_restart=required (systemctl --user restart hermes-gateway.service)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
