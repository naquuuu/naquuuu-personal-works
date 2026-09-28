import asyncio
import unittest
from relay_runtime import retry_primary, vision_budget


class Guards(unittest.IsolatedAsyncioTestCase):
    async def test_retry_cap_and_backoff(self):
        calls, delays = [], []
        class Busy(Exception):
            status_code = 503
        async def call():
            calls.append(1)
            raise Busy('synthetic-secret-must-not-be-returned')
        async def sleep(delay):
            delays.append(delay)
        with self.assertRaises(Busy):
            await retry_primary(call, retries=99, sleep=sleep)
        self.assertEqual(len(calls), 3)
        self.assertEqual(delays, [1, 2])

    async def test_auth_not_retried(self):
        calls = []
        async def call():
            calls.append(1)
            raise ValueError('unauthorized')
        with self.assertRaises(ValueError):
            await retry_primary(call)
        self.assertEqual(len(calls), 1)

    async def test_budget_cancels(self):
        cancelled = []
        async def call():
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.append(True)
        with self.assertRaises(TimeoutError):
            await vision_budget(call, timeout=.01)
        self.assertEqual(cancelled, [True])

if __name__ == '__main__':
    unittest.main()
