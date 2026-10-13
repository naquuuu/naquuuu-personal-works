"""Host-only authenticated WhatsApp policy; never expose identifiers to models.

Call intercept() only with the bridge event, before building a model event.
State remains local. No CLI accepts model-supplied identities or mutations.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading

from relay_outbound import sanitize_outbound_text, SAFE_FALLBACK_REPLY, requested_creative_allowance, requested_status_allowance
from wa_group_memory import GroupMemory
from wa_owner_gate import evaluate, is_sender_id, digits_only

logger = logging.getLogger(__name__)

GROUPS = 'WHATSAPP_GROUP_ALLOWED_USERS'
PEOPLE = 'WHATSAPP_ALLOWED_USERS'
PROMOTED = 'WHATSAPP_FREE_RESPONSE_CHATS'
COMMANDS = {'/allow-group', '/allow-person', '/list', '/remove'}
GROUP_RE = re.compile(r'^[0-9]{5,25}@g\.us$')
RAW_RE = re.compile(r'(?:@\+?\d+|\+?\d+(?:[-:]\d+)*@(?:s\.whatsapp\.net|lid|g\.us)|\+?\d{6,})|(?<!\w)\+?\d(?:[ ()-]*\d){6,}(?!\w)')
LOCK = threading.RLock()
# Request-scoped final reply: the first final claim wins for a turn, and an
# identical failure line is never delivered twice for the same chat.
FINAL_CLAIM_SECONDS = 600
FAILURE_LINE_SECONDS = 120
FAILURE_LINES = frozenset({SAFE_FALLBACK_REPLY})
# Bot-to-bot loop breaker (owner-set 2026-10-14): more than BURST_LIMIT replies
# by the bot to one chat inside BURST_WINDOW_SECONDS trips a quiet cooldown.
BURST_WINDOW_SECONDS = 300
BURST_LIMIT = 20
BURST_COOLDOWN_SECONDS = 600


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


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
        self.active_turns: dict[str, dict] = {}
        self.creative_requests: dict[tuple[str, str], tuple[dict, dt.datetime]] = {}
        self.status_requests: dict[tuple[str, str], dt.datetime] = {}
        self.final_claims: dict[tuple[str, str], dt.datetime] = {}
        self.recent_failures: dict[tuple[str, str], dt.datetime] = {}
        self.reply_times: dict[str, list[dt.datetime]] = {}
        self.reply_cooldowns: dict[str, dt.datetime] = {}
        self.group_memory = GroupMemory.from_env_file(self.env_path)
        try:
            saved = json.loads(cache_path.read_text(encoding='utf-8'))
            if isinstance(saved, dict):
                self.names = {k: v for k, v in saved.items() if isinstance(v, str) and self.safe_name(v)}
        except (OSError, ValueError):
            pass

    @staticmethod
    def safe_name(name: str) -> bool:
        return bool(name.strip()) and len(name) <= 100 and not RAW_RE.search(name) and not any(ord(c) < 32 for c in name)

    @staticmethod
    def is_status_message(text: str) -> bool:
        norm = " ".join(text.strip().lower().split())
        return norm in {
            "masih aku kerjakan.",
            "masih aku kerjakan",
            "working on it...",
            "still working on it...",
            "processing...",
        }

    def observe(self, event: dict) -> None:
        """Bridge-sourced name only. Never infer names from message text."""
        sender, name = str(event.get('senderId') or ''), str(event.get('senderName') or '')
        if is_sender_id(sender) and self.safe_name(name):
            with LOCK:
                self.names[sender] = name.strip()
                self.names[digits_only(sender)] = name.strip()
                _atomic(self.cache_path, json.dumps(self.names, ensure_ascii=False))
        chat_id = str(event.get('chatId') or '')
        if chat_id:
            body = str(event.get('body') or '')
            quoted_text = str(event.get('quotedText') or '') if event.get('hasQuotedMessage') else ''
            allowance = requested_creative_allowance(body, quoted_text)
            with LOCK:
                self.active_turns[chat_id] = {
                    'status_sent': False,
                    'started_at': dt.datetime.now(dt.timezone.utc),
                }
                now = dt.datetime.now(dt.timezone.utc)
                self.creative_requests = {
                    key: value for key, value in self.creative_requests.items()
                    if value[1] > now
                }
                message_id = str(event.get('messageId') or '')
                if allowance and message_id:
                    self.creative_requests[(chat_id, message_id)] = (allowance, now + dt.timedelta(minutes=10))
                while len(self.creative_requests) > 128:
                    self.creative_requests.pop(next(iter(self.creative_requests)))
                self.status_requests = {
                    key: value for key, value in self.status_requests.items()
                    if value > now
                }
                if message_id and requested_status_allowance(body):
                    self.status_requests[(chat_id, message_id)] = now + dt.timedelta(minutes=10)
                while len(self.status_requests) > 128:
                    self.status_requests.pop(next(iter(self.status_requests)))
                if self.group_memory.enabled_for(chat_id):
                    self.group_memory.record(chat_id, body,
                                             name=self.names.get(sender) or self.names.get(digits_only(sender)) or "",
                                             names=self.names)

    def scrub(self, text: str, *, chat_id: str | None = None, reply_to: str | None = None,
              notice_allowance: bool = False) -> str:
        repetition_allowance = None
        if chat_id and reply_to:
            with LOCK:
                grant = self.creative_requests.get((chat_id, reply_to))
                if grant and grant[1] > dt.datetime.now(dt.timezone.utc):
                    repetition_allowance = grant[0]
        sanitized, is_clean = sanitize_outbound_text(text, repetition_allowance=repetition_allowance,
                                                     notice_allowance=notice_allowance)
        if not is_clean:
            return SAFE_FALLBACK_REPLY

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
        return RAW_RE.sub(replace, sanitized)

    def promoted(self, chat_id: str) -> bool:
        text = self.env_path.read_text(encoding='utf-8')
        return bool(GROUP_RE.fullmatch(chat_id)) and chat_id in _entries(text, PROMOTED) and chat_id in _entries(text, GROUPS)

    def inject_group_context(self, chat_id: str, text: str) -> str:
        """Prepend the bounded recent-chatter block for an opted-in chat (ADR-048).

        Returns the text unchanged when the window is disabled, empty, or when
        there is nothing to say. The current message is excluded from the block
        because observe() recorded it moments before this call. Diagnostics are
        counts-only: window size and whether a block was produced, never content.
        """
        if not self.group_memory.enabled_for(chat_id):
            return text
        size = self.group_memory.window_size(chat_id)
        block = self.group_memory.render(chat_id, skip_last=True)
        logger.warning("group_memory_diag inject window=%d block=%d", size, int(bool(block)))
        if block and str(text or "").strip():
            return block + "\n\n" + text
        return text

    def claim_final(self, chat_id: str, reply_to: str | None, content: str = "") -> bool:
        """End-of-turn idempotency: the first final claim wins for an inbound message.

        Returns True when this turn may send, False for a duplicate attempt
        (retry events, double fallback paths) or while the bot-to-bot loop
        breaker is cooling a chat down. Status lines never consume the slot.
        """
        if not reply_to:
            return True
        if self.is_status_message(content):
            return True
        now = _now_utc()
        key = (chat_id, str(reply_to))
        with LOCK:
            self.final_claims = {k: v for k, v in self.final_claims.items() if v > now}
            if key in self.final_claims:
                return False
            if not self._burst_allows(chat_id, now):
                logger.warning("reply_burst_suppressed=1")
                return False
            self.final_claims[key] = now + dt.timedelta(seconds=FINAL_CLAIM_SECONDS)
            while len(self.final_claims) > 256:
                self.final_claims.pop(next(iter(self.final_claims)))
        return True

    def _burst_allows(self, chat_id: str, now: dt.datetime) -> bool:
        """Count logical replies per chat; trip a quiet cooldown past the limit."""
        cooldown = self.reply_cooldowns.get(chat_id)
        if cooldown and cooldown > now:
            return False
        if cooldown:
            self.reply_cooldowns.pop(chat_id, None)
        horizon = now - dt.timedelta(seconds=BURST_WINDOW_SECONDS)
        times = [t for t in self.reply_times.get(chat_id, []) if t > horizon]
        times.append(now)
        self.reply_times[chat_id] = times
        while len(self.reply_times) > 64:
            self.reply_times.pop(next(iter(self.reply_times)))
        if len(times) > BURST_LIMIT:
            self.reply_cooldowns[chat_id] = now + dt.timedelta(seconds=BURST_COOLDOWN_SECONDS)
            logger.warning("reply_burst count=%d cooldown_seconds=%d", len(times), BURST_COOLDOWN_SECONDS)
            return False
        return True

    def release_final(self, chat_id: str, reply_to: str | None) -> None:
        """Un-claim a turn after a definite, unconfirmed send failure so a single
        plain failure line (or a user retry) can still go out."""
        if not reply_to:
            return
        with LOCK:
            self.final_claims.pop((chat_id, str(reply_to)), None)

    def outbound(self, payload: dict, *, proactive: bool = False) -> dict:
        """Keep routing IDs host-side; scrub every user-visible text field."""
        chat_id = str(payload.get('chatId') or '')
        if proactive and not self.promoted(chat_id):
            raise ValueError('Initiation is limited to promoted groups.')

        msg = str(payload.get('message') or '')
        if self.is_status_message(msg):
            with LOCK:
                turn = self.active_turns.get(chat_id)
                if turn and turn.get('status_sent'):
                    return {}
                if turn:
                    turn['status_sent'] = True

        result = dict(payload)
        reply_to = str(payload.get('replyTo') or '') or None
        notice_allowance = False
        if reply_to:
            with LOCK:
                grant = self.status_requests.get((chat_id, reply_to))
                notice_allowance = bool(grant and grant > dt.datetime.now(dt.timezone.utc))
        for key in ('message', 'caption', 'question', 'fileName', 'name', 'address'):
            if isinstance(result.get(key), str):
                result[key] = self.scrub(result[key], chat_id=chat_id, reply_to=reply_to,
                                         notice_allowance=notice_allowance)
        if isinstance(result.get('options'), list):
            result['options'] = [self.scrub(str(v), chat_id=chat_id, reply_to=reply_to,
                                            notice_allowance=notice_allowance) for v in result['options']]
        for mention in result.get('mentions') or []:
            if not is_sender_id(mention) or not self.names.get(digits_only(mention)):
                raise ValueError('Unresolved mention; delivery refused.')

        text = result.get('message')
        if isinstance(text, str) and text in FAILURE_LINES:
            now = dt.datetime.now(dt.timezone.utc)
            digest = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
            key = (chat_id, reply_to) if reply_to else (chat_id, digest)
            with LOCK:
                self.recent_failures = {k: v for k, v in self.recent_failures.items() if v > now}
                if key in self.recent_failures:
                    return {}
                self.recent_failures[key] = now + dt.timedelta(seconds=FAILURE_LINE_SECONDS)
                while len(self.recent_failures) > 256:
                    self.recent_failures.pop(next(iter(self.recent_failures)))
        return result

    def intercept(self, event: dict) -> str | None:
        # Authentication runs BEFORE examining/parsing the command body.
        owner, _ = evaluate(str(event.get('senderId') or ''), self.env_path.parent)
        # Baileys may expose an opaque LID as senderId and the same sender's
        # phone JID as senderAltId. Both fields must come from the bridge event.
        if not owner:
            owner, _ = evaluate(str(event.get('senderAltId') or ''), self.env_path.parent)
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
                    if command == '/remove' and evaluate(target, self.env_path.parent)[0]:
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
