"""Host-only authenticated WhatsApp policy; never expose identifiers to models.

Call intercept() only with the bridge event, before building a model event.
State remains local. No CLI accepts model-supplied identities or mutations.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading

from wa_owner_gate import evaluate, is_sender_id, digits_only

GROUPS = 'WHATSAPP_GROUP_ALLOWED_USERS'
PEOPLE = 'WHATSAPP_ALLOWED_USERS'
PROMOTED = 'WHATSAPP_FREE_RESPONSE_CHATS'
COMMANDS = {'/allow-group', '/allow-person', '/list', '/remove'}
GROUP_RE = re.compile(r'^[0-9]{5,25}@g\.us$')
RAW_RE = re.compile(r'(?:@\+?\d+|\+?\d+(?:[-:]\d+)*@(?:s\.whatsapp\.net|lid|g\.us)|\+?\d{6,})|(?<!\w)\+?\d(?:[ ()-]*\d){6,}(?!\w)')
LOCK = threading.RLock()


def _entries(text: str, key: str) -> set[str]:
    values = set()
    for line in text.splitlines():
        match = re.match(r'^\s*(?:export\s+)?' + re.escape(key) + r'\s*=\s*(.*)$', line)
        if match:
            values = {v.strip() for v in match[1].strip().strip('\"\'').split(',') if v.strip()}
    return values


def _atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.wa-policy-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as out:
            out.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class ChatPolicy:
    def __init__(self, env_path: Path, cache_path: Path):
        self.env_path = env_path
        self.cache_path = cache_path
        self.names: dict[str, str] = {}
        try:
            saved = json.loads(cache_path.read_text(encoding='utf-8'))
            if isinstance(saved, dict):
                self.names = {k: v for k, v in saved.items() if isinstance(v, str) and self.safe_name(v)}
        except (OSError, ValueError):
            pass

    @staticmethod
    def safe_name(name: str) -> bool:
        return bool(name.strip()) and len(name) <= 100 and not RAW_RE.search(name) and not any(ord(c) < 32 for c in name)

    def observe(self, event: dict) -> None:
        """Bridge-sourced name only. Never infer names from message text."""
        sender, name = str(event.get('senderId') or ''), str(event.get('senderName') or '')
        if is_sender_id(sender) and self.safe_name(name):
            with LOCK:
                self.names[sender] = name.strip()
                self.names[digits_only(sender)] = name.strip()
                _atomic(self.cache_path, json.dumps(self.names, ensure_ascii=False))

    def scrub(self, text: str) -> str:
        def replace(match: re.Match) -> str:
            raw = match[0]
            # A real ISO calendar date is operational text, not a phone ID.
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw):
                try:
                    dt.date.fromisoformat(raw)
                    return raw
                except ValueError:
                    pass
            name = self.names.get(raw.lstrip('@+')) or self.names.get(re.sub(r'\D', '', raw))
            if not name or not self.safe_name(name):
                raise ValueError('Unresolved identity; delivery refused.')
            return ('@' if raw.startswith('@') else '') + name
        return RAW_RE.sub(replace, text)

    def promoted(self, chat_id: str) -> bool:
        text = self.env_path.read_text(encoding='utf-8')
        return bool(GROUP_RE.fullmatch(chat_id)) and chat_id in _entries(text, PROMOTED) and chat_id in _entries(text, GROUPS)

    def outbound(self, payload: dict, *, proactive: bool = False) -> dict:
        """Keep routing IDs host-side; scrub every user-visible text field."""
        if proactive and not self.promoted(str(payload.get('chatId') or '')):
            raise ValueError('Initiation is limited to promoted groups.')
        result = dict(payload)
        for key in ('message', 'caption', 'question', 'fileName', 'name', 'address'):
            if isinstance(result.get(key), str):
                result[key] = self.scrub(result[key])
        if isinstance(result.get('options'), list):
            result['options'] = [self.scrub(str(v)) for v in result['options']]
        for mention in result.get('mentions') or []:
            if not is_sender_id(mention) or not self.names.get(digits_only(mention)):
                raise ValueError('Unresolved mention; delivery refused.')
        return result

    def intercept(self, event: dict) -> str | None:
        # Authentication runs BEFORE examining/parsing the command body.
        owner, _ = evaluate(str(event.get('senderId') or ''))
        # Baileys may expose an opaque LID as senderId and the same sender's
        # phone JID as senderAltId. Both fields must come from the bridge event.
        if not owner:
            owner, _ = evaluate(str(event.get('senderAltId') or ''))
        body = str(event.get('body') or '').strip()
        command = body.split(maxsplit=1)[0] if body else ''
        if command not in COMMANDS:
            return None
        if not owner:
            return 'Only the owner can change access.'
        if body != command:
            return 'Use the command alone; reply to a person to choose them.'
        with LOCK:
            try:
                text = self.env_path.read_text(encoding='utf-8')
                groups, people = _entries(text, GROUPS), _entries(text, PEOPLE)
                if command == '/list':
                    return f'Groups: {len(groups)}; people: {len(people)}.'
                replied = str(event.get('quotedParticipant') or '') if event.get('hasQuotedMessage') and event.get('quotedMessageId') else ''
                group = str(event.get('chatId') or '') if event.get('isGroup') else ''
                key, target = (PEOPLE, replied) if command == '/allow-person' or (command == '/remove' and replied) else (GROUPS, group)
                if not (is_sender_id(target) if key == PEOPLE else GROUP_RE.fullmatch(target)):
                    return 'Reply to the person, or use the group command inside that group.'
                if key == PEOPLE:
                    target = digits_only(target)
                    if command == '/remove' and evaluate(target)[0]:
                        return 'Owner access cannot be removed from chat.'
                entries = _entries(text, key)
                if command == '/remove':
                    entries = {v for v in entries if not (digits_only(v) == target if key == PEOPLE and is_sender_id(v) else v == target)}
                else:
                    entries.add(target)
                updates = {key: entries}
                if command == '/remove' and key == GROUPS:
                    updates[PROMOTED] = _entries(text, PROMOTED) - {target}
                lines = text.splitlines()
                for setting, values in updates.items():
                    pattern = re.compile(r'^\s*(?:export\s+)?' + re.escape(setting) + r'\s*=')
                    lines = [line for line in lines if not pattern.match(line)]
                    lines.append(setting + '=' + ','.join(sorted(values)))
                stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
                backup = self.env_path.with_name(self.env_path.name + '.bak-' + stamp)
                shutil.copy2(self.env_path, backup)
                os.chmod(backup, 0o600)
                _atomic(self.env_path, '\n'.join(lines) + '\n')
                for setting, values in updates.items():
                    os.environ[setting] = ','.join(sorted(values))
                return 'Access removed.' if command == '/remove' else 'Access allowed.'
            except (OSError, ValueError):
                return 'I could not update access; please try again later.'


_default: ChatPolicy | None = None


def host_policy() -> ChatPolicy:
    global _default
    if _default is None:
        home = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
        _default = ChatPolicy(home / '.env', home / 'wa-display-names.json')
    return _default
