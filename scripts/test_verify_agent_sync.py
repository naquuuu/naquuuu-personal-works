"""Unit tests for scripts/verify_agent_sync.py."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import verify_agent_sync


class VerifyAgentSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.opencode_dir = self.root / ".opencode" / "agent"
        self.agy_dir = self.root / ".agents" / "agents"
        self.opencode_dir.mkdir(parents=True)
        self.agy_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_detects_missing_agy_agent(self):
        # OpenCode has builder, AGY is empty
        (self.opencode_dir / "naquuuu-builder.md").write_text(
            "---\nname: naquuuu-builder\n---\nBuilds things.\n", encoding="utf-8"
        )
        (self.root / "CLAUDE.md").write_text("Reference AGENTS.md", encoding="utf-8")
        
        ok, issues = verify_agent_sync.check_sync(self.root)
        self.assertFalse(ok)
        self.assertTrue(any("Missing in .agents/agents" in issue for issue in issues))

    def test_detects_missing_claude_md(self):
        # Both have builder, but CLAUDE.md is missing
        content = "---\nname: naquuuu-builder\n---\nBuilds things.\n"
        (self.opencode_dir / "naquuuu-builder.md").write_text(content, encoding="utf-8")
        (self.agy_dir / "naquuuu-builder.md").write_text(content, encoding="utf-8")

        ok, issues = verify_agent_sync.check_sync(self.root)
        self.assertFalse(ok)
        self.assertTrue(any("CLAUDE.md" in issue for issue in issues))

    def test_passes_when_all_surfaces_match(self):
        content = "---\nname: naquuuu-builder\n---\n## Before you act\nBuilds things.\n"
        (self.opencode_dir / "naquuuu-builder.md").write_text(content, encoding="utf-8")
        (self.agy_dir / "naquuuu-builder.md").write_text(content, encoding="utf-8")
        (self.root / "CLAUDE.md").write_text(
            "Reference AGENTS.md\nnaquuuu-builder\n### Result\n### Files Changed\n### Evidence\n### Blockers\n",
            encoding="utf-8",
        )

        ok, issues = verify_agent_sync.check_sync(self.root, expected_agents=["naquuuu-builder"])
        self.assertTrue(ok, f"Expected pass but got issues: {issues}")
        self.assertEqual(len(issues), 0)


if __name__ == "__main__":
    unittest.main()
