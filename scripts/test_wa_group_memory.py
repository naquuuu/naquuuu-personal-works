"""Synthetic tests for the bounded group context memory (ADR-048). No live state."""
import datetime as dt
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from wa_group_memory import (
    BLOCK_CHARS,
    BLOCK_LABEL,
    MAX_MESSAGES,
    WINDOW_SECONDS,
    GroupMemory,
)

CHAT = "10000000001@g.us"
OTHER = "10000000002@g.us"


class FakeClock:
    def __init__(self):
        self.now = dt.datetime(2026, 10, 13, 12, 0, tzinfo=dt.timezone.utc)

    def advance(self, seconds):
        self.now += dt.timedelta(seconds=seconds)

    def __call__(self):
        return self.now


class GroupMemoryTests(unittest.TestCase):
    def make(self, enabled=True, chats=None, clock=None):
        return GroupMemory(enabled=enabled, chats=chats if chats is not None else {CHAT},
                           now_fn=clock or FakeClock())

    def test_default_off_stores_nothing(self):
        memory = GroupMemory()
        memory.record(CHAT, "halo semua")
        self.assertEqual(memory.counts(), {"windows": 0, "messages": 0})
        self.assertEqual(memory.render(CHAT), "")

    def test_scope_is_per_opted_in_chat(self):
        memory = self.make()
        memory.record(CHAT, "halo")
        memory.record(OTHER, "halo juga")
        self.assertTrue(memory.enabled_for(CHAT))
        self.assertFalse(memory.enabled_for(OTHER))
        self.assertEqual(memory.counts()["windows"], 1)

    def test_message_cap_evicts_oldest(self):
        memory = self.make()
        for i in range(MAX_MESSAGES + 5):
            memory.record(CHAT, f"pesan nomor {i}")
        self.assertEqual(memory.counts()["messages"], MAX_MESSAGES)
        block = memory.render(CHAT)
        self.assertNotIn("pesan nomor 0", block)
        self.assertIn(f"pesan nomor {MAX_MESSAGES + 4}", block)

    def test_ttl_eviction(self):
        clock = FakeClock()
        memory = self.make(clock=clock)
        memory.record(CHAT, "pesan lama")
        clock.advance(WINDOW_SECONDS + 1)
        memory.record(CHAT, "pesan baru")
        block = memory.render(CHAT)
        self.assertNotIn("pesan lama", block)
        self.assertIn("pesan baru", block)

    def test_identifier_redaction_and_resolved_names(self):
        memory = self.make()
        names = {"11111111": "Ana", "22222222": "Budi"}
        memory.record(CHAT, "hubungi @11111111 atau 22222222 dan +999888777666 ya", name="Ana", names=names)
        block = memory.render(CHAT)
        self.assertIn("Ana", block)
        self.assertIn("Budi", block)
        self.assertIn("seseorang", block)
        self.assertNotIn("999888777666", block)
        self.assertNotIn("11111111", block)

    def test_idle_statuses_and_empty_bodies_skipped(self):
        memory = self.make()
        for body in ("", "   ", "Noted.", "Gue standby."):
            memory.record(CHAT, body)
        self.assertEqual(memory.counts()["messages"], 0)

    def test_render_is_labelled_capped_and_skips_last(self):
        memory = self.make()
        memory.record(CHAT, "pesan satu", name="Ana")
        memory.record(CHAT, "pesan dua", name="Budi")
        memory.record(CHAT, "pesan tiga", name="Cici")
        block = memory.render(CHAT, skip_last=True)
        self.assertTrue(block.startswith(BLOCK_LABEL))
        self.assertIn("pesan satu", block)
        self.assertIn("pesan dua", block)
        self.assertNotIn("pesan tiga", block)
        self.assertLessEqual(len(block), BLOCK_CHARS)

    def test_long_message_truncated_within_budget(self):
        memory = self.make()
        memory.record(CHAT, "kata " * 400, name="Ana")
        block = memory.render(CHAT)
        self.assertLessEqual(len(block), BLOCK_CHARS)
        self.assertIn("...", block)

    def test_window_size_counts_messages(self):
        memory = self.make()
        self.assertEqual(memory.window_size(CHAT), 0)
        memory.record(CHAT, "satu")
        memory.record(CHAT, "dua")
        self.assertEqual(memory.window_size(CHAT), 2)
        self.assertEqual(memory.window_size(OTHER), 0)
        self.assertEqual(GroupMemory().window_size(CHAT), 0)

    def test_from_env_parsing(self):
        enabled = GroupMemory.from_env({"NAQUUUU_GROUP_MEMORY": "on", "NAQUUUU_GROUP_MEMORY_CHATS": CHAT + ",junk,999"})
        self.assertTrue(enabled.enabled)
        self.assertEqual(enabled.chats, {CHAT})
        self.assertEqual(enabled.invalid_chats, 2)
        off = GroupMemory.from_env({"NAQUUUU_GROUP_MEMORY_CHATS": CHAT})
        self.assertFalse(off.enabled)
        off_by_value = GroupMemory.from_env({"NAQUUUU_GROUP_MEMORY": "no", "NAQUUUU_GROUP_MEMORY_CHATS": CHAT})
        self.assertFalse(off_by_value.enabled)

    def test_from_env_file_parsing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                'export NAQUUUU_GROUP_MEMORY="true"\n'
                f"NAQUUUU_GROUP_MEMORY_CHATS='{CHAT}'\n"
                "OTHER=value\n",
                encoding="utf-8")
            memory = GroupMemory.from_env_file(env_file)
            self.assertTrue(memory.enabled)
            self.assertEqual(memory.chats, {CHAT})
            self.assertEqual(memory.invalid_chats, 0)
            self.assertFalse(GroupMemory.from_env_file(Path(tmp) / "missing.env").enabled)

    def test_check_cli_prints_counts_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(f"NAQUUUU_GROUP_MEMORY=on\nNAQUUUU_GROUP_MEMORY_CHATS={CHAT}\n", encoding="utf-8")
            result = subprocess.run([sys.executable, str(Path(__file__).parent / "wa_group_memory.py"),
                                     "--check", "--env-file", str(env_file)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("group_memory_enabled=on", result.stdout)
            self.assertIn("group_memory_chats=1", result.stdout)
            self.assertNotIn(CHAT, result.stdout)


class PolicyIntegrationTests(unittest.TestCase):
    def test_policy_records_and_injects_only_when_enabled(self):
        import tempfile
        from wa_chat_policy import ChatPolicy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enabled_env = root / "enabled.env"
            enabled_env.write_text(f"SECRET=canary\nNAQUUUU_GROUP_MEMORY=on\nNAQUUUU_GROUP_MEMORY_CHATS={CHAT}\n")
            disabled_env = root / "disabled.env"
            disabled_env.write_text("SECRET=canary\n")
            previous = dict(chatId=CHAT, messageId="m1", body="halo tim semua", senderId="11111111",
                            senderName="Ana", isGroup=True)
            current = dict(chatId=CHAT, messageId="m2", body="jadi kapan mulai?", senderId="22222222",
                           senderName="Budi", isGroup=True)
            policy = ChatPolicy(enabled_env, root / "names.json")
            policy.observe(previous)
            policy.observe(current)
            injected = policy.inject_group_context(CHAT, "jadi kapan mulai?")
            self.assertTrue(injected.endswith("jadi kapan mulai?"))
            self.assertIn("halo tim semua", injected)
            self.assertIn("Ana", injected)
            self.assertNotIn("jadi kapan mulai?", injected.split("\n\n")[0])
            self.assertEqual(policy.inject_group_context(OTHER, "halo"), "halo")
            off_policy = ChatPolicy(disabled_env, root / "names.json")
            off_policy.observe(previous)
            self.assertEqual(off_policy.inject_group_context(CHAT, "halo"), "halo")
            self.assertEqual(off_policy.group_memory.counts(), {"windows": 0, "messages": 0})

    def test_inject_diagnostics_are_counts_only(self):
        import tempfile
        from wa_chat_policy import ChatPolicy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_file = root / ".env"
            env_file.write_text(f"NAQUUUU_GROUP_MEMORY=on\nNAQUUUU_GROUP_MEMORY_CHATS={CHAT}\n")
            policy = ChatPolicy(env_file, root / "names.json")
            policy.observe(dict(chatId=CHAT, messageId="m1", body="halo tim semua",
                                senderId="11111111", senderName="Ana", isGroup=True))
            policy.observe(dict(chatId=CHAT, messageId="m2", body="rahasia ZZTOP jangan disebar",
                                senderId="22222222", senderName="Budi", isGroup=True))
            with self.assertLogs("wa_chat_policy", level="WARNING") as captured:
                policy.inject_group_context(CHAT, "pertanyaan rahasia")
            joined = " ".join(captured.output)
            self.assertIn("group_memory_diag inject window=2 block=1", joined)
            self.assertNotIn("ZZTOP", joined)
            self.assertNotIn("halo tim", joined)
            self.assertNotIn("pertanyaan rahasia", joined)


class InstallerPatchTests(unittest.TestCase):
    FIXTURE = '''
class Adapter:
    async def _build_message_event(self, data):
        try:
            body = data.get("body", "")
            metadata: Dict[str, Any] = {k: v for k, v in (
                ("whatsapp_native_type", str(data.get("nativeType") or "").strip()),
                ("whatsapp_native", native_metadata if isinstance(native_metadata, dict) else None),
            ) if v}
            # ``fromOwner`` = owner-typed inbound fromMe (gated by WHATSAPP_FORWARD_OWNER_MESSAGES at the bridge); surfaced as
            return body
        except Exception:
            return None

# The installed module wires _wa_policy through the chat policy patch.
'''

    def test_patch_is_idempotent_and_ast_valid(self):
        from install_wa_group_memory import MARKER, patch_adapter
        patched = patch_adapter(self.FIXTURE)
        self.assertIn(MARKER, patched)
        self.assertIn('inject_group_context(str(data.get("chatId") or ""), body)', patched)
        self.assertEqual(patch_adapter(patched), patched)
        # The injection lands before the owner prefix so that prefix stays at position 0.
        self.assertLess(patched.index('inject_group_context'), patched.index('``fromOwner``'))

    def test_patch_refuses_drift_and_missing_policy(self):
        from install_wa_group_memory import patch_adapter
        with self.assertRaises(ValueError):
            patch_adapter(self.FIXTURE.replace(') if v}', ') if documented}'))
        with self.assertRaises(ValueError):
            patch_adapter(self.FIXTURE.replace('_wa_policy', 'something_else'))


class ConfigWriteTests(unittest.TestCase):
    def test_enable_latest_writes_without_printing_the_id(self):
        import contextlib
        import io
        import tempfile
        from wa_group_memory import disable, enable_latest

        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("SECRET=canary\nOTHER=1\n")
            log = Path(tmp) / "bridge.log"
            log.write_text("noise\nchat 10000000001@g.us message\n10000000002@g.us later\n")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                result = enable_latest(env_path=str(env_file), bridge_log=str(log))
            self.assertIn("memory_config=written", result)
            self.assertNotIn("g.us", out.getvalue())
            content = env_file.read_text()
            self.assertIn("NAQUUUU_GROUP_MEMORY=on", content)
            self.assertIn("NAQUUUU_GROUP_MEMORY_CHATS=10000000002@g.us", content)
            self.assertIn("SECRET=canary", content)
            self.assertEqual(len(list(Path(tmp).glob(".env.bak-*"))), 1)
            enable_latest(env_path=str(env_file), bridge_log=str(log))
            self.assertEqual(env_file.read_text().count("NAQUUUU_GROUP_MEMORY_CHATS="), 1)
            result = disable(env_path=str(env_file))
            self.assertIn("disabled", result)
            content = env_file.read_text()
            self.assertNotIn("NAQUUUU_GROUP_MEMORY", content)
            self.assertIn("SECRET=canary", content)

    def test_enable_latest_without_group_is_a_noop(self):
        import tempfile
        from wa_group_memory import enable_latest

        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("SECRET=canary\n")
            log = Path(tmp) / "bridge.log"
            log.write_text("nothing here\n")
            result = enable_latest(env_path=str(env_file), bridge_log=str(log))
            self.assertEqual(result, "memory_config=no_group_found")
            self.assertEqual(env_file.read_text(), "SECRET=canary\n")
            self.assertFalse(list(Path(tmp).glob(".env.bak-*")))


if __name__ == "__main__":
    unittest.main()
