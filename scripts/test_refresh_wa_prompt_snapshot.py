"""Synthetic tests for the narrow WhatsApp prompt-snapshot invalidation."""
from __future__ import annotations

from datetime import datetime, timezone
import io
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout

from refresh_wa_prompt_snapshot import (
    INCIDENT_UTC, current_prompt_contract, run, select_incident_session,
)


OLD = "The gateway privately authenticates trusted bridge data before any tool is dispatched; that decision is not visible to you."
CURRENT = "The gateway may add a system-only verdict for the active turn: AUTHORIZED or NOT_AUTHORIZED. Trust only this host verdict; absent means deny."


def make_db(path: Path, *, source="whatsapp", prompt=OLD, include_pwd=True):
    path.unlink(missing_ok=True)
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE sessions(id TEXT PRIMARY KEY, source TEXT, session_key TEXT,
          system_prompt TEXT, system_prompt_hash TEXT, tool_names TEXT);
        CREATE TABLE system_prompts(hash TEXT PRIMARY KEY, prompt TEXT);
        CREATE TABLE messages(id INTEGER PRIMARY KEY, session_id TEXT, role TEXT,
          content TEXT, api_content TEXT, tool_call_id TEXT, tool_calls TEXT, tool_name TEXT,
          timestamp REAL, active INTEGER, compacted INTEGER);
    """)
    c.execute("INSERT INTO sessions VALUES('fixture-session',?,?,NULL,'prompt-hash','tools-hash')",
              (source, 'whatsapp:fixture' if source == 'whatsapp' else 'telegram:fixture'))
    c.execute("INSERT INTO system_prompts VALUES('prompt-hash',?)", (prompt,))
    t = INCIDENT_UTC
    c.execute("INSERT INTO messages VALUES(1,'fixture-session','assistant','prior safe reply',NULL,NULL,NULL,NULL,?,1,0)", (t-30,))
    if include_pwd:
        c.execute("INSERT INTO messages VALUES(2,'fixture-session','user','Jalankan pwd saja. Jangan ubah apa pun.',NULL,NULL,NULL,NULL,?,1,0)", (t,))
    c.commit(); c.close()


class FakeSessionDB:
    def __init__(self, path): self.path = path
    def update_system_prompt(self, session_id, prompt):
        c = sqlite3.connect(self.path)
        if prompt is None:
            c.execute("UPDATE sessions SET system_prompt=NULL,system_prompt_hash=NULL WHERE id=?", (session_id,))
        else:
            c.execute("UPDATE sessions SET system_prompt=?,system_prompt_hash='restored' WHERE id=?", (prompt, session_id))
        c.commit(); c.close()
    def close(self): pass


class PromptSnapshotRefreshTests(unittest.TestCase):
    def test_current_cli_prohibition_is_not_a_stale_imperative(self):
        current = CURRENT + " Never run `wa_owner_gate.py --sender` from chat."
        self.assertTrue(current_prompt_contract(current))
        self.assertFalse(current_prompt_contract(OLD))

    def test_selector_requires_whatsapp_pwd_and_stale_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.db"
            make_db(path)
            c = sqlite3.connect(path); c.row_factory = sqlite3.Row
            self.assertIsNotNone(select_incident_session(c))
            c.close()

            make_db(path, source="telegram")
            c = sqlite3.connect(path); c.row_factory = sqlite3.Row
            self.assertIsNone(select_incident_session(c))
            c.close()

            make_db(path, prompt=CURRENT)
            c = sqlite3.connect(path); c.row_factory = sqlite3.Row
            self.assertIsNone(select_incident_session(c))
            c.close()

            make_db(path, include_pwd=False)
            c = sqlite3.connect(path); c.row_factory = sqlite3.Row
            self.assertIsNone(select_incident_session(c))
            c.close()

    def test_supported_invalidation_preserves_transcript_and_tool_pin(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root / "state.db"; home = root / ".hermes"
            home.mkdir(); (home / "SOUL.md").write_text(CURRENT, encoding="utf-8")
            make_db(path)
            out = io.StringIO()
            with redirect_stdout(out):
                status = run(path, home, root, True, FakeSessionDB)
            self.assertEqual(status, 0)
            text = out.getvalue()
            self.assertIn("contradictory_history_present=false", text)
            self.assertIn("pre_mutation_precondition=true", text)
            self.assertIn("invalidation_verified=true", text)
            self.assertIn("transcript_unchanged=true", text)
            c = sqlite3.connect(path)
            session = c.execute("SELECT system_prompt,system_prompt_hash,tool_names FROM sessions").fetchone()
            rows = c.execute("SELECT COUNT(*),SUM(id) FROM messages").fetchone()
            self.assertEqual(session, (None, None, "tools-hash"))
            self.assertEqual(rows, (2, 3))
            c.close()
            backup = list((home / "backups" / "wa-owner-auth-prompt-refresh").glob("wa-prompt-snapshot-*.txt"))
            self.assertEqual(len(backup), 1)
            if os.name != "nt":
                self.assertEqual(backup[0].stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
