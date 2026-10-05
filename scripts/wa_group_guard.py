"""Quiet group delivery and bounded acknowledgement filtering, without identities."""
from __future__ import annotations

import re


def allow_group_silence(source) -> bool:
    """Use trusted routing fields, never a model's description of the message."""
    platform = getattr(source, 'platform', None)
    kind = getattr(source, 'chat_type', None)
    return (getattr(platform, 'value', platform) == 'whatsapp'
            and getattr(kind, 'value', kind) == 'group')


_ACKS = frozenset({
    'noted', 'siap kapan pun', 'gue standby', 'aku standby',
    'no active task to stop', 'jawaban belum bisa ditampilkan silakan coba lagi',
    'no_reply', '[silent]',
})


def should_ignore_group_event(event: dict, *, explicitly_addressed: bool = False) -> bool:
    """Drop only idle/status bodies, including replies to a bot's earlier notice.

    Names do not prove someone is a bot. Quotes alone do not turn routine idle
    acknowledgements into a fresh request. A real mention, command or bot name
    preserves the user's ability to address the bot explicitly.
    """
    if event.get('isGroup') is not True or explicitly_addressed:
        return False
    body = ' '.join(str(event.get('body') or '').lower().split())
    norm = re.sub(r'[.!?,;:]+', '', body).strip()
    if norm in _ACKS:
        return True
    if body.startswith('⚠️ the model returned only a silence marker for a message that needed a reply.'):
        return True
    return body.startswith('status: gue aktif dan siap. tidak ada topik baru yang masuk,')
