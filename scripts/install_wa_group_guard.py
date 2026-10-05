"""Install the group silence fix on the current source contract, with backups.

Reads source code only, never Hermes state/config. Validate every proposal before
writing. No service restart or model calls. Reapplying is idempotent.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
from pathlib import Path
import shutil

MARKER = '# NAQUUUU_GROUP_SILENCE_V1'


def one(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if text.count(old) != 1:
        raise ValueError('Group guard source mismatch; no patch written.')
    return text.replace(old, new, 1)


def helper_import(text: str) -> str:
    if MARKER not in text:
        text += '''\n\n# NAQUUUU_GROUP_SILENCE_V1
from pathlib import Path as _wa_guard_path
import os as _wa_guard_os
import sys as _wa_guard_sys
_wa_guard_root = _wa_guard_os.environ.get("NAQUUUU_WORKSPACE")
if not _wa_guard_root:
    raise RuntimeError("NAQUUUU_WORKSPACE is required for group guard")
_wa_guard_sys.path.insert(0, str(_wa_guard_path(_wa_guard_root) / "scripts"))
_wa_guard_sys.path.insert(0, str(_wa_guard_path.home() / ".local/share/naquuuu/relay-guards"))
from wa_group_guard import allow_group_silence as _wa_group_silence
from wa_group_guard import should_ignore_group_event as _wa_ignore_group_event
'''
    return text


def turn_patch(text: str) -> str:
    text = one(text,
        'if _intentional_silence and not is_machinery_display_kind(_silence_kind):',
        'if _intentional_silence and not (is_machinery_display_kind(_silence_kind) or _wa_group_silence(source)):')
    text = one(text,
        'if is_machinery_display_kind(turn_ctx.persist_user_display_kind):',
        'if is_machinery_display_kind(turn_ctx.persist_user_display_kind) or _wa_group_silence(turn_ctx.source):')
    return helper_import(text)


def startup_patch(text: str) -> str:
    text = one(text, 'return "" if machinery else _UNEXPECTED_SILENCE_REPLY',
               'return "" if machinery or _wa_group_silence(origin) else _UNEXPECTED_SILENCE_REPLY')
    return helper_import(text)


def adapter_patch(text: str) -> str:
    text = one(text, '                            policy = _wa_policy()\n', '''                            if _wa_ignore_group_event(msg_data, explicitly_addressed=(
                                self._message_mentions_bot(msg_data)
                                or self._message_matches_mention_patterns(msg_data)
                                or str(msg_data.get("body") or "").strip().startswith("/")
                            )):
                                continue
                            policy = _wa_policy()
''')
    text = one(text, '                            policy.observe(msg_data)',
               '                            policy.observe(dict(msg_data, body=self._clean_bot_mention_text(str(msg_data.get("body") or ""), msg_data)))')
    # Guard the WHOLE reply before chunking; per-chunk guards alone can miss a
    # repeated flood split into individually innocuous chunks.
    text = one(text,
        '            chunks = self.truncate_message(self.format_message(content), self._outgoing_chunk_limit())',
        '            content = self.format_message(content)\n            content = _wa_policy().scrub(content, chat_id=chat_id, reply_to=reply_to if len(content) <= self._outgoing_chunk_limit() else None)\n            chunks = self.truncate_message(content, self._outgoing_chunk_limit())')
    text = one(text, '            content = _wa_policy().scrub(content)\n',
               '            content = _wa_policy().scrub(content, chat_id=to_whatsapp_jid(chat_id))\n')
    # A suppressed generic status is a successful no-op, not a failed send.
    text = one(text,
        '            payload = _wa_policy().outbound(payload)\n            async with self._bridge_req',
        '            payload = _wa_policy().outbound(payload)\n            if not payload:\n                return SendResult(success=True, message_id=None)\n            async with self._bridge_req')
    text = one(text, 'from wa_chat_policy import host_policy as _wa_policy',
               '_policy_sys.path.insert(0, str(_PolicyPath.home() / ".local/share/naquuuu/relay-guards"))\nfrom wa_chat_policy import host_policy as _wa_policy')
    return helper_import(text)


def proposals(repo: Path) -> list[tuple[Path, str]]:
    return [(repo / rel, patch((repo / rel).read_text(encoding='utf-8')))
            for rel, patch in [
                ('gateway/run_turn.py', turn_patch),
                ('gateway/run_startup.py', startup_patch),
                ('plugins/platforms/whatsapp/adapter.py', adapter_patch),
            ]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-repo', required=True, type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    helpers = Path.home() / '.local/share/naquuuu/relay-guards'
    if not all((helpers / name).is_file() for name in
               ('wa_group_guard.py', 'wa_chat_policy.py', 'relay_outbound.py')):
        raise ValueError('Install relay helper overlay first; no patch written.')
    changes = proposals(args.hermes_repo)
    for path, text in changes:
        ast.parse(text, filename=path.name)
    if args.check:
        print('group_guard_source_contract=pass')
        return
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    count = 0
    for path, text in changes:
        if text != path.read_text(encoding='utf-8'):
            shutil.copy2(path, path.with_name(path.name + '.bak-' + stamp))
            path.write_text(text, encoding='utf-8')
            count += 1
    print(f'group_guard_files_changed={count}')


if __name__ == '__main__':
    main()
