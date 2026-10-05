import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import patch
from scripts import hermes_agent_activity as activity

class ActivityTests(unittest.TestCase):
    def test_only_allowlisted_aggregate_fields_leave_host(self):
        canary = 'SYNTHETIC_PRIVATE_CANARY'
        agent = N(name='naquuuubot', status='active', tasks=2, tools=3,
                  files=1, errors=0, file_paths=[canary], description=canary)
        state = N(agents=[agent, N(name=canary)],
                  tasks=[{'status': 'pending', 'content': canary}],
                  edges=[{'label': canary}])
        with tempfile.NamedTemporaryFile() as f:
            with patch.object(activity.viz, 'resolve_session_file', return_value=Path(f.name)), \
                 patch.object(activity.viz, 'build_state', return_value=state):
                result = activity.summary(Path('.'))
        self.assertNotIn(canary, json.dumps(result))
        self.assertEqual(len(result['agents']), 1)
        self.assertEqual(result['tasks']['pending'], 1)

    def test_missing_telemetry_is_an_empty_state(self):
        with patch.object(activity.viz, 'resolve_session_file', side_effect=FileNotFoundError):
            self.assertFalse(activity.summary(Path('.'))['available'])

    def test_stale_snapshot_never_claims_active_work(self):
        agent = N(name='naquuuubot', status='active', tasks=0, tools=0, files=0, errors=0)
        state = N(agents=[agent], tasks=[], edges=[])
        source = N(stat=lambda: N(st_mtime=0))
        with patch.object(activity.viz, 'resolve_session_file', return_value=source), \
             patch.object(activity.viz, 'build_state', return_value=state):
            result = activity.summary(Path('.'))
        self.assertFalse(result['fresh'])
        self.assertEqual(result['agents'][0]['status'], 'idle')

if __name__ == '__main__':
    unittest.main()
