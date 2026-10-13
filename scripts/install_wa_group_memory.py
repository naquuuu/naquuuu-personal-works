"""Insert the bounded group-context injection into the pinned WhatsApp adapter.

Reads source code only, never Hermes state/config. Validate before writing.
No service restart and no model calls. Reapplying is idempotent.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
from pathlib import Path
import shutil

MARKER = '# NAQUUUU_GROUP_MEMORY_V1'


def patch_adapter(source: str) -> str:
    if MARKER in source:
        return source
    if '_wa_policy' not in source:
        raise ValueError('Chat policy hooks must be installed first; no patch written.')
    anchor = ('            ) if v}\n'
              '            # ``fromOwner`` = owner-typed inbound fromMe '
              '(gated by WHATSAPP_FORWARD_OWNER_MESSAGES at the bridge); surfaced as\n')
    if source.count(anchor) != 1:
        raise ValueError('Unrecognised event-build source; no patch written.')
    replacement = ('            ) if v}\n'
                   '            # NAQUUUU_GROUP_MEMORY_V1: bounded in-memory context for opted-in chats.\n'
                   '            body = _wa_policy().inject_group_context(str(data.get("chatId") or ""), body)\n'
                   '            # ``fromOwner`` = owner-typed inbound fromMe '
                   '(gated by WHATSAPP_FORWARD_OWNER_MESSAGES at the bridge); surfaced as\n')
    patched = source.replace(anchor, replacement, 1)
    ast.parse(patched)
    return patched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-repo', required=True, type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    adapter = args.hermes_repo / 'plugins/platforms/whatsapp/adapter.py'
    patched = patch_adapter(adapter.read_text(encoding='utf-8'))
    if args.check:
        print('group_memory_source_contract=pass')
        return
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    if patched != adapter.read_text(encoding='utf-8'):
        shutil.copy2(adapter, adapter.with_name(adapter.name + '.bak-' + stamp))
        adapter.write_text(patched, encoding='utf-8')
        print('group_memory_files_changed=1')
    else:
        print('group_memory_files_changed=0')


if __name__ == '__main__':
    main()
