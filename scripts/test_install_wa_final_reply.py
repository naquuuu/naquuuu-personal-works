"""Synthetic tests for the request-scoped final-reply claim and its installer."""
import ast
import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
from install_wa_final_reply import MARKER, patch_adapter
from wa_chat_policy import ChatPolicy


SEND_FIXTURE = '''
class FixtureAdapter:
    async def send(self, chat_id, content, reply_to=None, metadata=None):
        """Format, chunk, and post a WhatsApp text reply."""
        if not content or not content.strip():
            return SendResult(success=True, message_id=None)
        chat_id = to_whatsapp_jid(chat_id)
        try:
            content = self.format_message(content)
            chunks = self.truncate_message(content, 4096)
            for idx, chunk in enumerate(chunks):
                payload = {"chatId": chat_id, "message": chunk}
                if reply_to and idx == 0:
                    payload["replyTo"] = reply_to
                result = await self._post_bridge_message("send", payload, timeout=30)
                if not result.success:
                    return SendResult(success=False, error="Delivery uncertain; automatic replay stopped",
                                      raw_response={"partial_overflow": True, "delivery_uncertain": True})
            return SendResult(success=True, message_id="ok")
        except Exception as e:
            return SendResult(success=False, error="Delivery uncertain; automatic replay stopped",
                              raw_response={"partial_overflow": True, "delivery_uncertain": True})

    async def edit_message(self, chat_id, message_id, content):
        return None
# The installed module imports _wa_policy elsewhere; this comment keeps that
# contract visible without executing an import inside the fixture.
'''


class FinalReplyPatchTests(unittest.TestCase):
    def test_patch_is_idempotent_and_ast_valid(self):
        patched = patch_adapter(SEND_FIXTURE)
        ast.parse(patched)
        self.assertIn(MARKER, patched)
        self.assertIn('claim_final(chat_id, reply_to, content)', patched)
        self.assertIn('release_final(chat_id, reply_to)', patched)
        self.assertEqual(patch_adapter(patched), patched)
        # The claim precedes every post; the release sits on both failure exits.
        self.assertLess(patched.index('claim_final'), patched.index('_post_bridge_message("send"'))
        self.assertEqual(patched.count('release_final(chat_id, reply_to)'), 2)

    def test_patch_refuses_drift(self):
        with self.assertRaises(ValueError):
            patch_adapter(SEND_FIXTURE.replace('chat_id = to_whatsapp_jid(chat_id)', 'chat_id = chat_id'))
        with self.assertRaises(ValueError):
            patch_adapter('class Nothing:\n    pass\n')
        with self.assertRaises(ValueError):
            patch_adapter(SEND_FIXTURE.replace('_wa', ''))

    def test_claim_suppresses_duplicates_and_releases_on_failure(self):
        patched = patch_adapter(SEND_FIXTURE)
        namespace = {'SendResult': SimpleNamespace, 'to_whatsapp_jid': lambda value: value}
        with tempfile.TemporaryDirectory() as tmp:
            policy = ChatPolicy(Path(tmp) / 'synthetic.env', Path(tmp) / 'names.json')
            namespace['_wa_policy'] = lambda: policy
            exec(compile(patched, '<fixture-send>', 'exec'), namespace)
            base = namespace['FixtureAdapter']

            class Stub(base):
                def __init__(self):
                    self.posted = []
                    self.fail_next = False

                def format_message(self, content):
                    return content

                def truncate_message(self, text, limit):
                    return [text[i:i + limit] for i in range(0, len(text), limit)]

                async def _post_bridge_message(self, path, payload, timeout):
                    if self.fail_next:
                        self.fail_next = False
                        return SimpleNamespace(success=False, error='synthetic failure')
                    self.posted.append(payload)
                    return SimpleNamespace(success=True, message_id='synthetic-out')

            async def exercise():
                stub = Stub()
                first = await stub.send('synthetic-chat', 'Jawaban final satu.', reply_to='turn-1')
                self.assertTrue(first.success)
                self.assertEqual(len(stub.posted), 1)
                # A duplicate attempt for the same inbound message is a no-op success.
                duplicate = await stub.send('synthetic-chat', 'Jawaban final satu.', reply_to='turn-1')
                self.assertTrue(duplicate.success)
                self.assertEqual(len(stub.posted), 1)
                # A new turn still sends.
                second = await stub.send('synthetic-chat', 'Jawaban final dua.', reply_to='turn-2')
                self.assertTrue(second.success)
                self.assertEqual(len(stub.posted), 2)
                # Status lines never consume the turn's final slot.
                await stub.send('synthetic-chat', 'masih aku kerjakan.', reply_to='turn-3')
                answered = await stub.send('synthetic-chat', 'Jawaban akhir tiga.', reply_to='turn-3')
                self.assertTrue(answered.success)
                self.assertEqual(len(stub.posted), 4)
                # A definite failure releases the turn so one more attempt can go out.
                stub.fail_next = True
                failed = await stub.send('synthetic-chat', 'Jawaban empat.', reply_to='turn-4')
                self.assertFalse(failed.success)
                retried = await stub.send('synthetic-chat', 'Jawaban empat, baris kedua.', reply_to='turn-4')
                self.assertTrue(retried.success)
                self.assertEqual(len(stub.posted), 5)
                # Sends without a reply target are never suppressed.
                await stub.send('synthetic-chat', 'Pesan proaktif.')
                await stub.send('synthetic-chat', 'Pesan proaktif.')
                self.assertEqual(len(stub.posted), 7)

            asyncio.run(exercise())


if __name__ == '__main__':
    unittest.main()
