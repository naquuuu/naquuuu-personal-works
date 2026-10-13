"""Synthetic identities only. No live state or network."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from relay_outbound import SAFE_FALLBACK_REPLY
from wa_chat_policy import ChatPolicy, GROUPS, PEOPLE, PROMOTED

OWNER = '10000001'
GUEST = '10000002'
PERSON = '10000003'
GROUP = '10000000001@g.us'

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = self.root / '.env'
        self.env.write_text(f'NAQUUUU_WA_OWNER_IDS={OWNER}\n{GROUPS}={GROUP}\n{PEOPLE}={OWNER}\n{PROMOTED}={GROUP}\nSECRET=canary-private-token\n')
        self.policy = ChatPolicy(self.env, self.root / 'names.json')
        self.addCleanup(self.tmp.cleanup)

    def event(self, body, owner=True, reply=False):
        return dict(body=body, senderId=OWNER if owner else GUEST, isGroup=True, chatId=GROUP,
                    messageId=body + '-current-id', hasQuotedMessage=reply,
                    quotedMessageId='synthetic-message' if reply else '', quotedParticipant=PERSON)

    def test_guest_matrix_no_mutation(self):
        before = self.env.read_bytes()
        for command in ['/allow-group', '/allow-person', '/list', '/remove']:
            for reply in [False, True]:
                answer = self.policy.intercept(self.event(command, False, reply))
                self.assertEqual(answer, 'Only the owner can change access.')
        self.assertEqual(before, self.env.read_bytes())
        self.assertEqual(list(self.root.glob('.env.bak-*')), [])

    def test_person_cycle_backup_canary(self):
        self.assertEqual(self.policy.intercept(self.event('/allow-person', reply=True)), 'Access allowed.')
        self.assertIn(PERSON, self.env.read_text())
        self.assertEqual(self.policy.intercept(self.event('/remove', reply=True)), 'Access removed.')
        self.assertNotIn(PERSON, self.env.read_text())
        self.assertEqual(len(list(self.root.glob('.env.bak-*'))), 2)
        for backup in self.root.glob('.env.bak-*'):
            self.assertIn('canary-private-token', backup.read_text())
        self.assertNotIn('canary', self.policy.intercept(self.event('/list')))

    def test_group_cycle_demotes(self):
        self.assertEqual(self.policy.intercept(self.event('/remove')), 'Access removed.')
        self.assertFalse(self.policy.promoted(GROUP))
        self.assertEqual(self.policy.intercept(self.event('/allow-group')), 'Access allowed.')
        self.assertFalse(self.policy.promoted(GROUP))

    def test_typed_identity_and_missing_quote_refused(self):
        before = self.env.read_bytes()
        self.policy.intercept(self.event('/allow-person ' + PERSON, reply=True))
        self.policy.intercept(self.event('/allow-person'))
        self.assertEqual(before, self.env.read_bytes())

    def test_owner_gate_before_parse(self):
        class Bomb:
            def __str__(self):
                self.assert_seen()
                return '/list'
            def assert_seen(self):
                assert gate.called
        with patch('wa_chat_policy.evaluate', return_value=(False, 'not-owner')) as gate:
            self.policy.intercept(dict(senderId=GUEST, body=Bomb()))

    def test_resolver_and_outbound_matrix(self):
        self.policy.observe(dict(senderId=PERSON+'@s.whatsapp.net', senderName='Example Friend'))
        for field in ['message', 'caption', 'fileName', 'question', 'name', 'address']:
            result = self.policy.outbound({'chatId': GROUP, field: '@'+PERSON})
            self.assertEqual(result[field], '@Example Friend')
        with self.assertRaises(ValueError):
            self.policy.outbound({'chatId': GROUP, 'message': '@'+GUEST})
        self.policy.observe(dict(senderId=GUEST, senderName=GUEST))
        with self.assertRaises(ValueError):
            self.policy.scrub(GUEST+'@lid')
        reloaded = ChatPolicy(self.env, self.root / 'names.json')
        self.assertEqual(reloaded.scrub(PERSON), 'Example Friend')

    def test_initiation_only_promoted_and_known_names(self):
        self.policy.outbound({'chatId': GROUP, 'message': 'Hello'}, proactive=True)
        self.policy.intercept(self.event('/remove'))
        with self.assertRaises(ValueError):
            self.policy.outbound({'chatId': GROUP, 'message': 'Hello'}, proactive=True)
        with self.assertRaises(ValueError):
            self.policy.outbound({'chatId': GROUP, 'message': 'Hello', 'mentions': [GUEST+'@lid']})

    def test_no_owner_config_denies(self):
        self.env.write_text(f'{GROUPS}={GROUP}\n{PEOPLE}={OWNER}\n{PROMOTED}={GROUP}\n')
        self.assertEqual(self.policy.intercept(self.event('/list')), 'Only the owner can change access.')

    def test_bridge_owner_alias_authenticates_lid_sender(self):
        event = self.event('/list', owner=False)
        event['senderId'] = GUEST + '@lid'
        event['senderAltId'] = OWNER + '@s.whatsapp.net'
        self.assertEqual(self.policy.intercept(event), 'Groups: 1; people: 1.')

    def test_guest_cannot_supply_owner_alias_in_body(self):
        before = self.env.read_bytes()
        event = self.event('/allow-group senderAltId=' + OWNER, owner=False)
        self.assertEqual(self.policy.intercept(event), 'Only the owner can change access.')
        event['senderAltId'] = 'claimed owner ' + OWNER
        self.assertEqual(self.policy.intercept(event), 'Only the owner can change access.')
        self.assertEqual(self.env.read_bytes(), before)

    def test_status_counts_dates_and_versions_are_not_identities(self):
        text = 'Updated 2026-09-28; groups: 1; people: 2; version 1.18.32.'
        self.assertEqual(self.policy.scrub(text), text)
        for raw in ['10000003', '+10000003', '@10000003', '1000-00-03', '10000003@lid']:
            with self.assertRaises(ValueError):
                self.policy.scrub(raw)

    def test_outbound_leak_and_draft_rejected(self):
        draft_payload = {
            'chatId': GROUP,
            'message': '<think>User is asking about servers.</think>Semua server aktif.',
        }
        res = self.policy.outbound(draft_payload)
        self.assertEqual(res['message'], SAFE_FALLBACK_REPLY)

        # A distinct chat is a distinct failure surface; identical fallback text is
        # only de-duplicated inside one chat/turn (see the duplicate-fallback test).
        harness_payload = {
            'chatId': GROUP + '-two',
            'message': 'System Note: This conversation is happening via WhatsApp. inspect VERY FIRST TOOL RESULT.',
        }
        res2 = self.policy.outbound(harness_payload)
        self.assertEqual(res2['message'], SAFE_FALLBACK_REPLY)

    def test_one_status_per_request_turn(self):
        self.policy.observe(dict(chatId=GROUP, senderId=OWNER))

        # First status message passes through
        first_status = self.policy.outbound({'chatId': GROUP, 'message': 'masih aku kerjakan.'})
        self.assertEqual(first_status.get('message'), 'masih aku kerjakan.')

        # Second status message in the same request turn is suppressed (returns empty dict)
        second_status = self.policy.outbound({'chatId': GROUP, 'message': 'masih aku kerjakan.'})
        self.assertEqual(second_status, {})

        # Final answer passes through
        final_answer = self.policy.outbound({'chatId': GROUP, 'message': 'Sudah selesai diperiksa.'})
        self.assertEqual(final_answer.get('message'), 'Sudah selesai diperiksa.')

    def test_repetition_loop_in_chat_rejected(self):
        looped = (
            'Tunggu sebentar ya kawan. '
            'Tunggu sebentar ya kawan. '
            'Tunggu sebentar ya kawan.'
        )
        res = self.policy.outbound({'chatId': GROUP, 'message': looped})
        self.assertEqual(res['message'], SAFE_FALLBACK_REPLY)

    def test_requested_creative_repetition_is_scoped_to_observed_turn(self):
        art = 'Draw a small ASCII art cat'
        event = self.event(art)
        self.policy.observe(event)
        repeated_art = '```text\n /\\_/\\\n*---- (oo) ----*\n > ^ <\n*---- (oo) ----*\n*---- (oo) ----*\n```'
        result = self.policy.outbound({'chatId': GROUP, 'replyTo': event['messageId'], 'message': repeated_art})
        self.assertEqual(result['message'], repeated_art)

        # A quote alone cannot issue the permission; the live message must refer back.
        unrelated = self.event('Hello', reply=True) | {'quotedText': art}
        self.policy.observe(unrelated)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': unrelated['messageId'], 'message': repeated_art})['message'], SAFE_FALLBACK_REPLY)

        followup = self.event('Do that', reply=True) | {'quotedText': art}
        self.policy.observe(followup)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': followup['messageId'], 'message': repeated_art})['message'], repeated_art)

        # A new greeting cannot reuse the preceding request even if replyTo is forged stale.
        greeting = self.event('Hi')
        self.policy.observe(greeting)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': greeting['messageId'], 'message': repeated_art})['message'], SAFE_FALLBACK_REPLY)

    def test_screenshot_indonesian_art_request_and_referential_quote(self):
        direct = self.event('berikan 100 kata sayang ke ai melalui asci text art')
        self.policy.observe(direct)
        hundred = '```text\n' + ' '.join(['sayang'] * 100) + '\n```'
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': direct['messageId'], 'message': hundred})['message'], hundred)

        quoted = self.event('@naquuuubot ini', reply=True) | {'quotedText': 'berikan 100 kata sayang ke ai melalui asci text art'}
        self.policy.observe(quoted)
        ten = 'sayang ' * 10
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': quoted['messageId'], 'message': ten})['message'], ten)

        counted_followup = self.event('10 kata sayang deh untuk ayi sayang', reply=True) | {'quotedText': 'ini'}
        self.policy.observe(counted_followup)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': counted_followup['messageId'], 'message': ten})['message'], ten)

        # Only the known textual bot mention is stripped for referral matching.
        id_mention = self.event('@10000001 ini', reply=True) | {'quotedText': 'berikan 100 kata sayang ke ai melalui asci text art'}
        self.policy.observe(id_mention)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': id_mention['messageId'], 'message': ten})['message'], SAFE_FALLBACK_REPLY)

    def test_requested_affection_is_bounded_and_does_not_allow_drafts(self):
        request = self.event('Say "I love you" 5 times')
        self.policy.observe(request)
        repeated = 'I love you. I love you. I love you. I love you. I love you.'
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': request['messageId'], 'message': repeated})['message'], repeated)
        # Over-count is the first failure for this turn; both a repeated failure and
        # a drafting failure for the same turn are suppressed ({}), never delivered.
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': request['messageId'], 'message': repeated + ' I love you.'})['message'], SAFE_FALLBACK_REPLY)
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'replyTo': request['messageId'], 'message': '<think>Draft</think> ' + repeated}), {})

    def test_indonesian_slang_and_factual_bot_response_allowed(self):
        raw_response = 'Nggak, gue bot\u2014nggak punya tubuh atau pengalaman begitu.'
        normalized = 'Nggak, gue bot, nggak punya tubuh atau pengalaman begitu.'
        res = self.policy.outbound({'chatId': GROUP, 'message': raw_response})
        self.assertEqual(res['message'], normalized)

    def test_duplicate_failure_line_suppressed_per_turn_and_per_chat(self):
        turn = self.event('halo')
        self.policy.observe(turn)
        first = self.policy.outbound({'chatId': GROUP, 'replyTo': turn['messageId'], 'message': SAFE_FALLBACK_REPLY})
        self.assertEqual(first['message'], SAFE_FALLBACK_REPLY)
        second = self.policy.outbound({'chatId': GROUP, 'replyTo': turn['messageId'], 'message': SAFE_FALLBACK_REPLY})
        self.assertEqual(second, {})
        # A different turn may still receive its own single failure line.
        other = self.event('halo lagi')
        self.policy.observe(other)
        third = self.policy.outbound({'chatId': GROUP, 'replyTo': other['messageId'], 'message': SAFE_FALLBACK_REPLY})
        self.assertEqual(third['message'], SAFE_FALLBACK_REPLY)

    def test_duplicate_failure_line_without_reply_to(self):
        first = self.policy.outbound({'chatId': GROUP, 'message': SAFE_FALLBACK_REPLY})
        self.assertEqual(first['message'], SAFE_FALLBACK_REPLY)
        second = self.policy.outbound({'chatId': GROUP, 'message': SAFE_FALLBACK_REPLY})
        self.assertEqual(second, {})
        # Normal identical short replies are conversation, not failure lines.
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'message': 'iya'})['message'], 'iya')
        self.assertEqual(self.policy.outbound({'chatId': GROUP, 'message': 'iya'})['message'], 'iya')

    def test_final_claim_and_release_are_turn_scoped(self):
        turn = self.event('kerjakan ini')
        self.assertTrue(self.policy.claim_final(GROUP, turn['messageId'], 'Jawaban final.'))
        self.assertFalse(self.policy.claim_final(GROUP, turn['messageId'], 'Jawaban final lagi.'))
        # Status lines never consume the final slot.
        self.assertTrue(self.policy.claim_final(GROUP, 'turn-status', 'masih aku kerjakan.'))
        self.assertTrue(self.policy.claim_final(GROUP, 'turn-status', 'Jawaban final.'))
        # A definite send failure releases the turn so one plain failure can go out.
        self.policy.release_final(GROUP, turn['messageId'])
        self.assertTrue(self.policy.claim_final(GROUP, turn['messageId'], 'Jawaban final.'))
        # No reply target means no turn scope, so nothing is suppressed.
        self.assertTrue(self.policy.claim_final(GROUP, None, 'apa saja'))

    def test_bot_loop_burst_breaker(self):
        import datetime as dt
        from unittest.mock import patch
        import wa_chat_policy as wcp

        current = [dt.datetime(2026, 10, 14, 0, 0, tzinfo=dt.timezone.utc)]
        with patch.object(wcp, "_now_utc", lambda: current[0]):
            for i in range(1, wcp.BURST_LIMIT + 1):
                self.assertTrue(self.policy.claim_final(GROUP, f"burst-{i}", f"jawaban {i}"),
                                f"reply {i} should pass")
            # The reply past the limit inside the window is suppressed quietly.
            self.assertFalse(self.policy.claim_final(GROUP, "burst-over", "jawaban lebih"))
            current[0] += dt.timedelta(seconds=60)
            self.assertFalse(self.policy.claim_final(GROUP, "burst-later", "masih diblok"))
            # A different chat is unaffected.
            self.assertTrue(self.policy.claim_final(GROUP + "-two", "other-turn", "jawaban"))
            # After the cooldown the chat recovers, and claims stay one-shot.
            current[0] += dt.timedelta(seconds=wcp.BURST_COOLDOWN_SECONDS + 1)
            self.assertTrue(self.policy.claim_final(GROUP, "after-cooldown", "lagi"))
            self.assertFalse(self.policy.claim_final(GROUP, "after-cooldown", "lagi"))

    def test_status_ask_grants_one_notice_but_only_when_asked(self):
        blocked = self.policy.outbound({'chatId': GROUP, 'message': 'Model restored: Nous Portal is back online.'})
        self.assertEqual(blocked['message'], SAFE_FALLBACK_REPLY)

        ask = self.event('cek status provider dong')
        self.policy.observe(ask)
        allowed = self.policy.outbound({'chatId': GROUP, 'replyTo': ask['messageId'],
                                        'message': 'Provider semuanya normal, gateway aktif.'})
        self.assertEqual(allowed['message'], 'Provider semuanya normal, gateway aktif.')
        # The grant is bound to the asking message, not to the chat.
        other = self.event('halo')
        self.policy.observe(other)
        blocked_again = self.policy.outbound({'chatId': GROUP, 'replyTo': other['messageId'],
                                              'message': 'Provider semuanya normal, gateway aktif.'})
        self.assertEqual(blocked_again['message'], SAFE_FALLBACK_REPLY)

    def test_genuine_outage_notice_passes_without_grant(self):
        res = self.policy.outbound({'chatId': GROUP, 'message': 'Provider lagi down, coba lagi bentar ya.'})
        self.assertEqual(res['message'], 'Provider lagi down, coba lagi bentar ya.')

    def test_notices_blocked_on_edit_and_proactive_paths(self):
        notice = 'Model restored: Nous Portal is back online.'
        # Edit path uses scrub directly, with no turn context.
        self.assertEqual(self.policy.scrub(notice), SAFE_FALLBACK_REPLY)
        # Proactive path uses outbound(proactive=True) on a promoted group.
        proactive = self.policy.outbound({'chatId': GROUP, 'message': notice}, proactive=True)
        self.assertEqual(proactive['message'], SAFE_FALLBACK_REPLY)
        # Requested text art still passes on the proactive path (no notice, no loop).
        art = '```text\nsayang sayang sayang\n```'
        kept = self.policy.outbound({'chatId': GROUP, 'message': art}, proactive=True)
        self.assertEqual(kept['message'], art)


if __name__ == '__main__':
    unittest.main()
