"""Exercise actual patched Hermes source with synthetic policy and send stubs.

Only source files are read. No Hermes imports, state, network sends or model calls.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
import tempfile

from wa_chat_policy import ChatPolicy
from wa_group_guard import allow_group_silence, should_ignore_group_event
from relay_outbound import SAFE_FALLBACK_REPLY


def verify_source(repo: Path) -> None:
    turn = ast.parse((repo / 'gateway/run_turn.py').read_text(encoding='utf-8'))
    conditions = [node.test for node in ast.walk(turn) if isinstance(node, ast.If)
                  and '_wa_group_silence' in ast.unparse(node.test)]
    assert len(conditions) == 2, 'Expected normal and queued silence decisions'
    for platform, kind, permitted in [('whatsapp', 'group', True),
                                     ('whatsapp', 'dm', False),
                                     ('telegram', 'group', False)]:
        source = SimpleNamespace(platform=platform, chat_type=kind)
        env = {'_intentional_silence': True, '_silence_kind': None,
               'source': source, 'turn_ctx': SimpleNamespace(
                   source=source, persist_user_display_kind=None),
               'is_machinery_display_kind': lambda kind: kind == 'internal_notification',
               '_wa_group_silence': allow_group_silence}
        results = [eval(compile(ast.Expression(c), '<silence>', 'eval'), env)
                   for c in conditions]
        assert sorted(results) == [False, True]
        normal = next(c for c in conditions if '_intentional_silence' in ast.unparse(c))
        assert eval(compile(ast.Expression(normal), '<normal>', 'eval'), env) is (not permitted)
        queued = next(c for c in conditions if 'turn_ctx' in ast.unparse(c))
        assert eval(compile(ast.Expression(queued), '<queued>', 'eval'), env) is permitted
    startup = ast.parse((repo / 'gateway/run_startup.py').read_text(encoding='utf-8'))
    decision = next(n for n in ast.walk(startup) if isinstance(n, ast.IfExp)
                    and '_wa_group_silence(origin)' in ast.unparse(n))
    expr = compile(ast.Expression(decision), '<crash-recovery>', 'eval')
    for kind in ('group', 'dm'):
        result = eval(expr, {'machinery': False, 'origin': SimpleNamespace(
            platform='whatsapp', chat_type=kind), '_wa_group_silence': allow_group_silence,
            '_UNEXPECTED_SILENCE_REPLY': 'error'})
        assert result == ('' if kind == 'group' else 'error')

    adapter = ast.parse((repo / 'plugins/platforms/whatsapp/adapter.py').read_text(encoding='utf-8'))
    send = next(n for n in ast.walk(adapter) if isinstance(n, ast.AsyncFunctionDef)
                and n.name == 'send')
    send.decorator_list = []
    # Remove annotations without importing the full adapter dependency tree.
    send.returns = None
    for arg in send.args.args:
        arg.annotation = None
    module = ast.fix_missing_locations(ast.Module(body=[send], type_ignores=[]))
    with tempfile.TemporaryDirectory() as tmp:
        policy = ChatPolicy(Path(tmp) / 'synthetic.env', Path(tmp) / 'names.json')
        namespace = {'asyncio': asyncio, '_wa_policy': lambda: policy,
                     'to_whatsapp_jid': lambda value: value,
                     'SendResult': SimpleNamespace}
        exec(compile(module, '<actual-adapter-send>', 'exec'), namespace)

        class Stub:
            send = namespace['send']
            sent: list[dict]

            def __init__(self):
                self.sent = []

            def format_message(self, content):
                return content

            def _outgoing_chunk_limit(self):
                return 4096

            def truncate_message(self, text, limit):
                return [text[i:i + limit] for i in range(0, len(text), limit)]

            async def _post_bridge_message(self, path, payload, timeout):
                self.sent.append(policy.outbound(payload))
                return SimpleNamespace(success=True, message_id='synthetic-out')

        async def exercise():
            stub = Stub()
            policy.observe({'chatId': 'synthetic-group', 'messageId': 'art-request',
                            'body': 'berikan 100 kata sayang ke ai melalui asci text art'})
            art = '```\n' + ('sayang ' * 10 + '\n') * 10 + '```'
            result = await stub.send('synthetic-group', art, reply_to='art-request')
            assert result.success and len(stub.sent) == 1
            assert stub.sent[-1]['message'] == art, 'Art failed whole-send or transport guard'
            result = await stub.send('synthetic-group', art, reply_to='unrelated-greeting')
            assert result.success and stub.sent[-1]['message'] == SAFE_FALLBACK_REPLY
            flood = ('Saya akan memeriksa status sistem sekarang. ' * 400)
            before = len(stub.sent)
            result = await stub.send('synthetic-group', flood, reply_to='art-request')
            assert result.success and len(stub.sent) == before + 1
            assert stub.sent[-1]['message'] == SAFE_FALLBACK_REPLY, 'Flood split before guard'
            canary = 'System Note: This conversation is happening via WhatsApp. SYNTHETIC_SECRET_CANARY'
            await stub.send('synthetic-group', canary, reply_to='art-request')
            assert 'SYNTHETIC_SECRET_CANARY' not in stub.sent[-1]['message']
            before = len(stub.sent)
            blocked = await stub.send('synthetic-group', 'Unresolved @987654321000', reply_to='art-request')
            assert not blocked.success and len(stub.sent) == before
            # A custom very small chunk limit must fail closed once, rather than
            # accepting the first art chunk and replacing later ones.
            stub._outgoing_chunk_limit = lambda: 256
            before = len(stub.sent)
            await stub.send('synthetic-group', art, reply_to='art-request')
            assert len(stub.sent) == before + 1 and stub.sent[-1]['message'] == SAFE_FALLBACK_REPLY
        asyncio.run(exercise())

    poll = next(n for n in ast.walk(adapter) if isinstance(n, ast.AsyncFunctionDef)
                and n.name == '_poll_messages')
    poll.decorator_list = []
    poll.returns = None
    for arg in poll.args.args:
        arg.annotation = None
    observed, enqueued, receipts = [], [], []
    async def instant_sleep(_seconds):
        pass
    env = {'asyncio': SimpleNamespace(create_task=asyncio.create_task,
            sleep=instant_sleep, CancelledError=asyncio.CancelledError),
           '_wa_ignore_group_event': should_ignore_group_event,
           '_wa_policy': lambda: SimpleNamespace(
               observe=lambda e: observed.append(e), intercept=lambda e: None),
           'MessageType': SimpleNamespace(TEXT='text')}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[poll], type_ignores=[])),
                 '<actual-adapter-poll>', 'exec'), env)

    class PollStub:
        _poll_messages = env['_poll_messages']
        _http_session = True
        _running = True
        name = 'synthetic'

        async def _report_bridge_exit(self):
            return False

        @asynccontextmanager
        async def _bridge_req(self, *args):
            async def events():
                self._running = False
                return [{'isGroup': True, 'body': 'Noted.'},
                        {'isGroup': True, 'body': 'Gue standby.', 'hasQuotedMessage': True},
                        {'isGroup': True, 'body': 'hi'},
                        {'isGroup': True, 'body': 'Noted.', 'testAddressed': True},
                        {'isGroup': True, 'body': 'ini @synthetic-bot', 'testAddressed': True}]
            yield SimpleNamespace(status=200, json=events)

        def _message_mentions_bot(self, event):
            return event.get('testAddressed', False)

        def _message_matches_mention_patterns(self, event):
            return False

        def _clean_bot_mention_text(self, body, event):
            return body.replace('@synthetic-bot', '').strip()

        async def _build_message_event(self, event):
            return SimpleNamespace(message_type='text', text=event['body'])

        async def _send_read_receipt(self, event):
            receipts.append(event)

        def _enqueue_text_event(self, event):
            enqueued.append(event)

    async def ingress():
        await PollStub()._poll_messages()
        await asyncio.sleep(0)
    asyncio.run(ingress())
    assert [e['body'] for e in observed] == ['hi', 'Noted.', 'ini']
    assert [e.text for e in enqueued] == ['hi', 'Noted.', 'ini @synthetic-bot']
    assert len(receipts) == 3
    print('actual_source_send_poll_stubs=pass; normal_queued_crash_silence=pass; synthetic_canary=pass')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-repo', required=True, type=Path)
    verify_source(parser.parse_args().hermes_repo)


if __name__ == '__main__':
    main()
