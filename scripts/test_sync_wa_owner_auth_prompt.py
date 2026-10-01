"""Synthetic checks for the exact-anchor WhatsApp prompt mirror update."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from sync_wa_owner_auth_prompt import (
    SKILL_NEW, SKILL_OLD, SOUL_REPLACEMENTS, run, transform_skill, transform_soul,
)


class PromptMirrorSyncTests(unittest.TestCase):
    def test_exact_anchors_update_and_keep_unrelated_sections(self):
        old_soul = "# header\n" + "\n".join(old for old, _new in SOUL_REPLACEMENTS) + "\n## Other\nkeep me\n"
        new_soul = transform_soul(old_soul)
        self.assertTrue(all(new in new_soul for _old, new in SOUL_REPLACEMENTS))
        self.assertIn("## Other\nkeep me", new_soul)
        self.assertNotIn("decision is not visible to you", new_soul.lower())
        self.assertEqual(transform_soul(new_soul), new_soul)

        skill = "---\nname: opencode-relay\n---\n\n# Relay\n\n" + SKILL_OLD + "\n\nKeep this paragraph.\n"
        updated_skill = transform_skill(skill)
        self.assertIn(SKILL_NEW, updated_skill)
        self.assertIn("Keep this paragraph.", updated_skill)
        self.assertEqual(transform_skill(updated_skill), updated_skill)

    def test_apply_backs_up_privately_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / ".hermes"
            soul_path = home / "SOUL.md"
            skill_path = home / "skills" / "relay" / "opencode-relay" / "SKILL.md"
            skill_path.parent.mkdir(parents=True)
            soul_old = "\n".join(old for old, _new in SOUL_REPLACEMENTS) + "\n"
            skill_old = "---\nname: opencode-relay\n---\n" + SKILL_OLD + "\n"
            soul_path.write_text(soul_old, encoding="utf-8")
            skill_path.write_text(skill_old, encoding="utf-8")
            self.assertEqual(run(home, True), 0)
            self.assertIn("may add a system-only verdict", soul_path.read_text(encoding="utf-8"))
            self.assertIn("system-only verdict", skill_path.read_text(encoding="utf-8"))
            backup_dir = home / "backups" / "wa-owner-auth-prompt-sync"
            backups = list(backup_dir.iterdir())
            self.assertEqual(len(backups), 2)
            if os.name != "nt":
                self.assertEqual(backup_dir.stat().st_mode & 0o777, 0o700)
                self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in backups))
            self.assertEqual(run(home, True), 0)
            self.assertEqual(len(list(backup_dir.iterdir())), 2)


if __name__ == "__main__":
    unittest.main()
