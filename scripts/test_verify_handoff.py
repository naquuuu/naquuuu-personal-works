"""Unit tests for scripts/verify_handoff.py."""
import io
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import verify_handoff


class VerifyHandoffTests(unittest.TestCase):
    def test_valid_handoff_passes(self):
        text = """
### Result
Successfully implemented the sync validator.

### Files Changed
- scripts/verify_agent_sync.py
- tests/test_verify_agent_sync.py

### Evidence
pytest tests/ -v ran with 3 passed in 0.12s.

### Blockers
None.
"""
        ok, errors = verify_handoff.validate_handoff(text)
        self.assertTrue(ok, f"Expected pass, got: {errors}")
        self.assertEqual(len(errors), 0)

    def test_missing_block_fails(self):
        # Missing ### Blockers
        text = """
### Result
Implemented feature.

### Files Changed
- file.py

### Evidence
Tests passed.
"""
        ok, errors = verify_handoff.validate_handoff(text)
        self.assertFalse(ok)
        self.assertTrue(any("Missing required block: '### Blockers'" in e for e in errors))

    def test_empty_evidence_fails(self):
        text = """
### Result
Implemented feature.

### Files Changed
- file.py

### Evidence

### Blockers
None.
"""
        ok, errors = verify_handoff.validate_handoff(text)
        self.assertFalse(ok)
        self.assertTrue(any("Section '### Evidence' is empty" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
