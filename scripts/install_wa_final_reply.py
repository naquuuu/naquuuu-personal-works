"""Insert the request-scoped final-reply claim into the pinned WhatsApp send path.

Reads source code only, never Hermes state/config. Validate before writing.
No service restart and no model calls. Reapplying is idempotent.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
from pathlib import Path
import shutil

MARKER = '# NAQUUUU_FINAL_REPLY_V1'


def patch_adapter(source: str) -> str:
    if MARKER in source:
        return source
    if '_wa_policy' not in source:
        raise ValueError('Chat policy hooks must be installed first; no patch written.')
    start = source.index('    async def send(self,')
    end = source.index('    async def edit_message(', start)
    block = source[start:end]

    anchor = '        chat_id = to_whatsapp_jid(chat_id)\n        try:\n'
    if anchor not in block:
        raise ValueError('Unrecognised send source; no patch written.')
    claim = '''        chat_id = to_whatsapp_jid(chat_id)
        # NAQUUUU_FINAL_REPLY_V1: one final reply per inbound message; duplicate
        # attempts (retry events, double fallback paths) become a no-op success.
        if _wa_policy().claim_final(chat_id, reply_to, content) is False:
            return SendResult(success=True, message_id=None)
        try:
'''
    block = block.replace(anchor, claim, 1)

    chunk_failure = '''                if not result.success:
                    return SendResult(success=False, error="Delivery uncertain; automatic replay stopped",'''
    chunk_failure_new = '''                if not result.success:
                    _wa_policy().release_final(chat_id, reply_to)
                    return SendResult(success=False, error="Delivery uncertain; automatic replay stopped",'''
    if chunk_failure not in block:
        raise ValueError('Unrecognised send failure source; no patch written.')
    block = block.replace(chunk_failure, chunk_failure_new, 1)

    exception_failure = '''        except Exception as e:
            return SendResult(success=False, error="Delivery uncertain; automatic replay stopped",'''
    exception_failure_new = '''        except Exception as e:
            _wa_policy().release_final(chat_id, reply_to)
            return SendResult(success=False, error="Delivery uncertain; automatic replay stopped",'''
    if exception_failure not in block:
        raise ValueError('Unrecognised send exception source; no patch written.')
    block = block.replace(exception_failure, exception_failure_new, 1)

    patched = source[:start] + block + source[end:]
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
        print('final_reply_source_contract=pass')
        return
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    if patched != adapter.read_text(encoding='utf-8'):
        shutil.copy2(adapter, adapter.with_name(adapter.name + '.bak-' + stamp))
        adapter.write_text(patched, encoding='utf-8')
        print('final_reply_files_changed=1')
    else:
        print('final_reply_files_changed=0')


if __name__ == '__main__':
    main()
