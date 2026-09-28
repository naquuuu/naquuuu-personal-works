"""Offline regression checks for Spotify fetch/cache/status boundaries."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import spotify_taste as taste


class SpotifyCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {
            "NAQUUUU_WORKSPACE": self.directory.name,
            "SPOTIFY_CLIENT_ID": "synthetic-client-canary",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_fetch_then_status_uses_snapshot_without_more_network(self):
        taste.save_token({"access_token": "synthetic-access-canary",
                          "refresh_token": "synthetic-refresh-canary",
                          "expires_at": time.time() + 3600})
        output = io.StringIO()
        with patch.object(taste, "_open_json", return_value={"items": []}) as request:
            with contextlib.redirect_stdout(output):
                self.assertEqual(taste.run_fetch(), 0)
            self.assertEqual(request.call_count, 8)
            cached = taste.snapshot_path().read_bytes()
            request.reset_mock()
            with contextlib.redirect_stdout(output):
                self.assertEqual(taste.run_status(), 0)
                self.assertEqual(taste.run_status(), 0)
            request.assert_not_called()
            self.assertEqual(taste.snapshot_path().read_bytes(), cached)
        self.assertIn("network:    not contacted", output.getvalue())
        self.assertNotIn("canary", output.getvalue())

    def test_expired_status_never_refreshes_or_prints_token_metadata(self):
        taste.save_token({"access_token": "synthetic-access-canary",
                          "refresh_token": "synthetic-refresh-canary",
                          "expires_at": 1, "scope": "synthetic-scope-canary"})
        output = io.StringIO()
        with patch.object(taste, "_open_json", side_effect=AssertionError("network")):
            with contextlib.redirect_stdout(output):
                self.assertEqual(taste.run_status(), 0)
        self.assertIn("token expired", output.getvalue())
        self.assertNotIn("canary", output.getvalue())

    def test_missing_auth_fails_fetch_without_network(self):
        with patch.object(taste, "_open_json", side_effect=AssertionError("network")):
            with self.assertRaisesRegex(taste.TasteError, "not authenticated"):
                taste.run_fetch()


if __name__ == "__main__":
    unittest.main()
